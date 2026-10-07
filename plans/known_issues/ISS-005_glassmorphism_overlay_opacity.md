# ISS-005 — glassmorphism cover overlay was near-opaque, hiding background image

**Severity:** MEDIUM  
**Status:** ✅ FIXED (2026-08-02)  
**Affects:** `glassmorphism` theme, `cover` layout  
**Commit:** `cover.html` — glassmorphism overlay split from dark-theme block

---

## Symptom

The glassmorphism cover slide rendered as almost entirely white. Even after the image path fix (ISS-006) correctly loaded the background image, the overlay gradient covered it nearly completely.

---

## Root Cause

`templates/cover.html` grouped glassmorphism with dark themes (dark_neon, gradient_flow, aurora) for the overlay gradient:

```css
/* BEFORE FIX — glassmorphism grouped with dark themes */
body.dark_neon .cover-overlay,
body.gradient_flow .cover-overlay,
body.aurora .cover-overlay,
body.glassmorphism .cover-overlay {        ← included here
  background: linear-gradient(
    100deg,
    rgba(var(--bg-rgb), 1)    0%,         ← 100% opaque at left edge
    rgba(var(--bg-rgb), 0.92) 45%,        ← 92% opaque at 45% across
    rgba(var(--bg-rgb), 0.55) 65%,
    rgba(var(--bg-rgb), 0.1)  85%,
    transparent 100%
  );
}
```

With `--bg: #F7FAFC` (near-white), the overlay at 0% is `rgba(247,250,252, 1.0)` — **solid white**. The left 45% of the slide is completely opaque, hiding the background image entirely.

---

## Fix Applied

Separated glassmorphism into its own overlay rule with reduced opacity:

```css
/* AFTER FIX */
body.glassmorphism .cover-overlay {
  background: linear-gradient(
    100deg,
    rgba(var(--bg-rgb), 0.75) 0%,    ← was 1.0 → now 0.75
    rgba(var(--bg-rgb), 0.60) 35%,   ← was 0.92
    rgba(var(--bg-rgb), 0.30) 55%,   ← was 0.55
    rgba(var(--bg-rgb), 0.05) 75%,
    transparent 100%
  );
  backdrop-filter: blur(12px);        ← added genuine frosted glass
  -webkit-backdrop-filter: blur(12px);
}
```

**Result:** Cover Q-score went from ~5 (all-white after image was broken) → **Q=85** (rich visual mix of gradient image + frosted overlay).

---

## Verification

```python
# Run comparison script and check glassmorphism_AI_light cover score
# Expected: Q ≥ 75
```

Confirmed via theme_analysis.json: `NEW_glassmorphism_AI_light_cover: Q=85`.
