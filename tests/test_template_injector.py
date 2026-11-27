"""
test_template_injector.py — Unit tests for SlidesGo native PPTX template injection.
"""

import os
import glob
import pytest
from pptx import Presentation
from ppt_maker.core.schemas import MasterPlan, Slide, Theme, BulletBlock
from ppt_maker.export.template_injector import TemplateInjector

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.environ.get(
    "SLIDESGO_TEMPLATES_DIR",
    os.path.join(_REPO_ROOT, "temp", "slidesgoppts")
)
HAS_LOCAL_TEMPLATES = os.path.isdir(TEMPLATES_DIR) and len(
    glob.glob(os.path.join(TEMPLATES_DIR, "*.pptx"))
) >= 10


def test_synthetic_template_injection(tmp_path):
    """Hermetic unit test that verifies TemplateInjector without needing external template files."""
    template_dir = tmp_path / "custom_templates"
    template_dir.mkdir()
    template_path = template_dir / "Minimalist Pitch Deck by Slidesgo.pptx"

    # Create a synthetic 3-slide template presentation
    prs = Presentation()
    # Slide 1: Title Layout
    s1 = prs.slides.add_slide(prs.slide_layouts[0])
    s1.shapes.title.text = "Old Title 1"
    s1.placeholders[1].text = "Old Subtitle 1"

    # Slide 2: Content Layout
    s2 = prs.slides.add_slide(prs.slide_layouts[1])
    s2.shapes.title.text = "Old Title 2"
    s2.placeholders[1].text = "Old Content Bullet"

    # Slide 3: Content Layout
    s3 = prs.slides.add_slide(prs.slide_layouts[1])
    s3.shapes.title.text = "Old Title 3"
    s3.placeholders[1].text = "Old Content Bullet 2"

    prs.save(str(template_path))

    injector = TemplateInjector(templates_dir=str(template_dir))

    # Test listing
    templates = injector.list_available_templates()
    assert len(templates) == 1
    assert "Minimalist Pitch Deck by Slidesgo.pptx" in templates

    # Test finding
    found = injector.find_template("Minimalist Pitch Deck")
    assert found is not None
    assert os.path.isfile(found)

    # Test injection
    out_file = str(tmp_path / "injected_synthetic.pptx")
    plan = MasterPlan(
        theme=Theme(structural_class="slidesgo_minimalist_business"),
        slides=[
            Slide(slide_number=1, layout_type="cover", title="Synthetic AI Cover", subtitle="Generated in CI"),
            Slide(slide_number=2, layout_type="generic", title="Synthetic Architecture", subtitle="Decoupled Pipeline", content_blocks=[BulletBlock(items=["Pydantic Schema", "Playwright CDM"])]),
            Slide(slide_number=3, layout_type="split", title="Synthetic Impact", subtitle="Reliability", content_blocks=[BulletBlock(items=["100% CI pass", "Fast execution"])])
        ]
    )

    success = injector.inject("Minimalist Pitch Deck", plan, out_file)
    assert success is True
    assert os.path.isfile(out_file)

    # Verify injected contents
    result_prs = Presentation(out_file)
    assert len(result_prs.slides) == 3
    s1_texts = [p.text.strip() for s in result_prs.slides[0].shapes if s.has_text_frame for p in s.text_frame.paragraphs if p.text.strip()]
    assert any("Synthetic AI Cover" in t for t in s1_texts)


@pytest.mark.skipif(not HAS_LOCAL_TEMPLATES, reason="Local SlidesGo PPTX templates not present in temp/slidesgoppts")
def test_list_templates():
    injector = TemplateInjector(templates_dir=TEMPLATES_DIR)
    templates = injector.list_available_templates()
    assert len(templates) >= 10
    assert any("Minimalist Pitch Deck" in t for t in templates)
    assert any("Tech Startup" in t for t in templates)


@pytest.mark.skipif(not HAS_LOCAL_TEMPLATES, reason="Local SlidesGo PPTX templates not present in temp/slidesgoppts")
def test_find_template():
    injector = TemplateInjector(templates_dir=TEMPLATES_DIR)
    found_pitch = injector.find_template("Minimalist Pitch Deck")
    assert found_pitch is not None
    assert os.path.isfile(found_pitch)

    found_tech = injector.find_template("tech_startup")
    assert found_tech is not None
    assert os.path.isfile(found_tech)


@pytest.mark.skipif(not HAS_LOCAL_TEMPLATES, reason="Local SlidesGo PPTX templates not present in temp/slidesgoppts")
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
