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


