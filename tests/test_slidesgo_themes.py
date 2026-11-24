"""
test_slidesgo_themes.py — Unit tests for the 9 newly ingested SlidesGo themes.
"""

import pytest
from ppt_maker.core.schemas import Theme
from ppt_maker.design.theme_resolver import ThemeResolver
from ppt_maker.design.theme_palettes import PALETTES, PALETTE_MANAGED_THEMES

SLIDESGO_THEMES = [
    'slidesgo_abstract_art',
    'slidesgo_aesthetic_retro',
    'slidesgo_creative_watercolor',
    'slidesgo_dark_tech',
    'slidesgo_digital_nostalgia',
    'slidesgo_minimalist_business',
    'slidesgo_modern_proposal',
    'slidesgo_tech_startup',
    'slidesgo_impressionism',
]


@pytest.mark.parametrize("theme_name", SLIDESGO_THEMES)
def test_slidesgo_theme_in_palette_managed(theme_name):
    """Every SlidesGo theme must be declared in PALETTE_MANAGED_THEMES."""
    assert theme_name in PALETTE_MANAGED_THEMES
    assert theme_name in PALETTES
    assert "default" in PALETTES[theme_name]


@pytest.mark.parametrize("theme_name", SLIDESGO_THEMES)
def test_slidesgo_theme_resolution(theme_name):
    """ThemeResolver must successfully resolve CSS variables and typography."""
    resolved, pal = ThemeResolver.resolve(theme_name, 'default', {})
    assert pal == 'default'
    assert '--primary' in resolved
    assert '--bg' in resolved
    assert '--text' in resolved
    assert '--font-header' in resolved
    assert '--font-body' in resolved


@pytest.mark.parametrize("theme_name", SLIDESGO_THEMES)
def test_slidesgo_theme_schema_validation(theme_name):
    """Theme schema must accept the new structural class."""
    theme = Theme(structural_class=theme_name)
    assert theme.structural_class == theme_name


def test_procedural_textures_definitions():
    """Verify procedural SVG Data URI textures for resolution-independent GPU rendering."""
    from ppt_maker.design.theme_textures import (
        get_procedural_texture,
        has_procedural_texture,
        SVG_CREATIVE_WATERCOLOR,
        SVG_DARK_TECH,
        SVG_MODERN_PROPOSAL,
        SVG_AESTHETIC_RETRO
    )

    # Core archetype mappings must exist
    for arch in ["slidesgo_dark_tech", "slidesgo_creative_watercolor", "slidesgo_modern_proposal", "slidesgo_aesthetic_retro"]:
        assert has_procedural_texture(arch)
        tex = get_procedural_texture(arch)
        assert tex.startswith("url(\"data:image/svg+xml,")
        assert tex.endswith("\")")

    # Critical Performance Constraint: Watercolor texture numOctaves must be <= 2
    assert "numOctaves='2'" in SVG_CREATIVE_WATERCOLOR


def test_theme_resolver_procedural_resolution():
    """Verify ThemeResolver wires procedural SVG textures when requested or when raster assets are absent."""
    # 1. Explicit use_procedural=True
    resolved_proc, _ = ThemeResolver.resolve(
        structural_class="slidesgo_dark_tech",
        palette_name=None,
        ai_css_vars={},
        use_procedural=True
    )
    assert "--bg-texture" in resolved_proc
    assert "data:image/svg+xml" in resolved_proc["--bg-texture"]

    # 2. Theme without a raster texture file (e.g. corporate_clean) falls back to procedural
    resolved_corp, _ = ThemeResolver.resolve(
        structural_class="corporate_clean",
        palette_name=None,
        ai_css_vars={}
    )
    assert "--bg-texture" in resolved_corp
    assert "data:image/svg+xml" in resolved_corp["--bg-texture"]


