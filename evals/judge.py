"""
judge.py — Calibrated LLM-as-a-Judge for Presentation Evaluation.

Evaluates generated presentation slides against source text using a structured,
binary checklist Pydantic schema and position-bias mitigated pairwise comparison.
"""

import os
import json
import re
from typing import List, Dict, Any, Optional, Literal, Tuple
from pydantic import BaseModel, Field

try:
    from ppt_maker.core.schemas import MasterPlan, Slide
except ImportError:
    from schemas import MasterPlan, Slide


class SlideEvaluation(BaseModel):
    """Structured evaluation of a single slide against source material."""
    slide_number: int
    is_grounded_in_source: bool = Field(
        description="True if all metrics, facts, and substantive claims are strictly grounded in the source text with zero hallucination."
    )
    has_single_takeaway: bool = Field(
        description="True if the slide focuses on exactly one central insight or narrative takeaway."
    )
    free_of_filler_phrases: bool = Field(
        description="True if free of empty corporate buzzwords (e.g., 'leverage synergies', 'paradigm shift', 'best-in-class', 'moving forward')."
    )
    concise_and_punchy: bool = Field(
        description="True if copy is active, scannable, and free of dense walls of text."
    )
    criticism: Optional[str] = Field(
        default=None,
        description="Concise explanation of any failed criteria or improvement advice."
    )

    @property
    def score(self) -> float:
        """Normalized score between 0.0 and 1.0 based on passed criteria."""
        criteria = [
            self.is_grounded_in_source,
            self.has_single_takeaway,
            self.free_of_filler_phrases,
            self.concise_and_punchy,
        ]
        return sum(1.0 for c in criteria if c) / len(criteria)


class ComparisonVerdict(BaseModel):
    """Pairwise comparison result with position bias mitigation."""
    preferred_model: Literal['model_a', 'model_b', 'tie'] = Field(
        description="Winning candidate or tie."
    )
    score_a: float = Field(description="Normalized quality score for Candidate A (0.0 to 1.0).")
    score_b: float = Field(description="Normalized quality score for Candidate B (0.0 to 1.0).")
    reasoning: str = Field(description="Reasoning justifying the decision.")
    position_bias_detected: bool = Field(
        default=False,
        description="True if forward and reverse orders produced conflicting preferences."
    )


_JUDGE_SYSTEM_PROMPT = """\
You are an expert, calibrated Presentation Design Judge.
Evaluate the provided slide against the source material on four strict criteria:

1. is_grounded_in_source: All claims, numbers, metrics, and technical facts MUST be directly supported by or explicitly present in the source text. If the slide invents figures, features, or partnerships not in the source, set this to FALSE.
2. has_single_takeaway: The slide must present a single clear, cohesive message rather than bundling multiple disparate topics.
3. free_of_filler_phrases: Slide must NOT use empty corporate buzzwords or filler phrases like 'in order to', 'leverage synergy', 'paradigm shift', 'moving forward', 'best-in-class'.
4. concise_and_punchy: The slide copy must be punchy, scannable, active, and free of long paragraphs or walls of text.

Output ONLY a valid JSON object matching the SlideEvaluation schema.
"""


def _extract_json_text(text: str) -> str:
    """Extracts raw JSON string from LLM response text."""
    text = text.strip()
    match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if match:
        return match.group(1).strip()
    match = re.search(r'(\{[\s\S]*\})', text)
    if match:
        return match.group(1).strip()
    return text


def evaluate_slide(slide: Slide, source_text: str, client=None) -> SlideEvaluation:
    """
    Evaluates a single slide against the source material at temperature=0.0.
    """
    if client is None:
        try:
            from ppt_maker.core.api_keys import get_client
        except ImportError:
            from api_keys import get_client
        client, _ = get_client()

    if client is None:
        raise RuntimeError("No Gemini API key found. Set GEMINI_API_KEY in your environment or .env to run LLM judge evaluations.")

    slide_json = slide.model_dump_json(indent=2)
    prompt = (
        f"=== SOURCE MATERIAL ===\n"
        f"{source_text}\n\n"
        f"=== CANDIDATE SLIDE ===\n"
        f"{slide_json}\n\n"
        f"Evaluate this slide strictly against the criteria. Return JSON."
    )

    from google.genai import types
    response = client.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=[prompt],
        config=types.GenerateContentConfig(
            system_instruction=_JUDGE_SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.0,
            max_output_tokens=1000,
        )
    )

    raw_text = _extract_json_text(response.text)
    eval_dict = json.loads(raw_text)
    eval_dict['slide_number'] = slide.slide_number
    return SlideEvaluation(**eval_dict)


def evaluate_deck_judge(master_plan: MasterPlan, source_text: str, client=None) -> Dict[str, Any]:
    """
    Evaluates all slides in a MasterPlan using the calibrated judge.
    Returns composite metrics and per-slide results.
    """
    evaluations: List[SlideEvaluation] = []
    for slide in master_plan.slides:
        res = evaluate_slide(slide, source_text, client=client)
        evaluations.append(res)

    n = len(evaluations)
    if n == 0:
        return {"overall_judge_score": 0.0, "evaluations": []}

    grounded_rate = sum(1.0 for e in evaluations if e.is_grounded_in_source) / n
    single_takeaway_rate = sum(1.0 for e in evaluations if e.has_single_takeaway) / n
    filler_free_rate = sum(1.0 for e in evaluations if e.free_of_filler_phrases) / n
    punchy_rate = sum(1.0 for e in evaluations if e.concise_and_punchy) / n

    avg_score = sum(e.score for e in evaluations) / n
    overall_judge_score = round(avg_score * 100, 1)

    return {
        "overall_judge_score": overall_judge_score,
        "slide_count": n,
        "grounded_rate": round(grounded_rate, 3),
        "single_takeaway_rate": round(single_takeaway_rate, 3),
        "filler_free_rate": round(filler_free_rate, 3),
        "punchy_rate": round(punchy_rate, 3),
        "evaluations": [e.model_dump() for e in evaluations],
    }


_PAIRWISE_JUDGE_SYSTEM_PROMPT = """\
You are an impartial presentation judge comparing two candidate slide designs for the same content.
Review both candidates against the source text.
Choose which candidate is superior based on grounding, narrative clarity, aesthetic restraint, and conciseness.
Return JSON with fields:
- preferred: "candidate_1" | "candidate_2" | "tie"
- reasoning: short explanation
"""


def compare_slides(
    slide_a: Slide,
    slide_b: Slide,
    source_text: str,
    client=None
) -> ComparisonVerdict:
    """
    Compares two candidate slides with position bias mitigation.
    Executes symmetric forward (A, B) and reverse (B, A) queries.
    """
    if client is None:
        try:
            from ppt_maker.core.api_keys import get_client
        except ImportError:
            from api_keys import get_client
        client, _ = get_client()

    if client is None:
        raise RuntimeError("No Gemini API key found. Set GEMINI_API_KEY in your environment or .env to run pairwise comparisons.")

    from google.genai import types

    json_a = slide_a.model_dump_json(indent=2)
    json_b = slide_b.model_dump_json(indent=2)

    # 1. Forward pass: Candidate 1 = A, Candidate 2 = B
    prompt_fwd = (
        f"=== SOURCE TEXT ===\n{source_text}\n\n"
        f"=== CANDIDATE 1 ===\n{json_a}\n\n"
        f"=== CANDIDATE 2 ===\n{json_b}\n\n"
        f"Which candidate slide is superior? Return JSON."
    )
    resp_fwd = client.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=[prompt_fwd],
        config=types.GenerateContentConfig(
            system_instruction=_PAIRWISE_JUDGE_SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.0,
            max_output_tokens=600,
        )
    )
    data_fwd = json.loads(_extract_json_text(resp_fwd.text))
    pref_fwd = data_fwd.get("preferred")  # "candidate_1" -> A, "candidate_2" -> B, "tie"

    # 2. Reverse pass: Candidate 1 = B, Candidate 2 = A
    prompt_rev = (
        f"=== SOURCE TEXT ===\n{source_text}\n\n"
        f"=== CANDIDATE 1 ===\n{json_b}\n\n"
        f"=== CANDIDATE 2 ===\n{json_a}\n\n"
        f"Which candidate slide is superior? Return JSON."
    )
    resp_rev = client.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=[prompt_rev],
        config=types.GenerateContentConfig(
            system_instruction=_PAIRWISE_JUDGE_SYSTEM_PROMPT,
            response_mime_type="application/json",
            temperature=0.0,
            max_output_tokens=600,
        )
    )
    data_rev = json.loads(_extract_json_text(resp_rev.text))
    pref_rev = data_rev.get("preferred")  # "candidate_1" -> B, "candidate_2" -> A, "tie"

    # 3. Position bias reconciliation
    # Translate reverse pass into Model A/B space
    rev_choice_model = "model_b" if pref_rev == "candidate_1" else ("model_a" if pref_rev == "candidate_2" else "tie")
    fwd_choice_model = "model_a" if pref_fwd == "candidate_1" else ("model_b" if pref_fwd == "candidate_2" else "tie")

    position_bias = False
    if fwd_choice_model == rev_choice_model:
        preferred = fwd_choice_model
        reasoning = data_fwd.get("reasoning", "")
    else:
        position_bias = True
        # Resolve conflict via independent checklist evaluations
        eval_a = evaluate_slide(slide_a, source_text, client=client)
        eval_b = evaluate_slide(slide_b, source_text, client=client)
        if eval_a.score > eval_b.score:
            preferred = "model_a"
        elif eval_b.score > eval_a.score:
            preferred = "model_b"
        else:
            preferred = "tie"
        reasoning = (
            f"Positional bias detected (fwd={fwd_choice_model}, rev={rev_choice_model}). "
            f"Reconciled via checklist scores: Model A={eval_a.score:.2f}, Model B={eval_b.score:.2f}."
        )

    eval_a = evaluate_slide(slide_a, source_text, client=client)
    eval_b = evaluate_slide(slide_b, source_text, client=client)

    return ComparisonVerdict(
        preferred_model=preferred,
        score_a=eval_a.score,
        score_b=eval_b.score,
        reasoning=reasoning,
        position_bias_detected=position_bias,
    )


def calibrate_judge(calibration_dataset: List[Dict[str, Any]], client=None) -> Dict[str, Any]:
    """
    Runs judge against the pre-labeled ground truth calibration set.
    Asserts >= 90% alignment before automated benchmark usage.
    """
    total_checks = 0
    correct_checks = 0
    results = []

    for item in calibration_dataset:
        source_text = item["source_text"]
        slide = Slide(**item["slide"])
        expected = item["expected"]

        actual = evaluate_slide(slide, source_text, client=client)

        item_correct = 0
        fields = [
            "is_grounded_in_source",
            "has_single_takeaway",
            "free_of_filler_phrases",
            "concise_and_punchy",
        ]
        field_matches = {}
        for f in fields:
            total_checks += 1
            exp_val = expected[f]
            act_val = getattr(actual, f)
            match = (exp_val == act_val)
            if match:
                correct_checks += 1
                item_correct += 1
            field_matches[f] = {"expected": exp_val, "actual": act_val, "match": match}

        results.append({
            "id": item.get("id"),
            "slide_number": slide.slide_number,
            "accuracy": item_correct / len(fields),
            "fields": field_matches,
            "criticism": actual.criticism,
        })

    accuracy = correct_checks / total_checks if total_checks else 0.0
    passed = accuracy >= 0.90

    return {
        "accuracy": round(accuracy, 3),
        "accuracy_pct": f"{accuracy * 100:.1f}%",
        "passed": passed,
        "total_checks": total_checks,
        "correct_checks": correct_checks,
        "details": results,
    }
