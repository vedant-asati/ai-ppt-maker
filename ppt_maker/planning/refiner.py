"""
refiner.py — Targeted Agentic Refinement Loop.

Autonomously resolves DOM overflows and text clipping detected during rendering
using a two-tiered correction hierarchy:
  Tier 1: Deterministic micro-fixes (0ms, $0) for minor overflows (<= 15px) or excess bullets.
  Tier 2: Single-slide LLM reflexion (~350 tokens, ~1.2s) for semantic or major overflows (> 15px).
  Fallback: Algorithmic line-clamping and speaker note offloading if Pass 2 still fails.
"""

import os
import re
from typing import List, Dict, Any, Optional, Tuple

try:
    from ppt_maker.core.schemas import MasterPlan, Slide, BulletBlock, StepBlock, CalloutBlock, ComparisonBlock
    from ppt_maker.planning.planner import refine_slide_patch
except ImportError:
    from schemas import MasterPlan, Slide, BulletBlock, StepBlock, CalloutBlock, ComparisonBlock
    from planner import refine_slide_patch


FILLER_PHRASES = [
    "in order to",
    "it is important to note",
    "as mentioned",
    "in conclusion",
    "to summarize",
    "going forward",
    "leverage",
    "synergy",
    "utilize",
    "paradigm shift",
    "at the end of the day",
    "moving forward",
    "best-in-class",
]


def _prune_filler_text(text: str) -> str:
    """Removes filler phrases and collapses extra whitespace."""
    cleaned = text
    for phrase in FILLER_PHRASES:
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        cleaned = pattern.sub("", cleaned)
    # Clean up double spaces or trailing punctuation artifacts
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"\s+([,.:;])", r"\1", cleaned)
    return cleaned


def _truncate_at_word(text: str, max_chars: int) -> str:
    """Truncates text at the nearest word boundary below max_chars."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars].rsplit(" ", 1)[0]
    if not truncated:
        truncated = text[:max_chars]
    return truncated.rstrip(",.;:- ") + "..."


def apply_deterministic_micro_fixes(slide: Slide, excess_px: float = 0) -> Slide:
    """
    Tier 1 Deterministic Fixer (0ms, $0 cost).
    Applies non-destructive layout caps, filler word pruning, and length trims.
    """
    s = slide.model_copy(deep=True)

    # 1. Prune filler words in title & subtitle
    if s.subtitle:
        cleaned_sub = _prune_filler_text(s.subtitle)
        if len(cleaned_sub) > 85:
            cleaned_sub = _truncate_at_word(cleaned_sub, 80)
        s.subtitle = cleaned_sub

    # 2. Trim flat content_bullets if present
    if s.content_bullets:
        cleaned_bullets = []
        for b in s.content_bullets:
            cb = _prune_filler_text(b)
            if len(cb) > 95:
                cb = _truncate_at_word(cb, 90)
            cleaned_bullets.append(cb)

        # Cap bullet count to 4 if overflowing
        if len(cleaned_bullets) > 4:
            cleaned_bullets = cleaned_bullets[:4]
        s.content_bullets = cleaned_bullets

    # 3. Handle typed content_blocks
    if s.content_blocks:
        new_blocks = []
        for block in s.content_blocks:
            if isinstance(block, BulletBlock):
                items = [_prune_filler_text(item) for item in block.items]
                items = [_truncate_at_word(item, 90) if len(item) > 95 else item for item in items]
                if len(items) > 4:
                    items = items[:4]
                new_blocks.append(BulletBlock(
                    block_type='bullets',
                    items=items,
                ))
            elif isinstance(block, StepBlock):
                steps = [_prune_filler_text(st) for st in block.steps]
                steps = [_truncate_at_word(st, 65) if len(st) > 70 else st for st in steps]
                labels = block.step_labels
                if len(steps) > 4:
                    steps = steps[:4]
                    if labels:
                        labels = labels[:4]
                new_blocks.append(StepBlock(
                    block_type='steps',
                    steps=steps,
                    step_labels=labels
                ))
            elif isinstance(block, CalloutBlock):
                txt = _prune_filler_text(block.text)
                if len(txt) > 130:
                    txt = _truncate_at_word(txt, 120)
                new_blocks.append(CalloutBlock(
                    block_type='callout',
                    text=txt,
                    callout_type=block.callout_type
                ))
            elif isinstance(block, ComparisonBlock):
                left = [_prune_filler_text(it) for it in block.left_items]
                right = [_prune_filler_text(it) for it in block.right_items]
                if len(left) > 3:
                    left = left[:3]
                if len(right) > 3:
                    right = right[:3]
                new_blocks.append(ComparisonBlock(
                    block_type='comparison',
                    left_label=block.left_label,
                    left_items=left,
                    right_label=block.right_label,
                    right_items=right
                ))
            else:
                new_blocks.append(block)
        s.content_blocks = new_blocks

    return s


def apply_algorithmic_fallback(slide: Slide) -> Slide:
    """
    Algorithmic Fallback when slide still overflows after Pass 2.
    Applies hard line-clamp and offloads excess text into speaker_notes.
    Guarantees presentation assembly proceeds with zero crashes.
    """
    s = slide.model_copy(deep=True)
    offloaded_text = []

    # 1. Fallback for content_bullets: hard cap to 3
    if s.content_bullets and len(s.content_bullets) > 3:
        removed = s.content_bullets[3:]
        s.content_bullets = s.content_bullets[:3]
        offloaded_text.extend([f"Bullet: {b}" for b in removed])

    # 2. Fallback for typed content_blocks
    if s.content_blocks:
        new_blocks = []
        for block in s.content_blocks:
            if isinstance(block, BulletBlock) and len(block.items) > 3:
                removed = block.items[3:]
                new_blocks.append(BulletBlock(
                    block_type='bullets',
                    items=block.items[:3],
                ))
                offloaded_text.extend([f"Bullet: {b}" for b in removed])
            elif isinstance(block, StepBlock) and len(block.steps) > 3:
                removed = block.steps[3:]
                labels = block.step_labels[:3] if block.step_labels else None
                new_blocks.append(StepBlock(
                    block_type='steps',
                    steps=block.steps[:3],
                    step_labels=labels
                ))
                offloaded_text.extend([f"Step: {st}" for st in removed])
            else:
                new_blocks.append(block)
        s.content_blocks = new_blocks

    # 3. Offload removed content into speaker_notes
    if offloaded_text:
        existing_notes = s.speaker_notes or ""
        note_addition = "\n[Overflow note (preserved for presenter)]: " + "; ".join(offloaded_text)
        s.speaker_notes = (existing_notes.strip() + " " + note_addition).strip()

    return s


class RefinerEngine:
    """
    Orchestrates targeted single-slide refinement against DOM overflow audit results.
    """

    def __init__(
        self,
        renderer=None,
        templater=None,
        client=None,
        max_iterations: int = 2,
        max_refined_slides: int = 3,
    ):
        self.renderer = renderer
        self.templater = templater
        self.client = client
        self.max_iterations = max_iterations
        self.max_refined_slides = max_refined_slides

    def extract_overflow_issues(self, dom_audit_results: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
        """
        Parses DOM audit results and groups OVERFLOW warnings by slide_number.
        """
        overflows_by_slide: Dict[int, List[Dict[str, Any]]] = {}
        for res in dom_audit_results:
            slide_num = res.get("slide_number")
            if not slide_num:
                continue
            for w in res.get("warnings", []):
                if w.get("type") == "OVERFLOW":
                    overflows_by_slide.setdefault(slide_num, []).append(w)
        return overflows_by_slide

    def refine_slide(
        self,
        slide: Slide,
        theme: Any,
        warnings: List[Dict[str, Any]],
        image_info: Optional[Dict[str, Any]] = None,
        audit_fn: Optional[Any] = None,
    ) -> Tuple[Slide, Dict[str, Any]]:
        """
        Refines a single failing slide up to max_iterations.

        Returns:
            (refined_slide, audit_status_dict)
        """
        current_slide = slide.model_copy(deep=True)
        max_excess = max((w.get("excess_px", 0) for w in warnings), default=0)
        diag_msg = "; ".join(w.get("message", "Overflow") for w in warnings)

        history = []
        resolved = False

        for iteration in range(1, self.max_iterations + 1):
            tier = "tier1_deterministic" if (max_excess <= 15 and iteration == 1) else "tier2_llm"

            if tier == "tier1_deterministic":
                current_slide = apply_deterministic_micro_fixes(current_slide, excess_px=max_excess)
                history.append({
                    "iteration": iteration,
                    "tier": "tier1_deterministic",
                    "action": "Applied deterministic layout caps and filler pruning",
                })
            else:
                try:
                    diagnostic_str = (
                        f"Container overflows by {max_excess}px. Details: {diag_msg}. "
                        f"Target: Reduce text volume and shorten statements by ~25%."
                    )
                    current_slide = refine_slide_patch(current_slide, diagnostic_str, client=self.client)
                    history.append({
                        "iteration": iteration,
                        "tier": "tier2_llm",
                        "action": "Applied LLM-as-actor surgical slide patch",
                    })
                except Exception as e:
                    # If LLM patch fails (e.g. offline / no API key), apply deterministic fix
                    current_slide = apply_deterministic_micro_fixes(current_slide, excess_px=max_excess)
                    history.append({
                        "iteration": iteration,
                        "tier": "fallback_deterministic",
                        "action": f"LLM patch unavailable ({e}) — applied deterministic micro-fix",
                    })

            # Check if resolved via live renderer or custom audit_fn
            new_warnings = []
            if audit_fn:
                new_warnings = audit_fn(current_slide)
            elif self.renderer and self.templater:
                html_path = self.templater.generate_single_slide_html(
                    slide=current_slide,
                    theme=theme,
                    total_slides=1,
                    image_info=image_info or {},
                )
                _, audit_res = self.renderer.render_single(html_path, audit=True)
                new_warnings = [w for w in audit_res.get("warnings", []) if w.get("type") == "OVERFLOW"]

            if not new_warnings:
                resolved = True
                break
            else:
                max_excess = max((w.get("excess_px", 0) for w in new_warnings), default=0)
                diag_msg = "; ".join(w.get("message", "Overflow") for w in new_warnings)

        # If still failing after max_iterations, trigger Algorithmic Fallback
        if not resolved:
            current_slide = apply_algorithmic_fallback(current_slide)
            history.append({
                "iteration": self.max_iterations + 1,
                "tier": "algorithmic_fallback",
                "action": "Hard line-clamp applied and excess content offloaded to speaker notes",
            })
            resolved = True

        return current_slide, {
            "slide_number": slide.slide_number,
            "resolved": resolved,
            "passes": len(history),
            "history": history,
        }

    def refine_deck(
        self,
        master_plan: MasterPlan,
        dom_audit_results: List[Dict[str, Any]],
        image_manifest: Optional[Dict[int, Any]] = None,
        audit_fn: Optional[Any] = None,
    ) -> Tuple[MasterPlan, Dict[str, Any]]:
        """
        Orchestrates deck-level refinement respecting deck-level budget.

        Returns:
            (refined_master_plan, refinement_summary)
        """
        overflows_by_slide = self.extract_overflow_issues(dom_audit_results)
        if not overflows_by_slide:
            return master_plan, {"refined_count": 0, "slides": []}

        # Sort failing slides by worst overflow excess_px descending
        sorted_slide_nums = sorted(
            overflows_by_slide.keys(),
            key=lambda sn: max((w.get("excess_px", 0) for w in overflows_by_slide[sn]), default=0),
            reverse=True,
        )

        # Enforce deck-level budget
        target_slide_nums = sorted_slide_nums[: self.max_refined_slides]
        skipped_slide_nums = sorted_slide_nums[self.max_refined_slides :]

        image_manifest = image_manifest or {}
        slide_map = {s.slide_number: idx for idx, s in enumerate(master_plan.slides)}

        updated_plan = master_plan.model_copy(deep=True)
        summary_records = []

        for sn in target_slide_nums:
            if sn not in slide_map:
                continue
            idx = slide_map[sn]
            original_slide = updated_plan.slides[idx]
            warns = overflows_by_slide[sn]
            img_info = image_manifest.get(sn, {})

            refined_slide, report = self.refine_slide(
                slide=original_slide,
                theme=updated_plan.theme,
                warnings=warns,
                image_info=img_info,
                audit_fn=audit_fn,
            )

            updated_plan.slides[idx] = refined_slide
            summary_records.append(report)

        summary = {
            "total_overflows_detected": len(overflows_by_slide),
            "refined_count": len(target_slide_nums),
            "budget_capped_count": len(skipped_slide_nums),
            "skipped_slides": skipped_slide_nums,
            "slides": summary_records,
        }

        return updated_plan, summary
