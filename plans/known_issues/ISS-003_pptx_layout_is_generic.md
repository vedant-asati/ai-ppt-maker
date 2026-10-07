# ISS-003 — PPTX exporter uses a single generic 3-box layout for all slide types

**Severity:** HIGH  
**Status:** OPEN  
**Affects:** All 12 slides in any exported `.pptx`  
**Discovered:** 2026-08-02 — PPTX shape audit  
**Related file:** [`pptx_exporter.py`](../../../pptx_exporter.py)

---

## Symptom

Every slide in the exported PPTX has exactly the same shape structure, regardless of the HTML layout:

```
Slide N: 4 shapes
  PICTURE (background image)  → full-slide 13.33" × 7.50"
  TextBox: eyebrow label       → top-left
  TextBox: title               → below eyebrow
  TextBox: body text           → lower half
```

This is a **3-text-box generic template** applied uniformly to every layout including:
- `stat` (should show 200px hero number prominently)
- `quote` (should have large centered quote text)
- `split` (should have two-column layout)
- `infographic` (should have bullet/icon grid)
- `timeline` (should have chronological flow)

**Verified output from PPTX shape audit:**

```
Slide 5 (quote):   eyebrow='PERSPECTIVE'  title='AI allows us...'  body='— — Modern...'
Slide 9 (stat):    eyebrow='THE IMPACT'   title='Efficiency at Scale'  body='75%\nTime Saved'
Slide 8 (split):   eyebrow='BEST PRACTICES'  title='Enhancing...'  body=(split content merged)
```

Slide 9 (stat) has the hero number `75%` packed into the body text box at font size 72pt — but positioned at (1.0", 2.1") in a 11.7" wide text box alongside other text. In the HTML, the hero number fills 200px with dedicated typography.

---

## Root Cause

**`pptx_exporter.py`** uses a flat JSON extraction strategy. It reads `slide['title']`, `slide['eyebrow']`, and `slide['body_text']` and places them as three text boxes with hardcoded positions. There is no layout-aware branching.

```python
# Current code (simplified):
def _add_text_overlays(self, slide, plan_slide):
    title = plan_slide.get('title', '')
    eyebrow = plan_slide.get('eyebrow', plan_slide.get('section_label', ''))
    body = _flatten_body(plan_slide)  # all content merged into one string
    
    # Same 3 shapes for every layout:
    add_text_box(slide, eyebrow, left=0.8, top=0.5, ...)
    add_text_box(slide, title,   left=0.8, top=1.0, ...)
    add_text_box(slide, body,    left=0.8, top=3.0, ...)
```

The `layout_type` field is never read. The `stats`, `quote_text`, `timeline_items`, `columns`, `infographic_items` fields are silently discarded.

---

## Evidence

### master_plan.json — Slide 9 (stat) full data:
```json
{
  "slide_number": 9,
  "layout_type": "stat",
  "title": "Efficiency at Scale",
  "eyebrow": "THE IMPACT",
  "stat_value": "75%",
  "stat_label": "Time Saved",
  "stat_description": "Average time saved per presentation..."
}
```

### PPTX shape audit — Slide 9:
```
TextBox at (2.0", 0.5"):  'THE IMPACT'           ← eyebrow OK
TextBox at (0.8", 1.1"):  'Efficiency at Scale'  ← title OK
TextBox at (1.0", 2.1"):  '75%'                  ← hero number but: 72pt, cramped
TextBox at (2.0", 4.2"):  'Time Saved'           ← label
```

The PPTX exporter correctly identifies `stat_value` and creates an extra box for it (5 shapes vs 4 for other slides), but the positions don't reflect the HTML's 200px centered hero number design.

### Quote slide 5 — PPTX vs HTML comparison:

| Attribute | HTML (correct) | PPTX (incorrect) |
|-----------|---------------|-----------------|
| Quote text | 90px, italic, full-width centered card | 26pt, left-aligned text box |
| Attribution | 24px, right-aligned with dash | 14pt, left-aligned, mispositioned |
| Background | frosted glass card, visual accent | plain bg image |

---

## Impact Assessment

- PPTX is **technically editable** but not visually faithful to the HTML design
- The exported PPTX doesn't reflect layout intent — a `stat` slide looks like a `generic` slide
- Split layout loses its two-column structure
- Quote loses its typographic treatment
- The PPTX is better than nothing but can't be considered a quality output

---

## Proposed Fix

### Phase 1 — Layout-aware text extraction (short-term)

Add a `layout_type` dispatch in `pptx_exporter.py`:

```python
def _add_text_overlays(self, pptx_slide, plan_slide):
    layout = plan_slide.get('layout_type', 'generic')
    dispatch = {
        'cover':       self._layout_cover,
        'generic':     self._layout_generic,
        'stat':        self._layout_stat,
        'quote':       self._layout_quote,
        'split':       self._layout_split,
        'infographic': self._layout_infographic,
        'timeline':    self._layout_timeline,
    }
    handler = dispatch.get(layout, self._layout_generic)
    handler(pptx_slide, plan_slide)
```

### Phase 2 — Per-layout positioning (medium-term)

Implement layout-specific shape sets:

| Layout | Shapes needed |
|--------|--------------|
| `stat` | eyebrow, title, hero-value (large, centered), label |
| `quote` | quote text (large, italic, full-width), attribution (right-aligned) |
| `split` | eyebrow, title (left column), body (left column), image panel (right) |
| `infographic` | eyebrow, title, bullet grid (3-col, icon + text pairs) |
| `timeline` | eyebrow, title, step sequence (horizontal or vertical) |

### Phase 3 — Slide master / layout inheritance (long-term)

Use python-pptx's `SlideLayout` to define proper masters for each layout type instead of manual shape positioning.

---

## Files to Modify

- [`pptx_exporter.py`](../../../pptx_exporter.py) — add layout-aware dispatch + per-layout handlers

---

## Verification

After fix:
1. Open PPTX in LibreOffice Impress
2. Stat slide (slide 9) should show `75%` in large centered text matching the HTML
3. Quote slide (slide 5) should show the quote in large italic centered text
4. Split slide (slide 8) should show two visible columns
