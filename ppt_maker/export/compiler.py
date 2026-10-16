"""
compiler.py — PDF compilation and speaker notes export.

Combines rendered PNG slides into a high-quality PDF.
Exports a rich speaker notes companion markdown document.
"""

import os
from PIL import Image


class Compiler:
    def __init__(self):
        pass

    def compile_to_pdf(self, image_paths: list, output_pdf: str) -> bool:
        """Compile rendered PNG slides into a single PDF file."""
        if not image_paths:
            print("No images to compile.")
            return False

        print(f"Compiling {len(image_paths)} images to {output_pdf}...")

        try:
            first_image = Image.open(image_paths[0]).convert('RGB')
        except Exception as e:
            print(f"[Error] Could not open first slide image: {e}")
            return False

        rest = []
        for path in image_paths[1:]:
            try:
                img = Image.open(path).convert('RGB')
                rest.append(img)
            except Exception as e:
                print(f"  [Warning] Could not open {path}: {e} — skipping slide.")

        out_dir = os.path.dirname(output_pdf)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        try:
            first_image.save(
                output_pdf,
                save_all=True,
                append_images=rest,
                quality=100,
                subsampling=0,
                resolution=150.0,   # 150 DPI — good balance of quality vs file size
            )
            print(f"Successfully saved PDF to {output_pdf}")
            return True
        except PermissionError:
            # PDF is open in another app — save with versioned name
            alt = output_pdf.replace(".pdf", "_v2.pdf")
            print(f"  [Warning] {output_pdf} is locked (open in another app?). Saving as {alt}")
            first_image.save(
                alt,
                save_all=True,
                append_images=rest,
                quality=100,
                subsampling=0,
                resolution=150.0,
            )
            print(f"Successfully saved PDF to {alt}")
            return True
        except Exception as e:
            print(f"  [Error] PDF compilation failed: {e}")
            return False

    def merge_pdfs(self, pdf_files: list, output_pdf: str) -> bool:
        """
        Merge per-slide vector PDFs into a single multi-page PDF.

        Uses pypdf (already installed) — pure Python, no extra dependencies.
        Each input PDF should be a single-page vector PDF from render_to_pdf().
        """
        if not pdf_files:
            print("No PDFs to merge.")
            return False

        print(f"Merging {len(pdf_files)} slides to {output_pdf}...")

        from pypdf import PdfWriter

        out_dir = os.path.dirname(output_pdf)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        writer = PdfWriter()
        skipped = 0
        for pdf_path in pdf_files:
            if os.path.exists(pdf_path):
                writer.append(pdf_path)
            else:
                print(f"  [Warning] Missing slide PDF: {pdf_path} — skipping.")
                skipped += 1

        if skipped:
            print(f"  [Warning] {skipped} slide(s) missing — PDF may be incomplete.")

        # Determine output path — fall back to versioned name if file is locked
        target_path = output_pdf
        try:
            # Probe writeability before committing
            with open(target_path, 'wb') as f:
                writer.write(f)
            writer.close()
            print(f"Successfully saved PDF to {target_path}")
            return True
        except PermissionError:
            # File is open in a PDF viewer — save with versioned name
            alt = output_pdf.replace(".pdf", "_v2.pdf")
            print(f"  [Warning] {output_pdf} is locked (open in viewer?). Saving as {alt}")
            try:
                with open(alt, 'wb') as f:
                    writer.write(f)
                writer.close()
                print(f"Successfully saved PDF to {alt}")
                return True
            except Exception as e:
                print(f"  [Error] PDF merge failed on fallback path: {e}")
                return False
        except Exception as e:
            print(f"  [Error] PDF merge failed: {e}")
            return False

    def export_speaker_notes(self, master_plan, output_file: str):
        """
        Export a rich speaker notes companion markdown file.

        Sections per slide:
          - Layout type + eyebrow tag
          - Title
          - Content summary (block types used)
          - Speaker notes text
          - Presenter Q&A prompts (drawn from slide_purpose)
        """
        if not master_plan.slides:
            return

        out_dir = os.path.dirname(output_file)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        lines = [
            f"# Speaker Notes",
            f"",
            f"**Theme**: `{master_plan.theme.structural_class}`"
            + (f" / `{master_plan.theme.palette}`" if master_plan.theme.palette else ""),
            f"**Total Slides**: {len(master_plan.slides)}",
            f"",
            f"---",
            f"",
        ]

        for slide in master_plan.slides:
            # ── Slide header ─────────────────────────────────────────────
            eyebrow_str = f" · {slide.eyebrow}" if slide.eyebrow else ""
            lines += [
                f"## Slide {slide.slide_number}{eyebrow_str}",
                f"",
                f"**{slide.title}**",
                f"",
            ]

            # Layout + metadata tags
            tags = [f"`{slide.layout_type}`"]
            if slide.narrative_weight:
                tags.append(f"`{slide.narrative_weight}`")
            if slide.slide_purpose:
                tags.append(f"`{slide.slide_purpose}`")
            lines.append(" ".join(tags))
            lines.append("")

            if slide.subtitle:
                lines.append(f"*{slide.subtitle}*")
                lines.append("")

            # ── Content summary ───────────────────────────────────────────
            if slide.content_blocks:
                block_desc = self._describe_blocks(slide.content_blocks)
                if block_desc:
                    lines.append(f"**Content:** {block_desc}")
                    lines.append("")

            # ── Speaker notes ─────────────────────────────────────────────
            if slide.speaker_notes:
                lines.append(slide.speaker_notes)
            else:
                lines.append("*No presenter notes provided for this slide.*")
            lines.append("")

            # ── Presenter transition prompt ───────────────────────────────
            transition = self._transition_prompt(slide)
            if transition:
                lines.append(f"> **Transition:** {transition}")
                lines.append("")

            lines.append("---")
            lines.append("")

        # ── Appendix: image prompts for manual generation ─────────────────
        slides_needing_images = [
            s for s in master_plan.slides
            if s.requires_image and s.image_prompt
        ]
        if slides_needing_images:
            lines += [
                "## Appendix: Image Prompts",
                "",
                "If you want to regenerate images manually, use these prompts:",
                "",
            ]
            for slide in slides_needing_images:
                lines += [
                    f"### Slide {slide.slide_number} — {slide.title}",
                    f"```",
                    slide.image_prompt,
                    f"```",
                    "",
                ]

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        print(f"Successfully saved Speaker Notes to {output_file}")

    def _describe_blocks(self, content_blocks: list) -> str:
        """Summarise content_blocks into a human-readable string."""
        parts = []
        for block in content_blocks:
            bt = block.block_type
            if bt == 'bullets':
                n = len(block.items or [])
                parts.append(f"{n} bullet points")
            elif bt == 'stat':
                parts.append(f"stat: {block.value} — {block.label}")
            elif bt == 'pullquote':
                attr = f" ({block.attribution})" if block.attribution else ""
                short = (block.quote or '')[:60]
                parts.append(f'quote: "{short}…"{attr}')
            elif bt == 'comparison':
                parts.append(
                    f"comparison: {block.left_label} vs {block.right_label}"
                )
            elif bt == 'steps':
                n = len(block.steps or [])
                parts.append(f"{n} steps")
            elif bt == 'callout':
                parts.append(f"{block.callout_type or 'insight'} callout")
            elif bt == 'keyvalue':
                n = len(block.pairs or [])
                parts.append(f"{n} key-value pairs")
        return " · ".join(parts) if parts else ''

    def _transition_prompt(self, slide) -> str:
        """Return a presenter transition suggestion based on slide_purpose."""
        purpose = getattr(slide, 'slide_purpose', None) or ''
        transitions = {
            'opening_hook':     "Pause after the opening hook. Let the number or statement land before moving on.",
            'problem_statement': "Ask the audience: 'How many of you have felt this pain personally?'",
            'evidence':         "Refer back to the source — 'This isn't anecdotal, the data shows it clearly.'",
            'solution_intro':   "Bridge: 'So what do we do about this? Here's what we built.'",
            'solution_detail':  "Invite questions: 'Any questions on how this works before we look at results?'",
            'social_proof':     "Pause: 'I want you to hear this — this is a real customer, not a demo account.'",
            'call_to_action':   "Make the ask direct. State it once, clearly. Then wait.",
            'thesis':           "Restate the conclusion in one sentence before moving to evidence.",
            'summary':          "Offer a quick recap: 'To summarise what we covered today…'",
        }
        return transitions.get(purpose, '')
