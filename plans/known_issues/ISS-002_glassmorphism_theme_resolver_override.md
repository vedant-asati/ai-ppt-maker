# ISS-002 — ThemeResolver glassmorphism dark-bg enforcement is counter-productive

**Severity:** HIGH  
**Status:** OPEN (fix committed but should be reverted)  
**Affects:** glassmorphism theme, ThemeResolver step 9  
**Discovered:** 2026-08-02 — theme comparison analysis  
**Committed in:** `theme_resolver.py` step 9

---

## Symptom

After adding step 9 to `ThemeResolver.resolve()` (which darkens `--bg` from `#F7FAFC` to `#31363F` when luminance > 0.4), the glassmorphism cover slide dropped from **Q=85 to Q=26**.

**Before step 9 (glassmorphism_AI_light):**
```
cover:   Q=85   brightness=144   range=120   ✅
generic: Q=65   brightness=241   range=128   ✅  
split:   Q=79   brightness=182   range=170   ✅
```

**After step 9 (glassmorphism_FIXED):**
```
cover:   Q=26   brightness=72    range=21    ❌
generic: Q=66   brightness=72    range=123   ✅ (generic is layout-driven, unaffected)
split:   Q=22   brightness=69    range=33    ❌
```

---

## Root Cause

### Why the AI light bg actually works better:

The glassmorphism theme after the **image path fix (ISS-006)** now correctly renders background images. The current gradient images have brightness ~80 (deep blue/teal/purple). The visual quality emerges from the **mix** of:

1. Background image (brightness 80, rich blue/purple gradient)
2. Glassmorphism overlay (75% opacity white-ish bg)
3. The slide content on top

The resulting slide center brightness is ~144 — rich middle-ground between pure white (255) and pure dark (0). **This mix is visually optimal.**

### Why forcing dark bg destroys this:

When step 9 forces `--bg: #31363F` (brightness ~54):
- The glassmorphism overlay becomes `rgba(49,54,63, ...)` — dark semi-transparent grey
- Mixed with the dark gradient image (brightness 80) → everything blurs into a **uniform dark muddy tone**
- Color range collapses from 120 → 21 (the gradient variations are swamped by the grey)

### The fundamental misunderstanding:

Glassmorphism's beauty comes from **contrast**: light frosted cards floating above a colorful backdrop. Both work:
- Light backdrop + dark tinted glass cards ← classic glassmorphism
- Dark backdrop + light frosted glass cards ← dark glassmorphism

The AI chose light-backdrop glassmorphism, and after ISS-006 was fixed, this works correctly. Forcing dark bg without also updating all the glass card CSS creates neither — just a muddy dark slide.

---

## Evidence

### Code committed in `theme_resolver.py` (step 9):

```python
# 9. glassmorphism: enforce dark background for the glass effect.
if structural_class == 'glassmorphism':
    bg = merged.get('--bg', '#F7FAFC')
    lum = cls.relative_luminance(bg)
    if lum > 0.4:  # too light for glass effect
        dark_bg = cls.darken(bg, 0.80)    # #F7FAFC → #31363F
        merged['--bg'] = dark_bg
        merged['--text'] = '#F0F0F0'
        ...
```

### Pixel comparison:

| Position | glassmorphism_AI (light) | glassmorphism_FIXED (dark) |
|----------|------------------------|---------------------------|
| center (0.5, 0.5) | (246, 249, 252) — card bg | (49, 54, 63) — dark flat |
| text area (0.2, 0.45) | (26, 32, 44) — dark text | (160, 164, 170) — grey text |
| right edge (0.9, 0.5) | (200, 220, 240) — gradient | (60, 65, 72) — dark grey |

The light version has a 220-point delta between text-on-card (dark) and gradient background (light). The dark version has only a 44-point delta — everything blends together.

---

## Proposed Fix

**Revert step 9** from `theme_resolver.py`.

The glassmorphism theme does NOT need dark bg enforcement:
1. After ISS-006 is fixed, images load correctly
2. The AI's choice of light bg + colored gradient images creates good visual contrast (Q=85)
3. If a truly dark glassmorphism is desired, it should be a **separate palette** in `PALETTES['glassmorphism']`, not an override

### Alternative (if dark glass is wanted):
Instead of the override, add a curated `glassmorphism` palette:
```python
# theme_palettes.py
PALETTES['glassmorphism'] = {
    'dark_glass': {
        '--bg': '#0D1117', '--bg-rgb': '13,17,23',
        '--primary': '#58A6FF', '--primary-rgb': '88,166,255',
        '--text': '#E6EDF3', '--text-secondary': 'rgba(230,237,243,0.65)',
        '--card-bg': 'rgba(255,255,255,0.06)',
    },
    'light_glass': {
        # No overrides — let AI colors through
    }
}
```

---

## Files to Modify

- [`theme_resolver.py`](../../../theme_resolver.py) — remove step 9 (lines ~196–220)

---

## Verification

After removing step 9:
```bash
python scripts/theme_comparison.py
```
Expected: `glassmorphism_FIXED` column disappears; `glassmorphism_AI_light` column stays at Q≥80 on cover.
