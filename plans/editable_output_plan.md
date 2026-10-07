# Editable Output — Plan & Architecture

**Status**: Implemented (Tier 1 + Tier 2)  
**Date**: 2026-08-02

## Problem
The original pipeline produced rasterized output:
- PDF = PNGs stitched via PIL. Text is not selectable/searchable.
- PPTX = PNGs as backgrounds with invisible 4pt gray text. Useless for editing.

User need: Make final tweaks (fix a typo, adjust a number) without re-running the 7-minute pipeline.

## Solution: Two-Pass Output (Option 6)

### Tier 1: Vector PDF (page.pdf())
Replace PIL screenshot stitch with Playwright's native `page.pdf()`:
- All CSS effects preserved (glassmorphism, aurora, gradients, blur)
- Text is **selectable, searchable, copyable**
- ~50% smaller file size (vector paths vs raster pixels)
- No new dependencies (pypdf already installed)

**New pipeline**:
```
Phase 5:  render_all() → PNGs         (only when --pptx or --audit)
Phase 5b: render_to_pdf() → per-slide PDFs  ← NEW
Phase 6:  merge_pdfs() → final PDF          ← replaces compile_to_pdf()
```

Key params for `page.pdf()`:
- `print_background=True` — without this, CSS backgrounds are stripped
- `margin: 0px` — zero margins (slides are full-bleed)
- `prefer_css_page_size=False` — use our explicit 1920×1080 dimensions

### Tier 2: Visible PPTX Overlays
Full rewrite of `pptx_exporter.py`:
- Text at proper sizes (28–36pt title, 16pt bullets)
- Layout-specific positioning (cover = centered, split = left 50%, stat = big number, etc.)
- Theme-aware colors: reads `--text` and `--primary` from `resolved_vars`
- Speaker notes preserved

### Tier 3: HTML reveal.js Export
Deferred for future. Idea: wrap per-slide HTML in reveal.js sections for 100% visual fidelity + browser-based presenting.

## Files Changed

| File | Change |
|------|--------|
| `renderer.py` | Added `render_to_pdf()` |
| `compiler.py` | Added `merge_pdfs()` |
| `cli.py` | Vector PDF pipeline + smart PNG skip + pass `resolved_vars` to PPTX |
| `pptx_exporter.py` | Full rewrite with layout-aware, visible text overlays |

## Layout Positioning Map (pptx_exporter.py)

Positions in (left, top, width, height) inches on 13.333" × 7.5" canvas:

```
cover:       eyebrow(2.0,2.0,9.3,0.5), title(1.5,2.6,10.3,1.6), centered
split:       eyebrow(0.8,0.5,5.8,0.45), title(0.8,1.0,5.8,1.3), left-half only
stat:        value(1.0,2.0,11.3,2.2) at 72pt, label(2.0,4.3,9.3,0.8), centered
quote:       quote(1.5,1.8,10.3,3.5) italic, attribution(2.5,5.5,8.3,0.7)
generic:     eyebrow top-left, title below, content area (0.8,3.0,11.7,4.0)
timeline:    same as generic
infographic: same as generic
```

## Edge Cases

- `render_to_pdf()` falls back to `compile_to_pdf(PNGs)` if vector render fails
- PPTX color fallback: white text / gold accent if `resolved_vars` is empty/None
- PPTX stat layout: if no `stat` block found, renders as generic content
- PPTX quote layout: if no `pullquote` block found, uses title as quote text
- Locked output files: both PDF and PPTX save with `_v2` suffix as fallback

## Future / Tier 3 Notes

For reveal.js export, key steps would be:
1. Read each per-slide HTML file
2. Wrap content in `<section>` tags
3. Embed reveal.js (bundled offline or CDN)
4. Output single `presentation.html` file
5. Add `--html-slides` flag to CLI

Reveal.js has 100% visual fidelity because it IS the HTML — no rasterization at all.
Users can edit HTML source for changes, present in browser with speaker notes view.
