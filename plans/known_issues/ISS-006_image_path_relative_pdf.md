# ISS-006 — Relative image paths caused white pages in vector PDF

**Severity:** CRITICAL  
**Status:** ✅ FIXED (2026-08-02)  
**Affects:** All themes, vector PDF output  
**Commit:** `templater.py` — absolute `file://` URI for `image_path`

---

## Symptom

All PDF pages appeared completely white (or body-background colour only). The background images assigned by the `ImageGenerator` were not rendered in the PDF, even though the files existed on disk.

**Before fix — pixel evidence (via `pdftoppm`):**
```
Slide 1: avg_rgb=(247,250,252)  color_range=2   Q=1   ← solid white
Slide 2: avg_rgb=(247,250,252)  color_range=0   Q=0   ← solid white
```

**After fix:**
```
Slide 1: avg_rgb=(144,149,152)  color_range=121  Q=85  ← rich mix
```

---

## Root Cause

`templater.py` passed the image path to the Jinja2 template as a **relative path**:

```python
# BEFORE FIX
image_path = img_info.get('path', '')  # e.g. "assets/slide_1.png"
```

The HTML files are written to `temp_build/`. When Playwright opens `file:///…/temp_build/slide_001.html` and the HTML contains `<img src="assets/slide_1.png">`, the browser resolves the relative path as:

```
file:///…/temp_build/assets/slide_1.png   ← DOES NOT EXIST
```

The actual file lives at:
```
file:///…/ppt-maker/assets/slide_1.png    ← EXISTS
```

### Why did screenshots work but PDF failed?

Playwright's `page.screenshot()` renders the page before timeout, and the `onerror="this.style.display='none'"` handler fires on image load failure. By the time the screenshot was taken in the old raster pipeline, the image element was already hidden — meaning screenshots also never showed the background image (just the body background). The raster pipeline was broken the same way, but it was less noticeable because the glassmorphism body background is close to white, so the visual difference was subtle.

The vector PDF (`page.pdf()`) uses Chromium's PDF renderer, which is stricter about resource resolution. A 404 on an image causes the image rectangle to be omitted from the PDF entirely — resulting in a pure white slide with only text XObjects.

### Verified with browser DevTools:
```javascript
// In page.evaluate():
img.complete        // → true (load event fired)
img.naturalWidth    // → 0   (← failed to load, reported as 0×0)
img.src             // → "file:///…/temp_build/assets/slide_1.png" (wrong path)
```

---

## Fix Applied

```python
# AFTER FIX — templater.py
raw_image_path = img_info.get('path', '')
if raw_image_path and os.path.isfile(raw_image_path):
    # Absolute file:// URI — browser resolves correctly from any directory
    image_path = f"file://{os.path.abspath(raw_image_path)}"
    has_image = True
else:
    image_path = ''
    has_image = False
```

**Verified after fix:**
```javascript
img.complete      // → true
img.naturalWidth  // → 1920  (correctly loaded)
img.src           // → "file:///…/ppt-maker/assets/slide_1.png" (correct)
```

PDF now embeds `XObject /X10` (Type: Image, Width: 1920, Height: 1080) on each slide.

---

## Regression Risk

- Any future code that writes HTML to a subdirectory of `ppt-maker/` and passes `image_path` must use absolute `file://` URIs
- The `onerror="this.style.display='none'"` handler in templates silently hides broken images — add a `console.error` log to make debugging easier in future
