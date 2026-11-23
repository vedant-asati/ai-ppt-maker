"""
test_slidesgo_layouts.py — Unit tests for KPI Dashboard and Roadmap Chain layout archetypes.
"""

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
    assert "card_1" in LAYOUT_POSITIONS["kpi_dashboard"]
    assert "card_4" in LAYOUT_POSITIONS["kpi_dashboard"]
    assert "step_1" in LAYOUT_POSITIONS["roadmap_chain"]
    assert "step_4" in LAYOUT_POSITIONS["roadmap_chain"]

