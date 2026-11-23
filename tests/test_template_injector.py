"""
test_template_injector.py — Unit tests for SlidesGo native PPTX template injection.
"""

import os
import pytest
from pptx import Presentation
from ppt_maker.core.schemas import MasterPlan, Slide, Theme, BulletBlock
from ppt_maker.export.template_injector import TemplateInjector

TEMPLATES_DIR = "/home/intruder-jsr/exps/ai-ppt-maker/temp/slidesgoppts"


def test_list_templates():
    injector = TemplateInjector(templates_dir=TEMPLATES_DIR)
    templates = injector.list_available_templates()
    assert len(templates) >= 10
    assert any("Minimalist Pitch Deck" in t for t in templates)
    assert any("Tech Startup" in t for t in templates)


def test_find_template():
    injector = TemplateInjector(templates_dir=TEMPLATES_DIR)
    found_pitch = injector.find_template("Minimalist Pitch Deck")
    assert found_pitch is not None
    assert os.path.isfile(found_pitch)

    found_tech = injector.find_template("tech_startup")
    assert found_tech is not None
    assert os.path.isfile(found_tech)


def test_inject_master_plan(tmp_path):
    injector = TemplateInjector(templates_dir=TEMPLATES_DIR)
    out_file = str(tmp_path / "injected_output.pptx")

    slides = [
        Slide(
            slide_number=1,
            layout_type="cover",
            title="Next-Gen AI Presentations",
            subtitle="Autonomous Synthesis at Scale"
        ),
        Slide(
            slide_number=2,
            layout_type="generic",
            title="Core Architecture",
            subtitle="Decoupled Synthesis Pipeline",
            content_blocks=[BulletBlock(items=["DeckArchitect Blueprint", "Batched Concurrency", "Fault Recovery"])]
        ),
        Slide(
            slide_number=3,
            layout_type="split",
            title="Operational Impact",
            subtitle="Immediate Value Creation",
            content_blocks=[BulletBlock(items=["99.9% Pipeline Uptime", "3x API Quota Throughput"])]
        )
    ]
    plan = MasterPlan(
        theme=Theme(structural_class="slidesgo_minimalist_business"),
        slides=slides
    )

    success = injector.inject("Minimalist Pitch Deck", plan, out_file)
    assert success is True
    assert os.path.isfile(out_file)

    # Reopen and inspect
    prs = Presentation(out_file)
    assert len(prs.slides) == 3

    # Check slide 1 text
    s1_texts = []
    for s in prs.slides[0].shapes:
        if s.has_text_frame:
            for p in s.text_frame.paragraphs:
                if p.text.strip():
                    s1_texts.append(p.text.strip())

    assert any("Next-Gen AI Presentations" in t for t in s1_texts)

