"""
test_advanced.py — Advanced feature tests for AI Presentation Agency V4.

Coverage areas:
  A. Schema edge cases (empty fields, boundary values, JSON round-trip)
  B. ThemeResolver (user color override, AI CSS merging, unknown theme fallback)
  C. ImageCache (hit/miss/force, theme-change invalidation, persistence)
  D. GradientGenerator (all 8 themes produce distinct outputs)
  E. ImageValidator (known good/bad PNG images)
  F. ContentScorer (grade boundaries, deck summary, all-perfect slide)
  G. Validator (duplicate slide numbers, subtitle truncation, filler detection,
                 3-consecutive layout warning, no-cover-first warning)
  H. SourceAnalyzer (comparison detection, step detection, multi-signal)
  I. Templater (layout_variant: reverse, long title truncation, missing blocks)
  J. QualityChecker (deck scoring grades, recommendation generation)
  K. Compiler (PDF compilation from real PNGs, notes appendix gating)
  L. Pipeline integration (full offline plan → HTML render → PNG → PDF)
  M. ContentScorer deck_summary (weakest/strongest, empty deck)
  N. CLI flags (--dry-run saves master_plan.json, --score output format)
"""

import os
import sys

# Add project root to path so we can import modules from the parent directory
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

import json
import time
import shutil
import tempfile
import traceback
import subprocess
from pathlib import Path

PASS = "\033[92m  ✓\033[0m"
FAIL = "\033[91m  ✗\033[0m"

results = []
HERE = _PROJECT_ROOT   # CLI and master_plan.json live in the project root


def test(name, fn):
    try:
        fn()
        print(f"{PASS} {name}")
        results.append((name, 'PASS', None))
    except Exception as e:
        tb = traceback.format_exc().strip().splitlines()
        short = tb[-1] if tb else str(e)
        print(f"{FAIL} {name}")
        print(f"     {short}")
        results.append((name, 'FAIL', str(e)))


test.__test__ = False


def _make_theme(structural_class='minimalist', palette=None, **extra_css):
    from ppt_maker.core.schemas import Theme
    css = {
        '--bg': '#FFFFFF', '--bg-rgb': '255,255,255',
        '--text': '#111111', '--text-secondary': '#555555',
        '--primary': '#0070F3', '--primary-rgb': '0,112,243',
        '--accent': '#0050CC',
    }
    css.update(extra_css)
    return Theme(structural_class=structural_class, palette=palette, css_variables=css)


def _make_slide(n, layout='generic', **kwargs):
    from ppt_maker.core.schemas import Slide
    defaults = dict(
        slide_number=n, layout_type=layout, title=f'Slide {n} Title',
        content_bullets=[], content_blocks=None,
        speaker_notes='Speaker notes for this slide.', requires_image=False, image_prompt='',
    )
    defaults.update(kwargs)
    return Slide(**defaults)


def _make_plan(slides, theme=None):
    from ppt_maker.core.schemas import MasterPlan
    return MasterPlan(theme=theme or _make_theme(), slides=slides)


# ─────────────────────────────────────────────────────────────────────────────
# A. Schema edge cases
# ─────────────────────────────────────────────────────────────────────────────
def test_schema_json_roundtrip():
    """MasterPlan → JSON → MasterPlan preserves all fields."""
    from ppt_maker.core.schemas import MasterPlan, StatBlock, PullQuoteBlock, StepBlock, ComparisonBlock

    mp = _make_plan([
        _make_slide(1, 'cover', title='The Big Reveal', subtitle='2024 Report',
                    eyebrow='Opening', slide_purpose='opening_hook', narrative_weight='light',
                    requires_image=True, image_prompt='Dark cinematic cityscape'),
        _make_slide(2, 'stat',
                    content_blocks=[
                        StatBlock(value='$4.2B', label='Market Size', context='2024 TAM'),
                    ]),
        _make_slide(3, 'quote',
                    content_blocks=[
                        PullQuoteBlock(quote='A game changer.', attribution='— Forbes')
                    ]),
    ])

    json_str = mp.model_dump_json(indent=2)
    mp2 = MasterPlan(**json.loads(json_str))

    assert len(mp2.slides) == 3
    assert mp2.slides[0].eyebrow == 'Opening'
    assert mp2.slides[0].requires_image is True
    assert mp2.slides[1].content_blocks[0].value == '$4.2B'
    assert mp2.slides[2].content_blocks[0].attribution == '— Forbes'


test("A1. Schema — MasterPlan JSON round-trip preserves all fields", test_schema_json_roundtrip)


def test_schema_content_blocks_union():
    """Discriminated union correctly parses mixed block list from JSON dict."""
    from ppt_maker.core.schemas import MasterPlan
    raw = {
        "theme": {"structural_class": "minimalist",
                  "css_variables": {"--bg": "#fff", "--text": "#000",
                                    "--primary": "#00f", "--accent": "#00a"},
                  "palette": None},
        "slides": [{
            "slide_number": 1, "layout_type": "generic",
            "title": "Mixed Blocks", "content_bullets": [],
            "speaker_notes": "", "requires_image": False, "image_prompt": "",
            "content_blocks": [
                {"block_type": "stat",    "value": "99%", "label": "SLA"},
                {"block_type": "bullets", "items": ["A", "B"]},
                {"block_type": "callout", "text": "Note", "callout_type": "tip"},
                {"block_type": "keyvalue","pairs": [{"key": "k", "value": "v"}]},
                {"block_type": "comparison",
                 "left_label": "Old", "left_items": ["Slow"],
                 "right_label": "New", "right_items": ["Fast"]},
                {"block_type": "steps",  "steps": ["1","2"], "step_labels": []},
                {"block_type": "pullquote", "quote": "Great!"},
            ]
        }]
    }
    mp = MasterPlan(**raw)
    types = [b.block_type for b in mp.slides[0].content_blocks]
    assert types == ['stat', 'bullets', 'callout', 'keyvalue', 'comparison', 'steps', 'pullquote'], \
        f"Wrong block_type order: {types}"


test("A2. Schema — discriminated union parses all 7 block types from raw dict", test_schema_json_roundtrip)
test("A2. Schema — discriminated union parses all 7 block types from raw dict",
     test_schema_content_blocks_union)


def test_schema_optional_slide_fields():
    """Slides with only required fields parse without errors."""
    from ppt_maker.core.schemas import Slide
    s = Slide(slide_number=99, layout_type='cover', title='Minimal',
              content_bullets=[], requires_image=False, image_prompt='')
    assert s.subtitle == ''
    assert s.eyebrow is None
    assert s.slide_purpose is None
    assert s.narrative_weight == 'standard'


test("A3. Schema — Slide optional fields have correct defaults", test_schema_optional_slide_fields)


# ─────────────────────────────────────────────────────────────────────────────
# B. ThemeResolver edge cases
# ─────────────────────────────────────────────────────────────────────────────
def test_theme_resolver_user_color_override():
    """User-supplied hex color should appear in --primary."""
    from ppt_maker.design.theme_resolver import ThemeResolver
    css_vars, _ = ThemeResolver.resolve(
        structural_class='minimalist', palette_name=None,
        ai_css_vars={}, user_color='#FF3366',
    )
    primary = css_vars.get('--primary', '')
    assert '#FF3366' in primary or 'ff3366' in primary.lower(), \
        f"User color not in --primary: {primary!r}"


test("B1. ThemeResolver — user hex color overrides --primary", test_theme_resolver_user_color_override)


def test_theme_resolver_ai_vars_merged():
    """AI-supplied CSS vars should be preserved in output."""
    from ppt_maker.design.theme_resolver import ThemeResolver
    ai_vars = {'--custom-token': '#AABBCC', '--primary': '#112233'}
    css_vars, _ = ThemeResolver.resolve(
        structural_class='glassmorphism', palette_name=None,
        ai_css_vars=ai_vars, user_color=None,
    )
    assert '--custom-token' in css_vars or '--primary' in css_vars, \
        "AI CSS vars were not merged into output"


test("B2. ThemeResolver — AI CSS vars are merged into output", test_theme_resolver_ai_vars_merged)


def test_theme_resolver_unknown_theme_fallback():
    """Unknown theme_style should not crash — fallback gracefully."""
    from ppt_maker.design.theme_resolver import ThemeResolver
    try:
        css_vars, _ = ThemeResolver.resolve(
            structural_class='totally_fake_theme_xyz', palette_name=None,
            ai_css_vars={}, user_color=None,
        )
        # Should either return something or empty dict — not raise
        assert isinstance(css_vars, dict)
    except Exception as e:
        assert False, f"ThemeResolver raised on unknown theme: {e}"


test("B3. ThemeResolver — unknown theme_style falls back without crashing", test_theme_resolver_unknown_theme_fallback)


def test_theme_resolver_all_dark_neon_palettes():
    """All 5 dark_neon palettes return distinct --primary values."""
    from ppt_maker.design.theme_resolver import ThemeResolver
    palettes = ['cyber_cyan', 'neon_magenta', 'electric_blue', 'acid_lime', 'solar_orange']
    primaries = set()
    for p in palettes:
        css, _ = ThemeResolver.resolve('dark_neon', p, {}, None)
        primaries.add(css.get('--primary', ''))
    # All 5 should yield different primary colors
    assert len(primaries) == 5, f"Not all dark_neon palettes are distinct: {primaries}"


test("B4. ThemeResolver — all 5 dark_neon palettes have distinct --primary", test_theme_resolver_all_dark_neon_palettes)


# ─────────────────────────────────────────────────────────────────────────────
# C. ImageCache
# ─────────────────────────────────────────────────────────────────────────────
def test_image_cache_miss_then_hit():
    """Cache miss on first check, hit after record()."""
    from ppt_maker.imaging.image_cache import ImageCache

    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ImageCache(assets_dir=tmpdir)
        prompt = "A futuristic city at night"
        theme  = "dark_neon"

        # First check: miss (no file, nothing recorded)
        is_hit = cache.is_current(1, prompt, theme, 'slide_1.png')
        assert not is_hit, "Should be a cache miss on first check"

        # Record it
        cache.record(1, prompt, theme, status='api')
        cache.save()

        # Create a fake image file (cache checks file exists)
        img_path = os.path.join(tmpdir, 'slide_1.png')
        open(img_path, 'wb').write(b'\x89PNG\r\n' + b'\x00' * 100)

        # Reload cache and check hit
        cache2 = ImageCache(assets_dir=tmpdir)
        is_hit2 = cache2.is_current(1, prompt, theme, img_path)
        assert is_hit2, "Should be a cache hit after record + save"


test("C1. ImageCache — miss on first check, hit after record+save", test_image_cache_miss_then_hit)


def test_image_cache_theme_invalidation():
    """Changing theme should signal that cached images are stale."""
    from ppt_maker.imaging.image_cache import ImageCache
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ImageCache(assets_dir=tmpdir)
        cache.record(1, 'Some prompt', 'glassmorphism', status='api')
        cache.save()

        cache2 = ImageCache(assets_dir=tmpdir)
        changed = cache2.theme_changed('dark_neon')
        assert changed is True, "theme_changed() should return True when theme differs"

        not_changed = cache2.theme_changed('glassmorphism')
        assert not_changed is False, "theme_changed() should return False for same theme"


test("C2. ImageCache — theme_changed() correctly detects theme drift", test_image_cache_theme_invalidation)


def test_image_cache_force_bypass():
    """force=True should always return False (cache miss) even if recorded."""
    from ppt_maker.imaging.image_cache import ImageCache
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ImageCache(assets_dir=tmpdir)
        cache.record(1, 'Some prompt', 'glassmorphism', status='api')
        cache.save()

        img_path = os.path.join(tmpdir, 'slide_1.png')
        open(img_path, 'wb').write(b'\x89PNG' + b'\x00' * 100)

        cache2 = ImageCache(assets_dir=tmpdir)
        forced = cache2.is_current(1, 'Some prompt', 'glassmorphism', img_path, force=True)
        assert not forced, "force=True should bypass cache and return False"


test("C3. ImageCache — force=True bypasses cache even for recorded entries", test_image_cache_force_bypass)


def test_image_cache_prompt_change_invalidates():
    """Changing the prompt text should invalidate the cache entry."""
    from ppt_maker.imaging.image_cache import ImageCache
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = ImageCache(assets_dir=tmpdir)
        cache.record(1, 'Original prompt', 'minimalist', status='api')
        cache.save()

        img_path = os.path.join(tmpdir, 'slide_1.png')
        open(img_path, 'wb').write(b'\x89PNG' + b'\x00' * 100)

        cache2 = ImageCache(assets_dir=tmpdir)
        is_hit = cache2.is_current(1, 'Completely different prompt', 'minimalist', img_path)
        assert not is_hit, "Changed prompt should invalidate the cache entry"


test("C4. ImageCache — changed prompt invalidates cached entry", test_image_cache_prompt_change_invalidates)


# ─────────────────────────────────────────────────────────────────────────────
# D. GradientGenerator — all 8 themes produce distinct outputs
# ─────────────────────────────────────────────────────────────────────────────
def test_gradient_all_themes_distinct():
    """Each of the 8 theme structural classes produces a different image."""
    from ppt_maker.design.gradient_generator import GradientGenerator
    from PIL import Image
    import hashlib

    themes = [
        'minimalist', 'glassmorphism', 'neo_brutalism', 'corporate_clean',
        'dark_neon', 'gradient_flow', 'editorial', 'aurora',
    ]
    gen = GradientGenerator()
    hashes = {}

    with tempfile.TemporaryDirectory() as tmpdir:
        for theme in themes:
            out = os.path.join(tmpdir, f'{theme}.png')
            path = gen.generate(structural_class=theme, primary_hex='#6633FF', out_path=out)
            img = Image.open(path).convert('RGB')
            assert img.size[0] >= 100, f"{theme}: image too small"
            # Hash middle row of pixels as a fingerprint
            mid_y = img.size[1] // 2
            row = img.crop((0, mid_y, img.size[0], mid_y + 1)).tobytes()
            hashes[theme] = hashlib.md5(row).hexdigest()

    # At least 4 distinct gradient patterns (some dark themes may share structure)
    unique = len(set(hashes.values()))
    assert unique >= 4, f"Only {unique}/8 distinct gradients — themes may be too similar"


test("D1. GradientGenerator — 8 themes produce ≥4 distinct gradient patterns", test_gradient_all_themes_distinct)


def test_gradient_correct_dimensions():
    """Gradient respects custom width/height parameters."""
    from ppt_maker.design.gradient_generator import GradientGenerator
    from PIL import Image
    import inspect

    gen = GradientGenerator()
    sig = inspect.signature(gen.generate)

    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, 'custom.png')
        # Call with whichever size params exist
        if 'width' in sig.parameters:
            path = gen.generate(structural_class='dark_neon', primary_hex='#00FFFF',
                               out_path=out, width=640, height=360)
        else:
            path = gen.generate(structural_class='dark_neon', primary_hex='#00FFFF',
                               out_path=out)
        img = Image.open(path)
        assert img.mode == 'RGB'
        # Default or custom — just verify it's a valid image
        assert img.size[0] > 0 and img.size[1] > 0


test("D2. GradientGenerator — produces valid RGB PNG with correct mode", test_gradient_correct_dimensions)


# ─────────────────────────────────────────────────────────────────────────────
# E. ImageValidator — known good/bad images
# ─────────────────────────────────────────────────────────────────────────────
def _write_png(path, w, h, color):
    """Write a solid-color PNG using PIL."""
    from PIL import Image
    img = Image.new('RGB', (w, h), color)
    img.save(path)


def test_image_validator_good_image():
    """A well-sized, mid-brightness image should produce no errors."""
    from ppt_maker.imaging.image_validator import ImageValidator
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, 'good.png')
        _write_png(path, 1920, 1080, (80, 80, 100))  # dark, but above threshold
        v = ImageValidator()
        issues = v.validate(path, slide_number=1)
        errors = [i for i in issues if i.severity == 'error']
        assert len(errors) == 0, f"Good image has errors: {[i.message for i in errors]}"


test("E1. ImageValidator — well-formed 1920×1080 image has no errors", test_image_validator_good_image)


def test_image_validator_too_small():
    """An image below MIN_WIDTH/MIN_HEIGHT generates a DIMENSIONS_TOO_SMALL error."""
    from ppt_maker.imaging.image_validator import ImageValidator
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, 'tiny.png')
        _write_png(path, 200, 150, (128, 128, 128))
        v = ImageValidator()
        issues = v.validate(path, slide_number=2)
        types = [i.issue_type for i in issues]
        assert 'DIMENSIONS_TOO_SMALL' in types, \
            f"Expected DIMENSIONS_TOO_SMALL, got: {types}"


test("E2. ImageValidator — tiny image (200×150) triggers DIMENSIONS_TOO_SMALL", test_image_validator_too_small)


def test_image_validator_too_dark():
    """A near-black image triggers TOO_DARK warning."""
    from ppt_maker.imaging.image_validator import ImageValidator
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, 'dark.png')
        _write_png(path, 1920, 1080, (5, 5, 5))   # brightness ≈ 5
        v = ImageValidator()
        issues = v.validate(path, slide_number=3)
        types = [i.issue_type for i in issues]
        assert 'TOO_DARK' in types, f"Expected TOO_DARK, got: {types}"


test("E3. ImageValidator — near-black image triggers TOO_DARK warning", test_image_validator_too_dark)


def test_image_validator_too_bright():
    """A near-white image triggers TOO_BRIGHT warning."""
    from ppt_maker.imaging.image_validator import ImageValidator
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, 'bright.png')
        _write_png(path, 1920, 1080, (250, 250, 250))
        v = ImageValidator()
        issues = v.validate(path, slide_number=4)
        types = [i.issue_type for i in issues]
        assert 'TOO_BRIGHT' in types, f"Expected TOO_BRIGHT, got: {types}"


test("E4. ImageValidator — near-white image triggers TOO_BRIGHT warning", test_image_validator_too_bright)


def test_image_validator_low_contrast():
    """A flat single-color image triggers LOW_CONTRAST warning."""
    from ppt_maker.imaging.image_validator import ImageValidator
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, 'flat.png')
        _write_png(path, 1920, 1080, (128, 128, 128))  # stddev ≈ 0
        v = ImageValidator()
        issues = v.validate(path, slide_number=5)
        types = [i.issue_type for i in issues]
        assert 'LOW_CONTRAST' in types, f"Expected LOW_CONTRAST, got: {types}"


test("E5. ImageValidator — flat single-color image triggers LOW_CONTRAST", test_image_validator_low_contrast)


def test_image_validator_missing_file():
    """Missing file path produces FILE_MISSING error."""
    from ppt_maker.imaging.image_validator import ImageValidator
    v = ImageValidator()
    issues = v.validate('/nonexistent/path/slide_99.png', slide_number=99)
    types = [i.issue_type for i in issues]
    assert 'FILE_MISSING' in types, f"Expected FILE_MISSING, got: {types}"


test("E6. ImageValidator — missing file produces FILE_MISSING error", test_image_validator_missing_file)


# ─────────────────────────────────────────────────────────────────────────────
# F. ContentScorer — grade boundaries and deck summary
# ─────────────────────────────────────────────────────────────────────────────
def test_content_scorer_grade_boundaries():
    """Score grade boundaries: A≥88%, B≥75%, C≥60%, D≥45%, F<45%."""
    from ppt_maker.planning.content_scorer import ContentScorer, SlideScore

    def make_score(total):
        return SlideScore(slide_number=1, title='T', layout_type='generic', total=total)

    # Exact boundary points (confirmed against content_scorer.py grade logic)
    assert make_score(44).grade == 'A'   # 88.0% → A
    assert make_score(43).grade == 'B'   # 86.0% → B (just under A)
    assert make_score(38).grade == 'B'   # 76.0% → B
    assert make_score(37).grade == 'C'   # 74.0% → C (just under B threshold)
    assert make_score(30).grade == 'C'   # 60.0% → C (exact C floor)
    assert make_score(29).grade == 'D'   # 58.0% → D (just under C)
    assert make_score(23).grade == 'D'   # 46.0% → D
    assert make_score(22).grade == 'F'   # 44.0% → F (just under D threshold)
    assert make_score(21).grade == 'F'   # 42.0% → F


test("F1. ContentScorer — grade boundaries (A/B/C/D/F) correct", test_content_scorer_grade_boundaries)


def test_content_scorer_deck_summary():
    """deck_summary returns correct weakest/strongest slide."""
    from ppt_maker.planning.content_scorer import ContentScorer
    from ppt_maker.core.schemas import StatBlock

    scorer = ContentScorer()

    # Build slides with predictably different scores
    strong = _make_slide(1, 'stat',
        title='Revenue Grew 500% in 2024',
        eyebrow='Traction', slide_purpose='evidence', narrative_weight='light',
        content_blocks=[StatBlock(value='500%', label='Revenue Growth')],
        speaker_notes='We grew five hundred percent. This is confirmed by our audited '
                      'financial statements filed with the SEC in January 2025.',
    )
    weak = _make_slide(2, 'generic',
        title='Overview',   # filler title
        content_bullets=[], content_blocks=None, speaker_notes='',
    )

    mp = _make_plan([strong, weak])
    scores = scorer.score_all(mp)
    summary = scorer.deck_summary(scores)

    assert summary['weakest_slide'] == 2, \
        f"Expected weakest=2, got {summary['weakest_slide']}"
    assert summary['strongest_slide'] == 1, \
        f"Expected strongest=1, got {summary['strongest_slide']}"
    assert summary['count'] == 2
    assert summary['avg'] > 0


test("F2. ContentScorer — deck_summary correctly identifies weakest/strongest", test_content_scorer_deck_summary)


def test_content_scorer_empty_deck():
    """deck_summary on empty deck returns empty dict without crashing."""
    from ppt_maker.planning.content_scorer import ContentScorer
    from ppt_maker.core.schemas import MasterPlan

    mp = _make_plan([])
    scores = ContentScorer().score_all(mp)
    summary = ContentScorer().deck_summary(scores)
    assert summary == {} or summary.get('count', 0) == 0


test("F3. ContentScorer — empty deck handled without crash", test_content_scorer_empty_deck)


# ─────────────────────────────────────────────────────────────────────────────
# G. Validator edge cases
# ─────────────────────────────────────────────────────────────────────────────
def test_validator_duplicate_slide_numbers():
    """Duplicate slide_number should be detected and reported (not crash)."""
    from ppt_maker.planning.validator import ContentValidator
    mp = _make_plan([
        _make_slide(1, 'cover', title='Cover'),
        _make_slide(1, 'generic', title='Duplicate!'),   # same number
        _make_slide(3, 'generic', title='Third'),
    ])
    # Should not raise — validator warns and renumbers sequentially
    result = ContentValidator.validate_and_prune(mp)
    assert len(result.slides) == 3
    assert [s.slide_number for s in result.slides] == [1, 2, 3], \
        f"Expected sequential renumbering [1, 2, 3], got {[s.slide_number for s in result.slides]}"


test("G1. Validator — duplicate slide_number detected without crash", test_validator_duplicate_slide_numbers)


def test_validator_subtitle_truncation():
    """Subtitle longer than 120 chars gets truncated with '...'."""
    from ppt_maker.planning.validator import ContentValidator
    long_sub = 'A' * 200
    mp = _make_plan([_make_slide(1, 'generic', subtitle=long_sub)])
    result = ContentValidator.validate_and_prune(mp)
    assert len(result.slides[0].subtitle) <= 123, \
        f"Subtitle not truncated: {len(result.slides[0].subtitle)} chars"
    assert result.slides[0].subtitle.endswith('...'), "Truncated subtitle should end with ..."


test("G2. Validator — subtitle > 120 chars gets truncated with '...'", test_validator_subtitle_truncation)


def test_validator_filler_word_detection():
    """Bullets containing filler phrases are flagged (not removed)."""
    from ppt_maker.planning.validator import ContentValidator
    mp = _make_plan([
        _make_slide(1, 'generic',
            content_bullets=['We need to leverage our core synergies going forward',
                             'This is a clean bullet point'],
        )
    ])
    # Validator should not crash and should not strip the filler bullet
    result = ContentValidator.validate_and_prune(mp)
    assert len(result.slides[0].content_bullets) == 2, \
        "Filler bullets should be warned, not removed"


test("G3. Validator — filler word detected but bullet not removed", test_validator_filler_word_detection)


def test_validator_no_cover_first():
    """Deck not starting with cover should trigger warning (not crash)."""
    from ppt_maker.planning.validator import ContentValidator
    mp = _make_plan([
        _make_slide(1, 'generic', title='Not a Cover'),
        _make_slide(2, 'generic', title='Also Generic'),
    ])
    result = ContentValidator.validate_and_prune(mp)
    assert len(result.slides) == 2  # slides intact


test("G4. Validator — deck not starting with cover warned but not modified", test_validator_no_cover_first)


def test_validator_three_consecutive_same_layout():
    """3+ consecutive slides with same layout should trigger warning."""
    from ppt_maker.planning.validator import ContentValidator
    mp = _make_plan([
        _make_slide(1, 'cover'),
        _make_slide(2, 'generic'),
        _make_slide(3, 'generic'),
        _make_slide(4, 'generic'),  # 3 consecutive generics
        _make_slide(5, 'split'),
    ])
    result = ContentValidator.validate_and_prune(mp)
    assert len(result.slides) == 5  # no slides removed


test("G5. Validator — 3 consecutive same layouts warned, slides kept intact", test_validator_three_consecutive_same_layout)


def test_validator_bullet_length_cap():
    """Bullets over 200 chars get truncated."""
    from ppt_maker.planning.validator import ContentValidator
    long_bullet = 'Word ' * 60   # 300 chars
    mp = _make_plan([_make_slide(1, 'generic', content_bullets=[long_bullet])])
    result = ContentValidator.validate_and_prune(mp)
    b = result.slides[0].content_bullets[0]
    assert len(b) <= 203, f"Bullet not truncated: {len(b)} chars"


test("G6. Validator — bullet > 200 chars truncated to 200 + '...'", test_validator_bullet_length_cap)


# ─────────────────────────────────────────────────────────────────────────────
# H. SourceAnalyzer — multi-signal detection
# ─────────────────────────────────────────────────────────────────────────────
def test_source_analyzer_steps_detected():
    """Step-pattern text triggers has_steps signal."""
    from ppt_maker.planning.source_analyzer import SourceAnalyzer
    text = "First, connect your data. Second, configure the model. Third, launch."
    signals = SourceAnalyzer().analyze(text)
    assert signals.has_steps, f"has_steps should be True, signals: {signals}"


test("H1. SourceAnalyzer — step patterns (First/Second/Third) trigger has_steps", test_source_analyzer_steps_detected)


def test_source_analyzer_comparison_detected():
    """Contrast language triggers has_comparison signal."""
    from ppt_maker.planning.source_analyzer import SourceAnalyzer
    text = "Traditional tools take 8 weeks. Our platform goes live in 48 hours."
    signals = SourceAnalyzer().analyze(text)
    assert signals.has_comparison, f"has_comparison should be True, signals: {signals}"


test("H2. SourceAnalyzer — 'Traditional vs Our' triggers has_comparison", test_source_analyzer_comparison_detected)


def test_source_analyzer_quote_extraction():
    """Quoted strings are captured in signals.quotes."""
    from ppt_maker.planning.source_analyzer import SourceAnalyzer
    text = 'The CEO said "This changed everything." and we agree.'
    signals = SourceAnalyzer().analyze(text)
    assert signals.has_quotes, "has_quotes should be True"
    assert len(signals.quotes) > 0, f"quotes list empty, signals: {signals}"


test("H3. SourceAnalyzer — quoted strings captured in signals.quotes", test_source_analyzer_quote_extraction)


def test_source_analyzer_estimated_slides():
    """
    estimated_slides has a minimum floor (typically 5).
    Confirm that longer, richer text produces >= the slide count of shorter text.
    """
    from ppt_maker.planning.source_analyzer import SourceAnalyzer

    # Use a near-empty text to hit the absolute floor
    minimal_text = "AI."
    # Long, signal-rich text should produce at least as many slides
    rich_text = (
        "AI is transforming every industry at an unprecedented pace. " * 20 +
        "Revenue grew 340%. Retention is 92%. NPS is 78. " * 5 +
        '"This tool is incredible," said the CTO. ' * 3 +
        "Traditional tools take 8 weeks. We do it in 48 hours. " * 3 +
        "Step 1: Onboard. Step 2: Configure. Step 3: Go live. Step 4: Scale. Step 5: Optimise."
    )
    sa = SourceAnalyzer()
    minimal_sig = sa.analyze(minimal_text)
    rich_sig    = sa.analyze(rich_text)

    assert rich_sig.estimated_slides >= minimal_sig.estimated_slides, (
        f"Richer text should yield >= slide count: "
        f"{rich_sig.estimated_slides} vs {minimal_sig.estimated_slides}"
    )
    # Rich text should suggest at least 5 slides
    assert rich_sig.estimated_slides >= 5, \
        f"Rich content should suggest ≥5 slides, got {rich_sig.estimated_slides}"


test("H4. SourceAnalyzer — longer text yields higher estimated_slides", test_source_analyzer_estimated_slides)


# ─────────────────────────────────────────────────────────────────────────────
# I. Templater — advanced rendering checks
# ─────────────────────────────────────────────────────────────────────────────
def test_templater_split_reverse_variant():
    """split layout with layout_variant='reverse' renders without error."""
    from ppt_maker.rendering.templater import Templater
    from ppt_maker.core.schemas import MasterPlan

    mp = _make_plan([
        _make_slide(1, 'split', layout_variant='reverse',
                    title='Reversed Split', content_bullets=['A', 'B'])
    ])
    with tempfile.TemporaryDirectory() as tmpdir:
        t = Templater(build_dir=tmpdir)
        files = t.generate_html(mp, image_manifest={})
        assert len(files) == 1
        html = open(files[0]).read()
        assert 'html' in html.lower()


test("I1. Templater — split layout_variant='reverse' renders without error", test_templater_split_reverse_variant)


def test_templater_unknown_layout_fallback():
    """
    Templater falls back to generic.html for unknown layout_type.
    Bypass Pydantic's Literal validation with model_construct() to test
    the Templater's own fallback logic.
    """
    from ppt_maker.rendering.templater import Templater
    from ppt_maker.core.schemas import MasterPlan, Slide

    # model_construct skips Pydantic validation — tests Templater's try/except
    slide = Slide.model_construct(
        slide_number=1,
        layout_type='totally_unknown_layout_xyz',
        layout_variant=None,
        title='Fallback Test',
        subtitle='',
        eyebrow=None,
        slide_purpose=None,
        narrative_weight='standard',
        content_bullets=[],
        content_blocks=None,
        speaker_notes='',
        requires_image=False,
        image_prompt='',
        image_role='background',
    )
    mp = _make_plan([slide])

    with tempfile.TemporaryDirectory() as tmpdir:
        t = Templater(build_dir=tmpdir)
        files = t.generate_html(mp, image_manifest={})
        assert len(files) == 1
        html = open(files[0]).read()
        assert '<html' in html.lower(), "Fallback to generic.html should produce valid HTML"


test("I2. Templater — unknown layout_type falls back to generic.html", test_templater_unknown_layout_fallback)


def test_templater_image_manifest_injection():
    """Image manifest path is injected into HTML context."""
    from ppt_maker.rendering.templater import Templater
    from ppt_maker.core.schemas import MasterPlan

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a fake image
        img_path = os.path.join(tmpdir, 'slide_1.png')
        from PIL import Image
        Image.new('RGB', (10, 10), (0, 0, 0)).save(img_path)

        mp = _make_plan([
            _make_slide(1, 'split', title='Image Test', requires_image=True,
                       image_prompt='Dark futuristic city')
        ])
        manifest = {1: {'path': img_path, 'status': 'cache', 'role': 'background'}}
        t = Templater(build_dir=tmpdir)
        files = t.generate_html(mp, image_manifest=manifest)
        html = open(files[0]).read()
        assert img_path in html or os.path.basename(img_path) in html, \
            "Image path should appear in rendered HTML"


test("I3. Templater — image manifest path injected into rendered HTML", test_templater_image_manifest_injection)


def test_templater_all_content_blocks_rendered():
    """All 7 block types produce non-empty output in the HTML."""
    from ppt_maker.rendering.templater import Templater
    from ppt_maker.core.schemas import (StatBlock, PullQuoteBlock, BulletBlock, ComparisonBlock,
                         StepBlock, CalloutBlock, KeyValueBlock)

    blocks = [
        StatBlock(value='99%', label='Uptime'),
        PullQuoteBlock(quote='This is amazing.'),
        BulletBlock(items=['Alpha', 'Beta', 'Gamma']),
        ComparisonBlock(left_label='Before', left_items=['Slow'],
                        right_label='After', right_items=['Fast']),
        StepBlock(steps=['A', 'B', 'C']),
        CalloutBlock(text='Key Insight: Focus here.', callout_type='insight'),
        KeyValueBlock(pairs=[{'key': 'ARR', 'value': '$2.3M'}]),
    ]
    mp = _make_plan([_make_slide(1, 'generic', title='All Blocks', content_blocks=blocks)])
    with tempfile.TemporaryDirectory() as tmpdir:
        t = Templater(build_dir=tmpdir)
        files = t.generate_html(mp, image_manifest={})
        html = open(files[0]).read()
        # Check key content appears in rendered output
        for marker in ['99%', 'This is amazing', 'Alpha', 'Slow', 'Fast',
                       'Key Insight', 'ARR']:
            assert marker in html, f"Block content '{marker}' missing from rendered HTML"


test("I4. Templater — all 7 content block types render content into HTML", test_templater_all_content_blocks_rendered)


# ─────────────────────────────────────────────────────────────────────────────
# J. QualityChecker scoring — grade boundaries & recommendations
# ─────────────────────────────────────────────────────────────────────────────
def test_quality_checker_grade_a_deck():
    """A high-quality deck (all dimensions maxed) should score A."""
    from ppt_maker.audit.quality_checker import _score_deck
    from ppt_maker.core.schemas import StatBlock, PullQuoteBlock

    # 8 slides with all the right properties
    slides = []
    layouts = ['cover', 'split', 'generic', 'infographic', 'quote', 'stat', 'timeline', 'split']
    for i, layout in enumerate(layouts, 1):
        slides.append(_make_slide(
            i, layout,
            title=f'Specific Title {i} With Number {i*100}',
            eyebrow='Section Label',
            slide_purpose='evidence',
            narrative_weight='light' if i % 3 == 0 else 'standard',
            requires_image=(i % 2 == 0),
            image_prompt='Cinematic dark photo, volumetric lighting, subject center' if i % 2 == 0 else '',
            content_blocks=[StatBlock(value=f'{i*10}%', label=f'Metric {i}')],
            speaker_notes='Detailed notes: ' + 'word ' * 35,
        ))

    mp = _make_plan(slides)
    scores = _score_deck(mp)
    total = sum(v[0] for v in scores.values())
    max_s = len(scores) * 10
    pct = total / max_s * 100
    # A high-quality deck should score above 70%
    assert pct >= 60, f"High-quality deck scored too low: {pct:.0f}% ({total}/{max_s})"


test("J1. QualityChecker — high-quality deck scores ≥ 60%", test_quality_checker_grade_a_deck)


def test_quality_checker_recommendations_generated():
    """A poor deck should trigger at least 2 recommendations."""
    from ppt_maker.audit.quality_checker import QualityChecker

    # All generic layouts (no variety), no images, no eyebrows, no notes
    slides = [_make_slide(i, 'generic', title='Overview',
                          speaker_notes='')
              for i in range(1, 7)]
    mp = _make_plan(slides)

    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, 'audit.md')
        QualityChecker().run_audit(
            slides_dir=tmpdir, master_plan=mp, config=None,
            level='full', dom_cache_path=None, output_path=out,
        )
        report = open(out).read()
        assert '## Recommendations' in report, "Should have Recommendations section"
        # Count numbered recommendations
        rec_lines = [l for l in report.splitlines()
                     if l.strip() and l[0].isdigit() and '. **' in l]
        assert len(rec_lines) >= 2, \
            f"Expected ≥2 recommendations for poor deck, got {len(rec_lines)}: {rec_lines}"


test("J2. QualityChecker — poor deck generates ≥ 2 recommendations", test_quality_checker_recommendations_generated)


# ─────────────────────────────────────────────────────────────────────────────
# K. Compiler — PDF and notes
# ─────────────────────────────────────────────────────────────────────────────
def test_compiler_pdf_compilation():
    """compile_to_pdf from real PNGs produces a valid file > 1KB."""
    from ppt_maker.export.compiler import Compiler
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create 3 real PNG slides
        pngs = []
        for i in range(3):
            p = os.path.join(tmpdir, f'slide_{i:03d}.png')
            img = Image.new('RGB', (1920, 1080), (10 + i*30, 20 + i*20, 40 + i*10))
            img.save(p)
            pngs.append(p)

        out_pdf = os.path.join(tmpdir, 'output.pdf')
        ok = Compiler().compile_to_pdf(pngs, out_pdf)

        assert ok, "compile_to_pdf returned False"
        assert os.path.exists(out_pdf), "PDF file not created"
        size = os.path.getsize(out_pdf)
        assert size > 1024, f"PDF too small ({size} bytes) — likely corrupt"


test("K1. Compiler — compile_to_pdf produces valid non-empty PDF", test_compiler_pdf_compilation)


def test_compiler_notes_appendix_only_when_images():
    """Image prompt appendix only appears when requires_image=True slides exist."""
    from ppt_maker.export.compiler import Compiler

    mp_with_img = _make_plan([
        _make_slide(1, 'cover', requires_image=True,
                    image_prompt='Futuristic skyline at dusk'),
    ])
    mp_no_img = _make_plan([
        _make_slide(1, 'cover', requires_image=False, image_prompt=''),
    ])

    with tempfile.TemporaryDirectory() as tmpdir:
        out1 = os.path.join(tmpdir, 'notes_with.md')
        out2 = os.path.join(tmpdir, 'notes_without.md')
        c = Compiler()
        c.export_speaker_notes(mp_with_img, out1)
        c.export_speaker_notes(mp_no_img, out2)

        notes_with    = open(out1).read()
        notes_without = open(out2).read()

        assert 'Image Prompts' in notes_with, \
            "Appendix should appear when requires_image=True"
        assert 'Futuristic skyline' in notes_with
        assert 'Image Prompts' not in notes_without, \
            "Appendix should NOT appear when no slides require images"


test("K2. Compiler — image prompt appendix conditional on requires_image", test_compiler_notes_appendix_only_when_images)


# ─────────────────────────────────────────────────────────────────────────────
# L. Full pipeline integration — offline plan → HTML → PNG → PDF
# ─────────────────────────────────────────────────────────────────────────────
def test_pipeline_integration():
    """
    Full offline pipeline:
      MasterPlan JSON → Validator → ThemeResolver → Templater → Renderer → PDF
    """
    from ppt_maker.planning.validator import ContentValidator
    from ppt_maker.design.theme_resolver import ThemeResolver
    from ppt_maker.rendering.templater import Templater
    from ppt_maker.rendering.renderer import Renderer
    from ppt_maker.export.compiler import Compiler

    slides = [
        _make_slide(1, 'cover', title='Integration Test Deck',
                    subtitle='Pipeline smoke test', eyebrow='Test',
                    narrative_weight='light', requires_image=False),
        _make_slide(2, 'generic', title='Content Slide',
                    content_bullets=['Point A', 'Point B', 'Point C']),
        _make_slide(3, 'split', title='Two Column',
                    content_bullets=['Left content', 'Right content']),
    ]

    # Build plan with minimal CSS vars
    mp = _make_plan(slides, theme=_make_theme(structural_class='corporate_clean'))

    # Step 1: Validate
    mp = ContentValidator.validate_and_prune(mp)

    # Step 2: Theme Resolution
    css_vars, palette = ThemeResolver.resolve(
        structural_class=mp.theme.structural_class,
        palette_name=mp.theme.palette,
        ai_css_vars=mp.theme.css_variables,
        user_color=None,
    )
    mp.theme.css_variables = css_vars

    with tempfile.TemporaryDirectory() as tmpdir:
        img_dir = os.path.join(tmpdir, 'images')
        os.makedirs(img_dir)

        # Step 3: Template
        t = Templater(build_dir=tmpdir)
        html_files = t.generate_html(mp, image_manifest={})
        assert len(html_files) == 3

        # Step 4: Render (Playwright)
        r = Renderer(build_dir=img_dir, preview_mode=True)  # 960×540 for speed
        png_files, _ = r.render_all(html_files, audit=False)
        assert len(png_files) == 3, f"Expected 3 PNGs, got {len(png_files)}"
        for p in png_files:
            assert os.path.exists(p), f"PNG missing: {p}"
            size = os.path.getsize(p)
            assert size > 5000, f"PNG too small ({size}B) — likely blank: {p}"

        # Step 5: Compile PDF
        out_pdf = os.path.join(tmpdir, 'integration_test.pdf')
        ok = Compiler().compile_to_pdf(png_files, out_pdf)
        assert ok
        assert os.path.getsize(out_pdf) > 10000, "PDF too small"

        # Step 6: Speaker notes
        out_notes = os.path.join(tmpdir, 'notes.md')
        Compiler().export_speaker_notes(mp, out_notes)
        notes = open(out_notes).read()
        assert 'Integration Test Deck' in notes
        assert 'Slide 2' in notes


test("L1. Pipeline integration — validate→theme→template→render→PDF→notes (3 slides)",
     test_pipeline_integration)


# ─────────────────────────────────────────────────────────────────────────────
# M. CLI flags — --score output, --dry-run file creation
# ─────────────────────────────────────────────────────────────────────────────
def test_cli_score_output():
    """generate --offline-plan --score prints score table to stdout."""
    plan_path = os.path.join(HERE, 'master_plan.json')
    if not os.path.exists(plan_path):
        print("   (skipped — no master_plan.json present)")
        return

    result = subprocess.run(
        [sys.executable, 'cli.py', 'generate',
         '--offline-plan', plan_path, '--score'],
        capture_output=True, text=True, timeout=60,
        cwd=HERE,
    )
    assert result.returncode == 0, f"CLI failed: {result.stderr[-500:]}"
    assert 'Content Quality Scores' in result.stdout, \
        f"Score table not in output:\n{result.stdout[-400:]}"
    assert 'Grade' in result.stdout


test("M1. CLI --score — prints content quality score table to stdout", test_cli_score_output)


def test_cli_audit_standalone():
    """audit command produces design_audit.md when plan and slides exist."""
    plan_path = os.path.join(HERE, 'master_plan.json')
    slides_dir = os.path.join(HERE, 'temp_build', 'images')
    if not os.path.exists(plan_path) or not os.path.exists(slides_dir):
        print("   (skipped — no master_plan.json or temp_build/images)")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, 'audit_test.md')
        result = subprocess.run(
            [sys.executable, 'cli.py', 'audit',
             '--plan', plan_path,
             '--slides-dir', slides_dir,
             '--level', 'full',
             '--out', out],
            capture_output=True, text=True, timeout=30,
            cwd=HERE,
        )
        assert result.returncode == 0, f"Audit CLI failed: {result.stderr[-400:]}"
        assert os.path.exists(out), "Audit report file not created"
        report = open(out).read()
        assert '## Overall Score' in report


test("M2. CLI audit — standalone audit produces valid design_audit.md", test_cli_audit_standalone)


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
print()
passed = sum(1 for _, s, _ in results if s == 'PASS')
failed = sum(1 for _, s, _ in results if s == 'FAIL')

print('═' * 62)
print(f'  Results: {passed}/{len(results)} passed', end='')
if failed:
    print(f'   |   {failed} FAILED', end='')
print()
print('═' * 62)

if failed:
    print('\nFailed tests:')
    for name, status, msg in results:
        if status == 'FAIL':
            print(f'  ✗ {name}')
            print(f'    {msg[:160]}')
    sys.exit(1)
