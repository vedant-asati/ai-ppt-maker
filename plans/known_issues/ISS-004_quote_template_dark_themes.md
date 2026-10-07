# ISS-004 — quote template visual quality collapses on dark themes

**Severity:** MEDIUM  
**Status:** OPEN  
**Affects:** `quote` layout on dark_neon, aurora, gradient_flow themes  
**Discovered:** 2026-08-02 — theme comparison analysis

---

## Symptom

The `quote` layout produces very low visual quality on all dark themes:

| Theme | Quote Q-score | Notes |
|-------|-------------|-------|
| editorial | **97** ✅ | White bg with dark text = high contrast |
| glassmorphism_AI | 13 ⚠️ | Near-white, barely visible variation |
| dark_neon | **13** ⚠️ | Near-black, minimal visual variety |
| gradient_flow | **12** ⚠️ | Same — flat dark |
| aurora | **27** ⚠️ | Slightly better due to aurora CSS gradients |

Editorial scores 97 on quote because: white background → dark quote text → dark attribution → high pixel contrast. Every other theme loses this.

---

## Root Cause

### The quote template's structure:

```html
<div class="quote-card">
  <div class="quote-mark">"</div>
  <p class="quote-text">{{ quote_text }}</p>
  <p class="attribution">— {{ attribution }}</p>
</div>
```

The `.quote-card` has:
```css
.quote-card {
  background: var(--card-bg);         ← translucent white or dark
  border-left: 4px solid var(--primary);
  padding: var(--space-xl);
}
```

On dark themes:
- `--card-bg` ≈ `rgba(255,255,255,0.05)` — 5% white on near-black bg = effectively black card
- The quote card becomes nearly invisible against the dark body background
- `var(--primary)` accent border is the only color, but a 4px stripe provides negligible pixel impact on a 1920×1080 canvas

### Why editorial works:
- `--bg: #F9F6F1` (warm white) 
- `--card-bg: rgba(0,0,0,0.04)` (4% black on white = very light grey card)
- Dark text on light card = **228-point brightness range**

### Why dark themes fail:
- `--bg: #050505` (near-black)
- `--card-bg: rgba(255,255,255,0.05)` (near-black card)
- Light text on near-black bg = **22-point brightness range** (text is only decorative difference)

**The quote slide has no background image**, only CSS card styling. Without image support, the entire slide is one shade of black with text.

---

## Evidence

### Quote slide (slide 5) — master_plan.json:
```json
{
  "layout_type": "quote",
  "requires_image": false,
  "image_role": null,
  "quote_text": "Design is not just what it looks like, it is how it works.",
  "attribution": "Steve Jobs"
}
```

`requires_image: false` — the planner explicitly doesn't request an image. The template has an `{% if has_image %}` block, but it's never reached.

### DOM audit results:
```
Slide 5: overflow=0 broken_imgs=0 empty=0 body_overflow=False
```
No DOM errors — the slide renders fine, it's just visually flat.

### Quote template image block (from `templates/quote.html`):
```html
{% if has_image %}
<div class="quote-image">
  <img src="{{ image_path }}" alt="" onerror="this.style.display='none'">
</div>
{% endif %}
```
This block exists but never fires because `requires_image=False` in the plan.

---

## Impact Assessment

- Quote slides are visually below-par on 4 of 6 themes (67% of dark/mixed themes)
- The editorial theme happens to be the only one where the design philosophy aligns with quote aesthetics (light, typographic)
- The issue is a combination of: planner not requesting images + template not having fallback depth

---

## Proposed Fix

### Fix 1 — Update planner prompt to always request images for quote slides

In `planner.py` or the system prompt:
```python
# Quote slides benefit from atmospheric background images
if slide.get('layout_type') == 'quote':
    slide['requires_image'] = True
    slide['image_role'] = 'atmosphere'
    # Image prompt: abstract, soft, relevant to quote theme
```

### Fix 2 — CSS fallback radial gradient in `quote.html`

Even without an image, add ambient glow using the primary color:

```css
/* Quote: add ambient primary-color glow as visual depth */
body.dark_neon .quote-slide,
body.gradient_flow .quote-slide,
body.aurora .quote-slide,
body.glassmorphism .quote-slide {
  background:
    radial-gradient(ellipse at 20% 60%, rgba(var(--primary-rgb), 0.18) 0%, transparent 55%),
    radial-gradient(ellipse at 80% 30%, rgba(var(--primary-rgb), 0.10) 0%, transparent 45%),
    var(--bg);
}
```

### Fix 3 — Large decorative quote mark as visual element

Add a massive decorative `"` that renders as a gradient shape:

```css
.quote-mark-decorative {
  position: absolute;
  font-size: 400px;
  font-weight: 900;
  color: transparent;
  -webkit-text-stroke: 2px rgba(var(--primary-rgb), 0.15);
  top: -80px; left: 40px;
  line-height: 1;
  pointer-events: none;
  z-index: 0;
}
```

This creates visual mass without obscuring the quote text.

---

## Files to Modify

- [`templates/quote.html`](../../../templates/quote.html) — CSS radial glow + decorative mark
- [`planner.py`](../../../planner.py) — set `requires_image=True` for quote layouts

---

## Verification

After fix, run `scripts/theme_comparison.py`.  
Expected: quote Q-scores on dark themes improve from 12–27 to 40+.
