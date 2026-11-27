"""
template_injector.py — Injects AI-synthesized slide content directly into native SlidesGo PPTX templates.
Preserves all native vector graphics, high-res backgrounds, layout shapes, and slide masters.
"""

import os
import glob
from typing import Optional, List
from pptx import Presentation
from rich import print as rprint
from ppt_maker.core.schemas import MasterPlan, Slide

_PKG_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_TEMPLATES_DIR = os.environ.get(
    "SLIDESGO_TEMPLATES_DIR",
    os.path.join(_PKG_ROOT, "temp", "slidesgoppts")
)


class TemplateInjector:
    """
    Clones and injects content into native pre-designed SlidesGo PowerPoint presentations.
    """

    def __init__(self, templates_dir: Optional[str] = None):
        self.templates_dir = templates_dir or DEFAULT_TEMPLATES_DIR

    def list_available_templates(self) -> List[str]:
        """Return list of available PPTX template basenames."""
        if not os.path.isdir(self.templates_dir):
            return []
        files = glob.glob(os.path.join(self.templates_dir, "*.pptx"))
        return sorted([os.path.basename(f) for f in files])

    def find_template(self, query: str) -> Optional[str]:
        """
        Locate template file by exact path, filename, or substring query.
        e.g. 'Minimalist Pitch Deck', 'tech', 'watercolor'.
        """
        if os.path.isfile(query):
            return os.path.abspath(query)

        target = os.path.join(self.templates_dir, query)
        if os.path.isfile(target):
            return target

        if not query.lower().endswith(".pptx"):
            query_pptx = os.path.join(self.templates_dir, f"{query}.pptx")
            if os.path.isfile(query_pptx):
                return query_pptx

        # Case-insensitive substring match
        q_lower = query.lower().replace("-", " ").replace("_", " ")
        for fname in self.list_available_templates():
            f_clean = fname.lower().replace("-", " ").replace("_", " ")
            if q_lower in f_clean:
                return os.path.join(self.templates_dir, fname)

        return None

    def inject(
        self,
        template_name_or_path: str,
        master_plan: MasterPlan,
        output_path: str
    ) -> bool:
        """
        Inject master_plan slides into the chosen SlidesGo PPTX template and save.
        """
        template_path = self.find_template(template_name_or_path)
        if not template_path:
            rprint(f"  [Error] TemplateInjector: Template '{template_name_or_path}' not found in {self.templates_dir}.")
            return False

        rprint(f"TemplateInjector: Loading master template '{os.path.basename(template_path)}'...")
        try:
            prs = Presentation(template_path)
        except Exception as e:
            rprint(f"  [Error] TemplateInjector: Failed to load presentation: {e}")
            return False

        total_plan_slides = len(master_plan.slides)
        total_template_slides = len(prs.slides)
        rprint(f"  Template has {total_template_slides} slides; injecting {total_plan_slides} AI slides.")

        # Expand template if master has fewer slides than required
        if total_template_slides < total_plan_slides and len(prs.slides) > 0:
            last_layout = prs.slides[-1].slide_layout
            while len(prs.slides) < total_plan_slides:
                prs.slides.add_slide(last_layout)

        # Iterate and inject slide content
        for idx, slide_meta in enumerate(master_plan.slides):
            if idx >= len(prs.slides):
                break

            pptx_slide = prs.slides[idx]
            self._inject_slide_content(pptx_slide, slide_meta)

            # Speaker notes
            if slide_meta.speaker_notes:
                notes = pptx_slide.notes_slide
                notes.notes_text_frame.text = slide_meta.speaker_notes

        # Trim remaining unused slides from template
        while len(prs.slides) > total_plan_slides:
            rId = prs.slides._sldIdLst[-1].rId
            prs.part.drop_rel(rId)
            del prs.slides._sldIdLst[-1]

        # Save output
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        try:
            prs.save(output_path)
            rprint(f"TemplateInjector: Successfully saved injected presentation to {output_path}")
            return True
        except Exception as e:
            rprint(f"  [Error] TemplateInjector: Failed to save output PPTX: {e}")
            return False

    def _inject_slide_content(self, pptx_slide, slide_meta: Slide):
        """
        Classify text shapes on the slide and replace text content intelligently.
        """
        text_shapes = []
        for shape in pptx_slide.shapes:
            if shape.has_text_frame:
                has_text = any(p.text.strip() for p in shape.text_frame.paragraphs)
                if has_text:
                    # Calculate approximate font size or length
                    first_p = shape.text_frame.paragraphs[0]
                    font_size = 18
                    if first_p.runs and first_p.runs[0].font.size:
                        font_size = first_p.runs[0].font.size.pt
                    text_shapes.append((shape, font_size, shape.top))

        if not text_shapes:
            return

        # Sort text shapes: largest font first for title candidate, then vertical position
        text_shapes_by_font = sorted(text_shapes, key=lambda x: x[1], reverse=True)
        title_shape = text_shapes_by_font[0][0]

        # Inject title
        if slide_meta.title:
            tf = title_shape.text_frame
            if tf.paragraphs:
                p = tf.paragraphs[0]
                if p.runs:
                    p.runs[0].text = slide_meta.title
                    # Remove trailing runs to avoid ghosting
                    for r in p.runs[1:]:
                        r.text = ""
                else:
                    p.text = slide_meta.title
                # Clear extra paragraphs in title box
                for p_extra in tf.paragraphs[1:]:
                    p_extra.text = ""

        # Remaining shapes for subtitle and body
        remaining = [s[0] for s in text_shapes if s[0] != title_shape]
        if not remaining:
            return

        # Sort remaining vertically
        remaining_by_top = sorted(remaining, key=lambda s: s.top)

        # Subtitle
        if slide_meta.subtitle and remaining_by_top:
            sub_shape = remaining_by_top[0]
            tf = sub_shape.text_frame
            if tf.paragraphs:
                p = tf.paragraphs[0]
                if p.runs:
                    p.runs[0].text = slide_meta.subtitle
                    for r in p.runs[1:]:
                        r.text = ""
                else:
                    p.text = slide_meta.subtitle
                for p_extra in tf.paragraphs[1:]:
                    p_extra.text = ""
            remaining_by_top = remaining_by_top[1:]

        # Body / Content injection
        content_items = self._extract_content_lines(slide_meta)
        if content_items and remaining_by_top:
            body_shape = remaining_by_top[0]
            tf = body_shape.text_frame

            # Replace or extend paragraphs
            for i, item in enumerate(content_items):
                if i < len(tf.paragraphs):
                    p = tf.paragraphs[i]
                    if p.runs:
                        p.runs[0].text = item
                        for r in p.runs[1:]:
                            r.text = ""
                    else:
                        p.text = item
                else:
                    p = tf.add_paragraph()
                    p.text = item

            # Clear any leftover paragraphs in body box
            if len(tf.paragraphs) > len(content_items):
                for p_leftover in tf.paragraphs[len(content_items):]:
                    p_leftover.text = ""

    def _extract_content_lines(self, slide_meta: Slide) -> List[str]:
        """Extract clean text lines from blocks or bullets."""
        lines = []
        if slide_meta.content_blocks:
            for b in slide_meta.content_blocks:
                b_type = getattr(b, 'block_type', '')
                if b_type == 'bullets':
                    lines.extend([str(it) for it in getattr(b, 'items', [])])
                elif b_type == 'steps':
                    lines.extend([str(st) for st in getattr(b, 'steps', [])])
                elif b_type == 'pullquote':
                    q = getattr(b, 'quote', '')
                    att = getattr(b, 'attribution', '')
                    lines.append(f'"{q}"')
                    if att:
                        lines.append(f"— {att}")
                elif b_type == 'stat':
                    v = getattr(b, 'value', '')
                    lbl = getattr(b, 'label', '')
                    ctx = getattr(b, 'context', '')
                    lines.append(f"{v} {lbl}".strip())
                    if ctx:
                        lines.append(ctx)
                elif b_type in ('bento', 'kpi_dashboard'):
                    cards = getattr(b, 'cards', [])
                    for c in cards:
                        c_title = getattr(c, 'title', None) or getattr(c, 'label', None) or getattr(c, 'badge', None)
                        c_val = getattr(c, 'value', None) or getattr(c, 'stat_val', None)
                        c_body = getattr(c, 'body', None)
                        entry = f"{c_val} — {c_title}" if (c_val and c_title) else (c_title or c_val or "")
                        if entry:
                            lines.append(entry)
                        if c_body:
                            lines.append(c_body)

        if not lines and slide_meta.content_bullets:
            lines.extend(slide_meta.content_bullets)

        return lines

