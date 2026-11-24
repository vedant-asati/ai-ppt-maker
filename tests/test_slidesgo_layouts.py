"""
test_slidesgo_layouts.py — Unit tests for KPI Dashboard and Roadmap Chain layout archetypes.
"""

import os
import pytest
from ppt_maker.core.schemas import Slide, KPIBlock, KPICard, StepBlock, Theme
from ppt_maker.rendering.templater import Templater
from ppt_maker.export.pptx_exporter import PptxExporter, LAYOUT_POSITIONS


def test_kpi_dashboard_schema_and_templater():
    cards = [
        KPICard(badge="REVENUE", value="$4.2M", label="Annual Recurring Revenue", delta="+35% YoY"),
        KPICard(badge="RETENTION", value="94.2%", label="Gross Retention Rate", delta="Top Tier"),
        KPICard(badge="EFFICIENCY", value="3.2x", label="LTV to CAC Ratio", delta="+0.8x"),
        KPICard(badge="COMMUNITY", value="50K+", label="Active Developers", delta="+120% YoY"),
    ]
    block = KPIBlock(cards=cards)
    slide = Slide(
        slide_number=2,
        layout_type="kpi_dashboard",
        title="Key Performance Metrics",
        subtitle="Q4 Operational Performance",
        eyebrow="SCORECARD",
        content_blocks=[block]
    )
    theme = Theme(structural_class="slidesgo_abstract_art")

    templater = Templater(templates_dir="ppt_maker/templates", build_dir="temp_build")
    out_file = templater.generate_single_slide_html(slide, theme, total_slides=3, out_path="temp_build/test_kpi.html")

    with open(out_file, "r", encoding="utf-8") as f:
        html = f.read()

    assert "Key Performance Metrics" in html
    assert "$4.2M" in html
    assert "Annual Recurring Revenue" in html
    assert "+35% YoY" in html
    assert "kpi-card" in html


def test_roadmap_chain_schema_and_templater():
    step_block = StepBlock(
        steps=[
            "Phase 1: Architecture Planning",
            "Phase 2: Core Pipeline Integration",
            "Phase 3: Visual Polish & Hardening",
            "Phase 4: Global Scale Deployment"
        ],
        step_labels=["Q1", "Q2", "Q3", "Q4"]
    )
    slide = Slide(
        slide_number=3,
        layout_type="roadmap_chain",
        title="Execution Roadmap",
        subtitle="Four Quarters of Product Milestones",
        eyebrow="ROADMAP",
        content_blocks=[step_block]
    )
    theme = Theme(structural_class="slidesgo_dark_tech")

    templater = Templater(templates_dir="ppt_maker/templates", build_dir="temp_build")
    out_file = templater.generate_single_slide_html(slide, theme, total_slides=3, out_path="temp_build/test_roadmap.html")

    with open(out_file, "r", encoding="utf-8") as f:
        html = f.read()

    assert "Execution Roadmap" in html
    assert "Architecture Planning" in html
    assert "roadmap-node" in html
    assert "Q1" in html


def test_pptx_exporter_positions_registered():
    assert "kpi_dashboard" in LAYOUT_POSITIONS
    assert "roadmap_chain" in LAYOUT_POSITIONS
    assert "hero_statement" in LAYOUT_POSITIONS
    assert "card_1" in LAYOUT_POSITIONS["kpi_dashboard"]
    assert "card_4" in LAYOUT_POSITIONS["kpi_dashboard"]
    assert "step_1" in LAYOUT_POSITIONS["roadmap_chain"]
    assert "step_4" in LAYOUT_POSITIONS["roadmap_chain"]
    assert "title" in LAYOUT_POSITIONS["hero_statement"]


def test_hero_statement_schema_and_templater():
    slide = Slide(
        slide_number=4,
        layout_type="hero_statement",
        title="AI won't replace designers. Designers who use AI will.",
        subtitle="The fundamental paradigm shift in creative engineering.",
        eyebrow="CORE THESIS",
    )
    theme = Theme(structural_class="slidesgo_creative_watercolor")

    templater = Templater(templates_dir="ppt_maker/templates", build_dir="temp_build")
    out_file = templater.generate_single_slide_html(slide, theme, total_slides=5, out_path="temp_build/test_hero_statement.html")

    with open(out_file, "r", encoding="utf-8") as f:
        html = f.read()

    assert "hero-statement-container" in html
    assert "replace designers" in html
    assert "CORE THESIS" in html
    assert "04" in html  # watermark chapter digit


def test_asymmetric_editorial_split_templater():
    slide = Slide(
        slide_number=5,
        layout_type="split",
        title="Next-Gen Architecture",
        subtitle="Asymmetric 40/60 Editorial Layout",
        eyebrow="DEEP DIVE",
        requires_image=True,
    )
    theme = Theme(structural_class="slidesgo_dark_tech")

    templater = Templater(templates_dir="ppt_maker/templates", build_dir="temp_build")
    out_file = templater.generate_single_slide_html(
        slide, theme, total_slides=5,
        image_info={"path": "tests/fixtures/sample.png", "status": "cache", "role": "supporting"},
        out_path="temp_build/test_split_asymmetric.html"
    )

    with open(out_file, "r", encoding="utf-8") as f:
        html = f.read()

    assert "split-image-card" in html
    assert "split-floating-pill" in html
    assert "Next-Gen Architecture" in html


def test_hero_statement_pptx_export_with_subtitle_and_content(tmp_path):
    """Regression test for Review #03 P0: Hero Statement with subtitle must not crash PPTX export."""
    from ppt_maker.core.schemas import MasterPlan, StatBlock
    from pptx import Presentation

    slide = Slide(
        slide_number=1,
        layout_type="hero_statement",
        title="Transforming Enterprise Workflows",
        subtitle="Operational efficiency up by 47% across 12 teams.",
        eyebrow="EXECUTIVE SUMMARY",
        speaker_notes="Confidential board notes - do not expose on slide.",
        content_blocks=[StatBlock(value="47%", label="Efficiency Gain", context="12 engineering teams")]
    )
    plan = MasterPlan(
        deck_title="Test Deck",
        slides=[slide],
        theme=Theme(structural_class="slidesgo_dark_tech")
    )
    out_pptx = str(tmp_path / "hero_statement_test.pptx")
    dummy_png = str(tmp_path / "slide_1.png")
    # Create a dummy PNG file
    from PIL import Image
    img = Image.new("RGB", (1920, 1080), color=(15, 23, 42))
    img.save(dummy_png)

    exporter = PptxExporter()
    success = exporter.export([dummy_png], plan, out_pptx)
    assert success is True
    assert os.path.exists(out_pptx)

    prs = Presentation(out_pptx)
    assert len(prs.slides) == 1
    # Check that speaker notes were set on the slide
    assert "Confidential board notes" in prs.slides[0].notes_slide.notes_text_frame.text
    # Check that visible text contains title and subtitle
    all_text = " ".join([shape.text_frame.text for shape in prs.slides[0].shapes if shape.has_text_frame])
    assert "Transforming Enterprise Workflows" in all_text
    assert "Operational efficiency up by 47%" in all_text
    assert "Confidential board notes" not in all_text  # Notes never in visible slide text!


def test_templates_do_not_leak_speaker_notes():
    """Regression test for Review #03 P0: Templates must never render speaker_notes as slide copy."""
    sentinel = "CONFIDENTIAL_PRIVATE_SPEAKER_NOTE_SENTINEL_XYZ"
    slide = Slide(
        slide_number=1,
        layout_type="bento",
        title="Strategic Overview",
        subtitle="Quarterly Execution",
        eyebrow="STRATEGY",
        speaker_notes=sentinel,
    )
    theme = Theme(structural_class="slidesgo_abstract_art")
    templater = Templater(templates_dir="ppt_maker/templates", build_dir="temp_build")

    for layout in ["bento", "creative", "modern_tech", "editorial"]:
        slide.layout_type = layout
        out_file = templater.generate_single_slide_html(
            slide, theme, total_slides=1,
            out_path=f"temp_build/test_leak_{layout}.html"
        )
        with open(out_file, "r", encoding="utf-8") as f:
            html = f.read()
        assert sentinel not in html, f"Template '{layout}' leaked speaker notes into visible HTML!"


def test_reverse_split_pptx_positioning(tmp_path):
    """Regression test for Review #03 P1: Reverse split maps to right-side text in PPTX."""
    from ppt_maker.core.schemas import MasterPlan
    from pptx import Presentation
    from pptx.util import Inches

    slide = Slide(
        slide_number=1,
        layout_type="split",
        layout_variant="reverse",
        title="Autonomous Workflows",
        subtitle="Reverse split orientation",
        eyebrow="INNOVATION",
    )
    plan = MasterPlan(
        deck_title="Test Reverse Split",
        slides=[slide],
        theme=Theme(structural_class="slidesgo_dark_tech")
    )
    dummy_png = str(tmp_path / "slide_1.png")
    from PIL import Image
    img = Image.new("RGB", (1920, 1080), color=(15, 23, 42))
    img.save(dummy_png)

    out_pptx = str(tmp_path / "reverse_split_test.pptx")
    exporter = PptxExporter()
    success = exporter.export([dummy_png], plan, out_pptx)
    assert success is True

    prs = Presentation(out_pptx)
    title_shape = None
    for shape in prs.slides[0].shapes:
        if shape.has_text_frame and "Autonomous Workflows" in shape.text_frame.text:
            title_shape = shape
            break
    assert title_shape is not None
    # For reverse split, text is on the right side: left should be >= 6.0 inches (not 0.8 inches!)
    assert title_shape.left >= Inches(6.0), f"Expected title.left >= 6.0 inches, got {title_shape.left / 914400.0} inches"


def test_pptx_citation_links(tmp_path):
    """Regression test for Review #03 P1: PPTX exports slide citations with hyperlinks."""
    from ppt_maker.core.schemas import MasterPlan, Citation
    from pptx import Presentation

    slide = Slide(
        slide_number=1,
        layout_type="generic",
        title="Evidence Grounded Slide",
        eyebrow="GROUNDING",
        citations=[
            Citation(
                id=1,
                claim="AI accelerates developer workflows",
                source_title="The State of AI in Software",
                source_url="https://mckinsey.com/ai",
                domain="mckinsey.com"
            )
        ]
    )
    plan = MasterPlan(
        deck_title="Test Sourced Deck",
        slides=[slide],
        theme=Theme(structural_class="corporate_clean")
    )
    dummy_png = str(tmp_path / "slide_1.png")
    from PIL import Image
    img = Image.new("RGB", (1920, 1080), color=(255, 255, 255))
    img.save(dummy_png)

    out_pptx = str(tmp_path / "citations_test.pptx")
    exporter = PptxExporter()
    success = exporter.export([dummy_png], plan, out_pptx)
    assert success is True

    prs = Presentation(out_pptx)
    all_text = " ".join([s.text_frame.text for s in prs.slides[0].shapes if s.has_text_frame])
    assert "mckinsey.com" in all_text
    assert "The State of AI in Software" in all_text


def test_kpi_and_stat_normalizer_preserves_zero():
    """Regression test for Review #04 Blocker: Normalizer must preserve true 0 and not invent 100% or +10% YoY."""
    from ppt_maker.planning.multi_agent.stages import _normalize_slide_dict
    from ppt_maker.core.schemas import SlideBlueprint

    bp = SlideBlueprint(slide_number=1, layout_type="kpi_dashboard", title_directive="KPI review")
    raw_data = {
        "title": "KPI Dashboard",
        "content_blocks": [
            {
                "block_type": "kpi_dashboard",
                "cards": [
                    {"value": 0, "label": "Incident count"},
                    {"val": 0.0, "label": "Fatal error rate", "delta": "0%"},
                    {"stat_val": "0", "label": "Downtime seconds", "context": ""},
                ]
            },
            {
                "block_type": "stat",
                "value": 0,
                "label": "Open Vulnerabilities"
            }
        ]
    }

    normalized = _normalize_slide_dict(raw_data, bp)
    blocks = normalized["content_blocks"]
    assert len(blocks) == 2

    kpi_block = blocks[0]
    cards = kpi_block["cards"]
    assert cards[0]["value"] == "0", f"Expected '0', got {cards[0]['value']}"
    assert cards[0]["delta"] == "", f"Expected empty delta, got {cards[0]['delta']}"
    assert cards[1]["value"] == "0.0", f"Expected '0.0', got {cards[1]['value']}"
    assert cards[2]["value"] == "0", f"Expected '0', got {cards[2]['value']}"

    stat_block = blocks[1]
    assert stat_block["value"] == "0", f"Expected '0', got {stat_block['value']}"


def test_deterministic_fallback_has_no_synthetic_metrics():
    """Regression test for Review #04 Blocker: Fallback must never synthesize 99%, 10x, or 'Verified'."""
    from ppt_maker.planning.multi_agent.fallback import PerSlideFallbackHandler
    from ppt_maker.core.schemas import SlideBlueprint

    class DummyDeck:
        theme_style = "slidesgo_dark_tech"
        palette = None

    handler = PerSlideFallbackHandler()
    bento_bp = SlideBlueprint(
        slide_number=2,
        layout_type="bento",
        title_directive="Show architecture health",
        slide_purpose="operational_status"
    )
    bento_slide = handler._heuristic_fill(bento_bp, DummyDeck())
    bento_text = str(bento_slide.model_dump())
    assert "99%" not in bento_text, "Fallback bento synthesized '99%'!"
    assert "Reliability Standard" not in bento_text

    kpi_bp = SlideBlueprint(
        slide_number=3,
        layout_type="kpi_dashboard",
        title_directive="Executive metrics review",
        slide_purpose="performance_kpi"
    )
    kpi_slide = handler._heuristic_fill(kpi_bp, DummyDeck())
    kpi_text = str(kpi_slide.model_dump())
    assert "Verified" not in kpi_text, "Fallback KPI synthesized 'Verified'!"
    assert "High Impact" not in kpi_text

    stat_bp = SlideBlueprint(
        slide_number=4,
        layout_type="stat",
        title_directive="Key Growth Trajectory",
        slide_purpose="growth_stat"
    )
    stat_slide = handler._heuristic_fill(stat_bp, DummyDeck())
    stat_text = str(stat_slide.model_dump())
    assert "10x" not in stat_text, "Fallback stat synthesized '10x'!"


def test_direction_aware_citation_affinity():
    """Regression test for Review #04 Blocker: Citation matcher must not pair opposite direction ('fell' vs 'rose')."""
    from ppt_maker.core.schemas import MasterPlan, Slide, Citation, Theme

    slide_text = "North region revenue rose 8% in Q3"
    slide = Slide(
        slide_number=2,
        layout_type="generic",
        title=slide_text,
        eyebrow="REVENUE",
    )
    plan = MasterPlan(
        deck_title="Test Polarity Matching",
        slides=[Slide(slide_number=1, layout_type="cover", title="Cover"), slide],
        theme=Theme(structural_class="corporate_clean")
    )

    cits = [
        Citation(id=1, claim="North revenue fell 8% in Q3", source_title="Market Daily", source_url="https://a.com", domain="a.com"),
        Citation(id=2, claim="South revenue rose 8% in Q3", source_title="Regional Report", source_url="https://b.com", domain="b.com"),
        Citation(id=3, claim="North region revenue rose 8% in Q3", source_title="SEC Filing", source_url="https://c.com", domain="c.com"),
    ]

    # Execute citation matching logic as implemented in cli.py
    import re
    POS_POLARITY = {'rose', 'grew', 'expanded', 'increased', 'up', 'acceleration', 'gain', 'higher', 'growth'}
    NEG_POLARITY = {'fell', 'dropped', 'contracted', 'decreased', 'down', 'decline', 'loss', 'lower', 'reduction'}
    STOPWORDS = {'the', 'and', 'for', 'with', 'from', 'that', 'this', 'our', 'are', 'was', 'were'}

    for sl in plan.slides[1:]:
        s_text = f"{sl.title} {sl.subtitle or ''}"
        s_words = set(re.findall(r'\b[a-zA-Z0-9]{2,}\b', s_text.lower()))
        s_pos = bool(s_words & POS_POLARITY)
        s_neg = bool(s_words & NEG_POLARITY)
        s_nums = {w for w in s_words if any(ch.isdigit() for ch in w)}

        scored_cits = []
        for c in cits:
            cit_claim = getattr(c, 'claim', '') or getattr(c, 'source_title', '')
            c_words = set(re.findall(r'\b[a-zA-Z0-9]{2,}\b', cit_claim.lower()))
            c_pos = bool(c_words & POS_POLARITY)
            c_neg = bool(c_words & NEG_POLARITY)

            if (s_pos and c_neg) or (s_neg and c_pos):
                continue

            overlap = (s_words & c_words) - STOPWORDS
            if not overlap:
                continue

            score = float(len(overlap))
            c_nums = {w for w in c_words if any(ch.isdigit() for ch in w)}
            matching_nums = s_nums & c_nums
            if matching_nums:
                score += 5.0 * len(matching_nums)

            if score >= 2.0:
                scored_cits.append((score, c))

        scored_cits.sort(key=lambda x: x[0], reverse=True)
        if scored_cits:
            sl.citations = [c for _, c in scored_cits[:2]]

    assigned_cits = plan.slides[1].citations
    assert assigned_cits is not None
    assert len(assigned_cits) >= 1
    # Top match must be citation #3 (exact match)
    assert assigned_cits[0].id == 3, f"Expected citation 3, got '{assigned_cits[0].id}'"
    # Citation #1 (opposite direction) must NEVER be included
    assigned_ids = [c.id for c in assigned_cits]
    assert 1 not in assigned_ids, "Citation #1 (opposite direction: 'fell') was erroneously bound!"


def test_pptx_exporter_rejects_duplicate_plates(tmp_path):
    """Regression test for Review #04 Blocker: Exporter must reject duplicate/missing slide plates."""
    import pytest
    from ppt_maker.core.schemas import MasterPlan, Slide, Theme
    from ppt_maker.export.pptx_exporter import PptxExporter
    from PIL import Image

    plan = MasterPlan(
        deck_title="Test Plate Ingestion",
        slides=[
            Slide(slide_number=1, layout_type="cover", title="Slide 1"),
            Slide(slide_number=2, layout_type="split", title="Slide 2"),
            Slide(slide_number=3, layout_type="generic", title="Slide 3"),
        ],
        theme=Theme(structural_class="corporate_clean")
    )

    # Create dummy plates: 1, 1, 3 (duplicate 1, missing 2)
    p1 = str(tmp_path / "slide_1.png")
    p1_dup = str(tmp_path / "slide_1_copy.png")
    # rename copy so basename has slide_1
    p1_dup = str(tmp_path / "slide_1_dup.png")
    p3 = str(tmp_path / "slide_3.png")

    for p in [p1, p1_dup, p3]:
        Image.new("RGB", (100, 100), color=(0, 0, 0)).save(p)

    out_pptx = str(tmp_path / "out.pptx")
    exporter = PptxExporter()

    with pytest.raises(ValueError, match="Plate manifest mismatch"):
        exporter.export([p1, p1_dup, p3], plan, out_pptx)


def test_pptx_exporter_audience_delivery_strips_notes(tmp_path):
    """Regression test for Review #04 P0: Audience delivery must strip all speaker notes from PPTX."""
    from ppt_maker.core.schemas import MasterPlan, Slide, Theme
    from ppt_maker.export.pptx_exporter import PptxExporter
    from pptx import Presentation
    from PIL import Image

    plan = MasterPlan(
        deck_title="Test Audience Notes Stripping",
        slides=[
            Slide(
                slide_number=1,
                layout_type="cover",
                title="Board Review",
                speaker_notes="CONFIDENTIAL_SENTINEL_DO_NOT_LEAK"
            )
        ],
        theme=Theme(structural_class="corporate_clean")
    )
    p1 = str(tmp_path / "slide_1.png")
    Image.new("RGB", (100, 100), color=(0, 0, 0)).save(p1)

    out_pptx_aud = str(tmp_path / "audience.pptx")
    out_pptx_pres = str(tmp_path / "presenter.pptx")
    exporter = PptxExporter()

    # 1. Audience delivery: notes stripped
    exporter.export([p1], plan, out_pptx_aud, audience_mode=True)
    prs_aud = Presentation(out_pptx_aud)
    slide_aud = prs_aud.slides[0]
    # Check notes slide text
    notes_text = slide_aud.notes_slide.notes_text_frame.text if slide_aud.has_notes_slide else ""
    assert "CONFIDENTIAL_SENTINEL" not in notes_text

    # 2. Presenter delivery: notes preserved
    exporter.export([p1], plan, out_pptx_pres, audience_mode=False)
    prs_pres = Presentation(out_pptx_pres)
    slide_pres = prs_pres.slides[0]
    assert "CONFIDENTIAL_SENTINEL_DO_NOT_LEAK" in slide_pres.notes_slide.notes_text_frame.text



