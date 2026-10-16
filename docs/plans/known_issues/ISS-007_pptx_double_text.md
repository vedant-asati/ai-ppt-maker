# ISS-007 — PPTX background PNG baked in text, doubling with overlay text boxes

**Severity:** CRITICAL  
**Status:** ✅ FIXED (2026-08-02)  
**Affects:** All themes, PPTX output  
**Commit:** `renderer.py` + `cli.py` — new `render_background_only()` method

---

## Symptom

In the exported `.pptx`, every word of text appeared **twice** — once from the PNG background image (which was a full-render screenshot) and once from the `pptx_exporter`'s visible text overlay boxes. The two copies were slightly misaligned, creating a blurred/doubled appearance in LibreOffice Impress and PowerPoint.

The user reported: _"your ppt looks overlapped like this"_

**Verified via python-pptx inspection:**
```
Slide 1 — Shape 0 (PICTURE): background PNG with text baked in at pixel level
Slide 1 — Shape 1 (TEXT_BOX): 'INTRODUCTION'         ← overlay (same text, visible)
Slide 1 — Shape 2 (TEXT_BOX): 'Mastering AI-...'     ← overlay (same text, visible)
Slide 1 — Shape 3 (TEXT_BOX): 'Transform your...'    ← overlay (same text, visible)
```

Shape 0 + Shapes 1-3 = every word seen twice.

---

## Root Cause

The old PPTX export pipeline used `render_all()` to generate PNG screenshots:

```python
# OLD cli.py
png_files, _ = renderer.render_all(html_files, audit=False)
exporter.export(png_files, ...)  # ← full-render PNGs with text baked in
```

`render_all()` takes a Playwright screenshot of each slide at full fidelity — including all text rendered by Chromium. `pptx_exporter.export()` then:
1. Inserts this text-containing PNG as the slide background image (Shape 0)
2. Adds new text boxes on top for editability (Shapes 1-3)

Both layers display simultaneously in any PPTX viewer.

### Why it went unnoticed before:

The previous raster PDF pipeline also used `render_all()` PNGs as slide pages — but PDFs don't have a separate editable text layer, so there was no duplication. The problem only manifested when the PPTX export was added.

---

## Fix Applied

### New `render_background_only()` in `renderer.py`:

Renders each slide with **all text made pixel-transparent** via CSS injection:

```python
_HIDE_TEXT_CSS = """
    body *, body *::before, body *::after {
        color: transparent !important;
        -webkit-text-fill-color: transparent !important;
        text-shadow: none !important;
    }
"""
page.add_style_tag(content=_HIDE_TEXT_CSS)
page.screenshot(path=out_path)  # ← text-free design image
```

This preserves all visual design (gradients, glassmorphism, aurora blobs, background images, card shapes) while making text pixels fully transparent.

**Verified via pixel diff:**

| Position | Regular screenshot | Background-only PNG |
|----------|-------------------|---------------------|
| Title area (0.20, 0.45) | `(26, 32, 44)` — dark text | `(246, 250, 252)` — bg colour |
| Subtitle (0.18, 0.65) | `(247, 250, 252)` | `(247, 250, 252)` — same |

Delta at text position: **220 points** — text is completely invisible in the background PNG.

### `cli.py` updated:

```python
# NEW cli.py
bg_png_files = renderer.render_background_only(html_files)
exporter.export(bg_png_files, ...)  # ← text-free background PNGs
```

`need_pngs` (for `render_all`) is now only True when `--audit` is requested, not for PPTX.

---

## Result

```
PPTX Layer 1 (background image): visual design only — gradients, glass, images, NO TEXT
PPTX Layer 2 (text boxes):       single source of truth for all text — editable
```

Text appears exactly once per slide. No overlap.

---

## Regression Risk

- `render_background_only()` adds ~10s to the pipeline (1 Playwright session across 12 slides)
- The `color: transparent` injection must fire **before** the screenshot — the `time.sleep(0.05)` pause ensures the style is applied, but very slow systems might need a longer pause
- If a future template uses SVG text or canvas-rendered text, `color: transparent` may not hide it — those would need additional CSS selectors
