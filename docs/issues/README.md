# Known Issues — PPT Maker

> **Last updated:** 2026-08-02  
> **Pipeline version:** post-Aug-2026 bug-fix sprint  
> **Analyst:** Antigravity AI

---

## Index

| ID | Title | Severity | Status | Affects |
|----|-------|----------|--------|---------|
| [ISS-001](./ISS-001_stat_infographic_timeline_blank_bg.md) | stat/infographic/timeline render as flat color — no background depth | HIGH | OPEN | 4 slide layouts |
| [ISS-002](./ISS-002_glassmorphism_theme_resolver_override.md) | ThemeResolver glassmorphism dark-bg enforcement is counter-productive | HIGH | OPEN | glassmorphism theme |
| [ISS-003](./ISS-003_pptx_layout_is_generic.md) | PPTX exporter flattens all layouts to a single generic 3-box template | HIGH | OPEN | all themes |
| [ISS-004](./ISS-004_quote_template_dark_themes.md) | quote template visual quality collapses on dark themes | MEDIUM | OPEN | dark_neon, aurora, gradient_flow |
| [ISS-005](./ISS-005_glassmorphism_overlay_opacity.md) | glassmorphism cover overlay was near-opaque, hiding background image | MEDIUM | FIXED | glassmorphism cover |
| [ISS-006](./ISS-006_image_path_relative_pdf.md) | relative image paths caused white pages in vector PDF | CRITICAL | FIXED | all themes |
| [ISS-007](./ISS-007_pptx_double_text.md) | PPTX background PNG baked in text, doubling with overlay text boxes | CRITICAL | FIXED | all themes |
| [ISS-008](./ISS-008_glassmorphism_gradient_too_light.md) | glassmorphism gradient fallback images were near-white (br≈247) | MEDIUM | FIXED | glassmorphism |
| [ISS-009](./ISS-009_historic_pdf_blank_content_pages.md) | historic raster PDFs have blank/near-blank content pages | LOW | WONTFIX | old test outputs |
| [ISS-010](./ISS-010_image_cache_stale_after_palette_change.md) | gradient images cached with old colors after palette/preset changes | MEDIUM | OPEN | all themes |
| [ISS-REF](./ISS-REF_excellence_analysis.md) | **Reference Excellence Analysis** — Panch Parivartan deep audit (Q=100 avg) | — | REFERENCE | roadmap |


---

## Severity Guide

| Level | Meaning |
|-------|---------|
| **CRITICAL** | User-visible showstopper — output is broken |
| **HIGH** | Significantly degrades quality of output |
| **MEDIUM** | Partial degradation, workaround exists |
| **LOW** | Minor cosmetic or edge-case issue |

## Status Guide

| Status | Meaning |
|--------|---------|
| **OPEN** | Known, not yet fixed |
| **IN_PROGRESS** | Fix underway |
| **FIXED** | Committed fix, verified |
| **WONTFIX** | By design or not worth fixing |

---

## Quick Fix Priority

```
P0 (Do First):
  ISS-001 — stat/infographic/timeline have no background depth
  ISS-003 — PPTX uses single generic layout for all slide types

P1 (Important):
  ISS-002 — Revert harmful glassmorphism ThemeResolver step 9
  ISS-004 — Quote template dark theme fix
  ISS-010 — Stale image cache after preset/palette changes

P2 (Polish):
  (all others are FIXED or WONTFIX)
```
