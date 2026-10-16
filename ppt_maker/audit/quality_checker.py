"""
quality_checker.py — Design quality audit orchestrator.

Runs three audit layers and produces design_audit.md:

Layer 1 (DOM)   — Reads cached dom_audit.json from Playwright DOM injection
Layer 2 (PIL)   — Image quality checks via image_validator.py
Layer 3 (Score) — Deck-level design scoring heuristics

Optional Layer 4 (AI) — Asks Gemini to review a rendered slide image
"""

import os
import json
from typing import List, Optional
from datetime import datetime

try:
    from ppt_maker.core.schemas import MasterPlan
    from ppt_maker.imaging.image_validator import ImageValidator, ImageIssue
except ImportError:
    from schemas import MasterPlan
    from image_validator import ImageValidator, ImageIssue


# ─────────────────────────────────────────────────────────────────────────────
# Content scorer — deck-level design heuristics
# ─────────────────────────────────────────────────────────────────────────────

def _score_deck(master_plan: MasterPlan) -> dict:
    """
    Score the deck across 7 design quality dimensions.
    Returns a dict: {dimension: (score, notes)}
    """
    slides = master_plan.slides
    n = len(slides)
    if n == 0:
        return {}

    scores = {}

    # 1. Layout Variety (0–10) — scale-aware
    layouts = [s.layout_type for s in slides]
    unique_layouts = len(set(layouts))
    if n <= 7:
        variety_score = min(10, unique_layouts * 2)  # 5 unique = 10/10
    else:
        # For 8+ slides, need more variety for full marks
        target = 7 if n >= 13 else 5
        variety_score = min(10, int(unique_layouts / target * 10))
    # Penalty for consecutive same layouts
    consecutive_penalty = 0
    if n >= 8:
        # Stricter: penalize 2-consecutive for long decks
        for i in range(len(layouts) - 1):
            if layouts[i] == layouts[i+1]:
                consecutive_penalty += 1
    else:
        # Standard: only penalize 3-consecutive
        for i in range(len(layouts) - 2):
            if layouts[i] == layouts[i+1] == layouts[i+2]:
                consecutive_penalty += 1
    variety_score = max(0, variety_score - consecutive_penalty * 2)
    scores['layout_variety'] = (variety_score, f"{unique_layouts}/{n} unique layouts")

    # 2. Content Block Richness (0–10)
    slides_with_blocks = sum(1 for s in slides if s.content_blocks)
    richness_pct = slides_with_blocks / n
    richness_score = int(richness_pct * 10)
    block_types_used = set()
    for s in slides:
        if s.content_blocks:
            for b in s.content_blocks:
                block_types_used.add(b.block_type)
    type_bonus = min(2, len(block_types_used) - 1) if block_types_used else 0
    richness_score = min(10, richness_score + type_bonus)
    scores['content_richness'] = (
        richness_score,
        f"{slides_with_blocks}/{n} slides use typed blocks; {len(block_types_used)} block types"
    )

    # 3. Narrative Density Balance (0–10)
    light_slides = sum(1 for s in slides if s.narrative_weight == 'light')
    light_pct = light_slides / n
    # Ideal: 20–35% light slides
    if 0.2 <= light_pct <= 0.35:
        density_score = 10
    elif 0.1 <= light_pct < 0.2 or 0.35 < light_pct <= 0.5:
        density_score = 7
    elif light_pct == 0:
        density_score = 3
    else:
        density_score = 5
    scores['narrative_density'] = (density_score, f"{light_slides}/{n} slides are 'light'")

    # 4. Eyebrow Label Usage (0–10)
    eyebrow_count = sum(1 for s in slides if s.eyebrow)
    eyebrow_pct = eyebrow_count / n
    eyebrow_score = int(eyebrow_pct * 10)
    scores['eyebrow_usage'] = (eyebrow_score, f"{eyebrow_count}/{n} slides have eyebrow labels")

    # 5. Image Coverage (0–10)
    requires_image = sum(1 for s in slides if s.requires_image)
    img_pct = requires_image / n
    # Ideal: 40–70% of slides have images
    if 0.4 <= img_pct <= 0.7:
        img_score = 10
    elif 0.3 <= img_pct < 0.4 or 0.7 < img_pct <= 0.8:
        img_score = 7
    elif img_pct < 0.2:
        img_score = 4
    else:
        img_score = 6
    scores['image_coverage'] = (img_score, f"{requires_image}/{n} slides request images")

    # 6. Bullet Quality (0–10) — penalize long bullets and excessive counts
    all_bullets = []
    for s in slides:
        all_bullets.extend(s.content_bullets or [])
    if all_bullets:
        avg_len = sum(len(b) for b in all_bullets) / len(all_bullets)
        long_bullets = sum(1 for b in all_bullets if len(b) > 150)
        bullet_score = 10
        if avg_len > 120:
            bullet_score -= 3
        if long_bullets > 0:
            bullet_score -= min(3, long_bullets)
        bullet_score = max(0, bullet_score)
        scores['bullet_quality'] = (
            bullet_score,
            f"{len(all_bullets)} bullets total, avg {avg_len:.0f} chars, {long_bullets} too long"
        )
    else:
        scores['bullet_quality'] = (10, "No flat bullets used (using typed blocks ✓)")

    # 7. Speaker Notes Completeness (0–10)
    notes_ok = sum(
        1 for s in slides
        if s.speaker_notes and len(s.speaker_notes.split()) >= 20
    )
    notes_score = int((notes_ok / n) * 10)
    scores['speaker_notes'] = (notes_score, f"{notes_ok}/{n} slides have substantive speaker notes")

    return scores


# ─────────────────────────────────────────────────────────────────────────────
# QualityChecker
# ─────────────────────────────────────────────────────────────────────────────

class QualityChecker:

    def run_audit(
        self,
        slides_dir: str,
        master_plan: MasterPlan,
        config,
        level: str = 'full',             # 'quick' | 'full' | 'ai'
        dom_cache_path: Optional[str] = None,
        output_path: str = 'design_audit.md',
    ):
        """
        Run the full audit pipeline and write a design_audit.md report.
        """
        print(f"QualityChecker: Running level='{level}' audit...")
        all_warnings = []
        all_info = []
        image_issues: List[ImageIssue] = []
        deck_scores = {}

        # ── Layer 1: DOM audit (from cached json) ─────────────────────────
        dom_results = []
        if dom_cache_path and os.path.exists(dom_cache_path):
            try:
                with open(dom_cache_path, 'r') as f:
                    dom_results = json.load(f)
                for result in dom_results:
                    sn = result.get('slide_number', '?')
                    for w in result.get('warnings', []):
                        all_warnings.append({'slide': sn, 'layer': 'DOM', **w})
                    for info in result.get('info', []):
                        all_info.append({'slide': sn, 'layer': 'DOM', **info})
                print(f"  Layer 1 (DOM): {len(dom_results)} slides checked")
            except Exception as e:
                print(f"  Layer 1 (DOM): Could not read cache: {e}")
        else:
            print(f"  Layer 1 (DOM): No cache — run with --audit flag during generate")

        # ── Layer 2: Image quality (PIL) ──────────────────────────────────
        if level in ('full', 'ai'):
            validator = ImageValidator()
            # Build a quick manifest from slides_dir
            manifest = {}
            for slide in master_plan.slides:
                img_path = os.path.join('assets', f"slide_{slide.slide_number}.png")
                if os.path.exists(img_path):
                    manifest[slide.slide_number] = {'path': img_path}
            image_issues = validator.validate_all(manifest)
            print(f"  Layer 2 (PIL): {len(manifest)} images checked, {len(image_issues)} issues")

        # ── Layer 3: Deck scoring ─────────────────────────────────────────
        deck_scores = _score_deck(master_plan)
        total_score = sum(v[0] for v in deck_scores.values()) if deck_scores else 0
        max_score   = len(deck_scores) * 10
        score_pct   = (total_score / max_score * 100) if max_score else 0
        print(f"  Layer 3 (Score): {total_score}/{max_score} ({score_pct:.0f}%)")

        # ── Layer 4: AI review (optional) ────────────────────────────────
        ai_feedback = ''
        if level == 'ai':
            ai_feedback = self._ai_review(slides_dir, master_plan)

        # ── Write report ──────────────────────────────────────────────────
        self._write_report(
            output_path=output_path,
            master_plan=master_plan,
            dom_warnings=all_warnings,
            image_issues=image_issues,
            deck_scores=deck_scores,
            ai_feedback=ai_feedback,
            level=level,
        )
        print(f"  Audit report saved → {output_path}")

    def _ai_review(self, slides_dir: str, master_plan: MasterPlan) -> str:
        """Ask Gemini Flash to review the first 3 slides visually."""
        try:
            from ppt_maker.core.api_keys import get_api_keys, get_client
        except ImportError:
            from api_keys import get_api_keys, get_client
        keys = get_api_keys()
        if not keys:
            return "_AI review skipped — no API keys set._"
        try:
            from PIL import Image
            import io

            client, _ = get_client(0)

            # Pick up to 3 rendered PNGs
            pngs = sorted([
                f for f in os.listdir(slides_dir) if f.endswith('.png')
            ])[:3]

            if not pngs:
                return "_AI review skipped — no rendered slides found._"

            # Combine into one tall review strip
            images = []
            for f in pngs:
                try:
                    with Image.open(os.path.join(slides_dir, f)) as img:
                        images.append(img.copy())
                except Exception:
                    pass
            if not images:
                return "_AI review skipped — could not open rendered slides._"
            combined_w = max(i.width for i in images)
            combined_h = sum(i.height for i in images)
            strip = Image.new('RGB', (combined_w, combined_h), (30, 30, 30))
            y = 0
            for img in images:
                strip.paste(img, (0, y))
                y += img.height
                img.close()

            buf = io.BytesIO()
            strip.save(buf, format='PNG')
            buf.seek(0)

            prompt = (
                f"You are a senior slide designer reviewing a presentation.\n"
                f"Theme: {master_plan.theme.structural_class} / palette: {master_plan.theme.palette or 'AI-colored'}\n\n"
                f"Review these rendered slides (up to 3 shown). For each, provide:\n"
                f"1. Visual hierarchy: Is the reading order clear?\n"
                f"2. Whitespace: Is there breathing room or is it cluttered?\n"
                f"3. Typography: Are sizes proportional and readable?\n"
                f"4. Color usage: Does the accent color create contrast?\n"
                f"5. One specific improvement suggestion.\n\n"
                f"Keep each review under 80 words. Be direct and actionable."
            )

            # Upload strip
            uploaded = client.files.upload(
                file=buf,
                config={'mime_type': 'image/png'},
            )
            response = client.models.generate_content(
                model='gemini-3.1-flash-lite',
                contents=[prompt, uploaded],
            )
            try:
                client.files.delete(name=uploaded.name)
            except Exception:
                pass

            return response.text or "_AI review returned empty response._"

        except Exception as e:
            return f"_AI review failed: {e}_"

    def _write_report(
        self,
        output_path: str,
        master_plan: MasterPlan,
        dom_warnings: list,
        image_issues: List[ImageIssue],
        deck_scores: dict,
        ai_feedback: str,
        level: str,
    ):
        lines = [
            f"# Design Audit Report",
            f"",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"Audit Level: `{level}`  ",
            f"Theme: `{master_plan.theme.structural_class}`"
            + (f" / `{master_plan.theme.palette}`" if master_plan.theme.palette else ""),
            f"Slides: {len(master_plan.slides)}",
            f"",
        ]

        # ── Score summary ─────────────────────────────────────────────────
        if deck_scores:
            total = sum(v[0] for v in deck_scores.values())
            max_s = len(deck_scores) * 10
            pct = total / max_s * 100
            grade = 'A' if pct >= 85 else 'B' if pct >= 70 else 'C' if pct >= 55 else 'D'
            lines += [
                f"## Overall Score: {total}/{max_s} ({pct:.0f}%) — Grade {grade}",
                f"",
                f"| Dimension | Score | Notes |",
                f"|-----------|-------|-------|",
            ]
            for dim, (score, notes) in deck_scores.items():
                bar = '█' * score + '░' * (10 - score)
                lines.append(f"| {dim.replace('_', ' ').title()} | {score}/10 `{bar}` | {notes} |")
            lines.append("")

        # ── Layer 1: DOM warnings ─────────────────────────────────────────
        lines.append("## Layer 1 — DOM Audit")
        if dom_warnings:
            lines.append("")
            by_type: dict = {}
            for w in dom_warnings:
                t = w.get('type', 'UNKNOWN')
                by_type.setdefault(t, []).append(w)
            for wtype, items in by_type.items():
                lines.append(f"### {wtype} ({len(items)} occurrences)")
                for item in items[:5]:
                    lines.append(f"- Slide {item.get('slide', '?')}: {item.get('message', item)}")
                if len(items) > 5:
                    lines.append(f"- _(+{len(items)-5} more)_")
            lines.append("")
        else:
            lines.append("")
            lines.append("_No DOM issues detected (or no cached data)._")
            lines.append("")

        # ── Layer 2: Image issues ─────────────────────────────────────────
        lines.append("## Layer 2 — Image Quality")
        if image_issues:
            lines.append("")
            errors   = [i for i in image_issues if i.severity == 'error']
            warnings = [i for i in image_issues if i.severity == 'warning']
            if errors:
                lines.append(f"### Errors ({len(errors)})")
                for issue in errors:
                    lines.append(f"- **Slide {issue.slide_number}** `{issue.issue_type}`: {issue.message}")
            if warnings:
                lines.append(f"### Warnings ({len(warnings)})")
                for issue in warnings:
                    lines.append(f"- Slide {issue.slide_number} `{issue.issue_type}`: {issue.message}")
            lines.append("")
        else:
            lines.append("")
            lines.append("_All images passed quality checks._")
            lines.append("")

        # ── Slide-level detail ────────────────────────────────────────────
        lines += ["## Slide-by-Slide Summary", ""]
        lines += [
            "| # | Title | Layout | Blocks | Image | Eyebrow | Speaker Notes |",
            "|---|-------|--------|--------|-------|---------|---------------|",
        ]
        for slide in master_plan.slides:
            block_types = (
                ', '.join(set(b.block_type for b in slide.content_blocks))
                if slide.content_blocks else '—'
            )
            img_str  = f"✓ ({slide.image_role or 'bg'})" if slide.requires_image else '—'
            eyebrow  = slide.eyebrow or '—'
            notes_wc = len((slide.speaker_notes or '').split())
            notes_str = f"{notes_wc}w {'✓' if notes_wc >= 20 else '⚠'}"
            lines.append(
                f"| {slide.slide_number} | {slide.title[:35]}{'…' if len(slide.title)>35 else ''} "
                f"| `{slide.layout_type}` | {block_types} | {img_str} | {eyebrow} | {notes_str} |"
            )
        lines.append("")

        # ── AI Feedback ───────────────────────────────────────────────────
        if ai_feedback:
            lines += ["## Layer 4 — AI Design Review", "", ai_feedback, ""]

        # ── Recommendations ───────────────────────────────────────────────
        recommendations = self._build_recommendations(
            deck_scores, dom_warnings, image_issues, master_plan
        )
        if recommendations:
            lines += ["## Recommendations", ""]
            for i, rec in enumerate(recommendations, 1):
                lines.append(f"{i}. {rec}")
            lines.append("")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def _build_recommendations(
        self,
        deck_scores: dict,
        dom_warnings: list,
        image_issues: List[ImageIssue],
        master_plan: MasterPlan,
    ) -> List[str]:
        recs = []

        if deck_scores:
            for dim, (score, notes) in deck_scores.items():
                if score < 5:
                    if dim == 'layout_variety':
                        recs.append(
                            "**Layout variety is low.** Add `split`, `stat`, or `quote` slides "
                            "to create visual rhythm."
                        )
                    elif dim == 'content_richness':
                        recs.append(
                            "**Typed content blocks are underused.** Ask the Planner to use "
                            "`StatBlock`, `PullQuoteBlock`, or `ComparisonBlock` instead of flat bullets."
                        )
                    elif dim == 'narrative_density':
                        recs.append(
                            "**No breathing room slides.** Add 1–2 `stat` or `quote` layout slides "
                            "with `narrative_weight: light` to prevent cognitive overload."
                        )
                    elif dim == 'eyebrow_usage':
                        recs.append(
                            "**Eyebrow labels missing.** Add short category labels (e.g. 'Problem', "
                            "'Phase 2', 'Key Insight') to help the audience track their place in the story."
                        )
                    elif dim == 'image_coverage':
                        recs.append(
                            "**Low image coverage.** Set `requires_image: true` for cover and split "
                            "slides to make the deck more visually engaging."
                        )
                    elif dim == 'bullet_quality':
                        recs.append(
                            "**Bullets are too long.** Keep each bullet under 120 characters. "
                            "Split long points into two bullets or move detail to speaker notes."
                        )
                    elif dim == 'speaker_notes':
                        recs.append(
                            "**Speaker notes are thin.** Each slide should have 3–5 sentences "
                            "of presenter script. Notes should add context not visible on the slide."
                        )

        # DOM warning recommendations
        dom_types = set(w.get('type') for w in dom_warnings)
        if 'OVERFLOW' in dom_types:
            recs.append(
                "**Text overflow detected.** Some slides have content that exceeds the slide boundary. "
                "Reduce bullet count or shorten the title."
            )
        if 'FONT_TOO_SMALL' in dom_types:
            recs.append(
                "**Font size too small.** Some text elements are below 12px. "
                "Increase `--type-body` or reduce content density on affected slides."
            )

        # Image issue recommendations
        img_types = set(i.issue_type for i in image_issues)
        if 'TOO_DARK' in img_types:
            recs.append(
                "**Some images are too dark.** For dark-theme slides, ensure the image has "
                "enough contrast in the text overlay zone. Consider using the gradient fallback."
            )
        if 'CENTER_CLUTTERED' in img_types:
            recs.append(
                "**Image center is too busy.** Background images should keep the center 40% clear "
                "for text overlay. Regenerate with: 'keep center clear for text overlay' in the prompt."
            )

        return recs
