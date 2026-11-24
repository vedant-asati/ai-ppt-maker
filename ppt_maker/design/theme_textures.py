"""
ppt_maker.design.theme_textures — Procedural SVG Data URI Texture Generator.

Generates high-performance, lightweight, resolution-independent CSS background
textures as inline SVG Data URIs. Eliminates external disk I/O, network requests,
and heavy raster asset dependencies while maintaining pristine visual rendering
at any DPI scale (72 DPI preview to 144+ DPI print export).
"""

from typing import Optional, Dict

# ── Procedural SVG Data URIs ──────────────────────────────────────────────────
# All SVGs are URL-encoded for clean CSS embedding without base64 overhead.

# 1. Dark Tech / Tech Startup: Isometric Micro-Dot Grid with subtle cyan highlight
SVG_DARK_TECH = (
    "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
    "width='48' height='48' viewBox='0 0 48 48'%3E"
    "%3Ccircle cx='24' cy='24' r='1' fill='rgba(255,255,255,0.06)'/%3E"
    "%3Ccircle cx='48' cy='48' r='1' fill='rgba(255,255,255,0.06)'/%3E"
    "%3Ccircle cx='24' cy='48' r='0.75' fill='rgba(56,189,248,0.18)'/%3E"
    "%3C/svg%3E\")"
)

# 2. Creative Watercolor / Impressionism: Organic Paper Noise Grain (numOctaves strictly capped at 2)
SVG_CREATIVE_WATERCOLOR = (
    "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
    "width='300' height='300'%3E"
    "%3Cfilter id='paper' x='0' y='0' width='100%25' height='100%25'%3E"
    "%3CfeTurbulence type='fractalNoise' baseFrequency='0.04' numOctaves='2' result='noise'/%3E"
    "%3CfeColorMatrix type='matrix' values='0 0 0 0 0.96  0 0 0 0 0.94  0 0 0 0 0.91  0 0 0 0.045 0'/%3E"
    "%3C/filter%3E"
    "%3Crect width='100%25' height='100%25' filter='url(%23paper)'/%3E"
    "%3C/svg%3E\")"
)

# 3. Modern Proposal / Minimalist Business: Crisp Subtle Diagonal Geometric Mesh
SVG_MODERN_PROPOSAL = (
    "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
    "width='60' height='60' viewBox='0 0 60 60'%3E"
    "%3Cpath d='M60 0 L0 60 M0 0 L60 60' stroke='rgba(148,163,184,0.05)' stroke-width='1'/%3E"
    "%3C/svg%3E\")"
)

# 4. Aesthetic Retro / Digital Nostalgia / Abstract Art: Warm Halftone Dot Grain
SVG_AESTHETIC_RETRO = (
    "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
    "width='32' height='32' viewBox='0 0 32 32'%3E"
    "%3Ccircle cx='8' cy='8' r='0.8' fill='rgba(180,83,9,0.08)'/%3E"
    "%3Ccircle cx='24' cy='8' r='0.5' fill='rgba(180,83,9,0.05)'/%3E"
    "%3Ccircle cx='16' cy='24' r='0.8' fill='rgba(180,83,9,0.08)'/%3E"
    "%3C/svg%3E\")"
)

# 5. Technical Blueprint: Grid with Sub-Divisions
SVG_TECHNICAL_BLUEPRINT = (
    "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
    "width='100' height='100' viewBox='0 0 100 100'%3E"
    "%3Cdefs%3E%3Cpattern id='grid' width='20' height='20' patternUnits='userSpaceOnUse'%3E"
    "%3Cpath d='M 20 0 L 0 0 0 20' fill='none' stroke='rgba(59,130,246,0.04)' stroke-width='1'/%3E"
    "%3C/pattern%3E%3C/defs%3E"
    "%3Crect width='100' height='100' fill='url(%23grid)'/%3E"
    "%3Cpath d='M 100 0 L 0 0 0 100' fill='none' stroke='rgba(59,130,246,0.08)' stroke-width='1.5'/%3E"
    "%3C/svg%3E\")"
)


PROCEDURAL_TEXTURES: Dict[str, str] = {
    "slidesgo_dark_tech": SVG_DARK_TECH,
    "slidesgo_tech_startup": SVG_DARK_TECH,
    "dark_tech": SVG_DARK_TECH,
    "tech_startup": SVG_DARK_TECH,

    "slidesgo_creative_watercolor": SVG_CREATIVE_WATERCOLOR,
    "slidesgo_impressionism": SVG_CREATIVE_WATERCOLOR,
    "creative_watercolor": SVG_CREATIVE_WATERCOLOR,
    "watercolor": SVG_CREATIVE_WATERCOLOR,

    "slidesgo_modern_proposal": SVG_MODERN_PROPOSAL,
    "slidesgo_minimalist_business": SVG_MODERN_PROPOSAL,
    "modern_proposal": SVG_MODERN_PROPOSAL,
    "corporate_clean": SVG_MODERN_PROPOSAL,

    "slidesgo_aesthetic_retro": SVG_AESTHETIC_RETRO,
    "slidesgo_digital_nostalgia": SVG_AESTHETIC_RETRO,
    "slidesgo_abstract_art": SVG_AESTHETIC_RETRO,
    "aesthetic_retro": SVG_AESTHETIC_RETRO,

    "technical_blueprint": SVG_TECHNICAL_BLUEPRINT,
    "blueprint": SVG_TECHNICAL_BLUEPRINT,
}


def get_procedural_texture(theme_name: str) -> Optional[str]:
    """
    Returns the procedural CSS Data URI texture string for a given theme,
    or None if no procedural mapping exists.
    """
    if not theme_name:
        return None
    normalized = theme_name.lower().strip()
    return PROCEDURAL_TEXTURES.get(normalized)


def has_procedural_texture(theme_name: str) -> bool:
    """Returns True if a procedural texture exists for the theme."""
    return get_procedural_texture(theme_name) is not None
