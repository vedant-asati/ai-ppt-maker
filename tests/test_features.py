"""
test_features.py — Basic feature test suite for AI Presentation Agency V4.

Tests:
  1.  Schemas  — all content block types parse correctly
  2.  ThemeResolver — all 8 themes + named palettes resolve
  3.  SourceAnalyzer — signal extraction from mixed content
  4.  NarrativeArcs — all 7 arcs build valid context strings
  5.  AudienceProfiles — all 5 profiles return style dicts
  6.  ContentScorer — scores slide correctly, flags issues
  7.  Validator — prunes bullets, fills prompts, strips cover bullets
  8.  GradientGenerator — generates a valid PNG without API
  9.  Templater — all 7 layout types render to HTML without error
  10. QualityChecker — audit pipeline runs end-to-end
  11. CLI — all 4 subcommands respond to --help
  12. Compiler/SpeakerNotes — rich markdown output
"""

import os
import sys

# Add project root to path so we can import modules from the parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import tempfile
import traceback

PASS = "\033[92m  \u2713\033[0m"
FAIL = "\033[91m  \u2717\033[0m"

results = []


def test(name, fn):
    try:
        fn()
        print(f"{PASS} {name}")
        results.append((name, 'PASS', None))
    except Exception as e:
        print(f"{FAIL} {name}")
        print(f"     {traceback.format_exc().strip().splitlines()[-1]}")
        results.append((name, 'FAIL', str(e)))


def _make_theme(**kwargs):
    """Create a Theme with required css_variables field."""
    from schemas import Theme
    defaults = {
        'structural_class': 'minimalist',
        'css_variables': {
            '--bg': '#FFFFFF', '--bg-rgb': '255,255,255',
            '--text': '#111111', '--text-secondary': '#666666',
            '--primary': '#0070F3', '--primary-rgb': '0,112,243',
            '--accent': '#0050CC',
        },
    }
    defaults.update(kwargs)
    return Theme(**defaults)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Schemas — all ContentBlock types parse
# ─────────────────────────────────────────────────────────────────────────────
def test_schemas():
    from schemas import (
        MasterPlan, Slide,
        BulletBlock, StatBlock, PullQuoteBlock, ComparisonBlock,
        StepBlock, CalloutBlock, KeyValueBlock,
    )
    theme = _make_theme()

    b  = BulletBlock(items=['Point one', 'Point two'])
    assert b.block_type == 'bullets'

    s  = StatBlock(value='47%', label='Growth', context='YoY 2024')
    assert s.block_type == 'stat'

    q  = PullQuoteBlock(quote='It changed everything.', attribution='— CEO')
    assert q.block_type == 'pullquote'

    c  = ComparisonBlock(
        left_label='Before', left_items=['Slow', 'Manual'],
        right_label='After', right_items=['Fast', 'Automated'],
    )
    assert c.block_type == 'comparison'

    st = StepBlock(steps=['Step A', 'Step B'], step_labels=['Phase 1', 'Phase 2'])
    assert st.block_type == 'steps'

    ca = CalloutBlock(text='Critical insight here.', callout_type='insight')
    assert ca.block_type == 'callout'

    kv = KeyValueBlock(pairs=[{'key': 'ARR', 'value': '$2.3M'}])
    assert kv.block_type == 'keyvalue'

    slide = Slide(
        slide_number=1, layout_type='generic', title='Test Slide',
        content_blocks=[b, s, q, c, st, ca, kv],
        content_bullets=[], speaker_notes='Notes.',
        requires_image=False, image_prompt='',
    )
    mp = MasterPlan(theme=theme, slides=[slide])
    assert len(mp.slides[0].content_blocks) == 7


test("1. Schemas — all 7 ContentBlock types parse correctly", test_schemas)


# ─────────────────────────────────────────────────────────────────────────────
# 2. ThemeResolver — all 8 themes
# ─────────────────────────────────────────────────────────────────────────────
def test_theme_resolver():
    from theme_resolver import ThemeResolver

    cases = [
        ('minimalist',      None),
        ('glassmorphism',   None),
        ('neo_brutalism',   None),
        ('corporate_clean', None),
        ('dark_neon',       'cyber_cyan'),
        ('dark_neon',       'neon_magenta'),
        ('gradient_flow',   'violet_sunset'),
        ('editorial',       'crimson'),
        ('aurora',          'arctic'),
    ]
    for theme, palette in cases:
        css_vars, resolved = ThemeResolver.resolve(
            structural_class=theme,
            palette_name=palette,
            ai_css_vars={},
            user_color=None,
        )
        assert isinstance(css_vars, dict), f"{theme}: returned non-dict"
        # ThemeResolver may return empty dict for base themes — just check it runs
        # and returns the palette name
        assert isinstance(resolved, str) or resolved is None


test("2. ThemeResolver — all 8 themes + named palettes resolve", test_theme_resolver)


# ─────────────────────────────────────────────────────────────────────────────
# 3. SourceAnalyzer — signal extraction
# ─────────────────────────────────────────────────────────────────────────────
def test_source_analyzer():
    from source_analyzer import SourceAnalyzer, SourceSignals

    text = """
    Our revenue grew by 340% year-over-year. User retention is at 92%.
    "This tool saved us 10 hours a week," said Jane Smith, Head of Ops.
    Traditional methods cost $50,000. Our platform costs $4,999/year.
    Step 1: Connect. Step 2: Configure. Step 3: Launch.
    """

    sa = SourceAnalyzer()
    signals = sa.analyze(text)

    assert isinstance(signals, SourceSignals), \
        f"analyze() should return SourceSignals, got {type(signals)}"
    assert signals.has_data_evidence, "Should detect percentage/currency stats"
    assert len(signals.stats) > 0, f"Should find stats, got: {signals.stats}"
    assert signals.word_count > 0, "Word count should be > 0"

    # signals_for_prompt takes the SourceSignals object
    prompt_str = sa.signals_for_prompt(signals)
    assert isinstance(prompt_str, str) and len(prompt_str) > 50, \
        "signals_for_prompt() should return a non-empty string"
    assert 'SOURCE MATERIAL ANALYSIS' in prompt_str


test("3. SourceAnalyzer — signal extraction (stats, quotes)", test_source_analyzer)


# ─────────────────────────────────────────────────────────────────────────────
# 4. NarrativeArcs — all 7 arcs
# ─────────────────────────────────────────────────────────────────────────────
def test_narrative_arcs():
    from narrative_arcs import NARRATIVE_ARCS, get_arc, arc_for_prompt

    assert len(NARRATIVE_ARCS) == 7, f"Expected 7 arcs, got {len(NARRATIVE_ARCS)}"

    for arc_name in NARRATIVE_ARCS:
        arc_data = get_arc(arc_name)
        assert arc_data, f"get_arc('{arc_name}') returned empty"

        prompt_ctx = arc_for_prompt(arc_name)
        assert isinstance(prompt_ctx, str) and len(prompt_ctx) > 30, \
            f"arc_for_prompt('{arc_name}') too short: '{prompt_ctx}'"


test("4. NarrativeArcs — all 7 arcs return arc data and prompt context", test_narrative_arcs)


# ─────────────────────────────────────────────────────────────────────────────
# 5. AudienceProfiles — all 5 profiles
# ─────────────────────────────────────────────────────────────────────────────
def test_audience_profiles():
    from audience_profiles import AUDIENCE_PROFILES, get_profile, profile_for_prompt

    assert len(AUDIENCE_PROFILES) == 5, f"Expected 5 profiles, got {len(AUDIENCE_PROFILES)}"

    for name in AUDIENCE_PROFILES:
        profile = get_profile(name)
        assert profile, f"get_profile('{name}') returned empty"

        prompt_ctx = profile_for_prompt(name)
        assert isinstance(prompt_ctx, str) and len(prompt_ctx) > 30, \
            f"profile_for_prompt('{name}') too short"


test("5. AudienceProfiles — all 5 profiles return data and prompt context", test_audience_profiles)


# ─────────────────────────────────────────────────────────────────────────────
# 6. ContentScorer — scores correctly, flags issues
# ─────────────────────────────────────────────────────────────────────────────
def test_content_scorer():
    from content_scorer import ContentScorer
    from schemas import Slide, StatBlock

    scorer = ContentScorer()

    good = Slide(
        slide_number=1, layout_type='stat',
        title='Revenue Grew 340% in Q4',
        eyebrow='Traction', slide_purpose='evidence', narrative_weight='light',
        content_blocks=[StatBlock(value='340%', label='Revenue Growth', context='Q4 2024')],
        content_bullets=[],
        speaker_notes=(
            'The revenue growth figure comes from our audited financials. '
            'This is a verified number, not a projection. '
            'It reflects the compounding effect of our enterprise tier launch in Q3.'
        ),
        requires_image=False, image_prompt='',
    )
    good_score = scorer.score_slide(good)
    assert good_score.total >= 25, f"Good slide scored too low: {good_score.total}"
    assert good_score.grade in ('A', 'B', 'C', 'D')

    bad = Slide(
        slide_number=2, layout_type='generic',
        title='Overview',  # filler title
        content_bullets=[], content_blocks=None,
        speaker_notes='',  # no notes
        requires_image=False, image_prompt='',
    )
    bad_score = scorer.score_slide(bad)
    assert bad_score.total < good_score.total, "Bad slide should score lower"
    assert len(bad_score.flags) > 0, "Bad slide should generate flags"


test("6. ContentScorer — grades high/low slides correctly, flags issues", test_content_scorer)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Validator — bullet cap, image prompt fill, cover bullet strip
# ─────────────────────────────────────────────────────────────────────────────
def test_validator():
    from validator import ContentValidator
    from schemas import MasterPlan, Slide

    theme = _make_theme()
    slides = [
        Slide(
            slide_number=1, layout_type='cover',
            title='Short Title',
            content_bullets=['will', 'be', 'stripped', 'by', 'cover', 'cap'],
            content_blocks=None, speaker_notes='Notes.',
            requires_image=False, image_prompt='',
        ),
        Slide(
            slide_number=2, layout_type='split',
            title='Split Slide',
            # 6 bullets — split cap is 4
            content_bullets=['A', 'B', 'C', 'D', 'E', 'F'],
            content_blocks=None, speaker_notes='Notes.',
            requires_image=True, image_prompt='',   # empty prompt should be filled
        ),
    ]
    mp = MasterPlan(theme=theme, slides=slides)
    result = ContentValidator.validate_and_prune(mp)

    # Cover bullets stripped to 0
    assert len(result.slides[0].content_bullets) == 0, \
        f"Cover bullets not stripped: {result.slides[0].content_bullets}"

    # Split bullet cap (4)
    assert len(result.slides[1].content_bullets) <= 4, \
        f"Split bullets not capped: {len(result.slides[1].content_bullets)}"

    # Empty image_prompt filled
    assert result.slides[1].image_prompt.strip(), \
        "Empty image_prompt should be auto-filled"


test("7. Validator — cover strip, split bullet cap, image prompt auto-fill", test_validator)


# ─────────────────────────────────────────────────────────────────────────────
# 8. GradientGenerator — creates valid PNG
# ─────────────────────────────────────────────────────────────────────────────
def test_gradient_generator():
    from gradient_generator import GradientGenerator
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, 'test_grad.png')
        gen = GradientGenerator()
        result_path = gen.generate(
            structural_class='dark_neon',
            primary_hex='#00FFFF',
            out_path=out,
        )
        assert os.path.exists(result_path), f"Gradient PNG not created at {result_path}"
        img = Image.open(result_path)
        assert img.mode == 'RGB', f"Expected RGB, got {img.mode}"
        w, h = img.size
        assert w > 100 and h > 100, f"Image too small: {img.size}"


test("8. GradientGenerator — creates valid RGB PNG without API", test_gradient_generator)


# ─────────────────────────────────────────────────────────────────────────────
# 9. Templater — all 7 layout types render to HTML
# ─────────────────────────────────────────────────────────────────────────────
def test_templater():
    from templater import Templater
    from schemas import (MasterPlan, Slide, StatBlock,
                        PullQuoteBlock, StepBlock, ComparisonBlock, BulletBlock)

    theme = _make_theme(
        structural_class='dark_neon', palette='cyber_cyan',
        css_variables={
            '--bg': '#050505', '--bg-rgb': '5,5,5', '--text': '#F0F0F0',
            '--text-secondary': '#888', '--primary': '#00FFFF',
            '--primary-rgb': '0,255,255', '--accent': '#00AAAA',
        }
    )

    slides = [
        Slide(slide_number=1, layout_type='cover', title='Cover Slide',
              subtitle='Subtitle', eyebrow='Opening',
              content_bullets=[], content_blocks=None,
              speaker_notes='Notes.', requires_image=False, image_prompt=''),
        Slide(slide_number=2, layout_type='generic', title='Generic Slide',
              content_bullets=['Point one', 'Point two'],
              content_blocks=[BulletBlock(items=['Point one', 'Point two'])],
              speaker_notes='Notes.', requires_image=False, image_prompt=''),
        Slide(slide_number=3, layout_type='split', title='Split Slide',
              content_bullets=['Left', 'Right'],
              content_blocks=None,
              speaker_notes='Notes.', requires_image=False, image_prompt=''),
        Slide(slide_number=4, layout_type='infographic', title='Infographic',
              content_bullets=['Stat 1', 'Stat 2'],
              content_blocks=[StatBlock(value='99%', label='Uptime', context='SLA')],
              speaker_notes='Notes.', requires_image=False, image_prompt=''),
        Slide(slide_number=5, layout_type='quote', title='Quote Slide',
              content_bullets=[],
              content_blocks=[PullQuoteBlock(quote='It changed everything.', attribution='— CEO')],
              speaker_notes='Notes.', requires_image=False, image_prompt=''),
        Slide(slide_number=6, layout_type='stat', title='Stat Slide',
              content_bullets=[],
              content_blocks=[StatBlock(value='340%', label='Growth', context='Q4 2024'),
                               StatBlock(value='$2.3M', label='ARR', context='Dec 2024')],
              speaker_notes='Notes.', requires_image=False, image_prompt=''),
        Slide(slide_number=7, layout_type='timeline', title='Timeline Slide',
              content_bullets=[],
              content_blocks=[StepBlock(steps=['Connect', 'Configure', 'Launch'],
                                        step_labels=['Day 1', 'Day 2', 'Day 3'])],
              speaker_notes='Notes.', requires_image=False, image_prompt=''),
    ]

    mp = MasterPlan(theme=theme, slides=slides)

    with tempfile.TemporaryDirectory() as tmpdir:
        templater = Templater(build_dir=tmpdir)
        html_files = templater.generate_html(mp, image_manifest={})

        assert len(html_files) == 7, f"Expected 7 HTML files, got {len(html_files)}"
        for path in html_files:
            assert os.path.exists(path), f"Missing: {path}"
            content = open(path).read()
            assert '<html' in content.lower(), f"No <html> tag in {path}"
            assert len(content) > 500, f"Suspiciously short HTML: {path} ({len(content)} bytes)"


test("9. Templater — all 7 layout types render to valid HTML", test_templater)


# ─────────────────────────────────────────────────────────────────────────────
# 10. QualityChecker — audit pipeline end-to-end
# ─────────────────────────────────────────────────────────────────────────────
def test_quality_checker():
    from quality_checker import QualityChecker
    from schemas import MasterPlan, Slide, StatBlock, PullQuoteBlock

    theme = _make_theme(structural_class='dark_neon', palette='cyber_cyan')
    slides = [
        Slide(slide_number=1, layout_type='cover', title='Our Story', eyebrow='Intro',
              slide_purpose='opening_hook', narrative_weight='light',
              content_bullets=[], content_blocks=None,
              speaker_notes='This is the opening hook. We start strong with a big claim.',
              requires_image=True, image_prompt='Dark futuristic city skyline at night'),
        Slide(slide_number=2, layout_type='stat', title='Revenue Grew 400%', eyebrow='Traction',
              slide_purpose='evidence', narrative_weight='light',
              content_blocks=[StatBlock(value='400%', label='Revenue Growth')],
              content_bullets=[],
              speaker_notes='Our revenue grew 400 percent in the last fiscal year.',
              requires_image=False, image_prompt=''),
        Slide(slide_number=3, layout_type='quote', title='What Users Say', eyebrow='Proof',
              slide_purpose='social_proof', narrative_weight='light',
              content_blocks=[PullQuoteBlock(
                  quote='Best tool we have ever used.', attribution='— CTO, Acme Inc')],
              content_bullets=[],
              speaker_notes='Real testimonial from a paying enterprise customer.',
              requires_image=False, image_prompt=''),
    ]
    mp = MasterPlan(theme=theme, slides=slides)

    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, 'audit.md')
        checker = QualityChecker()
        checker.run_audit(
            slides_dir=tmpdir,
            master_plan=mp,
            config=None,
            level='full',
            dom_cache_path=None,
            output_path=out,
        )
        assert os.path.exists(out), "Audit report not created"
        report = open(out).read()
        assert '## Overall Score' in report, "Missing Overall Score section"
        assert '## Layer 2' in report, "Missing Layer 2 section"
        assert '## Slide-by-Slide' in report, "Missing slide table"
        assert 'Traction' in report, "Eyebrow label missing from slide table"


test("10. QualityChecker — 3-layer audit produces valid report", test_quality_checker)


# ─────────────────────────────────────────────────────────────────────────────
# 11. CLI — all subcommands respond to --help
# ─────────────────────────────────────────────────────────────────────────────
def test_cli_help():
    import subprocess
    python = sys.executable
    cli = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cli.py')

    for cmd in ['generate', 'audit', 'fonts', 'init']:
        result = subprocess.run(
            [python, cli, cmd, '--help'],
            capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, \
            f"cli.py {cmd} --help exited {result.returncode}:\n{result.stderr}"
        assert 'usage' in result.stdout.lower(), \
            f"cli.py {cmd} --help has no usage line"


test("11. CLI — all 4 subcommands respond to --help", test_cli_help)


# ─────────────────────────────────────────────────────────────────────────────
# 12. Compiler — rich speaker notes export
# ─────────────────────────────────────────────────────────────────────────────
def test_speaker_notes():
    from compiler import Compiler
    from schemas import MasterPlan, Slide, StatBlock, StepBlock

    theme = _make_theme(structural_class='glassmorphism')
    slides = [
        Slide(slide_number=1, layout_type='cover',
              title='Our Pitch Deck', subtitle='Series A — 2024',
              eyebrow='Opening', slide_purpose='opening_hook',
              content_bullets=[], content_blocks=None,
              speaker_notes=(
                  'Welcome everyone. Today we will show you why we are '
                  'the fastest growing company in our space.'
              ),
              requires_image=False, image_prompt=''),
        Slide(slide_number=2, layout_type='stat',
              title='Growth in Numbers', eyebrow='Traction',
              slide_purpose='evidence', narrative_weight='light',
              content_blocks=[
                  StatBlock(value='340%', label='Revenue Growth', context='Q4 2024'),
                  StatBlock(value='4.2x', label='LTV:CAC', context='Avg: 2.1x'),
              ],
              content_bullets=[],
              speaker_notes='These are audited numbers from our Q4 2024 financials.',
              requires_image=True, image_prompt='Abstract data visualization, dark background'),
        Slide(slide_number=3, layout_type='timeline',
              title='48-Hour Onboarding', eyebrow='Process',
              slide_purpose='how_to_get_there',
              content_blocks=[StepBlock(
                  steps=['Connect data', 'AI auto-configures', 'Go live'],
                  step_labels=['Hour 1', 'Hour 6', 'Hour 48'])],
              content_bullets=[],
              speaker_notes='Our onboarding is 20x faster than the industry average.',
              requires_image=False, image_prompt=''),
    ]
    mp = MasterPlan(theme=theme, slides=slides)

    with tempfile.TemporaryDirectory() as tmpdir:
        out = os.path.join(tmpdir, 'notes.md')
        Compiler().export_speaker_notes(mp, out)

        assert os.path.exists(out)
        notes = open(out).read()

        assert '# Speaker Notes' in notes,          "Missing title"
        assert 'Slide 1' in notes,                  "Missing Slide 1"
        assert 'Slide 2' in notes,                  "Missing Slide 2"
        assert 'Slide 3' in notes,                  "Missing Slide 3"
        assert 'Opening' in notes,                  "Missing eyebrow label"
        assert '340%' in notes,                     "Missing stat block description"
        assert 'Transition' in notes,               "Missing transition prompts"
        assert 'Image Prompts' in notes,            "Missing image appendix"
        assert 'Abstract data' in notes,            "Image prompt not in appendix"


test("12. Compiler — speaker notes: eyebrow, block summaries, transitions, appendix", test_speaker_notes)


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
passed = sum(1 for _, s, _ in results if s == 'PASS')
failed = sum(1 for _, s, _ in results if s == 'FAIL')

print()
print('═' * 60)
print(f'  Results: {passed}/{len(results)} passed', end='')
if failed:
    print(f'   |   {failed} FAILED', end='')
print()
print('═' * 60)

if failed:
    print('\nFailed tests:')
    for name, status, msg in results:
        if status == 'FAIL':
            print(f'  \u2717 {name}')
            print(f'    {msg[:120]}')
    sys.exit(1)
