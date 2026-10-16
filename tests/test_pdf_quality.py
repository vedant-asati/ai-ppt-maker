"""
test_pdf_quality.py — Generate 5 themed PDF decks for visual quality inspection.

Usage:
    python tests/test_pdf_quality.py

Output:
    test_output/
    ├── test1_yoga_dark_neon/       (6 slides, user images)
    ├── test2_unity_editorial/      (5 slides, user images)
    ├── test3_spiritual_glassmorphism/ (5 slides, user images)
    ├── test4_cyber_corporate/      (5 slides, gradient-only)
    ├── test5_iks_aurora/           (5 slides, gradient-only)
    └── summary_report.md
"""

import os
import sys
import time
import shutil

# Add project root to path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from PIL import Image
from ppt_maker.core.schemas import (
    MasterPlan, Slide, Theme,
    StatBlock, PullQuoteBlock, StepBlock, ComparisonBlock,
    BulletBlock, CalloutBlock, KeyValueBlock,
)
from ppt_maker.planning.validator import ContentValidator
from ppt_maker.design.theme_resolver import ThemeResolver
from ppt_maker.rendering.templater import Templater
from ppt_maker.rendering.renderer import Renderer
from ppt_maker.export.compiler import Compiler
from ppt_maker.audit.quality_checker import QualityChecker
from ppt_maker.planning.content_scorer import ContentScorer
from ppt_maker.design.gradient_generator import GradientGenerator

TEMP_DIR = os.path.join(_PROJECT_ROOT, 'temp')
OUTPUT_DIR = os.path.join(_PROJECT_ROOT, 'test_output')


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _img(name):
    """Resolve an image path from temp/."""
    return os.path.join(TEMP_DIR, name)


def _prepare_image(src_path, dest_path, target_w=1920, target_h=1080):
    """
    Copy and resize a user image to slide dimensions.
    Maintains aspect ratio and pads/crops to target size.
    """
    img = Image.open(src_path).convert('RGB')
    # Scale to cover target dimensions
    scale = max(target_w / img.width, target_h / img.height)
    new_w = int(img.width * scale)
    new_h = int(img.height * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    # Center crop to target
    left = (new_w - target_w) // 2
    top  = (new_h - target_h) // 2
    img = img.crop((left, top, left + target_w, top + target_h))
    img.save(dest_path, quality=95)
    return dest_path


def _make_theme(structural_class, palette=None):
    """Create a Theme with ThemeResolver-resolved CSS vars."""
    css_vars, resolved_palette = ThemeResolver.resolve(
        structural_class=structural_class,
        palette_name=palette,
        ai_css_vars={},
        user_color=None,
    )
    return Theme(
        structural_class=structural_class,
        palette=resolved_palette,
        css_variables=css_vars,
    )


def _build_manifest(slide_image_map, assets_dir):
    """
    Build image manifest from {slide_number: source_image_path_or_None}.
    Copies and resizes images into assets_dir, returns manifest dict.
    For None values, generates a gradient background.
    """
    manifest = {}
    gen = GradientGenerator()

    for slide_num, src in slide_image_map.items():
        dest = os.path.join(assets_dir, f'slide_{slide_num}.png')
        if src and os.path.exists(src):
            _prepare_image(src, dest)
            manifest[slide_num] = {
                'path': os.path.abspath(dest),
                'status': 'user',
                'role': 'background',
            }
        else:
            # Generate gradient fallback
            manifest[slide_num] = {
                'path': '',
                'status': 'none',
                'role': 'background',
            }
    return manifest


def run_deck(name, theme, slides, slide_image_map, output_subdir):
    """
    Run the full pipeline for one test deck:
    Validate → Theme → Prepare Images → Template → Render → PDF + Notes + Audit
    """
    deck_dir = os.path.join(OUTPUT_DIR, output_subdir)
    build_dir = os.path.join(deck_dir, 'build')
    assets_dir = os.path.join(deck_dir, 'assets')
    images_dir = os.path.join(build_dir, 'images')

    os.makedirs(build_dir, exist_ok=True)
    os.makedirs(assets_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)

    print(f'\n{"═" * 60}')
    print(f'  Building: {name}')
    print(f'  Theme:    {theme.structural_class} / {theme.palette or "default"}')
    print(f'  Slides:   {len(slides)}')
    print(f'{"═" * 60}')

    start = time.time()

    # Build MasterPlan
    mp = MasterPlan(theme=theme, slides=slides)

    # Validate
    mp = ContentValidator.validate_and_prune(mp)

    # Prepare images
    manifest = _build_manifest(slide_image_map, assets_dir)

    # Template
    templater = Templater(build_dir=build_dir)
    html_files = templater.generate_html(mp, image_manifest=manifest)

    # Render
    renderer = Renderer(build_dir=images_dir, preview_mode=False)
    png_files, _ = renderer.render_all(html_files, audit=False)

    # Compile PDF
    pdf_path = os.path.join(deck_dir, f'{output_subdir}.pdf')
    Compiler().compile_to_pdf(png_files, pdf_path)

    # Speaker notes
    notes_path = os.path.join(deck_dir, f'{output_subdir}_notes.md')
    Compiler().export_speaker_notes(mp, notes_path)

    # Audit
    audit_path = os.path.join(deck_dir, 'audit_report.md')
    try:
        QualityChecker().run_audit(
            slides_dir=images_dir,
            master_plan=mp,
            config=None,
            level='full',
            dom_cache_path=None,
            output_path=audit_path,
        )
    except Exception as e:
        print(f'  [Warn] Audit failed: {e}')

    # Content scoring
    scorer = ContentScorer()
    scores = scorer.score_all(mp)
    summary = scorer.deck_summary(scores)

    elapsed = time.time() - start
    pdf_size = os.path.getsize(pdf_path) if os.path.exists(pdf_path) else 0

    # Clean up build artifacts (keep only PDF, notes, audit)
    shutil.rmtree(build_dir, ignore_errors=True)
    shutil.rmtree(assets_dir, ignore_errors=True)

    result = {
        'name': name,
        'theme': f"{theme.structural_class}/{theme.palette or 'default'}",
        'slides': len(slides),
        'pdf_path': pdf_path,
        'pdf_size_kb': pdf_size / 1024,
        'notes_path': notes_path,
        'audit_path': audit_path,
        'avg_score': summary.get('avg', 0),
        'grade': summary.get('grade', 'N/A'),
        'elapsed': elapsed,
    }

    print(f'  ✓ PDF: {pdf_size/1024:.0f} KB  |  Score: {result["avg_score"]:.1f}/50 ({result["grade"]})  |  {elapsed:.1f}s')
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Test Deck 1: Yoga & Wellness (dark_neon / cyber_cyan)
# ─────────────────────────────────────────────────────────────────────────────

def build_deck_1():
    theme = _make_theme('dark_neon', 'cyber_cyan')
    slides = [
        Slide(
            slide_number=1, layout_type='cover',
            title='Yoga & Wellness',
            subtitle='Ancient Practice, Global Movement',
            eyebrow='Namaste',
            slide_purpose='opening_hook',
            narrative_weight='light',
            content_bullets=[],
            content_blocks=None,
            speaker_notes='Welcome to this presentation on the global yoga movement. '
                          'Yoga has transcended cultural and geographic borders to become '
                          'a worldwide phenomenon practiced by over 300 million people across 190 countries.',
            requires_image=True,
            image_prompt='Yoga silhouette at sunset',
        ),
        Slide(
            slide_number=2, layout_type='stat',
            title='The $80 Billion Wellness Economy',
            eyebrow='Market Size',
            slide_purpose='evidence',
            narrative_weight='standard',
            content_bullets=[],
            content_blocks=[
                StatBlock(value='$80B', label='Global Yoga Market', context='Projected by 2027'),
                StatBlock(value='300M+', label='Practitioners Worldwide', context='As of 2024'),
                StatBlock(value='72%', label='Report Reduced Stress', context='Clinical studies'),
            ],
            speaker_notes='The yoga industry has seen explosive growth. The global market '
                          'is projected to reach $80 billion by 2027, up from $37 billion in 2020. '
                          'This growth is driven by increasing awareness of mental health and preventive wellness.',
            requires_image=False,
            image_prompt='',
        ),
        Slide(
            slide_number=3, layout_type='split',
            title='Mind, Body & Spirit',
            eyebrow='Benefits',
            slide_purpose='core_message',
            narrative_weight='standard',
            content_bullets=[
                'Reduces cortisol and anxiety by 30-40%',
                'Improves flexibility and joint health',
                'Enhances cardiovascular fitness',
                'Builds mental resilience and focus',
            ],
            content_blocks=[
                BulletBlock(items=[
                    'Reduces cortisol and anxiety by 30-40%',
                    'Improves flexibility and joint health',
                    'Enhances cardiovascular fitness',
                    'Builds mental resilience and focus',
                ]),
            ],
            speaker_notes='Yoga provides a triple benefit: physical fitness, mental clarity, '
                          'and emotional balance. Clinical studies show regular practice reduces cortisol '
                          'levels by 30-40 percent, making it one of the most evidence-backed wellness practices.',
            requires_image=True,
            image_prompt='Meditation class in studio',
        ),
        Slide(
            slide_number=4, layout_type='timeline',
            title='The 12 Steps of Surya Namaskar',
            eyebrow='Practice',
            slide_purpose='how_to_get_there',
            narrative_weight='standard',
            content_bullets=[],
            content_blocks=[
                StepBlock(
                    steps=[
                        'Pranamasana — Mountain Pose',
                        'Hasta Uttanasana — Raised Arms',
                        'Uttanasana — Forward Fold',
                        'Ashwa Sanchalanasana — Lunge',
                        'Chaturanga — Plank',
                        'Ashtanga Namaskara — Eight-Point Salute',
                    ],
                    step_labels=['1', '2', '3', '4', '5', '6'],
                ),
            ],
            speaker_notes='Surya Namaskar is the foundation of most yoga practices. '
                          'These 12 postures flow together in a single sequence that takes 3-5 minutes '
                          'and engages all major muscle groups. It is traditionally performed at sunrise.',
            requires_image=False,
            image_prompt='',
        ),
        Slide(
            slide_number=5, layout_type='quote',
            title='Words of Wisdom',
            eyebrow='Inspiration',
            slide_purpose='social_proof',
            narrative_weight='light',
            content_bullets=[],
            content_blocks=[
                PullQuoteBlock(
                    quote='Arise, awake, and stop not till the goal is reached.',
                    attribution='— Swami Vivekananda',
                ),
            ],
            speaker_notes='Swami Vivekananda was one of the most influential figures in '
                          'bringing yoga and Vedanta philosophy to the Western world. His 1893 Chicago '
                          'speech at the Parliament of Religions remains one of the most quoted addresses in history.',
            requires_image=True,
            image_prompt='Yoga pose at sunrise',
        ),
        Slide(
            slide_number=6, layout_type='generic',
            title='Start Your Journey Today',
            eyebrow='Next Steps',
            slide_purpose='call_to_action',
            narrative_weight='light',
            content_bullets=[],
            content_blocks=[
                CalloutBlock(
                    text='Begin with just 15 minutes a day. Consistency matters more than intensity.',
                    callout_type='tip',
                ),
                KeyValueBlock(pairs=[
                    {'key': 'Best Time', 'value': 'Early morning (Brahma Muhurta)'},
                    {'key': 'Minimum Duration', 'value': '15 minutes daily'},
                    {'key': 'Starter Style', 'value': 'Hatha Yoga'},
                    {'key': 'Equipment', 'value': 'Just a mat'},
                ]),
            ],
            speaker_notes='The key message: start small, stay consistent. Hatha yoga is the '
                          'best entry point for beginners because of its slow, deliberate pace. '
                          'Even 15 minutes daily produces measurable health benefits within eight weeks of regular practice.',
            requires_image=True,
            image_prompt='Person doing yoga outdoors',
        ),
    ]

    image_map = {
        1: _img('fd.jpg'),       # yoga silhouette sunset
        2: None,                  # gradient (stat slide)
        3: _img('cv.jpeg'),      # meditation class
        4: None,                  # gradient (timeline)
        5: _img('fg.jpeg'),      # lotus pose silhouette
        6: _img('gd.jpeg'),      # yoga in nature
    }

    return run_deck('Yoga & Wellness', theme, slides, image_map, 'test1_yoga_dark_neon')


# ─────────────────────────────────────────────────────────────────────────────
# Test Deck 2: Unity in Diversity (editorial / crimson)
# ─────────────────────────────────────────────────────────────────────────────

def build_deck_2():
    theme = _make_theme('editorial', 'crimson')
    slides = [
        Slide(
            slide_number=1, layout_type='cover',
            title='Unity in Diversity',
            subtitle='The Soul of India',
            eyebrow='Bharat',
            slide_purpose='opening_hook',
            narrative_weight='light',
            content_bullets=[],
            content_blocks=None,
            speaker_notes='India is the world\'s largest democracy and one of its most diverse nations. '
                          'This presentation explores how India\'s diversity is its greatest strength, '
                          'binding 1.4 billion people across 28 states, 22 languages, and six major religions.',
            requires_image=True,
            image_prompt='Cultural map of India',
        ),
        Slide(
            slide_number=2, layout_type='infographic',
            title='India by the Numbers',
            eyebrow='Scale',
            slide_purpose='evidence',
            narrative_weight='standard',
            content_bullets=['22 official languages', '6 major religions', '28 states & 8 UTs'],
            content_blocks=[
                StatBlock(value='1.4B', label='Population', context='World\'s most populous nation'),
                StatBlock(value='22', label='Official Languages', context='Scheduled in Constitution'),
                StatBlock(value='2,000+', label='Ethnic Groups', context='Anthropological Survey'),
            ],
            speaker_notes='India\'s Constitution recognizes 22 official languages, but over 19,500 '
                          'dialects are spoken across the country. The Anthropological Survey of India '
                          'has documented over 2,000 distinct ethnic groups, making it the most diverse nation on Earth.',
            requires_image=True,
            image_prompt='Unity hands around globe',
        ),
        Slide(
            slide_number=3, layout_type='split',
            title='North Meets South',
            eyebrow='Contrast',
            slide_purpose='core_message',
            narrative_weight='standard',
            content_bullets=[],
            content_blocks=[
                ComparisonBlock(
                    left_label='North India',
                    left_items=['Roti & Paratha', 'Hindi & Urdu', 'Bollywood', 'Wheat-based cuisine'],
                    right_label='South India',
                    right_items=['Rice & Dosa', 'Tamil, Telugu, Kannada', 'Tollywood & Kollywood', 'Rice-based cuisine'],
                ),
            ],
            speaker_notes='The cultural divide between North and South India is one of the richest '
                          'examples of diversity within unity. Despite differences in language and food, '
                          'shared festivals like Diwali unite the nation.',
            requires_image=True,
            image_prompt='Indian culture collage',
        ),
        Slide(
            slide_number=4, layout_type='quote',
            title='The Iron Man\'s Vision',
            eyebrow='Legacy',
            slide_purpose='social_proof',
            narrative_weight='light',
            content_bullets=[],
            content_blocks=[
                PullQuoteBlock(
                    quote='Manpower without unity is not a strength unless it is harmonized '
                          'and united properly, then it becomes a spiritual power.',
                    attribution='— Sardar Vallabhbhai Patel',
                ),
            ],
            speaker_notes='Sardar Patel, the Iron Man of India, unified 562 princely states '
                          'into the Indian Union after independence in 1947. His diplomatic skill '
                          'prevented the Balkanization of India and created the unified nation we know today.',
            requires_image=True,
            image_prompt='Sardar Patel statue',
        ),
        Slide(
            slide_number=5, layout_type='generic',
            title='Festivals That Unite',
            eyebrow='Celebration',
            slide_purpose='evidence',
            narrative_weight='standard',
            content_bullets=[],
            content_blocks=[
                KeyValueBlock(pairs=[
                    {'key': 'Diwali', 'value': 'Festival of Lights — celebrated by Hindus, Sikhs, Jains'},
                    {'key': 'Eid', 'value': 'Marks end of Ramadan — celebrated across India'},
                    {'key': 'Christmas', 'value': '25 million Christians celebrate nationwide'},
                    {'key': 'Pongal', 'value': 'Harvest festival of Tamil Nadu'},
                    {'key': 'Baisakhi', 'value': 'Sikh New Year and harvest festival'},
                ]),
            ],
            speaker_notes='India celebrates more festivals than any other country on Earth. '
                          'What makes India unique is that people of all faiths participate in each other\'s celebrations.',
            requires_image=True,
            image_prompt='Indian flag with people',
        ),
    ]

    image_map = {
        1: _img('c.jpeg'),        # Unity in Diversity map
        2: _img('s.jpeg'),        # global diversity hands
        3: _img('images.jpeg'),   # Indian culture collage
        4: _img('xz.jpeg'),      # Sardar Patel quote
        5: _img('a.jpeg'),       # people with Indian flag
    }

    return run_deck('Unity in Diversity', theme, slides, image_map, 'test2_unity_editorial')


# ─────────────────────────────────────────────────────────────────────────────
# Test Deck 3: Spiritual Leaders (glassmorphism)
# ─────────────────────────────────────────────────────────────────────────────

def build_deck_3():
    theme = _make_theme('glassmorphism')
    slides = [
        Slide(
            slide_number=1, layout_type='cover',
            title='Spiritual Leaders of India',
            subtitle='Timeless Wisdom for a Modern World',
            eyebrow='Heritage',
            slide_purpose='opening_hook',
            narrative_weight='light',
            content_bullets=[],
            content_blocks=None,
            speaker_notes='India has been the birthplace of some of the world\'s most influential '
                          'spiritual thinkers. Their teachings continue to shape global consciousness '
                          'and have built organizations spanning over 180 countries with millions of practitioners.',
            requires_image=True,
            image_prompt='Swami Vivekananda portrait',
        ),
        Slide(
            slide_number=2, layout_type='generic',
            title='A Legacy of Enlightenment',
            eyebrow='Overview',
            slide_purpose='core_message',
            narrative_weight='standard',
            content_bullets=[],
            content_blocks=[
                BulletBlock(items=[
                    'Swami Vivekananda — Introduced Vedanta to the West at 1893 Chicago Parliament',
                    'Paramahansa Yogananda — Brought Kriya Yoga to America in 1920',
                    'Sri Aurobindo — Philosopher, poet, and independence activist',
                    'Sadhguru — 42M+ followers, Inner Engineering practiced globally',
                    'Sri Sri Ravi Shankar — Art of Living Foundation in 180+ countries',
                ]),
            ],
            speaker_notes='These five leaders represent different eras but share a common thread: '
                          'making ancient Indian wisdom accessible to modern audiences worldwide. '
                          'Their combined influence reaches hundreds of millions of people across every continent.',
            requires_image=True,
            image_prompt='Top spiritual leaders of India',
        ),
        Slide(
            slide_number=3, layout_type='quote',
            title='The Chicago Address, 1893',
            eyebrow='Historic Moment',
            slide_purpose='social_proof',
            narrative_weight='light',
            content_bullets=[],
            content_blocks=[
                PullQuoteBlock(
                    quote='I am proud to belong to a religion which has taught the world '
                          'both tolerance and universal acceptance.',
                    attribution='— Swami Vivekananda, Parliament of Religions, Chicago, 1893',
                ),
            ],
            speaker_notes='Vivekananda\'s 1893 address at the World Parliament of Religions was a watershed moment. '
                          'He received a standing ovation that lasted two minutes. His opening words '
                          '"Sisters and brothers of America" electrified the audience of 7,000.',
            requires_image=True,
            image_prompt='Swami Vivekananda tribute',
        ),
        Slide(
            slide_number=4, layout_type='stat',
            title='Global Impact in Numbers',
            eyebrow='Reach',
            slide_purpose='evidence',
            narrative_weight='standard',
            content_bullets=[],
            content_blocks=[
                StatBlock(value='180+', label='Countries', context='Art of Living presence'),
                StatBlock(value='42M', label='Sadhguru Followers', context='Across social media'),
                StatBlock(value='7,000', label='Ramakrishna Mission Centers', context='Worldwide'),
            ],
            speaker_notes='Indian spiritual movements have a truly global footprint. The Art of Living '
                          'Foundation alone operates in over 180 countries, while Sadhguru\'s Isha Foundation '
                          'has 42 million social media followers and centers across five continents.',
            requires_image=False,
            image_prompt='',
        ),
        Slide(
            slide_number=5, layout_type='split',
            title='Global Spiritual Conclave 2026',
            eyebrow='Upcoming',
            slide_purpose='call_to_action',
            narrative_weight='light',
            content_bullets=[],
            content_blocks=[
                CalloutBlock(
                    text='Haridwar, India — One Nation, One Vision, One Future',
                    callout_type='insight',
                ),
                KeyValueBlock(pairs=[
                    {'key': 'Where', 'value': 'Haridwar, Uttarakhand'},
                    {'key': 'Theme', 'value': 'Spirituality, Culture, Nation-Building'},
                    {'key': 'Vision', 'value': 'Viksit Bharat 2047'},
                ]),
            ],
            speaker_notes='The Global Spiritual Conclave 2026 brings together spiritual leaders, '
                          'youth influencers, and policymakers to foster ethical leadership. '
                          'Held in Haridwar, it aligns with the Viksit Bharat 2047 vision for a developed India.',
            requires_image=True,
            image_prompt='Global Spiritual Conclave 2026',
        ),
    ]

    image_map = {
        1: _img('er.jpg'),       # Swami Vivekananda tribute
        2: _img('qw.png'),      # Top 10 spiritual leaders
        3: _img('aa.jpeg'),     # Vivekananda tribute
        4: None,                 # gradient (stat slide)
        5: _img('aaz.jpeg'),    # Conclave poster
    }

    return run_deck('Spiritual Leaders of India', theme, slides, image_map, 'test3_spiritual_glassmorphism')


# ─────────────────────────────────────────────────────────────────────────────
# Test Deck 4: Cyber Security (corporate_clean) — gradient only
# ─────────────────────────────────────────────────────────────────────────────

def build_deck_4():
    theme = _make_theme('corporate_clean')
    slides = [
        Slide(
            slide_number=1, layout_type='cover',
            title='Cyber Security Awareness',
            subtitle='Secure Our World — NCSAM 2024',
            eyebrow='Handbook',
            slide_purpose='opening_hook',
            narrative_weight='light',
            content_bullets=[],
            content_blocks=None,
            speaker_notes='October is National Cyber Security Awareness Month. This presentation '
                          'covers the essentials every employee needs to know to protect themselves '
                          'and their organization from phishing, ransomware, and social engineering attacks.',
            requires_image=False,
            image_prompt='',
        ),
        Slide(
            slide_number=2, layout_type='stat',
            title='The Threat Landscape',
            eyebrow='Reality Check',
            slide_purpose='evidence',
            narrative_weight='standard',
            content_bullets=[],
            content_blocks=[
                StatBlock(value='3.4B', label='Phishing Emails/Day', context='Worldwide average'),
                StatBlock(value='$4.45M', label='Avg Data Breach Cost', context='IBM Report 2023'),
                StatBlock(value='82%', label='Breaches Involve Human Error', context='Verizon DBIR'),
            ],
            speaker_notes='The numbers are staggering. 3.4 billion phishing emails are sent every day. '
                          'The average cost of a data breach reached $4.45 million in 2023 according to IBM. '
                          'Most critically, 82 percent of breaches involve some form of human error.',
            requires_image=False,
            image_prompt='',
        ),
        Slide(
            slide_number=3, layout_type='split',
            title='Phishing vs Legitimate',
            eyebrow='Spot the Difference',
            slide_purpose='core_message',
            narrative_weight='standard',
            content_bullets=[],
            content_blocks=[
                ComparisonBlock(
                    left_label='🚨 Phishing Email',
                    left_items=['Urgent or threatening language', 'Misspelled sender domain',
                                'Asks for password/OTP', 'Suspicious attachments'],
                    right_label='✅ Legitimate Email',
                    right_items=['Professional tone', 'Official company domain',
                                 'Never asks for credentials', 'Expected attachments only'],
                ),
            ],
            speaker_notes='Train your eye to spot the differences. Phishing emails always create '
                          'urgency and use threatening language. Legitimate communications from your '
                          'company never ask for passwords via email and always come from verified domains.',
            requires_image=False,
            image_prompt='',
        ),
        Slide(
            slide_number=4, layout_type='timeline',
            title='5 Steps to Cyber Hygiene',
            eyebrow='Action Plan',
            slide_purpose='how_to_get_there',
            narrative_weight='standard',
            content_bullets=[],
            content_blocks=[
                StepBlock(
                    steps=[
                        'Use a password manager (Bitwarden, 1Password)',
                        'Enable 2FA on all accounts',
                        'Update software within 48 hours of patches',
                        'Never click links in unexpected emails',
                        'Back up data weekly (3-2-1 rule)',
                    ],
                    step_labels=['Step 1', 'Step 2', 'Step 3', 'Step 4', 'Step 5'],
                ),
            ],
            speaker_notes='These five steps, if followed consistently, prevent over 90 percent of common '
                          'cyber attacks targeting individuals and small businesses. The 3-2-1 backup '
                          'rule means three copies, two different media types, and one stored off-site.',
            requires_image=False,
            image_prompt='',
        ),
        Slide(
            slide_number=5, layout_type='generic',
            title='Your Security Checklist',
            eyebrow='Takeaway',
            slide_purpose='call_to_action',
            narrative_weight='light',
            content_bullets=[],
            content_blocks=[
                CalloutBlock(
                    text='Security is not a product, it is a process. '
                         'Start with one habit this week.',
                    callout_type='warning',
                ),
                KeyValueBlock(pairs=[
                    {'key': 'Password Length', 'value': '16+ characters minimum'},
                    {'key': '2FA Method', 'value': 'Authenticator app (not SMS)'},
                    {'key': 'Backup Frequency', 'value': 'Weekly, off-site'},
                    {'key': 'Patch Window', 'value': 'Within 48 hours'},
                    {'key': 'Report Phishing', 'value': 'security@yourcompany.com'},
                ]),
            ],
            speaker_notes='Leave your audience with a clear, actionable checklist. '
                          'The goal is one new security habit per week. Within five weeks, '
                          'you will have significantly reduced your personal and organizational attack surface.',
            requires_image=False,
            image_prompt='',
        ),
    ]

    # All gradients — no user images
    image_map = {n: None for n in range(1, 6)}

    return run_deck('Cyber Security Awareness', theme, slides, image_map, 'test4_cyber_corporate')


# ─────────────────────────────────────────────────────────────────────────────
# Test Deck 5: Indian Knowledge Systems (aurora / arctic)
# ─────────────────────────────────────────────────────────────────────────────

def build_deck_5():
    theme = _make_theme('aurora', 'arctic')
    slides = [
        Slide(
            slide_number=1, layout_type='cover',
            title='Indian Knowledge Systems',
            subtitle='Foundations of Ancient Wisdom',
            eyebrow='IKS',
            slide_purpose='opening_hook',
            narrative_weight='light',
            content_bullets=[],
            content_blocks=None,
            speaker_notes='Indian Knowledge Systems (IKS) is a semester course offered at IITs '
                          'covering the foundations of India\'s ancient intellectual traditions. '
                          'It bridges Vedic mathematics, Ayurveda, astronomy, metallurgy, and linguistics into a modern curriculum.',
            requires_image=False,
            image_prompt='',
        ),
        Slide(
            slide_number=2, layout_type='infographic',
            title='Six Pillars of Indian Knowledge',
            eyebrow='Framework',
            slide_purpose='core_message',
            narrative_weight='standard',
            content_bullets=[
                'Vedic Mathematics — Sulba Sutras, Aryabhata\'s zero',
                'Ayurveda — 5,000-year-old medical system',
                'Astronomy — Heliocentric model before Copernicus',
                'Metallurgy — Delhi Iron Pillar, 1,600 years rust-free',
                'Linguistics — Panini\'s grammar, 4th century BCE',
                'Architecture — Temple engineering, Vastu Shastra',
            ],
            content_blocks=[
                StatBlock(value='5,000+', label='Years of Documented Knowledge', context='Vedic period onwards'),
                StatBlock(value='6', label='Core Disciplines', context='IKS framework'),
            ],
            speaker_notes='Indian Knowledge Systems span at least 5,000 years of documented intellectual tradition. '
                          'Modern research institutions like IITs are now formalizing this knowledge '
                          'into structured courses that combine ancient texts with contemporary scientific methodology.',
            requires_image=False,
            image_prompt='',
        ),
        Slide(
            slide_number=3, layout_type='generic',
            title='Vedic Mathematics',
            eyebrow='Mathematics',
            slide_purpose='evidence',
            narrative_weight='standard',
            content_bullets=[],
            content_blocks=[
                KeyValueBlock(pairs=[
                    {'key': 'Zero (Shunya)', 'value': 'Invented by Aryabhata, 5th century CE'},
                    {'key': 'Decimal System', 'value': 'Hindu-Arabic numerals adopted globally'},
                    {'key': 'Pi (π)', 'value': 'Calculated to 4 decimals by Aryabhata'},
                    {'key': 'Pythagorean Theorem', 'value': 'Found in Sulba Sutras, 800 BCE'},
                    {'key': 'Infinity (Ananta)', 'value': 'Conceptualized in Isha Upanishad'},
                ]),
                CalloutBlock(
                    text='The concept of zero as a number (not just a placeholder) is arguably '
                         'India\'s greatest contribution to human civilization.',
                    callout_type='insight',
                ),
            ],
            speaker_notes='Aryabhata\'s contribution of zero as a number (shunya) transformed mathematics forever. '
                          'Without it, modern computing, physics, and engineering would be impossible. '
                          'The decimal system we use globally today originated from ancient Indian mathematicians.',
            requires_image=False,
            image_prompt='',
        ),
        Slide(
            slide_number=4, layout_type='quote',
            title='Ancient Wisdom, Modern Relevance',
            eyebrow='Philosophy',
            slide_purpose='social_proof',
            narrative_weight='light',
            content_bullets=[],
            content_blocks=[
                PullQuoteBlock(
                    quote='Vasudhaiva Kutumbakam — The whole world is one family.',
                    attribution='— Maha Upanishad, 6th century BCE',
                ),
            ],
            speaker_notes='This Upanishadic verse captures the essence of Indian philosophy: '
                          'universal brotherhood and interconnectedness. It was adopted as the official '
                          'theme of India\'s G20 presidency in 2023, resonating with leaders from all 20 member nations.',
            requires_image=False,
            image_prompt='',
        ),
        Slide(
            slide_number=5, layout_type='split',
            title='Ayurveda vs Modern Medicine',
            eyebrow='Health Sciences',
            slide_purpose='core_message',
            narrative_weight='standard',
            content_bullets=[],
            content_blocks=[
                ComparisonBlock(
                    left_label='Ayurveda',
                    left_items=['Preventive & holistic', 'Personalized (Prakriti-based)',
                                'Herbal & dietary', '5,000 years of empirical evidence'],
                    right_label='Modern Medicine',
                    right_items=['Curative & targeted', 'Standardized protocols',
                                 'Pharmaceutical-based', '200 years of clinical trials'],
                ),
            ],
            speaker_notes='Ayurveda and modern medicine are not adversaries but complementary systems. '
                          'The WHO now recognizes Ayurveda as a traditional medicine system, and India '
                          'has established AYUSH ministry to integrate traditional and modern healthcare approaches.',
            requires_image=False,
            image_prompt='',
        ),
    ]

    # All gradients — no user images
    image_map = {n: None for n in range(1, 6)}

    return run_deck('Indian Knowledge Systems', theme, slides, image_map, 'test5_iks_aurora')


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    # Clean previous output
    if os.path.exists(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print('╔══════════════════════════════════════════════════════════════╗')
    print('║         PDF Quality Test — Generating 5 Test Decks         ║')
    print('╚══════════════════════════════════════════════════════════════╝')

    results = []
    for builder in [build_deck_1, build_deck_2, build_deck_3, build_deck_4, build_deck_5]:
        try:
            result = builder()
            results.append(result)
        except Exception as e:
            import traceback
            print(f'\n  ✗ FAILED: {e}')
            traceback.print_exc()
            results.append({'name': builder.__name__, 'pdf_size_kb': 0, 'error': str(e)})

    # Generate summary report
    summary_path = os.path.join(OUTPUT_DIR, 'summary_report.md')
    with open(summary_path, 'w') as f:
        f.write('# PDF Quality Test — Summary Report\n\n')
        f.write(f'Generated: {time.strftime("%Y-%m-%d %H:%M:%S")}\n\n')
        f.write('| # | Deck | Theme | Slides | PDF Size | Score | Grade | Time |\n')
        f.write('|---|------|-------|--------|----------|-------|-------|------|\n')
        for i, r in enumerate(results, 1):
            if 'error' in r:
                f.write(f'| {i} | {r["name"]} | — | — | FAILED | — | — | — |\n')
            else:
                f.write(f'| {i} | {r["name"]} | {r["theme"]} | {r["slides"]} | '
                        f'{r["pdf_size_kb"]:.0f} KB | {r["avg_score"]:.1f}/50 | '
                        f'{r["grade"]} | {r["elapsed"]:.1f}s |\n')
        f.write('\n## Output Files\n\n')
        for r in results:
            if 'error' not in r:
                f.write(f'- **{r["name"]}**: [{os.path.basename(r["pdf_path"])}]'
                        f'({r["pdf_path"]})\n')

    print(f'\n{"═" * 60}')
    print(f'  Summary: {sum(1 for r in results if "error" not in r)}/{len(results)} decks generated')
    print(f'  Output:  {OUTPUT_DIR}/')
    print(f'  Report:  {summary_path}')
    print(f'{"═" * 60}')


if __name__ == '__main__':
    main()
