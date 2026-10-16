"""
content_scorer.py — Real-time slide content quality scoring.

Scores individual slides across 5 dimensions and returns structured feedback.
Used by the Validator to optionally print per-slide scores, and by the
QualityChecker for detailed reporting.

Scoring is purely heuristic — no API calls.
"""

from typing import List, Tuple
from dataclasses import dataclass, field


@dataclass
class SlideScore:
    slide_number: int
    title: str
    layout_type: str
    total: int                          # 0–50
    max_score: int = 50
    dimensions: dict = field(default_factory=dict)   # {dim: (score, note)}
    flags: List[str] = field(default_factory=list)   # short actionable flags

    @property
    def grade(self) -> str:
        pct = self.total / self.max_score * 100
        if pct >= 94: return 'A+'
        if pct >= 88: return 'A'
        if pct >= 75: return 'B'
        if pct >= 60: return 'C'
        if pct >= 45: return 'D'
        return 'F'

    @property
    def pct(self) -> float:
        return self.total / self.max_score * 100


# ─────────────────────────────────────────────────────────────────────────────
# Filler phrases to detect in titles + bullets
# ─────────────────────────────────────────────────────────────────────────────
_FILLER_IN_TITLE = [
    'introduction', 'overview', 'conclusion', 'summary', 'agenda',
    'thank you', 'questions', 'q&a', 'about us', 'the end',
]
_FILLER_IN_BULLETS = [
    'in order to', 'it is important', 'it should be noted', 'as mentioned',
    'moving forward', 'going forward', 'leverage', 'synergy', 'utilize',
    'paradigm', 'bandwidth', 'circle back', 'low-hanging fruit',
    'value add', 'best of breed',
]
_WEAK_VERBS = ['is', 'are', 'was', 'were', 'has', 'have']


class ContentScorer:

    def score_slide(self, slide) -> SlideScore:
        """Score a single slide across 5 dimensions (10 pts each = 50 max)."""
        dims = {}
        flags = []

        # ── 1. Title quality (10 pts) ─────────────────────────────────────
        title_score, title_note, title_flags = self._score_title(slide.title, slide.layout_type)
        dims['title'] = (title_score, title_note)
        flags.extend(title_flags)

        # ── 2. Content substance (10 pts) ─────────────────────────────────
        sub_score, sub_note, sub_flags = self._score_content(slide)
        dims['content'] = (sub_score, sub_note)
        flags.extend(sub_flags)

        # ── 3. Visual intent (10 pts) ─────────────────────────────────────
        vis_score, vis_note, vis_flags = self._score_visual(slide)
        dims['visual'] = (vis_score, vis_note)
        flags.extend(vis_flags)

        # ── 4. Metadata completeness (10 pts) ─────────────────────────────
        meta_score, meta_note, meta_flags = self._score_metadata(slide)
        dims['metadata'] = (meta_score, meta_note)
        flags.extend(meta_flags)

        # ── 5. Speaker notes (10 pts) ─────────────────────────────────────
        notes_score, notes_note, notes_flags = self._score_notes(slide)
        dims['speaker_notes'] = (notes_score, notes_note)
        flags.extend(notes_flags)

        total = sum(v[0] for v in dims.values())
        return SlideScore(
            slide_number=slide.slide_number,
            title=slide.title,
            layout_type=slide.layout_type,
            total=total,
            dimensions=dims,
            flags=flags,
        )

    def score_all(self, master_plan) -> List[SlideScore]:
        return [self.score_slide(s) for s in master_plan.slides]

    def deck_summary(self, scores: List[SlideScore]) -> dict:
        if not scores:
            return {}
        total    = sum(s.total for s in scores)
        max_s    = sum(s.max_score for s in scores)
        avg      = total / len(scores)
        weakest  = min(scores, key=lambda s: s.total)
        strongest = max(scores, key=lambda s: s.total)
        return {
            'total': total, 'max': max_s,
            'avg': avg, 'count': len(scores),
            'weakest_slide': weakest.slide_number,
            'weakest_score': weakest.total,
            'strongest_slide': strongest.slide_number,
            'strongest_score': strongest.total,
            'grade': self._grade(total / max_s * 100),
        }

    # ─────────────────────────────────────────────────────────────────────
    # Dimension scorers
    # ─────────────────────────────────────────────────────────────────────

    def _score_title(self, title: str, layout: str) -> Tuple[int, str, List[str]]:
        score = 10
        note  = 'Good'
        flags = []
        t = (title or '').strip()

        if not t or t.lower().startswith('slide '):
            return 0, 'Missing/generic', ['Title is missing or generic (e.g. "Slide 1")']

        # Filler title words
        tl = t.lower()
        for phrase in _FILLER_IN_TITLE:
            if phrase == tl or tl.startswith(phrase + ' ') or tl.endswith(' ' + phrase):
                score -= 4
                flags.append(f'Title "{t}" is a generic category label — be specific')
                break

        # Length checks
        words = t.split()
        if len(words) > 10:
            score -= 2
            flags.append(f'Title has {len(words)} words — aim for ≤8')
        elif len(words) < 2 and layout != 'cover':
            score -= 2
            flags.append('Title is very short — add a key detail')

        # Passive title check (starts with "The" or noun-only)
        if tl.startswith('the ') and len(words) <= 4:
            score -= 1
            flags.append('Title starts with "The" + noun — try a verb-led alternative')

        # Specific > vague: bonus for containing a number or proper noun
        has_number = any(c.isdigit() for c in t)
        has_caps   = sum(1 for w in words if w[0].isupper()) >= 2
        if has_number or has_caps:
            score = min(10, score + 1)

        return max(0, score), note if score == 10 else f'{score}/10', flags

    def _score_content(self, slide) -> Tuple[int, str, List[str]]:
        score = 0
        flags = []
        layout = slide.layout_type

        # Layouts that intentionally have no content body
        light_layouts = {'cover', 'quote', 'stat'}

        if slide.content_blocks:
            score = 7   # Base: has typed blocks
            block_types = {b.block_type for b in slide.content_blocks}

            # Bonus for using non-bullet blocks (real content richness)
            non_bullet = block_types - {'bullets'}
            if non_bullet:
                score += 2
            # Bonus for mixing 2+ different block types (content diversity)
            if len(block_types) >= 2:
                score = min(10, score + 1)

            # Penalty for too many bullet items
            for block in slide.content_blocks:
                if block.block_type == 'bullets':
                    items = block.items or []
                    if len(items) > 5:
                        score -= 2
                        flags.append(f'{len(items)} bullets — max 5 for readability')
                    # Check for filler in bullets
                    for item in items:
                        for phrase in _FILLER_IN_BULLETS:
                            if phrase in item.lower():
                                score -= 1
                                flags.append(f'Bullet contains filler: "{phrase}"')
                                break
                    # Check for long bullets
                    long = [i for i in items if len(i) > 130]
                    if long:
                        score -= 1
                        flags.append(f'{len(long)} bullet(s) exceed 130 chars')

        elif slide.content_bullets:
            score = 5   # Has content but legacy flat bullets
            if layout not in light_layouts:
                flags.append('Using flat bullets — consider typed content_blocks for richer design')
            n = len(slide.content_bullets)
            if n > 5:
                score -= 2
                flags.append(f'{n} bullets — cap at 5')

        elif layout in light_layouts:
            score = 10  # Light layout intentionally blank is perfect

        else:
            score = 0
            flags.append('Slide has no content — add content_blocks or content_bullets')

        return max(0, min(10, score)), f'{score}/10', flags

    def _score_visual(self, slide) -> Tuple[int, str, List[str]]:
        score = 0
        flags = []
        layout = slide.layout_type

        # Layouts that are visually self-contained (don't need images to look good)
        _SELF_CONTAINED = {'stat', 'timeline', 'infographic', 'quote'}

        # 1. Layout appropriateness (5 pts)
        if layout in ('cover', 'split', 'stat', 'quote', 'timeline', 'infographic', 'generic'):
            score += 5
        else:
            flags.append(f'Unknown layout "{layout}"')

        # 2. Image intent (3 pts)
        if slide.requires_image:
            prompt = (slide.image_prompt or '').strip()
            if len(prompt) >= 40:
                score += 3   # Detailed prompt
            elif len(prompt) >= 15:
                score += 2
            else:
                score += 2   # User-supplied images don't need long prompts
        elif layout in _SELF_CONTAINED:
            # Self-contained layouts are designed to look great without images
            score += 3
        elif not slide.requires_image:
            # Slide was designed without an image — this is intentional
            score += 2
        else:
            score += 1

        # 3. Layout variant (bonus)
        if getattr(slide, 'layout_variant', None):
            score = min(10, score + 1)

        # 4. Eyebrow label (bonus)
        if getattr(slide, 'eyebrow', None):
            score = min(10, score + 1)

        # 5. Subtitle adds visual hierarchy (bonus)
        if getattr(slide, 'subtitle', None):
            score = min(10, score + 1)

        return min(10, score), f'{min(10,score)}/10', flags

    def _score_metadata(self, slide) -> Tuple[int, str, List[str]]:
        score = 0
        flags = []

        # Layouts that correctly omit images
        _NO_IMAGE_OK = {'stat', 'timeline', 'infographic', 'quote'}

        # slide_purpose
        purpose = getattr(slide, 'slide_purpose', None)
        if purpose:
            score += 3
        else:
            flags.append('Missing slide_purpose — helps structure narrative arc')

        # narrative_weight
        weight = getattr(slide, 'narrative_weight', None)
        if weight:
            score += 2
        else:
            flags.append('Missing narrative_weight (light/standard/heavy)')

        # eyebrow label
        eyebrow = getattr(slide, 'eyebrow', None)
        if eyebrow:
            score += 3
        else:
            flags.append('Missing eyebrow label — helps audience track their place in the story')

        # image_role (if requires_image) OR layout-appropriate bonus
        if slide.requires_image:
            role = getattr(slide, 'image_role', None)
            if role in ('background', 'supporting', 'data', 'decorative'):
                score += 2
            else:
                flags.append('image_role should be: background | supporting | data | decorative')
        elif not slide.requires_image:
            # Image was correctly omitted by design
            score += 2

        return min(10, score), f'{min(10,score)}/10', flags

    def _score_notes(self, slide) -> Tuple[int, str, List[str]]:
        notes = (slide.speaker_notes or '').strip()
        flags = []

        if not notes:
            return 0, '0/10 — missing', ['No speaker notes — add 3–5 sentences of presenter script']

        words = notes.split()
        wc = len(words)

        if wc >= 30:
            score = 10
        elif wc >= 20:
            score = 8
        elif wc >= 12:
            score = 6
        elif wc >= 8:
            score = 4
            flags.append(f'Speaker notes are short ({wc} words) — aim for 25–50 words')
        else:
            score = 2
            flags.append(f'Speaker notes are very short ({wc} words) — add presenter context')

        # Penalty for notes that just repeat the title
        if slide.title.lower() in notes.lower() and wc < 20:
            score = max(0, score - 2)
            flags.append('Speaker notes appear to restate the title — add unique context')

        return score, f'{score}/10', flags

    @staticmethod
    def _grade(pct: float) -> str:
        if pct >= 94: return 'A+'
        if pct >= 88: return 'A'
        if pct >= 75: return 'B'
        if pct >= 60: return 'C'
        if pct >= 45: return 'D'
        return 'F'


def score_and_print(master_plan, verbose: bool = False) -> List[SlideScore]:
    """
    Convenience function: score all slides and print a summary table.
    Returns scores list.
    """
    scorer = ContentScorer()
    scores = scorer.score_all(master_plan)
    summary = scorer.deck_summary(scores)

    if not scores:
        return scores

    bar_w = 20
    print(f"\n  Content Quality Scores:")
    print(f"  {'Slide':<6} {'Title':<32} {'Layout':<12} {'Score':>6}  {'Grade'}")
    print(f"  {'-'*6} {'-'*32} {'-'*12} {'-'*6}  {'-'*5}")
    for s in scores:
        bar_filled = int(s.pct / 100 * bar_w)
        bar = '█' * bar_filled + '░' * (bar_w - bar_filled)
        short_title = s.title[:30] + ('…' if len(s.title) > 30 else '')
        print(f"  {s.slide_number:<6} {short_title:<32} {s.layout_type:<12} {s.total:>3}/50  {s.grade}")
        if verbose and s.flags:
            for flag in s.flags[:3]:
                print(f"         ↳ {flag}")

    avg = summary.get('avg', 0)
    grade = summary.get('grade', '?')
    weakest = summary.get('weakest_slide', '?')
    print(f"\n  Average: {avg:.1f}/50 — Grade {grade}  |  Weakest: Slide {weakest}")
    print()

    return scores
