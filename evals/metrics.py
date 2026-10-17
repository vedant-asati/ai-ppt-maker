"""
evals.metrics — Deterministic quality & telemetry metrics for AI Presentation Agency.

Computes 100% objective, deterministic metrics with zero LLM API dependency:
1. DOM Overflow Rate (Playwright container inspection)
2. Layout Monotony & Sequencing Penalty
3. Word Density & "Wall-of-Text" Detection
4. Content Block Richness & Diversity
5. System Telemetry & Token Cost Estimation
"""

from typing import List, Dict, Any, Optional, Set, Union
import re
try:
    from ppt_maker.core.schemas import MasterPlan, Slide
except ImportError:
    from schemas import MasterPlan, Slide


def _extract_slide_text(slide: Slide) -> str:
    """Extract all visible textual content from a Slide for word counting."""
    parts = []
    if slide.title:
        parts.append(slide.title)
    if slide.subtitle:
        parts.append(slide.subtitle)
    if slide.eyebrow:
        parts.append(slide.eyebrow)
    if slide.content_bullets:
        parts.extend(slide.content_bullets)
    if slide.content_blocks:
        for block in slide.content_blocks:
            b_type = getattr(block, 'block_type', '')
            if b_type == 'stat':
                parts.extend([str(getattr(block, 'value', '')), str(getattr(block, 'label', '')), str(getattr(block, 'context', '') or '')])
            elif b_type in ('pullquote', 'quote'):
                parts.extend([str(getattr(block, 'quote', '')), str(getattr(block, 'attribution', '') or '')])
            elif b_type == 'comparison':
                parts.extend([str(getattr(block, 'left_label', '')), str(getattr(block, 'right_label', ''))])
                parts.extend(getattr(block, 'left_items', []) or [])
                parts.extend(getattr(block, 'right_items', []) or [])
            elif b_type in ('steps', 'step'):
                steps = getattr(block, 'steps', []) or []
                labels = getattr(block, 'step_labels', []) or []
                parts.extend([str(s) for s in steps])
                parts.extend([str(l) for l in labels if l])
            elif b_type == 'callout':
                parts.append(str(getattr(block, 'text', '')))
            elif b_type == 'key_value':
                pairs = getattr(block, 'pairs', []) or []
                for p in pairs:
                    if isinstance(p, dict):
                        parts.extend([str(p.get('key', '')), str(p.get('val', '') or p.get('value', ''))])
                    else:
                        parts.extend([str(getattr(p, 'key', '')), str(getattr(p, 'val', '') or getattr(p, 'value', ''))])
            elif b_type == 'bullet':
                parts.extend(getattr(block, 'bullets', []) or [])
    return " ".join(filter(None, parts))


def calc_dom_overflow_rate(
    dom_audit_results: Optional[List[Union[Dict[str, Any], str]]],
    total_slides: int
) -> Dict[str, Any]:
    """
    Computes DOM overflow rate from Playwright DOM inspection results.
    
    Args:
        dom_audit_results: Either list of audit result dicts (from Renderer),
                           list of warning dicts, or list of string warnings.
        total_slides: Total number of slides in the deck.
    
    Returns:
        Dict with overflow_rate, overflow_slides, and total_overflow_instances.
    """
    if total_slides <= 0:
        return {
            "overflow_rate": 0.0,
            "overflow_slide_count": 0,
            "overflow_slides": [],
            "total_overflow_instances": 0,
            "passed": True
        }

    overflow_slides: Set[int] = set()
    total_overflow_instances = 0

    if dom_audit_results:
        for item in dom_audit_results:
            # Case A: Renderer audit format: {"slide_number": N, "warnings": [...]}
            if isinstance(item, dict):
                sn = item.get("slide_number") or item.get("slide")
                warnings = item.get("warnings", [])
                
                # Direct warning dictionary: {"type": "OVERFLOW", "slide": N, ...}
                if item.get("type") == "OVERFLOW" or "overflow" in str(item.get("message", "")).lower():
                    if sn is not None:
                        try:
                            overflow_slides.add(int(sn))
                        except (ValueError, TypeError):
                            pass
                    total_overflow_instances += 1
                
                # Nested warnings in slide audit
                for w in warnings:
                    w_msg = str(w.get("message", "") if isinstance(w, dict) else w).lower()
                    if "overflow" in w_msg or (isinstance(w, dict) and w.get("type") == "OVERFLOW"):
                        if sn is not None:
                            try:
                                overflow_slides.add(int(sn))
                            except (ValueError, TypeError):
                                pass
                        total_overflow_instances += 1
            
            # Case B: String warning: "[Slide 3] Card overflowed by 24px"
            elif isinstance(item, str):
                if "overflow" in item.lower():
                    total_overflow_instances += 1
                    match = re.search(r'\[(?:Slide\s+)?(\d+)\]|slide\s+(\d+)', item, re.IGNORECASE)
                    if match:
                        num = match.group(1) or match.group(2)
                        overflow_slides.add(int(num))

    sorted_overflow_slides = sorted(list(overflow_slides))
    overflow_count = len(sorted_overflow_slides)
    overflow_rate = round(overflow_count / total_slides, 4)

    return {
        "overflow_rate": overflow_rate,
        "overflow_slide_count": overflow_count,
        "overflow_slides": sorted_overflow_slides,
        "total_overflow_instances": total_overflow_instances,
        "passed": overflow_count == 0
    }


def calc_layout_monotony(master_plan: MasterPlan) -> Dict[str, Any]:
    """
    Computes layout sequence variety and penalties for consecutive identical layouts.
    
    A deck with 3 identical layouts in a row creates visual fatigue.
    """
    slides = getattr(master_plan, 'slides', [])
    total_slides = len(slides)
    if total_slides <= 1:
        return {
            "layouts": [s.layout_type for s in slides],
            "total_slides": total_slides,
            "unique_layouts": total_slides,
            "variety_ratio": 1.0,
            "consecutive_pairs": 0,
            "consecutive_triplets": 0,
            "monotony_score": 0.0,
            "passed": True
        }

    layouts = [s.layout_type for s in slides]
    unique_layouts = len(set(layouts))
    variety_ratio = round(unique_layouts / total_slides, 3)

    consecutive_pairs = 0
    consecutive_triplets = 0

    for i in range(total_slides - 1):
        if layouts[i] == layouts[i + 1]:
            consecutive_pairs += 1

    for i in range(total_slides - 2):
        if layouts[i] == layouts[i + 1] == layouts[i + 2]:
            consecutive_triplets += 1

    # Monotony penalty: normalized between 0.0 (high variety) and 1.0 (flat repetition)
    variety_deficit = max(0.0, 0.5 - variety_ratio)
    raw_penalty = (consecutive_triplets * 0.35) + (consecutive_pairs * 0.1) + (variety_deficit * 0.8)
    monotony_score = round(min(1.0, max(0.0, raw_penalty)), 3)

    return {
        "layouts": layouts,
        "total_slides": total_slides,
        "unique_layouts": unique_layouts,
        "variety_ratio": variety_ratio,
        "consecutive_pairs": consecutive_pairs,
        "consecutive_triplets": consecutive_triplets,
        "monotony_score": monotony_score,
        "passed": consecutive_triplets == 0 and monotony_score < 0.4
    }


def calc_word_density(master_plan: MasterPlan) -> Dict[str, Any]:
    """
    Computes per-slide and deck-level word density.
    
    Thresholds:
      - Sparse: < 15 words (unless cover/quote)
      - Optimal: 15 to 55 words (punchy, high-impact)
      - Dense: 56 to 80 words (starting to clutter)
      - Wall-of-Text: > 80 words (severe visual defect)
    """
    slides = getattr(master_plan, 'slides', [])
    total_slides = len(slides)
    if total_slides == 0:
        return {
            "total_words": 0,
            "avg_words_per_slide": 0.0,
            "min_words": 0,
            "max_words": 0,
            "per_slide": [],
            "optimal_density_rate": 0.0,
            "wall_of_text_count": 0,
            "passed": True
        }

    per_slide = []
    total_words = 0
    optimal_count = 0
    wall_of_text_count = 0

    for s in slides:
        text = _extract_slide_text(s)
        words = len(text.split())
        total_words += words

        layout = getattr(s, 'layout_type', 'generic')
        # Cover and quote slides naturally have fewer words
        if words > 80:
            status = "wall_of_text"
            wall_of_text_count += 1
        elif words > 55:
            status = "dense"
        elif words >= 15 or layout in ('cover', 'quote', 'stat'):
            status = "optimal"
            optimal_count += 1
        else:
            status = "sparse"

        per_slide.append({
            "slide_number": s.slide_number,
            "layout_type": layout,
            "word_count": words,
            "status": status
        })

    avg_words = round(total_words / total_slides, 1)
    word_counts = [item["word_count"] for item in per_slide]
    optimal_rate = round(optimal_count / total_slides, 3)

    return {
        "total_words": total_words,
        "avg_words_per_slide": avg_words,
        "min_words": min(word_counts) if word_counts else 0,
        "max_words": max(word_counts) if word_counts else 0,
        "per_slide": per_slide,
        "optimal_density_rate": optimal_rate,
        "wall_of_text_count": wall_of_text_count,
        "passed": wall_of_text_count == 0 and avg_words <= 60.0
    }


def calc_content_block_diversity(master_plan: MasterPlan) -> Dict[str, Any]:
    """
    Evaluates whether the presentation leverages structured content blocks
    (StatBlock, ComparisonBlock, PullQuoteBlock, StepBlock, etc.) vs. plain string bullets.
    """
    slides = getattr(master_plan, 'slides', [])
    total_slides = len(slides)
    if total_slides == 0:
        return {
            "slides_with_blocks": 0,
            "typed_blocks_coverage": 0.0,
            "block_type_counts": {},
            "diversity_score": 0.0,
            "passed": False
        }

    slides_with_blocks = 0
    block_type_counts: Dict[str, int] = {}

    for s in slides:
        blocks = getattr(s, 'content_blocks', None) or []
        if blocks:
            slides_with_blocks += 1
            for b in blocks:
                b_type = getattr(b, 'block_type', 'unknown')
                block_type_counts[b_type] = block_type_counts.get(b_type, 0) + 1

    coverage = round(slides_with_blocks / total_slides, 3)
    unique_types = len(block_type_counts)

    # Score out of 10: combination of coverage and type diversity
    type_bonus = min(3.0, unique_types * 0.75)
    coverage_score = coverage * 7.0
    diversity_score = round(min(10.0, coverage_score + type_bonus), 1)

    return {
        "slides_with_blocks": slides_with_blocks,
        "typed_blocks_coverage": coverage,
        "block_type_counts": block_type_counts,
        "unique_block_types": unique_types,
        "diversity_score": diversity_score,
        "passed": coverage >= 0.4
    }


def calc_system_telemetry(
    duration_s: float,
    token_usage: Optional[Dict[str, int]] = None,
    model_name: str = "gemini-3.1-flash-lite"
) -> Dict[str, Any]:
    """
    Calculates execution duration, token economics, and estimated API cost.
    
    Standard Pricing (Gemini 3.1 Flash Lite / 1.5 Flash):
      - Input:  $0.075 / 1,000,000 tokens
      - Output: $0.300 / 1,000,000 tokens
    """
    token_usage = token_usage or {}
    input_tokens = token_usage.get("input_tokens", 0)
    output_tokens = token_usage.get("output_tokens", 0)
    total_tokens = input_tokens + output_tokens

    # Default to Gemini 3.1 Flash Lite pricing
    rate_input = 0.075 / 1_000_000
    rate_output = 0.300 / 1_000_000

    estimated_cost = (input_tokens * rate_input) + (output_tokens * rate_output)
    throughput = round(total_tokens / duration_s, 1) if duration_s > 0 else 0.0

    return {
        "model_name": model_name,
        "duration_s": round(duration_s, 2),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "tokens_per_second": throughput,
        "estimated_cost_usd": round(estimated_cost, 6)
    }


def evaluate_master_plan_deterministic(
    master_plan: MasterPlan,
    dom_audit_results: Optional[List[Any]] = None,
    duration_s: float = 0.0,
    token_usage: Optional[Dict[str, int]] = None,
    model_name: str = "gemini-3.1-flash-lite"
) -> Dict[str, Any]:
    """
    Aggregates all deterministic quality dimensions into a unified scorecard.
    
    Weighted Composite Score (0-100):
      - DOM Overflow Score (30%): 100 * (1.0 - overflow_rate)
      - Layout Variety Score (25%): 100 * (1.0 - monotony_score)
      - Word Density Score (25%): 100 * optimal_density_rate
      - Content Block Diversity (20%): diversity_score * 10
    """
    total_slides = len(getattr(master_plan, 'slides', []))
    
    overflow = calc_dom_overflow_rate(dom_audit_results, total_slides)
    monotony = calc_layout_monotony(master_plan)
    density = calc_word_density(master_plan)
    diversity = calc_content_block_diversity(master_plan)
    telemetry = calc_system_telemetry(duration_s, token_usage, model_name=model_name)

    # Composite quality computation
    score_overflow = (1.0 - overflow["overflow_rate"]) * 30.0
    score_monotony = (1.0 - monotony["monotony_score"]) * 25.0
    score_density = density["optimal_density_rate"] * 25.0
    score_diversity = (diversity["diversity_score"] / 10.0) * 20.0

    composite_score = round(score_overflow + score_monotony + score_density + score_diversity, 1)

    # Determine letter grade
    if composite_score >= 85:
        grade = "A"
    elif composite_score >= 70:
        grade = "B"
    elif composite_score >= 55:
        grade = "C"
    elif composite_score >= 40:
        grade = "D"
    else:
        grade = "F"

    all_passed = bool(
        overflow["passed"] and
        monotony["passed"] and
        density["passed"] and
        composite_score >= 70.0
    )

    return {
        "composite_score": composite_score,
        "grade": grade,
        "all_passed": all_passed,
        "metrics": {
            "dom_overflow": overflow,
            "layout_monotony": monotony,
            "word_density": density,
            "content_diversity": diversity,
            "telemetry": telemetry
        }
    }
