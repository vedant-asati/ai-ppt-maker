import os
import json
import time
from contextlib import contextmanager
from pathlib import Path
from playwright.sync_api import sync_playwright
from rich.progress import track


class Renderer:
    def __init__(self, build_dir: str = 'temp_build', preview_mode: bool = False):
        self.build_dir = build_dir
        self.images_dir = os.path.join(build_dir, 'images')
        self.preview_mode = preview_mode
        self._playwright = None
        self._browser = None
        os.makedirs(self.images_dir, exist_ok=True)

    def __enter__(self):
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        if self._browser:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    @contextmanager
    def _browser_session(self):
        """Yields an active Chromium browser, reusing self._browser if active."""
        if self._browser:
            yield self._browser
        else:
            with sync_playwright() as p:
                b = p.chromium.launch(headless=True)
                try:
                    yield b
                finally:
                    b.close()

    def render_all(self, html_files: list, audit: bool = False):
        """
        Render each HTML file to PNG via Playwright.

        Returns:
          (png_files: List[str], dom_audit_results: List[dict])

        dom_audit_results is [] unless audit=True.
        """
        png_files = []
        dom_audit_results = []

        # Preview mode: half resolution
        viewport_width  = 960  if self.preview_mode else 1920
        viewport_height = 540  if self.preview_mode else 1080

        with self._browser_session() as browser:
            context = browser.new_context(
                viewport={'width': viewport_width, 'height': viewport_height}
            )
            page = context.new_page()
            try:
                for html_file in track(html_files, description="Rendering HTML to PNG..."):
                    file_url = Path(html_file).resolve().as_uri()
                    slide_num = self._slide_number_from_path(html_file)

                    # Navigate with timeout fallback
                    try:
                        page.goto(file_url, wait_until='networkidle', timeout=15000)
                    except Exception:
                        try:
                            page.goto(file_url, wait_until='domcontentloaded', timeout=8000)
                        except Exception as e:
                            print(f"  [Warning] Navigation failed for {html_file}: {e}")

                    # Wait for fonts to load
                    try:
                        page.evaluate("document.fonts.ready")
                    except Exception:
                        time.sleep(0.3)

                    # DOM audit injection (Layer 1)
                    audit_result = {"slide_number": slide_num, "warnings": [], "info": []}
                    if audit:
                        try:
                            raw = page.evaluate(_DOM_AUDIT_JS)
                            audit_result.update(raw)
                            audit_result["slide_number"] = slide_num
                        except Exception as e:
                            print(f"  [Warning] DOM audit failed for slide {slide_num}: {e}")

                    dom_audit_results.append(audit_result)

                    # Screenshot
                    base_name = os.path.basename(html_file).replace('.html', '.png')
                    out_path = os.path.join(self.images_dir, base_name)
                    page.screenshot(path=out_path, full_page=False)
                    png_files.append(out_path)
            finally:
                context.close()

        # Cache DOM audit results for standalone `audit` command
        if audit and dom_audit_results:
            cache_path = os.path.join(self.build_dir, 'dom_audit.json')
            with open(cache_path, 'w') as f:
                json.dump(dom_audit_results, f, indent=2)

        return png_files, dom_audit_results

    def render_to_pdf(self, html_files: list) -> list:
        """
        Render each HTML file to a vector PDF page via Playwright.

        Uses Chromium's native print engine — preserves ALL CSS effects:
        glassmorphism, backdrop-filter, gradients, aurora blobs, custom fonts.
        Text in the output is selectable, copyable, and searchable.

        Returns a list of per-slide .pdf file paths for merging.
        """
        pdf_dir = os.path.join(self.build_dir, 'pdfs')
        os.makedirs(pdf_dir, exist_ok=True)
        pdf_files = []

        # Preview mode: still 1920×1080 for PDF (no half-res for vector)
        width = '1920px'
        height = '540px' if self.preview_mode else '1080px'

        with self._browser_session() as browser:
            # Set viewport to match design dimensions so vw/vh units and JS
            # window.innerWidth/innerHeight are consistent with render_all()
            viewport_w = 1920
            viewport_h = 540 if self.preview_mode else 1080
            context = browser.new_context(
                viewport={'width': viewport_w, 'height': viewport_h}
            )
            page = context.new_page()
            try:
                for html_file in track(html_files, description="Rendering HTML to PDF (vector)..."):
                    file_url = Path(html_file).resolve().as_uri()

                    # Navigate — same fallback strategy as render_all
                    try:
                        page.goto(file_url, wait_until='networkidle', timeout=15000)
                    except Exception:
                        try:
                            page.goto(file_url, wait_until='domcontentloaded', timeout=8000)
                        except Exception as e:
                            print(f"  [Warning] Vector PDF: navigation failed for {html_file}: {e}")
                            continue

                    # Wait for fonts to load before capturing
                    try:
                        page.evaluate("document.fonts.ready")
                    except Exception:
                        time.sleep(0.3)

                    base_name = os.path.basename(html_file).replace('.html', '.pdf')
                    out_path = os.path.join(pdf_dir, base_name)

                    page.pdf(
                        path=out_path,
                        width=width,
                        height=height,
                        print_background=True,       # Critical — CSS backgrounds stripped without this
                        prefer_css_page_size=False,  # Use our explicit dimensions, not @page rules
                        margin={                      # Zero margins — slides are full-bleed
                            'top': '0px',
                            'right': '0px',
                            'bottom': '0px',
                            'left': '0px',
                        },
                    )
                    pdf_files.append(out_path)
            finally:
                context.close()

        return pdf_files

    def render_background_only(self, html_files: list) -> list:
        """
        Render each slide with all text made transparent — for PPTX backgrounds.

        The PPTX export strategy is:
          Layer 1 (background image): visual design only — gradients, glassmorphism,
                                      aurora blobs, images, decorative rules.
          Layer 2 (text boxes):       pptx_exporter's visible, editable text overlays.

        Without this, Layer 1 already contains rendered text (from the HTML screenshot)
        AND Layer 2 adds the same text again → doubled text visible in LibreOffice/PowerPoint.

        This method injects a CSS rule that sets `color: transparent` on all elements,
        which hides text pixels while preserving layout dimensions and all backgrounds.

        Returns a list of PNG paths (saved to temp_build/images/bg_slide_NNN.png).
        """
        bg_dir = os.path.join(self.build_dir, 'images', 'bg')
        os.makedirs(bg_dir, exist_ok=True)
        bg_files = []

        # CSS injected into every page to hide text while keeping visual design
        _HIDE_TEXT_CSS = """
            body *, body *::before, body *::after {
                color: transparent !important;
                -webkit-text-fill-color: transparent !important;
                text-shadow: none !important;
            }
        """

        viewport_w = 1920
        viewport_h = 540 if self.preview_mode else 1080

        with self._browser_session() as browser:
            context = browser.new_context(
                viewport={'width': viewport_w, 'height': viewport_h}
            )
            page = context.new_page()
            try:
                for html_file in track(html_files, description="Rendering PPTX backgrounds..."):
                    file_url = Path(html_file).resolve().as_uri()

                    try:
                        page.goto(file_url, wait_until='networkidle', timeout=15000)
                    except Exception:
                        try:
                            page.goto(file_url, wait_until='domcontentloaded', timeout=8000)
                        except Exception as e:
                            print(f"  [Warning] Background render: navigation failed for {html_file}: {e}")
                            continue

                    # Wait for fonts + images
                    try:
                        page.evaluate("document.fonts.ready")
                    except Exception:
                        time.sleep(0.3)

                    # Inject CSS to hide all text pixels
                    page.add_style_tag(content=_HIDE_TEXT_CSS)

                    # Small pause to let style apply
                    time.sleep(0.05)

                    base_name = os.path.basename(html_file).replace('.html', '.png')
                    out_path = os.path.join(bg_dir, base_name)
                    page.screenshot(path=out_path, full_page=False)
                    bg_files.append(out_path)
            finally:
                context.close()

        return bg_files

    def _slide_number_from_path(self, path: str) -> int:
        """Extract slide number from filename like slide_003.html → 3."""
        try:
            base = os.path.basename(path)
            return int(base.split('_')[1].split('.')[0])
        except (IndexError, ValueError):
            return 0


# ─────────────────────────────────────────────────────────────────────────────
# DOM Audit JavaScript — injected into Playwright page before screenshot
# Detects: overflow, broken images, small font sizes, placeholder images
# ─────────────────────────────────────────────────────────────────────────────

_DOM_AUDIT_JS = """
(() => {
  const warnings = [];
  const info = [];

  // 1. Overflow check — content cards, blocks, and text containers overflowing their bounds
  const containers = document.querySelectorAll(
    '.split-content, .generic-content, .card, .block-bullets, .block-comparison, .block-steps, .block-keyvalue, .slide-content, .quote-content, .stat-content, .content-blocks'
  );
  for (const el of containers) {
    if (el.clientHeight > 0 && el.scrollHeight > el.clientHeight + 6) {
      warnings.push({
        type: 'OVERFLOW',
        selector: el.className ? `.${el.className.split(' ').join('.')}` : el.tagName,
        excess_px: el.scrollHeight - el.clientHeight,
        message: `Container ${el.className || el.tagName} overflows by ${el.scrollHeight - el.clientHeight}px`
      });
    }
  }

  // 2. Broken image check
  const imgs = document.querySelectorAll('img');
  for (const img of imgs) {
    if (!img.complete || img.naturalWidth === 0) {
      warnings.push({
        type: 'BROKEN_IMAGE',
        src: img.src,
        message: `Broken image: ${img.src}`
      });
    }
    // Placeholder check (grey rectangle substitute)
    if (img.src && img.src.includes('placeholder')) {
      warnings.push({
        type: 'PLACEHOLDER_IMAGE',
        src: img.src,
        message: 'Placeholder image in use — real image not generated.'
      });
    }
  }

  // 3. Font size check — any text < 12px is unreadable at 1920px
  const textEls = document.querySelectorAll('h1, h2, h3, p, li, span, div');
  for (const el of textEls) {
    if (!el.textContent.trim()) continue;
    const fs = parseFloat(window.getComputedStyle(el).fontSize);
    if (fs > 0 && fs < 12) {
      warnings.push({
        type: 'FONT_TOO_SMALL',
        selector: el.tagName + '.' + el.className,
        font_size_px: fs,
        message: `Font size ${fs}px is too small for readability`
      });
    }
  }

  // 4. Info: collect key layout metrics
  const body = document.body;
  info.push({
    type: 'METRICS',
    scroll_height: body.scrollHeight,
    viewport_height: window.innerHeight,
    overflow_y: body.scrollHeight > window.innerHeight + 2,
  });

  return { warnings, info };
})()
"""
