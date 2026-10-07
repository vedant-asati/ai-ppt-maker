from schemas import MasterPlan, BulletBlock
from typing import List

# INT-09: layouts that benefit from panel/decorative images (module-level constants)
_PANEL_LAYOUTS   = frozenset({'generic', 'infographic', 'timeline'})
_SPLIT_LAYOUTS   = frozenset({'split'})
_IMAGE_OPTIONAL  = frozenset({'cover'})   # cover handles its own image in cover.html
_DECOR_LAYOUTS   = frozenset({'stat', 'quote'})

# Layout-specific bullet caps: how many bullets actually render in each template
_LAYOUT_BULLET_CAPS = {
    'cover':       0,  # cover template renders no bullets at all
    'split':       4,  # right panel has limited vertical space
    'infographic': 3,  # infographic cards hold 3 main points
    'generic':     6,  # full-width text column
    'quote':       0,  # full-slide quote — no bullets
    'stat':        0,  # hero stat layout — no bullets
    'timeline':    5,  # up to 5 steps
}
_DEFAULT_BULLET_CAP = 6

# Layouts that must not be consecutive in a deck
_NO_CONSECUTIVE = {'cover', 'quote', 'stat'}

# Filler words that indicate lazy bullet writing
_FILLER_PHRASES = [
    'in order to', 'it is important to note', 'it should be noted',
    'as mentioned earlier', 'the fact that', 'in conclusion',
    'to summarize', 'it goes without saying', 'needless to say',
    'as you can see', 'at the end of the day', 'moving forward',
    'going forward', 'leverage', 'synergy', 'utilize', 'paradigm shift',
    'drill down', 'circle back', 'take it offline', 'bandwidth',
    'best of breed', 'value add', 'low-hanging fruit', 'boil the ocean',
]


class ContentValidator:
    @staticmethod
    def validate_and_prune(master_plan: MasterPlan) -> MasterPlan:
        """
        Validates the generated MasterPlan to ensure UI constraints are met.
        Prunes excessive text, migrates legacy content_bullets → content_blocks,
        and checks deck-level structural quality.
        """
        print("Validator: Running post-generation checks...")
        issues = 0

        # ── 0. Sort & deduplicate slide numbers ───────────────────────────
        seen_numbers = set()
        for slide in master_plan.slides:
            if slide.slide_number in seen_numbers:
                print(f"  [Warning] Duplicate slide_number {slide.slide_number} detected.")
                issues += 1
            seen_numbers.add(slide.slide_number)
        master_plan.slides.sort(key=lambda s: s.slide_number)

        # ── 1. Per-slide checks ───────────────────────────────────────────
        for slide in master_plan.slides:
            layout = slide.layout_type
            cap    = _LAYOUT_BULLET_CAPS.get(layout, _DEFAULT_BULLET_CAP)

            # 1a. Empty title fallback
            if not (slide.title or '').strip():
                print(f"  [Fix] Slide {slide.slide_number}: empty title → fallback.")
                slide.title = f"Slide {slide.slide_number}"
                issues += 1

            # 1b. Cover title length warning (>40 chars may overflow CSS)
            if layout == 'cover' and len(slide.title) > 45:
                print(
                    f"  [Warn] Slide {slide.slide_number}: cover title is long "
                    f"({len(slide.title)} chars). Consider shortening to prevent overflow."
                )

            # 1c. Subtitle max length
            MAX_SUBTITLE_LEN = 120
            if slide.subtitle and len(slide.subtitle) > MAX_SUBTITLE_LEN:
                print(f"  [Fix] Slide {slide.slide_number}: subtitle too long → truncated.")
                slide.subtitle = slide.subtitle[:MAX_SUBTITLE_LEN - 3] + "..."
                issues += 1

            # 1d. Bullet count cap (layout-aware)
            if len(slide.content_bullets) > cap:
                print(
                    f"  [Fix] Slide {slide.slide_number} ({layout}): "
                    f"{len(slide.content_bullets)} bullets → capped to {cap}."
                )
                slide.content_bullets = slide.content_bullets[:cap]
                issues += 1

            # 1e. Bullet length cap
            MAX_BULLET_LEN = 200
            for i, bullet in enumerate(slide.content_bullets):
                if len(bullet) > MAX_BULLET_LEN:
                    print(
                        f"  [Fix] Slide {slide.slide_number} bullet {i+1}: "
                        f"{len(bullet)} chars → truncated."
                    )
                    slide.content_bullets[i] = bullet[:MAX_BULLET_LEN - 3] + "..."
                    issues += 1

            # 1f. Filler word detection in bullets
            for i, bullet in enumerate(slide.content_bullets):
                lower = bullet.lower()
                found = [p for p in _FILLER_PHRASES if p in lower]
                if found:
                    print(
                        f"  [Warn] Slide {slide.slide_number} bullet {i+1}: "
                        f"contains filler phrase(s): {found}"
                    )

            # 1g. requires_image=True but image_prompt is empty
            if slide.requires_image and not (slide.image_prompt or '').strip():
                print(
                    f"  [Fix] Slide {slide.slide_number}: requires_image=True "
                    f"but image_prompt is empty → using title as prompt."
                )
                slide.image_prompt = f"Visual representation of: {slide.title}"
                issues += 1

            # 1g2. INT-09: Force requires_image=True for content slides that lack images.
            if layout not in _IMAGE_OPTIONAL and not slide.requires_image:
                print(
                    f"  [Fix] Slide {slide.slide_number} ({layout}): "
                    f"requires_image=False → forcing True for visual richness."
                )
                slide.requires_image = True
                issues += 1

            # 1g3. INT-09: Set default image_role based on layout if not already set.
            if slide.requires_image and not slide.image_role:
                if layout in _PANEL_LAYOUTS:
                    slide.image_role = 'panel'
                elif layout in _SPLIT_LAYOUTS:
                    slide.image_role = 'supporting'
                elif layout in _DECOR_LAYOUTS:
                    slide.image_role = 'decorative'
                else:
                    slide.image_role = 'background'

            # 1g4. INT-09: Generate / upgrade image prompt.
            if slide.requires_image:
                prompt = (slide.image_prompt or '').strip()
                if not prompt or len(prompt) < 30 or prompt.startswith("Visual representation of:"):
                    role = slide.image_role or 'panel'
                    if role == 'panel':
                        composition = "portrait composition, vertical emphasis, subject centered"
                    elif role == 'supporting':
                        composition = "landscape, left-half clear for text overlay"
                    elif role == 'background':
                        composition = "landscape, left-half clear for text overlay, dramatic lighting"
                    else:
                        composition = "subtle, low-detail"
                    slide.image_prompt = (
                        f"Editorial illustration related to: {slide.title}. "
                        f"Warm tones, fine linework, {composition}. "
                        f"No text, logos, or watermarks."
                    )
                    if not prompt:  # only count as a fix if it was missing
                        issues += 1
                        print(
                            f"  [Fix] Slide {slide.slide_number}: no image_prompt "
                            f"→ generated contextual prompt."
                        )

            # 1h. Cover layout with bullets (they're not rendered — inform user)
            if layout == 'cover' and slide.content_bullets:
                print(
                    f"  [Info] Slide {slide.slide_number}: cover layout ignores bullets "
                    f"(they won't appear in the rendered output)."
                )

            # 1i. content_blocks × layout compatibility
            if slide.content_blocks:
                ContentValidator._check_block_compat(slide)

            # 1j. Migrate legacy content_bullets → BulletBlock if no content_blocks set
            if not slide.content_blocks and slide.content_bullets:
                if layout not in ('cover', 'quote', 'stat'):
                    slide.content_blocks = [BulletBlock(items=slide.content_bullets)]

        # ── 2. Deck-level structural checks ──────────────────────────────
        issues += ContentValidator._check_deck_structure(master_plan)

        # ── Summary ───────────────────────────────────────────────────────
        if issues == 0:
            print("Validator: All checks passed — no issues found.")
        else:
            print(f"Validator: Checks complete — {issues} issue(s) fixed automatically.")

        return master_plan

    @staticmethod
    def _check_block_compat(slide):
        """Warn when a content block type is incompatible with its layout."""
        from schemas import PullQuoteBlock, StatBlock
        layout = slide.layout_type
        for block in slide.content_blocks:
            if isinstance(block, PullQuoteBlock) and layout not in ('generic', 'split', 'quote'):
                print(
                    f"  [Warn] Slide {slide.slide_number}: PullQuoteBlock "
                    f"is not ideal for '{layout}' layout (use 'quote' or 'generic')."
                )
            if isinstance(block, StatBlock) and layout not in ('generic', 'split', 'stat', 'infographic'):
                print(
                    f"  [Warn] Slide {slide.slide_number}: StatBlock "
                    f"in '{layout}' layout will not be prominently rendered."
                )

    @staticmethod
    def _check_deck_structure(master_plan: MasterPlan) -> int:
        """Check deck-level structural quality. Returns warning count."""
        issues = 0
        slides = master_plan.slides
        n = len(slides)

        if not slides:
            return 0

        # Slide 1 should be a cover
        if slides[0].layout_type != 'cover':
            print(
                f"  [Warn] Slide 1 is '{slides[0].layout_type}' — "
                f"expected 'cover'. First slide should establish the deck theme."
            )

        # No more than 2 consecutive slides with the same layout (standard check)
        for i in range(len(slides) - 2):
            a, b, c = slides[i].layout_type, slides[i+1].layout_type, slides[i+2].layout_type
            if a == b == c:
                print(
                    f"  [Warn] Slides {slides[i].slide_number}–{slides[i+2].slide_number}: "
                    f"3 consecutive '{a}' layouts — vary the layout for visual rhythm."
                )

        # For 8+ slides: warn on 2 consecutive same layouts (stricter)
        if n >= 8:
            for i in range(len(slides) - 1):
                if slides[i].layout_type == slides[i+1].layout_type:
                    print(
                        f"  [Warn] Slides {slides[i].slide_number}–{slides[i+1].slide_number}: "
                        f"2 consecutive '{slides[i].layout_type}' layouts — "
                        f"avoid repeats in {n}-slide decks."
                    )

        # No two cover slides
        cover_count = sum(1 for s in slides if s.layout_type == 'cover')
        if cover_count > 1:
            print(f"  [Warn] {cover_count} slides with layout_type 'cover' — should be 1.")

        # Deck has at least some variety
        layout_types = set(s.layout_type for s in slides)
        if len(layout_types) == 1 and n > 2:
            print(
                f"  [Warn] All {n} slides use the same layout '{slides[0].layout_type}'. "
                f"Add variety with split, infographic, or generic layouts."
            )

        # For 10+ slides: minimum layout variety threshold
        if n >= 10:
            min_variety = 5 if n <= 12 else 6
            if len(layout_types) < min_variety:
                print(
                    f"  [Warn] {n}-slide deck uses only {len(layout_types)} layout types — "
                    f"aim for at least {min_variety} for visual variety."
                )

        # For 10+ slides: minimum breathing room slides
        if n >= 10:
            light_slides = sum(
                1 for s in slides
                if getattr(s, 'narrative_weight', 'standard') == 'light'
            )
            min_light = 2 if n <= 12 else 3
            if light_slides < min_light:
                print(
                    f"  [Warn] {n}-slide deck has only {light_slides} 'light' slide(s) — "
                    f"aim for at least {min_light} for visual breathing room."
                )

        return issues
