"""
theme_resolver.py — Bridges Planner output to Template rendering.

Merges curated palette variables, AI-generated CSS variables, and user
color overrides into a final dict of CSS variables.

Priority (highest wins):
  1. User's primary_color in config     → overrides --primary
  2. Curated palette (theme_palettes)   → fills structural variables
  3. AI-generated css_variables         → base vars not covered by palette
"""

import math
from typing import Optional, Tuple
try:
    from ppt_maker.design.theme_palettes import (
        PALETTES, DEFAULT_PALETTE, PALETTE_MANAGED_THEMES,
    )
except ImportError:
    from theme_palettes import (
        PALETTES, DEFAULT_PALETTE, PALETTE_MANAGED_THEMES,
    )


class ThemeResolver:

    # ── Color math helpers ────────────────────────────────────────────────

    @staticmethod
    def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
        h = hex_color.lstrip('#')
        if len(h) == 3:
            h = ''.join(c * 2 for c in h)
        elif len(h) != 6:
            raise ValueError(f"Invalid hex color: '{hex_color}'")
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    @staticmethod
    def rgb_to_str(rgb: Tuple[int, int, int]) -> str:
        return f"{rgb[0]},{rgb[1]},{rgb[2]}"

    @staticmethod
    def hex_to_rgb_str(hex_color: str) -> str:
        r, g, b = ThemeResolver.hex_to_rgb(hex_color)
        return f"{r},{g},{b}"

    @staticmethod
    def color_distance(c1: Tuple[int, int, int], c2: Tuple[int, int, int]) -> float:
        """Perceptually weighted RGB distance (approximate CIEDE2000)."""
        dr, dg, db = c1[0] - c2[0], c1[1] - c2[1], c1[2] - c2[2]
        return math.sqrt(2 * dr**2 + 4 * dg**2 + 3 * db**2)

    @staticmethod
    def relative_luminance(hex_color: str) -> float:
        """WCAG relative luminance (0=black, 1=white)."""
        r, g, b = ThemeResolver.hex_to_rgb(hex_color)
        def channel(c: int) -> float:
            v = c / 255
            return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
        return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)

    @staticmethod
    def contrast_ratio(hex_a: str, hex_b: str) -> float:
        """WCAG contrast ratio between two colors."""
        la = ThemeResolver.relative_luminance(hex_a)
        lb = ThemeResolver.relative_luminance(hex_b)
        lighter, darker = max(la, lb), min(la, lb)
        return (lighter + 0.05) / (darker + 0.05)

    @staticmethod
    def darken(hex_color: str, amount: float = 0.3) -> str:
        """Darken a hex color by `amount` (0.0–1.0)."""
        r, g, b = ThemeResolver.hex_to_rgb(hex_color)
        r = int(r * (1 - amount))
        g = int(g * (1 - amount))
        b = int(b * (1 - amount))
        return f"#{r:02X}{g:02X}{b:02X}"

    # ── Palette snap ──────────────────────────────────────────────────────

    @classmethod
    def find_nearest_palette(cls, structural_class: str, user_hex: str) -> str:
        """Snap user's hex color to the nearest palette by primary color distance."""
        try:
            user_rgb = cls.hex_to_rgb(user_hex)
        except ValueError:
            return DEFAULT_PALETTE.get(structural_class, "")

        theme_palettes = PALETTES.get(structural_class, {})
        best_name = DEFAULT_PALETTE.get(structural_class, next(iter(theme_palettes), ""))
        best_dist = float('inf')

        for name, vars_ in theme_palettes.items():
            primary = vars_.get('--primary')
            if primary:
                try:
                    dist = cls.color_distance(user_rgb, cls.hex_to_rgb(primary))
                    if dist < best_dist:
                        best_dist = dist
                        best_name = name
                except ValueError:
                    continue

        return best_name

    # ── Main resolver ─────────────────────────────────────────────────────

    @classmethod
    def resolve(
        cls,
        structural_class: str,
        palette_name: Optional[str],
        ai_css_vars: dict,
        user_color: Optional[str] = None,
    ) -> Tuple[dict, str]:
        """
        Merge all sources into a final CSS variable dict.

        Returns:
          (merged_vars: dict, resolved_palette_name: str)
        """
        theme_palettes = PALETTES.get(structural_class, {})

        # 1. Resolve palette name (validate or fall back to default)
        if palette_name and palette_name in theme_palettes:
            resolved_palette = palette_name
        elif structural_class in PALETTE_MANAGED_THEMES:
            resolved_palette = DEFAULT_PALETTE.get(structural_class, "")
            if palette_name:
                print(
                    f"  [ThemeResolver] Unknown palette '{palette_name}' for {structural_class}. "
                    f"Using default '{resolved_palette}'."
                )
        else:
            # AI-colored theme — no palette management
            resolved_palette = palette_name or ""

        # 2. Get palette vars
        palette_vars = theme_palettes.get(resolved_palette, {}).copy()

        # 3. Merge: AI vars first, then palette overwrites, then user on top
        merged = {**ai_css_vars, **palette_vars}

        # 4. Apply user's primary color override
        if user_color:
            try:
                cls.hex_to_rgb(user_color)  # validate
                merged['--primary'] = user_color
            except ValueError:
                print(f"  [ThemeResolver] Invalid primary_color '{user_color}' — ignored.")

        # 5. Auto-compute missing *-rgb variants for alpha usage in CSS
        for var in ('--primary', '--aurora-1', '--aurora-2', '--bg'):
            rgb_var = f"{var}-rgb"
            hex_val = merged.get(var)
            if hex_val and rgb_var not in merged:
                try:
                    merged[rgb_var] = cls.hex_to_rgb_str(hex_val)
                except ValueError:
                    pass

        # 6. gradient_flow: compute --bg-end if not in palette or AI vars
        if structural_class == 'gradient_flow' and '--bg-end' not in merged:
            bg = merged.get('--bg', '#0F0C29')
            merged['--bg-end'] = cls.darken(bg, 0.25)
            print(f"  [ThemeResolver] gradient_flow: auto-computed --bg-end from --bg.")

        # 7. aurora: validate that aurora-1 and aurora-2 are visually distinct
        if structural_class == 'aurora':
            a1 = merged.get('--aurora-1')
            a2 = merged.get('--aurora-2')
            if a1 and a2:
                try:
                    dist = cls.color_distance(cls.hex_to_rgb(a1), cls.hex_to_rgb(a2))
                    if dist < 80:
                        print(
                            f"  [ThemeResolver] aurora: --aurora-1 and --aurora-2 are too similar "
                            f"(dist={dist:.0f} < 80). Falling back to 'cosmic' palette."
                        )
                        fallback = PALETTES['aurora']['cosmic']
                        merged.update(fallback)
                        resolved_palette = 'cosmic'
                except ValueError:
                    pass

        # 8. editorial: validate primary vs bg contrast (WCAG decorative min 3:1)
        if structural_class == 'editorial':
            primary = merged.get('--primary')
            bg = merged.get('--bg', '#F9F6F1')
            if primary:
                try:
                    ratio = cls.contrast_ratio(primary, bg)
                    if ratio < 3.0:
                        print(
                            f"  [ThemeResolver] editorial: primary '{primary}' has low contrast "
                            f"({ratio:.1f}:1 vs bg). Falling back to 'navy' palette."
                        )
                        fallback = PALETTES['editorial']['navy']
                        merged.update(fallback)
                        resolved_palette = 'navy'
                except ValueError:
                    pass

        # 9. glassmorphism: enforce dark background for the glass effect.
        #    Glassmorphism is in DARK_THEMES but AI often picks near-white --bg
        #    (e.g. #F7FAFC), making all slides washed-out and defeating the
        #    frosted glass effect. The glass cards need contrast to look right.
        if structural_class == 'glassmorphism':
            bg = merged.get('--bg', '#F7FAFC')
            try:
                lum = cls.relative_luminance(bg)
                if lum > 0.4:  # too light for glass effect
                    dark_bg = cls.darken(bg, 0.80)
                    dark_bg_end = cls.darken(bg, 0.70)
                    print(
                        f"  [ThemeResolver] glassmorphism: AI bg '{bg}' is too light "
                        f"(lum={lum:.2f}). Darkening to '{dark_bg}' for glass effect."
                    )
                    merged['--bg'] = dark_bg
                    merged['--bg-end'] = dark_bg_end
                    merged['--bg-rgb'] = cls.hex_to_rgb_str(dark_bg)
                    # Ensure text is readable on dark background
                    merged['--text'] = '#F0F0F0'
                    merged['--text-secondary'] = 'rgba(255,255,255,0.65)'
                    # Card backgrounds: translucent white for the glass effect
                    merged['--card-bg'] = 'rgba(255, 255, 255, 0.08)'
            except ValueError:
                pass

        return merged, resolved_palette
