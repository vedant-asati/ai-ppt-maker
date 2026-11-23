"""
pptx_exporter.py — Export presentation as an editable PPTX file.

Strategy (Tier 2 — Visible Overlays):
  Each slide has:
    1. Full-bleed PNG background  — exact visual from the HTML→PNG pipeline
    2. Visible, editable text overlays — layout-aware, theme-colored, proper font sizes

  Layout-specific positioning ensures text boxes sit where they appear visually,
  so the user can: edit a title, fix a bullet, change a number — without
  touching the background image for small tweaks.

  Text colors are derived from the theme's --text CSS variable (already resolved),
  so dark themes get white text, light themes get dark text automatically.

Usage:
    from pptx_exporter import PptxExporter
    exporter = PptxExporter()
    exporter.export(png_files, master_plan, "output.pptx", resolved_vars=vars)
"""

import os
from typing import List, Optional, Dict, Tuple
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from rich import print as rprint


# ─── Slide dimensions (16:9) ─────────────────────────────────────────────────

SLIDE_W = Inches(13.333)   # 1920px at 144dpi
SLIDE_H = Inches(7.5)      # 1080px at 144dpi


# ─── Layout-specific text box positions ───────────────────────────────────────
# Format: (left, top, width, height) in Inches
# Designed around 13.333" × 7.5" slide canvas

LAYOUT_POSITIONS: Dict[str, Dict[str, Tuple]] = {
    'cover': {
        'eyebrow':   (2.0, 2.0,  9.3, 0.5),
        'title':     (1.5, 2.6,  10.3, 1.6),
        'subtitle':  (2.0, 4.3,  9.3, 0.8),
        'content':   (2.0, 5.3,  9.3, 1.8),
    },
    'split': {
        'eyebrow':   (0.8, 0.5,  5.8, 0.45),
        'title':     (0.8, 1.0,  5.8, 1.3),
        'subtitle':  (0.8, 2.4,  5.8, 0.65),
        'content':   (0.8, 3.2,  5.8, 3.8),
    },
    'stat': {
        'eyebrow':   (2.0, 0.5,  9.3, 0.5),
        'title':     (0.8, 1.1,  11.7, 0.9),   # title above the big number
        'value':     (1.0, 2.1,  11.3, 2.0),
        'label':     (2.0, 4.2,  9.3, 0.7),
        'content':   (2.0, 5.1,  9.3, 2.0),
    },
    'quote': {
        'eyebrow':   (1.5, 0.8,  10.3, 0.45),
        'quote':     (1.5, 1.8,  10.3, 3.5),
        'attribution': (2.5, 5.5, 8.3, 0.7),
    },
    'generic': {
        'eyebrow':   (0.8, 0.5,  11.7, 0.45),
        'title':     (0.8, 1.0,  11.7, 1.1),
        'subtitle':  (0.8, 2.2,  11.7, 0.65),
        'content':   (0.8, 3.0,  11.7, 4.0),
    },
    'timeline': {
        'eyebrow':   (0.8, 0.5,  11.7, 0.45),
        'title':     (0.8, 1.0,  11.7, 1.1),
        'subtitle':  (0.8, 2.2,  11.7, 0.65),
        'content':   (0.8, 3.0,  11.7, 4.0),
    },
    'infographic': {
        'eyebrow':   (0.8, 0.5,  11.7, 0.45),
        'title':     (0.8, 1.0,  11.7, 1.1),
        'subtitle':  (0.8, 2.2,  11.7, 0.65),
        'content':   (0.8, 3.0,  11.7, 4.0),
    },
    'bento_8_4': {
        'eyebrow':      (0.8, 0.45, 11.7, 0.35),
        'title':        (0.8, 0.85, 11.7, 0.70),
        'subtitle':     (0.8, 1.55, 11.7, 0.35),
        'hero_card':    (0.8, 1.70, 7.55, 5.10),
        'side_card_1':  (8.6, 1.70, 3.93, 2.45),
        'side_card_2':  (8.6, 4.35, 3.93, 2.45),
        'content':      (0.8, 1.70, 11.7, 5.10),
    },
    'bento_3col': {
        'eyebrow':      (0.8, 0.45, 11.7, 0.35),
        'title':        (0.8, 0.85, 11.7, 0.70),
        'subtitle':     (0.8, 1.55, 11.7, 0.35),
        'card_1':       (0.8, 1.70, 3.65, 5.10),
        'card_2':       (4.8, 1.70, 3.65, 5.10),
        'card_3':       (8.8, 1.70, 3.65, 5.10),
        'content':      (0.8, 1.70, 11.7, 5.10),
    },
    'editorial': {
        'eyebrow':      (0.8, 0.50, 6.80, 0.35),
        'title':        (0.8, 0.90, 6.80, 1.15),
        'content':      (0.8, 2.15, 6.80, 4.65),
        'caption':      (8.0, 5.80, 4.53, 0.80),
    },
    'creative': {
        'eyebrow':      (0.8, 0.50, 11.7, 0.35),
        'title':        (0.8, 0.90, 11.7, 0.75),
        'content':      (0.8, 1.75, 7.60, 5.00),
        'side_1':       (8.7, 1.75, 3.80, 2.35),
        'side_2':       (8.7, 4.40, 3.80, 2.35),
    },
    'modern_tech': {
        'eyebrow':      (0.8, 0.50, 11.7, 0.35),
        'title':        (0.8, 0.90, 11.7, 0.75),
        'content':      (0.8, 1.75, 7.60, 5.00),
        'aside':        (8.7, 1.75, 3.80, 5.00),
    },
    'kpi_dashboard': {
        'eyebrow':      (0.8, 0.50, 11.7, 0.35),
        'title':        (0.8, 0.90, 11.7, 0.75),
        'subtitle':     (0.8, 1.65, 11.7, 0.35),
        'card_1':       (0.8, 2.10, 5.65, 2.30),
        'card_2':       (6.85, 2.10, 5.65, 2.30),
        'card_3':       (0.8, 4.60, 5.65, 2.30),
        'card_4':       (6.85, 4.60, 5.65, 2.30),
        'content':      (0.8, 2.10, 11.7, 4.80),
    },
    'roadmap_chain': {
        'eyebrow':      (0.8, 0.50, 11.7, 0.35),
        'title':        (0.8, 0.90, 11.7, 0.75),
        'subtitle':     (0.8, 1.65, 11.7, 0.35),
        'step_1':       (0.8, 2.80, 2.70, 3.80),
        'step_2':       (3.8, 2.80, 2.70, 3.80),
        'step_3':       (6.8, 2.80, 2.70, 3.80),
        'step_4':       (9.8, 2.80, 2.70, 3.80),
        'content':      (0.8, 2.80, 11.7, 3.80),
    },
}
LAYOUT_POSITIONS['bento'] = LAYOUT_POSITIONS['bento_8_4']


# ─── Font size presets ────────────────────────────────────────────────────────

FONT_SIZES = {
    'cover_title':  Pt(36),
    'cover_sub':    Pt(20),
    'eyebrow':      Pt(12),
    'title':        Pt(28),
    'subtitle':     Pt(16),
    'stat_value':   Pt(72),
    'stat_label':   Pt(18),
    'quote_text':   Pt(26),
    'attribution':  Pt(14),
    'bullet':       Pt(16),
    'content':      Pt(15),
}


class PptxExporter:
    """Export rendered slides + metadata to an editable PPTX file."""

    def export(
        self,
        png_files: List[str],
        master_plan,
        output_path: str,
        resolved_vars: Optional[Dict] = None,
    ) -> bool:
        """
        Create a PPTX file with rendered PNGs as backgrounds
        and visible, layout-aware editable text overlays.

        Args:
            png_files:     Ordered list of rendered slide PNG paths.
            master_plan:   MasterPlan with slide metadata.
            output_path:   Path for the output .pptx file.
            resolved_vars: Theme CSS variable dict (for text/accent colors).
        """
        rprint("PptxExporter: Creating editable PPTX...")

        if not png_files:
            rprint("  [Warning] PptxExporter: no PNG files — cannot produce PPTX.")
            return False

        # Derive text and accent colors from theme vars
        text_color, accent_color = self._resolve_colors(resolved_vars or {})

        prs = Presentation()
        prs.slide_width = SLIDE_W
        prs.slide_height = SLIDE_H

        blank_layout = prs.slide_layouts[6]   # Blank — no placeholders

        slides_map = {s.slide_number: s for s in master_plan.slides}

        for i, png_path in enumerate(png_files):
            slide_number = i + 1
            slide_meta = slides_map.get(slide_number)

            if not os.path.exists(png_path):
                rprint(f"  [Warning] Missing PNG for slide {slide_number}: {png_path}")
                continue

            pptx_slide = prs.slides.add_slide(blank_layout)

            # ── Full-bleed background PNG ───────────────────────────────────
            pptx_slide.shapes.add_picture(
                png_path, Emu(0), Emu(0), SLIDE_W, SLIDE_H,
            )

            # ── Speaker notes ───────────────────────────────────────────────
            if slide_meta and slide_meta.speaker_notes:
                notes = pptx_slide.notes_slide
                notes.notes_text_frame.text = slide_meta.speaker_notes

            # ── Visible, layout-aware text overlays ─────────────────────────
            if slide_meta:
                self._add_overlays(pptx_slide, slide_meta, text_color, accent_color)

        # ── Save ────────────────────────────────────────────────────────────
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        try:
            prs.save(output_path)
            rprint(f"PptxExporter: Saved to {output_path}")
            return True
        except PermissionError:
            alt = output_path.replace(".pptx", "_v2.pptx")
            rprint(f"  [Warning] {output_path} locked — saving as {alt}")
            prs.save(alt)
            return True
        except Exception as e:
            rprint(f"  [Error] PPTX export failed: {e}")
            return False

    # ── Color resolution ──────────────────────────────────────────────────────

    def _resolve_colors(
        self, resolved_vars: Dict
    ) -> Tuple[RGBColor, RGBColor]:
        """
        Derive text + accent colors, and typography from theme CSS vars.

        --text  → body text color (white for dark themes, dark for light themes)
        --primary → accent color (used for stat values, eyebrow labels)
        --font-header → title font family
        --font-body   → content font family
        """
        def hex_to_rgb(hex_val: str) -> RGBColor:
            h = hex_val.lstrip('#')
            if len(h) != 6:
                raise ValueError(f"Bad hex: {hex_val}")
            return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

        try:
            text_color = hex_to_rgb(resolved_vars.get('--text', '#FFFFFF'))
        except (ValueError, TypeError):
            text_color = RGBColor(255, 255, 255)

        try:
            accent_color = hex_to_rgb(resolved_vars.get('--primary', '#F5C518'))
        except (ValueError, TypeError):
            accent_color = RGBColor(245, 197, 24)

        def clean_font(f_val: str, default: str) -> str:
            if not f_val:
                return default
            parts = f_val.split(',')
            return parts[0].strip("'\" ")

        self.header_font = clean_font(resolved_vars.get('--font-header', ''), 'Calibri')
        self.body_font = clean_font(resolved_vars.get('--font-body', ''), 'Calibri')

        return text_color, accent_color

    # ── Layout-aware overlays ─────────────────────────────────────────────────

    def _add_overlays(self, pptx_slide, slide_meta, text_color: RGBColor, accent_color: RGBColor):
        """Add visible, positioned text overlays based on layout type."""
        layout = slide_meta.layout_type or 'generic'
        positions = LAYOUT_POSITIONS.get(layout, LAYOUT_POSITIONS['generic'])

        is_centered = layout in ('cover', 'stat')
        title_align = PP_ALIGN.CENTER if is_centered else PP_ALIGN.LEFT

        # ── Eyebrow ──────────────────────────────────────────────────────
        if slide_meta.eyebrow and 'eyebrow' in positions:
            self._textbox(pptx_slide, slide_meta.eyebrow.upper(),
                          positions['eyebrow'], FONT_SIZES['eyebrow'],
                          accent_color, bold=True, alignment=title_align)

        # ── Stat layout ──────────────────────────────────────────────────
        if layout == 'stat':
            self._add_stat_overlays(pptx_slide, slide_meta, positions,
                                    text_color, accent_color)

        # ── Quote layout ─────────────────────────────────────────────────
        elif layout == 'quote':
            self._add_quote_overlays(pptx_slide, slide_meta, positions, text_color)

        # ── Bento layout (hero card + side cards) ─────────────────────────
        elif layout in ('bento', 'bento_8_4', 'bento_3col'):
            self._add_bento_overlays(pptx_slide, slide_meta, positions, text_color, accent_color)

        # ── KPI Dashboard layout ─────────────────────────────────────────
        elif layout == 'kpi_dashboard':
            self._add_kpi_overlays(pptx_slide, slide_meta, positions, text_color, accent_color)

        # ── Roadmap Chain layout ─────────────────────────────────────────
        elif layout == 'roadmap_chain':
            self._add_roadmap_overlays(pptx_slide, slide_meta, positions, text_color, accent_color)

        # ── Cover / Split / Generic / Timeline / Infographic ─────────────
        else:
            # Title
            if slide_meta.title and 'title' in positions:
                title_size = (FONT_SIZES['cover_title'] if layout == 'cover'
                              else FONT_SIZES['title'])
                self._textbox(pptx_slide, slide_meta.title,
                              positions['title'], title_size,
                              text_color, bold=True, alignment=title_align,
                              font_name=getattr(self, 'header_font', 'Calibri'))

            # Subtitle
            if slide_meta.subtitle and 'subtitle' in positions:
                sub_size = (FONT_SIZES['cover_sub'] if layout == 'cover'
                            else FONT_SIZES['subtitle'])
                self._textbox(pptx_slide, slide_meta.subtitle,
                              positions['subtitle'], sub_size,
                              text_color, italic=True, alignment=title_align)

            # Content blocks
            if 'content' in positions:
                content_lines = self._extract_content(slide_meta)
                if content_lines:
                    self._textbox(pptx_slide, '\n'.join(content_lines),
                                  positions['content'], FONT_SIZES['content'],
                                  text_color, alignment=PP_ALIGN.LEFT,
                                  wrap=True)

    def _add_stat_overlays(self, pptx_slide, slide_meta, positions,
                           text_color: RGBColor, accent_color: RGBColor):
        """Special handling for stat layout — big number + label."""
        # Title above the stat
        if slide_meta.title and 'title' in positions:
            self._textbox(pptx_slide, slide_meta.title,
                          positions['title'], FONT_SIZES['title'],
                          text_color, bold=True, alignment=PP_ALIGN.CENTER)

        # Extract stat block
        stat_block = None
        if slide_meta.content_blocks:
            for block in slide_meta.content_blocks:
                if block.block_type == 'stat':
                    stat_block = block
                    break

        if stat_block and 'value' in positions:
            self._textbox(pptx_slide, stat_block.value or '',
                          positions['value'], FONT_SIZES['stat_value'],
                          accent_color, bold=True, alignment=PP_ALIGN.CENTER)
            if stat_block.label and 'label' in positions:
                self._textbox(pptx_slide, stat_block.label,
                              positions['label'], FONT_SIZES['stat_label'],
                              text_color, alignment=PP_ALIGN.CENTER)
        elif 'content' in positions:
            # Fallback: no stat block found — render as generic content
            content_lines = self._extract_content(slide_meta)
            if content_lines:
                self._textbox(pptx_slide, '\n'.join(content_lines),
                              positions['content'], FONT_SIZES['content'],
                              text_color, wrap=True)

    def _add_quote_overlays(self, pptx_slide, slide_meta, positions, text_color: RGBColor):
        """Special handling for quote layout — centered italic quote + attribution."""
        quote_block = None
        if slide_meta.content_blocks:
            for block in slide_meta.content_blocks:
                if block.block_type == 'pullquote':
                    quote_block = block
                    break

        if quote_block and 'quote' in positions:
            quote_text = f'"{quote_block.quote}"' if quote_block.quote else ''
            self._textbox(pptx_slide, quote_text,
                          positions['quote'], FONT_SIZES['quote_text'],
                          text_color, italic=True,
                          alignment=PP_ALIGN.CENTER, wrap=True)
            if quote_block.attribution and 'attribution' in positions:
                self._textbox(pptx_slide, f"— {quote_block.attribution}",
                              positions['attribution'], FONT_SIZES['attribution'],
                              text_color, italic=True, alignment=PP_ALIGN.CENTER)
        elif slide_meta.title and 'quote' in positions:
            # Fallback: use title as quote text
            self._textbox(pptx_slide, f'"{slide_meta.title}"',
                          positions['quote'], FONT_SIZES['quote_text'],
                          text_color, italic=True, alignment=PP_ALIGN.CENTER, wrap=True)

    # ── Content extraction ────────────────────────────────────────────────────

    def _extract_content(self, slide_meta) -> List[str]:
        """Flatten content blocks into readable lines for a text overlay."""
        lines = []

        for block in (slide_meta.content_blocks or []):
            bt = block.block_type

            if bt == 'bullets' and block.items:
                for item in block.items:
                    lines.append(f"• {item}")

            elif bt == 'stat':
                lines.append(f"{block.value}  —  {block.label}")

            elif bt == 'pullquote' and block.quote:
                lines.append(f'"{block.quote}"')
                if block.attribution:
                    lines.append(f"— {block.attribution}")

            elif bt == 'steps' and block.steps:
                labels = block.step_labels or []
                for j, step in enumerate(block.steps):
                    label = labels[j] if j < len(labels) else f"Step {j+1}"
                    lines.append(f"{label}: {step}")

            elif bt == 'keyvalue' and block.pairs:
                for pair in block.pairs:
                    if isinstance(pair, dict):
                        k = pair.get('key', '')
                        v = pair.get('value', '')
                    elif hasattr(pair, 'key'):
                        k = getattr(pair, 'key', '')
                        v = getattr(pair, 'value', '')
                    else:
                        k, v = str(pair), ''
                    lines.append(f"{k}: {v}" if v else f"{k}")

            elif bt == 'comparison':
                l_label = block.left_label or 'Option A'
                r_label = block.right_label or 'Option B'
                l_items = ', '.join(block.left_items or [])
                r_items = ', '.join(block.right_items or [])
                lines.append(f"{l_label}: {l_items}")
                lines.append(f"{r_label}: {r_items}")

            elif bt == 'callout' and block.text:
                lines.append(f"💡 {block.text}")

        # Legacy fallback
        if not lines and slide_meta.content_bullets:
            lines = [f"• {b}" for b in slide_meta.content_bullets]

        return lines

    def _add_bento_overlays(self, pptx_slide, slide_meta, positions,
                            text_color: RGBColor, accent_color: RGBColor):
        """Special handling for Bento layouts (hero card + side cards)."""
        # Title
        if slide_meta.title and 'title' in positions:
            self._textbox(pptx_slide, slide_meta.title,
                          positions['title'], FONT_SIZES['title'],
                          text_color, bold=True, alignment=PP_ALIGN.LEFT)

        # Subtitle
        if slide_meta.subtitle and 'subtitle' in positions:
            self._textbox(pptx_slide, slide_meta.subtitle,
                          positions['subtitle'], FONT_SIZES['subtitle'],
                          text_color, italic=True, alignment=PP_ALIGN.LEFT)

        # Find bento block
        bento_block = None
        if slide_meta.content_blocks:
            for block in slide_meta.content_blocks:
                if getattr(block, 'block_type', None) == 'bento':
                    bento_block = block
                    break

        if bento_block and getattr(bento_block, 'cards', None):
            cards = bento_block.cards
            if 'hero_card' in positions and len(cards) >= 1:
                hero = cards[0]
                hero_text = []
                if hero.badge:
                    hero_text.append(f"[{hero.badge}]")
                if hero.title:
                    hero_text.append(hero.title)
                if hero.stat_val:
                    hero_text.append(f"{hero.stat_val} {hero.stat_label or ''}")
                if hero.body:
                    hero_text.append(hero.body)
                self._textbox(pptx_slide, '\n'.join(hero_text),
                              positions['hero_card'], FONT_SIZES['content'],
                              text_color, wrap=True)

            if 'side_card_1' in positions and len(cards) >= 2:
                c1 = cards[1]
                t1 = [f"[{c1.badge}]"] if c1.badge else []
                if c1.stat_val:
                    t1.append(f"{c1.stat_val} {c1.stat_label or ''}")
                if c1.title:
                    t1.append(c1.title)
                if c1.body:
                    t1.append(c1.body)
                self._textbox(pptx_slide, '\n'.join(t1),
                              positions['side_card_1'], FONT_SIZES['content'],
                              text_color, wrap=True)

            if 'side_card_2' in positions and len(cards) >= 3:
                c2 = cards[2]
                t2 = [f"[{c2.badge}]"] if c2.badge else []
                if c2.stat_val:
                    t2.append(f"{c2.stat_val} {c2.stat_label or ''}")
                if c2.title:
                    t2.append(c2.title)
                if c2.body:
                    t2.append(c2.body)
                self._textbox(pptx_slide, '\n'.join(t2),
                              positions['side_card_2'], FONT_SIZES['content'],
                              text_color, wrap=True)
            elif 'card_1' in positions:
                for idx, c in enumerate(cards[:3]):
                    card_key = f'card_{idx+1}'
                    if card_key in positions:
                        ct = [f"[{c.badge}]"] if c.badge else []
                        if c.stat_val:
                            ct.append(f"{c.stat_val} {c.stat_label or ''}")
                        if c.title:
                            ct.append(c.title)
                        if c.body:
                            ct.append(c.body)
                        self._textbox(pptx_slide, '\n'.join(ct),
                                      positions[card_key], FONT_SIZES['content'],
                                      text_color, wrap=True)
        else:
            if 'content' in positions:
                content_lines = self._extract_content(slide_meta)
                if content_lines:
                    self._textbox(pptx_slide, '\n'.join(content_lines),
                                  positions['content'], FONT_SIZES['content'],
                                  text_color, alignment=PP_ALIGN.LEFT, wrap=True)

    def _add_kpi_overlays(self, pptx_slide, slide_meta, positions,
                          text_color: RGBColor, accent_color: RGBColor):
        """Add visible text boxes for KPI dashboard 2x2 grid."""
        if slide_meta.eyebrow and 'eyebrow' in positions:
            self._textbox(pptx_slide, slide_meta.eyebrow.upper(),
                          positions['eyebrow'], FONT_SIZES['eyebrow'],
                          accent_color, bold=True,
                          font_name=getattr(self, 'header_font', 'Calibri'))

        if slide_meta.title and 'title' in positions:
            self._textbox(pptx_slide, slide_meta.title,
                          positions['title'], FONT_SIZES['title'],
                          text_color, bold=True,
                          font_name=getattr(self, 'header_font', 'Calibri'))

        if slide_meta.subtitle and 'subtitle' in positions:
            self._textbox(pptx_slide, slide_meta.subtitle,
                          positions['subtitle'], FONT_SIZES['subtitle'],
                          text_color, italic=True)

        cards = []
        if slide_meta.content_blocks:
            for b in slide_meta.content_blocks:
                if getattr(b, 'block_type', None) in ('kpi_dashboard', 'bento') and getattr(b, 'cards', None):
                    cards = b.cards
                    break

        if cards:
            for idx, c in enumerate(cards[:4]):
                ck = f'card_{idx+1}'
                if ck in positions:
                    lines = []
                    badge = getattr(c, 'badge', None)
                    if badge:
                        lines.append(f"[{badge}]")
                    val = getattr(c, 'value', None) or getattr(c, 'stat_val', None) or '100%'
                    delta = getattr(c, 'delta', None) or getattr(c, 'stat_context', None)
                    if delta:
                        lines.append(f"{val} ({delta})")
                    else:
                        lines.append(f"{val}")
                    lbl = getattr(c, 'label', None) or getattr(c, 'title', None) or getattr(c, 'stat_label', None)
                    if lbl:
                        lines.append(lbl)
                    body = getattr(c, 'body', None)
                    if body:
                        lines.append(body)
                    self._textbox(pptx_slide, '\n'.join(lines),
                                  positions[ck], FONT_SIZES['content'],
                                  text_color, wrap=True)
        else:
            if 'content' in positions:
                content_lines = self._extract_content(slide_meta)
                if content_lines:
                    self._textbox(pptx_slide, '\n'.join(content_lines),
                                  positions['content'], FONT_SIZES['content'],
                                  text_color, alignment=PP_ALIGN.LEFT, wrap=True)

    def _add_roadmap_overlays(self, pptx_slide, slide_meta, positions,
                              text_color: RGBColor, accent_color: RGBColor):
        """Add visible text boxes for horizontal roadmap chain."""
        if slide_meta.eyebrow and 'eyebrow' in positions:
            self._textbox(pptx_slide, slide_meta.eyebrow.upper(),
                          positions['eyebrow'], FONT_SIZES['eyebrow'],
                          accent_color, bold=True,
                          font_name=getattr(self, 'header_font', 'Calibri'))

        if slide_meta.title and 'title' in positions:
            self._textbox(pptx_slide, slide_meta.title,
                          positions['title'], FONT_SIZES['title'],
                          text_color, bold=True,
                          font_name=getattr(self, 'header_font', 'Calibri'))

        if slide_meta.subtitle and 'subtitle' in positions:
            self._textbox(pptx_slide, slide_meta.subtitle,
                          positions['subtitle'], FONT_SIZES['subtitle'],
                          text_color, italic=True)

        steps = []
        labels = []
        if slide_meta.content_blocks:
            for b in slide_meta.content_blocks:
                if getattr(b, 'block_type', None) == 'steps' and getattr(b, 'steps', None):
                    steps = b.steps
                    labels = getattr(b, 'step_labels', []) or []
                    break

        if not steps and slide_meta.content_bullets:
            steps = slide_meta.content_bullets

        if steps:
            for idx, s in enumerate(steps[:4]):
                sk = f'step_{idx+1}'
                if sk in positions:
                    lbl = labels[idx] if idx < len(labels) else f"Phase {idx+1}"
                    lines = [f"[{lbl}]", str(s)]
                    self._textbox(pptx_slide, '\n'.join(lines),
                                  positions[sk], FONT_SIZES['content'],
                                  text_color, wrap=True)
        else:
            if 'content' in positions:
                content_lines = self._extract_content(slide_meta)
                if content_lines:
                    self._textbox(pptx_slide, '\n'.join(content_lines),
                                  positions['content'], FONT_SIZES['content'],
                                  text_color, alignment=PP_ALIGN.LEFT, wrap=True)

    # ── Text box primitive ────────────────────────────────────────────────────

    def _textbox(
        self,
        slide,
        text: str,
        position: Tuple[float, float, float, float],
        font_size,
        color: RGBColor,
        bold: bool = False,
        italic: bool = False,
        alignment: PP_ALIGN = PP_ALIGN.LEFT,
        wrap: bool = True,
        font_name: Optional[str] = None,
    ):
        """
        Add a single positioned, formatted text box to a slide.
        Text is always visible (proper color + size).
        """
        if not text or not text.strip():
            return

        left, top, width, height = [Inches(v) for v in position]

        txBox = slide.shapes.add_textbox(left, top, width, height)
        tf = txBox.text_frame
        tf.word_wrap = wrap
        tf.auto_size = None   # Don't auto-resize — respect our position bounds
        # Zero-margin padding prevents PowerPoint default 0.1" margin clipping
        tf.margin_left = Inches(0.05)
        tf.margin_right = Inches(0.05)
        tf.margin_top = Inches(0.05)
        tf.margin_bottom = Inches(0.05)

        # First paragraph
        p = tf.paragraphs[0]
        p.alignment = alignment

        # Handle multi-line text (newlines → separate paragraphs)
        lines = text.split('\n')
        target_font = font_name or getattr(self, 'body_font', 'Calibri')
        for i, line in enumerate(lines):
            if i == 0:
                para = p
            else:
                para = tf.add_paragraph()
                para.alignment = alignment

            run = para.add_run()
            run.text = line
            run.font.name = target_font
            run.font.size = font_size
            run.font.bold = bold
            run.font.italic = italic
            run.font.color.rgb = color
