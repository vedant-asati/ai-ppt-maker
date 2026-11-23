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

