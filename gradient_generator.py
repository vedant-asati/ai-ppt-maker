"""
gradient_generator.py — Theme-aware gradient image generator for offline fallbacks.

Replaces the grey rectangle placeholder with visually coherent gradient backgrounds
that match the active structural class / palette.
"""

import os
import math
import random
from typing import Tuple, Optional

from PIL import Image, ImageDraw, ImageFilter
from theme_palettes import GRADIENT_FALLBACK_PRESETS, DARK_THEMES

WIDTH  = 1920
HEIGHT = 1080


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


class GradientGenerator:

    def generate(
        self,
        structural_class: str,
        primary_hex: Optional[str] = None,
        out_path: str = 'gradient.png',
        seed: int = 0,
    ) -> str:
        """
        Generate a theme-appropriate gradient image and save it to out_path.
        Returns out_path.
        """
        presets = GRADIENT_FALLBACK_PRESETS.get(
            structural_class,
            GRADIENT_FALLBACK_PRESETS['corporate_clean']
        )
        rng = random.Random(seed)
        start_rgb, end_rgb, angle, pattern = rng.choice(presets)

        # If user provided a primary color, tint the gradient toward it
        if primary_hex:
            try:
                primary_rgb = _hex_to_rgb(primary_hex)
                if structural_class in DARK_THEMES:
                    # Blend end color 30% toward the primary
                    end_rgb = self._blend(end_rgb, primary_rgb, 0.3)
                else:
                    # Blend start color 20% toward the primary (subtle)
                    start_rgb = self._blend(start_rgb, primary_rgb, 0.2)
            except (ValueError, IndexError):
                pass

        img = self._draw_gradient(start_rgb, end_rgb, angle)

        # Apply decorative pattern layer
        if pattern == 'glow':
            img = self._add_glow(img, primary_hex or '#00FFD1', structural_class)
        elif pattern == 'circles':
            img = self._add_circles(img, structural_class)
        elif pattern == 'shimmer':
            img = self._add_shimmer(img, primary_hex)
        elif pattern == 'grid':
            img = self._add_grid(img)
        elif pattern == 'dots':
            img = self._add_dots(img)
        # 'none' → no pattern

        # Light gaussian blur to smooth out banding
        if structural_class not in ('editorial', 'minimalist'):
            img = img.filter(ImageFilter.GaussianBlur(radius=1))

        os.makedirs(os.path.dirname(out_path) if os.path.dirname(out_path) else '.', exist_ok=True)
        img.save(out_path, format='PNG', optimize=True)
        return out_path

    # ─── gradient drawing ───────────────────────────────────────────────

    def _draw_gradient(
        self,
        start: Tuple[int, int, int],
        end: Tuple[int, int, int],
        angle: int = 135,
    ) -> Image.Image:
        img = Image.new('RGB', (WIDTH, HEIGHT))
        draw = ImageDraw.Draw(img)

        rad = math.radians(angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        # Project each pixel onto the gradient axis
        diagonal = math.sqrt(WIDTH**2 + HEIGHT**2)

        for y in range(0, HEIGHT, 2):        # step 2 for speed
            for x in range(0, WIDTH, 2):
                t = (x * cos_a + y * sin_a) / diagonal
                t = max(0.0, min(1.0, t))
                r = int(start[0] + t * (end[0] - start[0]))
                g = int(start[1] + t * (end[1] - start[1]))
                b = int(start[2] + t * (end[2] - start[2]))
                draw.rectangle([x, y, x+1, y+1], fill=(r, g, b))

        return img

    # ─── pattern overlays ───────────────────────────────────────────────

    def _add_glow(
        self,
        img: Image.Image,
        primary_hex: Optional[str],
        structural_class: str,
    ) -> Image.Image:
        """Dark-neon glow: one large radial glow at a random-ish position."""
        overlay = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        try:
            pr, pg, pb = _hex_to_rgb(primary_hex or '#00FFD1')
        except Exception:
            pr, pg, pb = 0, 255, 209

        # Main glow — top-left area (behind title zone)
        cx, cy = WIDTH // 4, HEIGHT // 3
        for radius in range(400, 0, -20):
            alpha = int(40 * (1 - radius / 400))
            draw.ellipse(
                [cx - radius, cy - radius, cx + radius, cy + radius],
                fill=(pr, pg, pb, alpha),
            )

        # Secondary smaller glow — bottom-right
        cx2, cy2 = WIDTH * 3 // 4, HEIGHT * 2 // 3
        for radius in range(200, 0, -20):
            alpha = int(20 * (1 - radius / 200))
            draw.ellipse(
                [cx2 - radius, cy2 - radius, cx2 + radius, cy2 + radius],
                fill=(pr, pg, pb, alpha),
            )

        base = img.convert('RGBA')
        merged = Image.alpha_composite(base, overlay)
        return merged.convert('RGB')

    def _add_circles(self, img: Image.Image, structural_class: str) -> Image.Image:
        """Glassmorphism / gradient-flow: soft translucent circles."""
        overlay = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        circles = [
            (WIDTH * 0.15, HEIGHT * 0.25, 380, (255, 255, 255, 18)),
            (WIDTH * 0.75, HEIGHT * 0.60, 300, (255, 255, 255, 12)),
            (WIDTH * 0.50, HEIGHT * 0.85, 250, (255, 255, 255, 10)),
            (WIDTH * 0.88, HEIGHT * 0.15, 180, (255, 255, 255, 8)),
        ]
        for cx, cy, r, color in circles:
            cx, cy, r = int(cx), int(cy), int(r)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)

        base = img.convert('RGBA')
        merged = Image.alpha_composite(base, overlay)
        return merged.convert('RGB')

    def _add_shimmer(self, img: Image.Image, primary_hex: Optional[str]) -> Image.Image:
        """Aurora shimmer: two large radial aurora blobs."""
        overlay = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        try:
            pr, pg, pb = _hex_to_rgb(primary_hex or '#6366F1')
        except Exception:
            pr, pg, pb = 99, 102, 241

        # Aurora blob 1 — top-left
        for r in range(500, 0, -25):
            alpha = int(35 * (1 - r / 500))
            draw.ellipse(
                [WIDTH // 5 - r, -r // 2, WIDTH // 5 + r, r],
                fill=(pr, pg, pb, alpha),
            )

        # Aurora blob 2 — bottom-right (contrasting tint)
        r2, g2, b2 = min(255, pb + 80), min(255, pg // 2), min(255, pr // 2)
        for r in range(400, 0, -25):
            alpha = int(25 * (1 - r / 400))
            draw.ellipse(
                [WIDTH - WIDTH // 4 - r, HEIGHT - r, WIDTH - WIDTH // 4 + r, HEIGHT + r // 2],
                fill=(r2, g2, b2, alpha),
            )

        base = img.convert('RGBA')
        merged = Image.alpha_composite(base, overlay)
        return merged.convert('RGB')

    def _add_grid(self, img: Image.Image) -> Image.Image:
        """Neo-brutalism: subtle dark grid lines."""
        draw = ImageDraw.Draw(img)
        line_color = (0, 0, 0, 30)
        step = 80
        for x in range(0, WIDTH, step):
            draw.line([(x, 0), (x, HEIGHT)], fill=(0, 0, 0), width=1)
        for y in range(0, HEIGHT, step):
            draw.line([(0, y), (WIDTH, y)], fill=(0, 0, 0), width=1)
        return img

    def _add_dots(self, img: Image.Image) -> Image.Image:
        """Corporate-clean: very subtle dot pattern."""
        draw = ImageDraw.Draw(img)
        step = 60
        for x in range(0, WIDTH + step, step):
            for y in range(0, HEIGHT + step, step):
                draw.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(150, 160, 180))
        return img

    # ─── color math ─────────────────────────────────────────────────────

    @staticmethod
    def _blend(
        base: Tuple[int, int, int],
        tint: Tuple[int, int, int],
        amount: float,
    ) -> Tuple[int, int, int]:
        return (
            int(base[0] + amount * (tint[0] - base[0])),
            int(base[1] + amount * (tint[1] - base[1])),
            int(base[2] + amount * (tint[2] - base[2])),
        )
