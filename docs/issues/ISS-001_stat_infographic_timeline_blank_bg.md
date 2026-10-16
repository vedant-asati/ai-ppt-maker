# ISS-001 — stat/infographic/timeline render as flat color

**Severity:** HIGH  
**Status:** OPEN  
**Affects:** `stat`, `infographic`, `timeline` layout templates (slides 3, 4, 9, 11 in current deck)  
**Discovered:** 2026-08-02 — theme comparison analysis

---

## Symptom

Slides using the `stat`, `infographic`, and `timeline` layout templates appear as a **flat single-colour rectangle** — either near-white (light themes) or near-black (dark themes). There is no visual depth, texture, or background imagery.

**Pixel evidence** (from `scripts/output/theme_analysis.json`):

| Theme | stat Q-score | infographic Q-score | Notes |
|-------|-------------|---------------------|-------|
| dark_neon | 3 | (not measured) | Q=3 = effectively flat |
| gradient_flow | 3 | — | flat black |
| aurora | 24 | — | slight gradient from CSS vars |
| editorial | 3 | — | flat white |
| glassmorphism_AI | 3 | — | flat white |
| glassmorphism_FIXED | 3 | — | flat dark grey |

**Compare to:** cover layout (Q=47–89 across themes), generic layout (Q=53–94).

---

## Root Cause

### Template feature matrix:

| Template | `has_image` block | `<img>` tag | Background depth | Visual Q |
|----------|:-----------------:|:-----------:|-----------------|---------|
| `cover.html` | ✅ | ✅ | Image + overlay | HIGH |
| `generic.html` | ✅ | ✅ | Card rows with CSS | HIGH |
| `split.html` | ✅ | ✅ | Half-image panel | MEDIUM |
| `stat.html` | ✅ (right panel) | ✅ | **Image at 8% opacity — only covers right panel** | LOW |
| `infographic.html` | ❌ | ❌ | **None — body background only** | ZERO |
| `timeline.html` | ❌ | ❌ | **None — body background only** | ZERO |
| `quote.html` | ✅ | ✅ | Card + image | VARIES |

**`infographic.html` has zero image support.** There is no `{% if has_image %}` block, no `<img>` tag, and no CSS background-image reference. The template relies entirely on `var(--bg)` body background — a single flat color.

**`timeline.html`** is identical — no image support at all.

**`stat.html`** has image support but positions it at `opacity: 0.08` inside the right-panel only (45% of slide width). The left 55% remains flat body background.

### Why slide 3/11 (infographic) shows Q=3:
```
Slide 3 (infographic): requires_image=True, image_exists=True (br=80)
→ Image assigned BUT template never renders it
→ Slide background = body background = var(--bg) = #F7FAFC (one color)
→ color_range = 0, Q = 0+3 = 3
```

---

## Evidence Code

**`templates/infographic.html`** — search for "image":
```
(no results — zero image references)
```

**`templates/timeline.html`** — search for "image":
```
(no results — zero image references)
```

**`templates/stat.html`** — image block:
```css
.stat-image {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  object-fit: cover;
  opacity: 0.08;   ← only 8% opacity AND only in right panel
  z-index: 0;
}
```

---

## Impact Assessment

- **4 of 12 slides** in a typical 12-slide deck are affected (33%)
- Affects **every theme** — the flat background is universal
- Dark themes (dark_neon, aurora) compound the problem: the flat body bg is near-black, making the slide look empty
- The AI correctly assigns images to infographic slides (`requires_image=True`, `image_role=supporting`) but the template silently ignores them

---

## Proposed Fix

### Option A — Full background image (recommended)
Add a full-bleed background image at low opacity to `infographic.html` and `timeline.html`:

```html
{% if has_image %}
<div class="slide-bg-texture" style="
  position: absolute; inset: 0; z-index: 0; pointer-events: none;
  background-image: url('{{ image_path }}');
  background-size: cover; background-position: center;
  opacity: 0.12;">
</div>
{% endif %}
```

Apply to: `infographic.html`, `timeline.html`

Also increase `stat.html` opacity from `0.08` to `0.15` and extend it to full-slide.

### Option B — CSS gradient depth (no image dependency)
If `has_image` is False, fall back to a CSS radial gradient using the primary color:

```css
body::before {
  content: '';
  position: fixed; inset: 0; z-index: -1;
  background: radial-gradient(ellipse at 20% 30%, rgba(var(--primary-rgb), 0.15) 0%, transparent 60%),
              radial-gradient(ellipse at 80% 70%, rgba(var(--primary-rgb), 0.08) 0%, transparent 50%);
}
```

### Recommended: Both A + B
- Apply Option A when image exists
- Apply Option B always as a base layer

---

## Files to Modify

- [`templates/infographic.html`](../../../templates/infographic.html) — add bg image block + CSS radial gradient
- [`templates/timeline.html`](../../../templates/timeline.html) — add bg image block + CSS radial gradient
- [`templates/stat.html`](../../../templates/stat.html) — extend image to full-slide, increase opacity

---

## Verification

After fix, run:
```bash
python scripts/theme_comparison.py
```
Expected: `stat`, `infographic`, `timeline` Q-scores increase from 3 → 30+ across all themes.
