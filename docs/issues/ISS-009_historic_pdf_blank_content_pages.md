# ISS-009 — Historic raster PDFs have blank/near-blank content pages

**Severity:** LOW  
**Status:** WONTFIX  
**Affects:** `test_output/` — historic test PDFs only (not current pipeline)  
**Discovered:** 2026-08-02 — historic PDF per-page audit

---

## Symptom

The five historic test PDFs in `test_output/` have **widely varying per-page quality** — some pages are near-blank:

| Test deck | Total pages | Blank pages (Q<10) | Low-quality (Q<30) |
|-----------|------------|--------------------|--------------------|
| test1_yoga_dark_neon | 6 | 0 | 0 |
| test2_unity_editorial | 5 | ~2 | ~3 |
| test3_spiritual_glassmorphism | 5 | 0 | ~4 |
| test4_cyber_corporate | 5 | ~2 | ~3 |
| test5_iks_aurora | 5 | 0 | ~4 |

**Pixel evidence (editorial page 2):**
```
edit-2.png: br=245  rng=1   Q=3  ← near-white, effectively blank
```

---

## Root Cause

These historic test PDFs were generated with the **old raster-based pipeline** (before the Aug-2026 refactor). That pipeline had all three bugs now fixed:
- ISS-006: relative image paths → images silently failed to load  
- ISS-005: glassmorphism overlay was near-opaque
- ISS-008: gradient fallback images were near-white

Additionally, those test decks were generated with fewer slides (5-6 pages instead of 12) and may have used different content plans that happened to produce more problematic layouts on certain pages.

The `dark_neon` test was the only one that consistently scored well because:
1. The body background is near-black (`#050505`) so even a flat background has ~0 brightness (low but consistent)
2. The dark_neon card layouts use heavy CSS borders and glow effects that show up even without images
3. The dark gradient images (brightness ~5-8) actually provide contrast against the slightly lighter card elements

---

## Why WONTFIX

These are historic test artefacts — snapshots of the pipeline at a previous point in time. They are used as a **baseline reference** to compare against current pipeline quality, not as ground truth for output quality.

The current pipeline (post-Aug-2026 fixes) produces significantly better output than these historic PDFs. The theme comparison analysis confirms:

```
glassmorphism cover:  historic Q=33  →  current Q=85   (+157%)
editorial cover:      historic Q=100 →  current Q=89   (slightly below, due to theme CSS injection method differences)
aurora cover:         historic Q=21  →  current Q=57   (+171%)
```

Regenerating the historic test PDFs with the current pipeline would make them no longer "historic" — defeating their purpose as baselines.

---

## Action Items (for reference only)

If the test outputs ever need to be refreshed:
```bash
# Regenerate test1 with current pipeline
python cli.py generate --plan yoga --theme dark_neon --output test_output/test1_yoga_dark_neon/
```

But **do not do this casually** — these files serve as regression baselines.
