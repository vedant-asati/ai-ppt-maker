# Image Pipeline Improvement Plan
## From Grey Rectangles to Slide-Ready Visuals

---

## 0. The Problem — Three Broken Things

### Break #1: Pipeline Ordering Bug

The current pipeline in [cli.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/cli.py) runs:

```
Phase 3: Templating  → generates HTML files referencing ../assets/slide_N.png
Phase 4: Images      → generates images to assets/slide_N.png
Phase 5: Rendering   → screenshots HTML to PNG
```

This works **by accident** — the HTML references images via relative path `../assets/slide_N.png`, and Playwright resolves this at screenshot time (Phase 5), by which point the images exist (Phase 4). But this ordering creates subtle bugs:

- If image generation **fails** for slide 3 (rate limit), the HTML still references `slide_3.png`. The `onerror` fallback loads `placeholder.png` — a grey rectangle with text. This gets baked into the final PDF permanently.
- If the user runs `--dry-run` and then manually edits `master_plan.json` to change an image prompt, re-running with `--offline-plan` skips regeneration (images already exist) unless `--force-images` is passed. But nothing tells the user this.
- The pipeline has no way to know whether an existing image matches the current prompt or is stale from a previous run.

### Break #2: Only 2 of 4 Templates Use Images

| Template | Uses Image? | How? |
|----------|-------------|------|
| [cover.html](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/templates/cover.html) | ✅ | Full-bleed `<img>` with gradient overlay |
| [split.html](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/templates/split.html) | ✅ | Right half `<img>` with `object-fit: cover` |
| [generic.html](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/templates/generic.html) | ❌ | Image generated but NEVER displayed |
| [infographic.html](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/templates/infographic.html) | ❌ | Image generated but NEVER displayed |

So for a 5-slide deck where the Planner sets `requires_image: true` on all slides, we **generate 5 images** (costing API quota) but only **use 2** (cover + split). The other 3 are wasted.

### Break #3: The Offline Fallback is Unusable

When the Gemini API is unavailable (no API key, rate limited, offline), the fallback is:

```python
img = Image.new('RGB', (1920, 1080), color=(200, 200, 200))  # grey rectangle
d = ImageDraw.Draw(img)
# ... draws prompt text on grey background
```

This produces a grey rectangle with the prompt text written on it in small Arial font. It looks broken, not like a design choice. Any deck rendered offline looks unprofessional.

---

## 1. Corrected Pipeline Architecture

### 1A. New Pipeline Ordering

```
Phase 1: Planning     → master_plan.json
Phase 2: Validation   → check/fix master_plan
Phase 3: Images       → generate/cache all images FIRST     ← MOVED UP
Phase 4: Templating   → generate HTML (now knows which images exist)
Phase 5: Rendering    → screenshot HTML → PNG
Phase 6: Compilation  → PNGs → PDF + speaker notes
```

Images must be generated **before** templating because:
1. The templater needs to know which images exist (to decide between `<img>` and a CSS gradient fallback)
2. The templater can pass `has_image=True/False` to the template context
3. Templates can adapt their layout when no image is available (e.g., `split.html` falls back to full-width text)

### 1B. Updated `cli.py` Phase Ordering

```python
# cli.py — corrected order

# ── Phase 3: Image Generation (BEFORE templating) ──────────
from image_generator import ImageGenerator
img_gen = ImageGenerator()
image_manifest = img_gen.generate_all(
    master_plan, config=config,
    force=getattr(args, 'force_images', False)
)
# image_manifest = {
#   1: {"path": "assets/slide_1.png", "status": "ready", "source": "api"},
#   2: {"path": "assets/slide_2.png", "status": "ready", "source": "cache"},
#   3: {"path": "assets/slide_3.png", "status": "fallback", "source": "gradient"},
#   4: {"path": None, "status": "skipped", "source": None},
# }

# ── Phase 4: Templating (receives image_manifest) ─────────
from templater import Templater
templater = Templater()
html_files = templater.generate_html(master_plan, image_manifest=image_manifest)
#                                                   ^^^^^^^^^^^^^^^^^^^^^^^^
# Templates now receive has_image, image_path, image_status per slide

# ── Phase 5: Rendering ────────────────────────────────────
# (unchanged)
```

### 1C. Updated Templater Interface

```python
# templater.py — image-aware rendering

class Templater:
    def generate_html(self, master_plan: MasterPlan, image_manifest: dict = None):
        image_manifest = image_manifest or {}

        for slide in master_plan.slides:
            # Build image context for this slide
            img_info = image_manifest.get(slide.slide_number, {})
            has_image = img_info.get('status') == 'ready'
            image_path = img_info.get('path', '')
            image_status = img_info.get('status', 'skipped')

            # Convert to relative path for HTML
            if image_path:
                image_path = os.path.relpath(image_path, self.build_dir)

            html_content = template.render(
                slide=slide,
                theme=master_plan.theme,
                total_slides=total_slides,
                has_image=has_image,            # NEW
                image_path=image_path,          # NEW: relative path or ''
                image_status=image_status,      # NEW: 'ready'|'fallback'|'skipped'
            )
```

---

## 2. Image Composition — All Templates Must Handle Images

### 2A. The `image_role` → Template Mapping

The content plan defines `image_role: 'background' | 'supporting' | 'data' | 'decorative'`. Each role has a different composition strategy:

| image_role | Composition | Templates |
|-----------|-------------|-----------|
| `background` | Full-bleed behind content with gradient overlay for text readability | `cover`, `quote`, `generic` (with overlay) |
| `supporting` | Placed beside content (right half, or bottom third) | `split` (right half), `generic` (bottom strip) |
| `data` | Placed as the primary content element | `generic` (replaces bullets), `infographic` (replaces grid) |
| `decorative` | Subtle texture/pattern behind content at low opacity | All templates via CSS `background-image` |

### 2B. Updated Template: `generic.html` — Image Support

Currently generic.html ignores images entirely. Fix:

```html
{% block content %}
<div class="generic-container {% if has_image and image_role == 'background' %}has-bg-image{% endif %}">

    {# Background image (image_role: 'background') #}
    {% if has_image and image_role == 'background' %}
    <div class="generic-bg-image" style="background-image: url('{{ image_path }}');"></div>
    <div class="generic-bg-overlay"></div>
    {% endif %}

    {# Decorative image (image_role: 'decorative') #}
    {% if has_image and image_role == 'decorative' %}
    <div class="generic-decor-image" style="background-image: url('{{ image_path }}');"></div>
    {% endif %}

    <div class="generic-content-wrapper">
        {% if slide.eyebrow %}
        <div class="slide-eyebrow">{{ slide.eyebrow }}</div>
        {% endif %}
        <div class="generic-rule"></div>
        <div class="generic-title">{{ slide.title }}</div>
        {% if slide.subtitle %}
        <div class="generic-subtitle">{{ slide.subtitle }}</div>
        {% endif %}

        {# If image_role is 'data', the image IS the content #}
        {% if has_image and image_role == 'data' %}
        <div class="generic-data-image">
            <img src="{{ image_path }}" alt="{{ slide.title }}">
        </div>
        {% else %}
        {# Normal content blocks (bullets, callout, etc.) #}
        <div class="generic-content">
            {% for bullet in slide.content_bullets %}
            <ul><li>{{ bullet }}</li></ul>
            {% endfor %}
        </div>
        {% endif %}
    </div>

    {# Supporting image (image_role: 'supporting') — bottom strip #}
    {% if has_image and image_role == 'supporting' %}
    <div class="generic-supporting-image">
        <img src="{{ image_path }}" alt="{{ slide.title }}">
    </div>
    {% endif %}
</div>
{% endblock %}
```

```css
/* generic.html — image composition styles */

/* Background image: full bleed with overlay */
.generic-bg-image {
    position: absolute;
    inset: 0;
    background-size: cover;
    background-position: center;
    z-index: 0;
}
.generic-bg-overlay {
    position: absolute;
    inset: 0;
    background: linear-gradient(
        135deg,
        rgba(var(--bg-rgb, 255,255,255), 0.92) 0%,
        rgba(var(--bg-rgb, 255,255,255), 0.75) 60%,
        rgba(var(--bg-rgb, 255,255,255), 0.5) 100%
    );
    z-index: 1;
}
.has-bg-image .generic-content-wrapper {
    position: relative;
    z-index: 2;
}

/* Decorative: subtle texture at low opacity */
.generic-decor-image {
    position: absolute;
    inset: 0;
    background-size: cover;
    background-position: center;
    opacity: 0.08;
    z-index: 0;
}

/* Data: image IS the content — centered, max-width constrained */
.generic-data-image {
    margin-top: 40px;
    text-align: center;
}
.generic-data-image img {
    max-width: 1400px;
    max-height: 600px;
    border-radius: var(--card-radius);
    box-shadow: var(--card-shadow);
}

/* Supporting: bottom strip */
.generic-supporting-image {
    position: absolute;
    bottom: 80px;
    right: 120px;
    width: 500px;
    height: 300px;
    overflow: hidden;
    border-radius: var(--card-radius);
    box-shadow: var(--card-shadow);
}
.generic-supporting-image img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}
```

### 2C. Updated Template: `infographic.html` — Image Support

Infographic currently never uses images. With `image_role: 'data'`, the image replaces the card grid:

```html
{% block content %}
<div class="info-container">
    <div class="info-rule"></div>
    <div class="info-title">{{ slide.title }}</div>
    {% if slide.subtitle %}
    <div class="info-subtitle">{{ slide.subtitle }}</div>
    {% endif %}

    {% if has_image and image_role == 'data' %}
    {# Data image replaces card grid #}
    <div class="info-data-image">
        <img src="{{ image_path }}" alt="{{ slide.title }}">
    </div>
    {% else %}
    <div class="info-grid">
        {% for bullet in slide.content_bullets %}
        <div class="info-card">
            <div class="info-number">{{ "%02d" | format(loop.index) }}</div>
            <div class="info-bullet">{{ bullet }}</div>
        </div>
        {% endfor %}
    </div>
    {% endif %}
</div>
{% endblock %}
```

### 2D. No-Image Fallback for Split Layout

Currently split.html shows a broken image or placeholder. When no image is available, it should gracefully fall back to full-width text:

```html
{% block content %}
<div class="split-container">
    <div class="split-left {% if not has_image %}split-full{% endif %}">
        {# content #}
    </div>

    {% if has_image %}
    <div class="split-right">
        <img src="{{ image_path }}" class="split-image" alt="{{ slide.title }}">
    </div>
    {% endif %}
</div>
{% endblock %}
```

```css
/* When no image available, text takes full width */
.split-full {
    width: 100%;
    max-width: 1400px;
}
```

---

## 3. Image Caching — Don't Regenerate What Hasn't Changed

### 3A. The Problem

Currently, `--force-images` is the only cache control — binary all-or-nothing. If you change the prompt for slide 3 only, you must either:
- Skip all images (`--force-images` not passed → all cached, including stale slide 3)
- Regenerate all images (`--force-images` → regenerates slides 1, 2, 4, 5 unnecessarily)

### 3B. Prompt-Hash Cache

```python
# image_generator.py — prompt-aware caching

import hashlib
import json

CACHE_MANIFEST_PATH = 'assets/.image_cache.json'

class ImageCache:
    """
    Tracks which images were generated from which prompt.
    If the prompt hasn't changed, skip regeneration.
    """

    def __init__(self, assets_dir='assets'):
        self.assets_dir = assets_dir
        self.manifest_path = os.path.join(assets_dir, '.image_cache.json')
        self.manifest = self._load()

    def _load(self) -> dict:
        if os.path.exists(self.manifest_path):
            with open(self.manifest_path, 'r') as f:
                return json.load(f)
        return {}

    def save(self):
        with open(self.manifest_path, 'w') as f:
            json.dump(self.manifest, f, indent=2)

    @staticmethod
    def _hash_prompt(prompt: str) -> str:
        return hashlib.sha256(prompt.strip().encode()).hexdigest()[:16]

    def is_current(self, slide_number: int, prompt: str) -> bool:
        """Returns True if the cached image matches the current prompt."""
        key = f"slide_{slide_number}"
        entry = self.manifest.get(key)
        if not entry:
            return False

        # Check if image file actually exists
        if not os.path.exists(entry.get('path', '')):
            return False

        # Check if prompt hash matches
        return entry.get('prompt_hash') == self._hash_prompt(prompt)

    def record(self, slide_number: int, prompt: str, path: str, source: str):
        """Record a generated/cached image."""
        key = f"slide_{slide_number}"
        self.manifest[key] = {
            "path": path,
            "prompt_hash": self._hash_prompt(prompt),
            "source": source,    # "api", "fallback", "user"
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
```

### 3C. Updated Generation Loop

```python
# image_generator.py — cache-aware generation

def generate_all(self, master_plan, config=None, force=False):
    cache = ImageCache(self.assets_dir)
    image_manifest = {}

    for slide in master_plan.slides:
        if not slide.requires_image:
            image_manifest[slide.slide_number] = {
                "path": None, "status": "skipped", "source": None
            }
            continue

        out_path = os.path.join(self.assets_dir, f"slide_{slide.slide_number}.png")
        prompt = slide.image_prompt or f"Visual for: {slide.title}"

        # Check cache (unless --force-images)
        if not force and cache.is_current(slide.slide_number, prompt):
            print(f"  [Cache] Slide {slide.slide_number}: prompt unchanged, using cached image.")
            image_manifest[slide.slide_number] = {
                "path": out_path, "status": "ready", "source": "cache"
            }
            continue

        # Check for user-provided image (see §5)
        user_image = os.path.join(self.assets_dir, f"user_slide_{slide.slide_number}.png")
        if os.path.exists(user_image):
            import shutil
            shutil.copy2(user_image, out_path)
            cache.record(slide.slide_number, prompt, out_path, "user")
            image_manifest[slide.slide_number] = {
                "path": out_path, "status": "ready", "source": "user"
            }
            print(f"  [User] Slide {slide.slide_number}: using user-provided image.")
            continue

        # Generate via API or fallback
        if self.has_api:
            success = self._generate_with_gemini(prompt, out_path)
            if success:
                cache.record(slide.slide_number, prompt, out_path, "api")
                image_manifest[slide.slide_number] = {
                    "path": out_path, "status": "ready", "source": "api"
                }
                continue

        # Fallback: generate gradient placeholder
        self._generate_quality_fallback(slide, config, out_path)
        cache.record(slide.slide_number, prompt, out_path, "fallback")
        image_manifest[slide.slide_number] = {
            "path": out_path, "status": "fallback", "source": "gradient"
        }

    cache.save()
    self._export_prompts(master_plan, config)
    return image_manifest
```

---

## 4. Offline Fallback — Beautiful Gradients Instead of Grey Rectangles

### 4A. The Problem

Current fallback:
```python
img = Image.new('RGB', (1920, 1080), color=(200, 200, 200))
# Grey rectangle with prompt text in small font
```

This makes every offline-generated deck look broken.

### 4B. The Solution: Theme-Aware Gradient Placeholders

Instead of grey rectangles, generate beautiful gradient images that match the deck's theme. These aren't "placeholders" — they're usable background images.

```python
# image_generator.py — quality fallback

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math
import random

class GradientGenerator:
    """
    Generates theme-aware gradient/pattern images as beautiful fallbacks.
    These should look intentional, not broken.
    """

    # Gradient presets per structural class
    GRADIENT_PRESETS = {
        'glassmorphism': [
            # (start_color, end_color, angle, pattern)
            ((240, 248, 255), (200, 220, 255), 135, 'circles'),     # ice blue
            ((255, 245, 240), (255, 220, 210), 135, 'circles'),     # warm blush
            ((240, 255, 245), (210, 245, 220), 135, 'circles'),     # mint
        ],
        'minimalist': [
            ((250, 250, 250), (240, 240, 240), 180, 'none'),        # near-white gradient
            ((245, 245, 248), (235, 235, 240), 135, 'none'),        # cool grey
        ],
        'neo_brutalism': [
            ((255, 245, 200), (255, 230, 160), 0, 'grid'),          # yellow paper
            ((200, 255, 220), (160, 240, 180), 0, 'grid'),          # green paper
            ((255, 220, 220), (255, 190, 190), 0, 'grid'),          # red paper
        ],
        'corporate_clean': [
            ((245, 248, 252), (230, 235, 245), 180, 'none'),        # cool professional
            ((250, 250, 252), (240, 242, 248), 135, 'dots'),        # subtle blue
        ],
        'dark_neon': [
            ((15, 15, 30), (25, 10, 45), 135, 'glow'),             # deep purple
            ((10, 20, 30), (5, 30, 50), 135, 'glow'),              # deep teal
        ],
        'aurora': [
            ((20, 10, 40), (10, 30, 60), 135, 'shimmer'),          # aurora base
        ],
    }

    @classmethod
    def generate(cls, slide, config, out_path):
        """Generate a beautiful gradient fallback image."""
        width, height = 1920, 1080
        theme = config.get('design_preferences', {}).get('theme_style', 'corporate_clean')
        primary_hex = config.get('design_preferences', {}).get('primary_color', '#2B6CB0')

        # Pick a gradient preset for this theme
        presets = cls.GRADIENT_PRESETS.get(theme, cls.GRADIENT_PRESETS['corporate_clean'])
        preset = presets[slide.slide_number % len(presets)]
        start_color, end_color, angle, pattern = preset

        # Create base gradient
        img = cls._draw_gradient(width, height, start_color, end_color, angle)
        draw = ImageDraw.Draw(img)

        # Add subtle pattern overlay
        if pattern == 'circles':
            cls._add_circles(draw, width, height, primary_hex)
        elif pattern == 'grid':
            cls._add_grid(draw, width, height)
        elif pattern == 'dots':
            cls._add_dots(draw, width, height, primary_hex)
        elif pattern == 'glow':
            cls._add_glow(img, width, height, primary_hex)
        elif pattern == 'shimmer':
            cls._add_shimmer(img, width, height, primary_hex)

        # Apply subtle blur to smooth everything
        img = img.filter(ImageFilter.GaussianBlur(radius=2))

        img.save(out_path, quality=95)

    @staticmethod
    def _draw_gradient(width, height, start, end, angle_deg):
        """Draw a linear gradient at the specified angle."""
        img = Image.new('RGB', (width, height))
        pixels = img.load()

        angle_rad = math.radians(angle_deg)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)

        # Project each pixel onto the gradient axis
        max_proj = abs(width * cos_a) + abs(height * sin_a)

        for y in range(height):
            for x in range(width):
                proj = (x * cos_a + y * sin_a)
                t = max(0, min(1, (proj + max_proj/2) / max_proj))

                r = int(start[0] + (end[0] - start[0]) * t)
                g = int(start[1] + (end[1] - start[1]) * t)
                b = int(start[2] + (end[2] - start[2]) * t)
                pixels[x, y] = (r, g, b)

        return img

    @staticmethod
    def _hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    @classmethod
    def _add_circles(cls, draw, width, height, primary_hex):
        """Add frosted circle shapes (glassmorphism aesthetic)."""
        rgb = cls._hex_to_rgb(primary_hex)
        random.seed(42)  # deterministic for cacheability
        for _ in range(5):
            cx = random.randint(0, width)
            cy = random.randint(0, height)
            r = random.randint(150, 400)
            fill = (*rgb, 8)  # very low alpha
            # PIL doesn't support alpha drawing on RGB, so approximate:
            for ring in range(r, r - 30, -3):
                draw.ellipse(
                    [cx - ring, cy - ring, cx + ring, cy + ring],
                    outline=(*rgb,), width=1
                )

    @classmethod
    def _add_grid(cls, draw, width, height):
        """Add a grid pattern (neo-brutalism aesthetic)."""
        grid_size = 80
        line_color = (0, 0, 0)  # will be very transparent
        for x in range(0, width, grid_size):
            draw.line([(x, 0), (x, height)], fill=(*line_color,), width=1)
        for y in range(0, height, grid_size):
            draw.line([(0, y), (width, y)], fill=(*line_color,), width=1)

    @classmethod
    def _add_dots(cls, draw, width, height, primary_hex):
        """Add a subtle dot pattern (corporate aesthetic)."""
        rgb = cls._hex_to_rgb(primary_hex)
        dot_spacing = 60
        dot_radius = 2
        for x in range(dot_spacing, width, dot_spacing):
            for y in range(dot_spacing, height, dot_spacing):
                draw.ellipse(
                    [x - dot_radius, y - dot_radius, x + dot_radius, y + dot_radius],
                    fill=rgb
                )

    @classmethod
    def _add_glow(cls, img, width, height, primary_hex):
        """Add radial glow points (dark_neon aesthetic)."""
        from PIL import ImageDraw
        rgb = cls._hex_to_rgb(primary_hex)
        overlay = Image.new('RGB', (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        random.seed(42)
        for _ in range(3):
            cx = random.randint(width // 4, 3 * width // 4)
            cy = random.randint(height // 4, 3 * height // 4)
            for r in range(300, 0, -5):
                opacity = int(15 * (r / 300))
                color = (
                    min(255, rgb[0] + opacity),
                    min(255, rgb[1] + opacity),
                    min(255, rgb[2] + opacity),
                )
                draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)

        # Blend overlay onto image
        from PIL import ImageChops
        img.paste(ImageChops.add(img, overlay))

    @classmethod
    def _add_shimmer(cls, img, width, height, primary_hex):
        """Add aurora-style color bands (aurora aesthetic)."""
        rgb = cls._hex_to_rgb(primary_hex)
        draw = ImageDraw.Draw(img)
        for i in range(5):
            y_center = height // 2 + (i - 2) * 120
            for dy in range(-80, 80, 3):
                alpha_factor = max(0, 1 - abs(dy) / 80)
                color = (
                    min(255, int(rgb[0] * 0.3 + 20 * alpha_factor)),
                    min(255, int(rgb[1] * 0.3 + 30 * alpha_factor)),
                    min(255, int(rgb[2] * 0.3 + 25 * alpha_factor)),
                )
                draw.line(
                    [(0, y_center + dy), (width, y_center + dy + random.randint(-20, 20))],
                    fill=color, width=2
                )
```

### 4C. Fallback Quality Comparison

| Aspect | Current Fallback | New Fallback |
|--------|-----------------|--------------|
| Background | Flat grey (#C8C8C8) | Theme-aware gradient |
| Pattern | None | Matching structural class (circles for glassmorphism, grid for brutalism) |
| Text | Prompt text in Arial | No text (clean background) |
| Usability | Looks broken | Looks intentional — usable in final deck |
| Dark themes | Grey on dark = terrible | Dark gradient with glow/shimmer |

---

## 5. User-Provided Images

### 5A. Convention-Based Override

Users can provide their own images by placing them in `assets/` with a specific naming convention:

```
assets/
  user_slide_1.png    ← user-provided image for slide 1
  user_slide_3.jpg    ← user-provided image for slide 3
  slide_2.png         ← AI-generated (or cached) image for slide 2
```

The generator checks for `user_slide_N.*` before attempting API generation:

```python
USER_IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp']

def _find_user_image(self, slide_number: int) -> str | None:
    """Check if user provided an image for this slide."""
    for ext in USER_IMAGE_EXTENSIONS:
        path = os.path.join(self.assets_dir, f"user_slide_{slide_number}{ext}")
        if os.path.exists(path):
            return path
    return None
```

### 5B. Image Resizing for User-Provided Images

User images may not be 1920×1080. Auto-resize:

```python
def _prepare_user_image(self, user_path: str, out_path: str):
    """Resize/crop user image to 1920×1080 while preserving aspect ratio."""
    img = Image.open(user_path)

    target_w, target_h = 1920, 1080
    target_ratio = target_w / target_h
    img_ratio = img.width / img.height

    if img_ratio > target_ratio:
        # Image is wider — crop sides
        new_width = int(img.height * target_ratio)
        left = (img.width - new_width) // 2
        img = img.crop((left, 0, left + new_width, img.height))
    else:
        # Image is taller — crop top/bottom
        new_height = int(img.width / target_ratio)
        top = (img.height - new_height) // 2
        img = img.crop((0, top, img.width, top + new_height))

    img = img.resize((target_w, target_h), Image.LANCZOS)
    img.save(out_path, quality=95)
```

### 5C. Config-Level Image Override

For more explicit control, users can specify per-slide image overrides in config:

```yaml
# config.yaml
image_overrides:
  1: "assets/my_cover_photo.jpg"      # use this specific file for slide 1
  4: "https://example.com/chart.png"  # download and use this URL for slide 4
  # all other slides: generate via API or fallback
```

---

## 6. Rate Limiting & Retry Strategy

### 6A. Current Problem

The current code catches 429 errors per-image and falls back to grey rectangle immediately. For a 10-slide deck, if the API quota is 5 images/minute, slides 6–10 all become grey rectangles.

### 6B. Smart Rate Limiter

```python
# image_generator.py — rate-aware generation

import time
from collections import deque

class RateLimiter:
    """
    Token bucket rate limiter for Gemini image API.
    Waits intelligently instead of failing immediately.
    """

    def __init__(self, max_per_minute=5, max_wait_seconds=120):
        self.max_per_minute = max_per_minute
        self.max_wait = max_wait_seconds
        self.request_times = deque()
        self.consecutive_429s = 0

    def wait_if_needed(self) -> bool:
        """
        Returns True if we can proceed, False if we should skip.
        Blocks (sleeps) if we need to wait for quota.
        """
        now = time.time()

        # Clean old entries (older than 60s)
        while self.request_times and now - self.request_times[0] > 60:
            self.request_times.popleft()

        if len(self.request_times) < self.max_per_minute:
            # Under quota — proceed immediately
            return True

        # Over quota — calculate wait time
        oldest = self.request_times[0]
        wait = 60 - (now - oldest) + 1  # wait until oldest request expires + buffer

        if wait > self.max_wait:
            print(f"  [Rate Limit] Would need to wait {wait:.0f}s — exceeds max wait. Skipping.")
            return False

        print(f"  [Rate Limit] Quota reached. Waiting {wait:.0f}s for next slot...")
        time.sleep(wait)
        return True

    def record_success(self):
        self.request_times.append(time.time())
        self.consecutive_429s = 0

    def record_429(self, retry_delay: int = None):
        self.consecutive_429s += 1
        if retry_delay:
            wait = retry_delay
        else:
            wait = min(60, 15 * (2 ** (self.consecutive_429s - 1)))  # exponential: 15, 30, 60

        if wait <= self.max_wait:
            print(f"  [Rate Limit] 429 received (attempt {self.consecutive_429s}). "
                  f"Waiting {wait}s...")
            time.sleep(wait)
        else:
            print(f"  [Rate Limit] 429 received. Wait would be {wait}s — skipping to fallback.")
```

### 6C. Integrated Generation Flow

```python
def generate_all(self, master_plan, config=None, force=False):
    rate_limiter = RateLimiter(max_per_minute=5, max_wait_seconds=120)
    cache = ImageCache(self.assets_dir)
    image_manifest = {}

    # Sort slides: generate images for cover/split FIRST (they're visible)
    # then generic/infographic (which may not display images)
    priority_order = sorted(
        [s for s in master_plan.slides if s.requires_image],
        key=lambda s: 0 if s.layout_type in ('cover', 'split') else 1
    )

    for slide in priority_order:
        # ... cache check, user-provided check ...

        if self.has_api:
            can_proceed = rate_limiter.wait_if_needed()
            if can_proceed:
                success = self._generate_with_gemini(prompt, out_path)
                if success:
                    rate_limiter.record_success()
                    # ...
                else:
                    rate_limiter.record_429()
                    # Try once more after waiting
                    if rate_limiter.wait_if_needed():
                        success = self._generate_with_gemini(prompt, out_path)
                        if success:
                            rate_limiter.record_success()
                            continue
            # If we get here, API failed — use fallback
            self._generate_quality_fallback(slide, config, out_path)
```

### 6D. Priority-Based Generation

Not all images are equally important. Generate high-priority images first:

| Priority | Layout × image_role | Why |
|----------|-------------------|-----|
| P0 (critical) | `cover` + `background` | First impression — must be excellent |
| P0 (critical) | `split` + `supporting` | Image is 50% of the slide |
| P1 (important) | `quote` + `background` | Full-screen visual, high impact |
| P1 (important) | any + `data` | Image IS the content |
| P2 (nice-to-have) | `generic` + `background` | Content overlays it heavily |
| P3 (skippable) | any + `decorative` | Gradient fallback looks fine |

If the API quota is limited, P0 images get generated first. P3 images always use gradient fallbacks.

```python
def _image_priority(self, slide) -> int:
    image_role = getattr(slide, 'image_role', 'background')
    if slide.layout_type in ('cover', 'split'):
        return 0
    if image_role == 'data':
        return 1
    if slide.layout_type == 'quote':
        return 1
    if image_role == 'decorative':
        return 3
    return 2
```

---

## 7. Image Quality Validation

### 7A. The Problem

The Gemini image API sometimes returns:
- Images with text/watermarks (despite prompt saying "no text")
- Wrong aspect ratio (square instead of 16:9)
- Very dark or blown-out images
- Images that don't match the prompt at all

### 7B. Automated Checks (PIL-based, no API)

```python
# image_validator.py

from PIL import Image
import numpy as np

class ImageValidator:
    """
    Post-generation quality checks using PIL.
    No API calls — runs locally and fast.
    """

    @staticmethod
    def validate(image_path: str, slide=None) -> list:
        issues = []
        img = Image.open(image_path)

        # 1. Dimension check
        if img.size != (1920, 1080):
            issues.append(
                f"Wrong dimensions: {img.size[0]}×{img.size[1]} "
                f"(expected 1920×1080). Will be resized."
            )

        # 2. Aspect ratio check (should be ~16:9 = 1.778)
        ratio = img.size[0] / img.size[1]
        if abs(ratio - 16/9) > 0.1:
            issues.append(
                f"Wrong aspect ratio: {ratio:.2f} (expected ~1.78). "
                f"Image may appear stretched or cropped."
            )

        # 3. Brightness check (too dark or too bright)
        arr = np.array(img.convert('L'))  # grayscale
        mean_brightness = arr.mean()

        if mean_brightness < 25:
            issues.append(
                f"Image is extremely dark (mean brightness: {mean_brightness:.0f}/255). "
                f"Text may be unreadable if overlaid."
            )
        elif mean_brightness > 240:
            issues.append(
                f"Image is nearly white (mean brightness: {mean_brightness:.0f}/255). "
                f"May appear blank."
            )

        # 4. Contrast check (standard deviation of brightness)
        std_brightness = arr.std()
        if std_brightness < 10:
            issues.append(
                f"Image has very low contrast (std: {std_brightness:.1f}). "
                f"May appear flat or uniform."
            )

        # 5. Center-region brightness (for background images with text overlay)
        image_role = getattr(slide, 'image_role', 'background') if slide else 'background'
        if image_role == 'background':
            h, w = arr.shape
            center = arr[h//4:3*h//4, w//4:3*w//4]
            center_std = center.std()

            if center_std > 80:
                issues.append(
                    f"Background image has high visual complexity in center region "
                    f"(std: {center_std:.0f}). Text readability may be poor. "
                    f"Consider image_role: 'supporting' instead."
                )

        # 6. File size check (suspiciously small = corrupt/placeholder)
        file_size = os.path.getsize(image_path)
        if file_size < 5000:  # < 5KB for a 1920×1080 image is suspect
            issues.append(
                f"File size is only {file_size} bytes — "
                f"may be corrupt or a failed download."
            )

        return issues

    @staticmethod
    def auto_fix(image_path: str) -> str:
        """
        Auto-fix common issues:
        - Resize to 1920×1080
        - Crop to 16:9 if needed
        Returns path to fixed image.
        """
        img = Image.open(image_path)

        if img.size != (1920, 1080):
            target_ratio = 1920 / 1080
            img_ratio = img.width / img.height

            if abs(img_ratio - target_ratio) > 0.05:
                # Crop to 16:9
                if img_ratio > target_ratio:
                    new_width = int(img.height * target_ratio)
                    left = (img.width - new_width) // 2
                    img = img.crop((left, 0, left + new_width, img.height))
                else:
                    new_height = int(img.width / target_ratio)
                    top = (img.height - new_height) // 2
                    img = img.crop((0, top, img.width, top + new_height))

            img = img.resize((1920, 1080), Image.LANCZOS)
            img.save(image_path, quality=95)

        return image_path
```

### 7C. Validation Integration

```python
# In image_generator.py, after successful API generation:

from image_validator import ImageValidator

success = self._generate_with_gemini(prompt, out_path)
if success:
    # Validate the generated image
    issues = ImageValidator.validate(out_path, slide=slide)
    if issues:
        for issue in issues:
            print(f"  [Image QA] Slide {slide.slide_number}: {issue}")
        # Auto-fix what we can
        ImageValidator.auto_fix(out_path)
```

---

## 8. Enhanced Prompt Export for Manual Generation

### 8A. Current Problem

The `image_prompts.txt` export is decent but has issues:
- All images get the same "Usage: Full-bleed background" instruction regardless of `image_role`
- No theme color hex values for chat-based generation
- No aspect ratio reminder
- No example of what "good" looks like for each role

### 8B. Improved Export Format

```python
# image_generator.py — enhanced prompt export

ROLE_INSTRUCTIONS = {
    'background': (
        "COMPOSITION: Full-bleed 1920×1080 background for a presentation slide.\n"
        "  - Text will be overlaid on the LEFT SIDE — keep that area simple/blurred.\n"
        "  - Strong visual interest on the RIGHT and edges.\n"
        "  - NO text, NO watermarks, NO logos, NO UI elements in the image."
    ),
    'supporting': (
        "COMPOSITION: 960×1080 image for the RIGHT HALF of a split-layout slide.\n"
        "  - The LEFT half will contain text — your image fills the RIGHT.\n"
        "  - Strong visual focus centered in the frame.\n"
        "  - NO text, NO watermarks."
    ),
    'data': (
        "COMPOSITION: 1920×1080 infographic, chart, or diagram.\n"
        "  - This IS the slide content — it must be clear and readable.\n"
        "  - Use a background color that matches the slide theme.\n"
        "  - Labels and annotations ARE allowed (they are part of the data).\n"
        "  - Clean, minimalist style. No decorative elements."
    ),
    'decorative': (
        "COMPOSITION: 1920×1080 abstract texture or pattern.\n"
        "  - Will be used at 8-15% opacity as a subtle background layer.\n"
        "  - Should be abstract — no recognizable objects.\n"
        "  - Low saturation, soft gradients preferred.\n"
        "  - NO text, NO logos."
    ),
}

def _export_prompts(self, master_plan, config):
    config = config or {}
    theme = config.get('design_preferences', {}).get('theme_style', '')
    primary = config.get('design_preferences', {}).get('primary_color', '')
    art_style = config.get('image_preferences', {}).get('art_style', '')
    audience = config.get('presentation_goals', {}).get('audience', '')
    total = len(master_plan.slides)

    entries = []
    for slide in master_plan.slides:
        if not slide.requires_image:
            continue

        image_role = getattr(slide, 'image_role', 'background')
        role_instruction = ROLE_INSTRUCTIONS.get(image_role, ROLE_INSTRUCTIONS['background'])

        entry = [
            f"{'='*60}",
            f"SLIDE {slide.slide_number} OF {total}",
            f"{'='*60}",
            f"Save as: assets/slide_{slide.slide_number}.png",
            f"",
            f"SLIDE CONTEXT:",
            f"  Title: \"{slide.title}\"",
            f"  Layout: {slide.layout_type}",
            f"  Image Role: {image_role}",
        ]

        if hasattr(slide, 'slide_purpose'):
            entry.append(f"  Narrative Purpose: {slide.slide_purpose}")
        if audience:
            entry.append(f"  Audience: {audience}")

        entry.extend([
            f"",
            f"DESIGN CONSTRAINTS:",
            f"  Dimensions: 1920 × 1080 pixels (16:9 landscape)",
            f"  Theme: {theme}" + (f" | Primary color: {primary}" if primary else ""),
            f"  Art style: {art_style}" if art_style else None,
            f"",
            role_instruction,
            f"",
            f"PROMPT:",
            f"  {slide.image_prompt or 'Abstract visual for: ' + slide.title}",
            f"",
        ])

        entries.append("\n".join(line for line in entry if line is not None))

    if entries:
        prompts_path = os.path.join(self.assets_dir, "image_prompts.txt")
        with open(prompts_path, "w", encoding="utf-8") as f:
            f.write("IMAGE GENERATION GUIDE\n")
            f.write(f"Deck: {total} slides | Theme: {theme} | Style: {art_style}\n")
            f.write("="*60 + "\n\n")
            f.write("HOW TO USE:\n")
            f.write("1. Copy each prompt block into Gemini, ChatGPT, or Midjourney\n")
            f.write("2. Generate a 1920×1080 image matching the description\n")
            f.write("3. Save to the path shown in 'Save as:'\n")
            f.write("4. Re-run: python cli.py generate --offline-plan master_plan.json\n")
            f.write("   (existing images won't be regenerated — only missing ones)\n\n")
            f.write("\n\n".join(entries))

        print(f"  [Export] Saved {len(entries)} image prompts to {prompts_path}")
```

---

## 9. Image Status in Speaker Notes & Dry-Run

### 9A. Dry-Run Image Status

When running `--dry-run`, show which images exist, which are cached, and which need generation:

```
--dry-run complete. Image status:
  Slide 1 (cover):       ⚠ NEEDS GENERATION  [background]
  Slide 2 (split):       ⚠ NEEDS GENERATION  [supporting]
  Slide 3 (generic):     ○ No image required
  Slide 4 (stat):        ○ No image required
  Slide 5 (quote):       ✓ User-provided: assets/user_slide_5.png
```

### 9B. Post-Generation Summary

```
Image Generation Summary:
  ✓ Slide 1: Generated via API (23.4 KB)
  ✓ Slide 2: Generated via API (31.2 KB)
  ⚡ Slide 3: Cached (prompt unchanged)
  ⚠ Slide 4: Gradient fallback (API quota reached)
  ✓ Slide 5: User-provided image

  API calls used: 2 | Cached: 1 | Fallback: 1 | User: 1
  Total generation time: 8.3s
  Prompts exported to: assets/image_prompts.txt
```

---

## 10. Edge Cases

| Scenario | Risk | Mitigation |
|----------|------|------------|
| User-provided image is 100×100px | Upscaling to 1920×1080 looks terrible | Warn if source < 960×540; suggest a higher-resolution image |
| User-provided image is CMYK TIFF | PIL can't handle all formats | Convert to RGB PNG on load; catch `UnidentifiedImageError` |
| API returns image with embedded text | "No text" in prompt ignored by model | ImageValidator could use OCR (pytesseract) to detect text — but this is heavy; keep as optional |
| Image file is corrupt (0 bytes) | PIL crashes on open | Wrap in try/except; re-download or use fallback |
| API returns transparent PNG | White text on transparent = invisible | Convert to RGB with white/dark background before saving |
| `assets/` directory has 50 stale images from previous runs | Confusing for user; wastes disk | `--clean-images` flag removes images not in current manifest |
| Playwright renders HTML before Google Fonts load | Text renders in fallback serif | Already handled: `wait_until='networkidle'` + `document.fonts.ready`. But add a 500ms safety margin |
| Image path has spaces or unicode | `<img src="...">` breaks in HTML | URL-encode the path in template rendering |
| User image is animated GIF | PIL reads first frame only | Warn user; extract first frame |
| Rate limit changes mid-generation | First 3 images succeed, then 429 | RateLimiter adapts dynamically based on 429 responses |

---

## 11. Implementation Phases

### Phase 1 — Pipeline Fix & Image Manifest
1. Reorder cli.py: images BEFORE templating
2. `generate_all()` returns `image_manifest` dict
3. Templater receives `image_manifest` and passes `has_image`, `image_path`, `image_role` to templates
4. All 4 existing templates updated with `{% if has_image %}` guards

### Phase 2 — Image Composition in Templates
5. `generic.html`: Add background, supporting, data, decorative image modes
6. `infographic.html`: Add data image mode (replaces card grid)
7. `split.html`: Add no-image fallback (full-width text)
8. `cover.html`: Add no-image fallback (gradient background)
9. New templates (`quote.html`, `stat.html`, `timeline.html`): Include image composition from the start

### Phase 3 — Caching
10. `ImageCache` class with prompt-hash manifest
11. `.image_cache.json` in assets/
12. Skip regeneration for unchanged prompts
13. `--force-images` bypasses cache
14. `--clean-images` removes stale cached images

### Phase 4 — Quality Fallbacks
15. `GradientGenerator` with theme-aware presets for all structural classes
16. Pattern overlays: circles, grid, dots, glow, shimmer
17. Replace grey rectangle fallback with gradient generator
18. Fallback quality validation (ensure gradient isn't solid color)

### Phase 5 — User-Provided Images
19. Convention-based override (`user_slide_N.{ext}`)
20. Auto-resize/crop to 1920×1080
21. Config-level `image_overrides:` support
22. Validation warnings for low-resolution user images

### Phase 6 — Rate Limiting
23. `RateLimiter` with token bucket
24. Smart wait vs. skip decision
25. Priority-based generation order (cover/split first)
26. Per-slide retry with exponential backoff
27. Generation summary with API call count

### Phase 7 — Image Validation
28. `ImageValidator` with dimension, brightness, contrast, center-complexity checks
29. Auto-fix: resize, crop to 16:9
30. Integration into generation loop (validate after every API image)
31. Optional OCR text detection (advanced, depends on pytesseract)

### Phase 8 — Enhanced Export & UX
32. Role-aware `image_prompts.txt` export
33. Dry-run image status display
34. Post-generation summary with stats
35. Image status in speaker notes export

---

## 12. File Change List

| File | Action | Description |
|------|--------|-------------|
| `cli.py` | MODIFY | Reorder phases (images before templating); pass image_manifest; `--clean-images` flag; image status in dry-run |
| `image_generator.py` | MODIFY | Returns image_manifest; cache integration; rate limiter; user image support; quality fallback; enhanced prompt export; priority ordering |
| `image_validator.py` | NEW | PIL-based quality checks: dimensions, brightness, contrast, center complexity; auto-fix resize/crop |
| `image_cache.py` | NEW | Prompt-hash cache with `.image_cache.json` manifest |
| `gradient_generator.py` | NEW | Theme-aware gradient fallbacks with pattern overlays for all structural classes |
| `templater.py` | MODIFY | Accepts `image_manifest`; passes `has_image`, `image_path`, `image_role` to templates |
| `templates/generic.html` | MODIFY | Add 4 image composition modes (background, supporting, data, decorative) |
| `templates/infographic.html` | MODIFY | Add data image mode replacing card grid |
| `templates/split.html` | MODIFY | Add no-image fallback (full-width text) |
| `templates/cover.html` | MODIFY | Add no-image fallback (gradient CSS) |
| `templates/quote.html` | NEW | (from content plan) — includes image composition from the start |
| `templates/stat.html` | NEW | (from content plan) — includes image composition from the start |
| `templates/timeline.html` | NEW | (from content plan) — includes image composition from the start |
| `compiler.py` | MODIFY | Image status in speaker notes export |

---

## 13. How This Plan Connects to the Other Two

```
┌─────────────────────────┐
│   Content Quality Plan  │ ← decides WHAT image to generate (image_role, image_prompt)
│   (§8: Image Quality)   │    and writes the prompt text
└────────┬────────────────┘
         │ image_prompt + image_role
         ▼
┌─────────────────────────┐
│   Image Pipeline Plan   │ ← decides HOW to generate it (API, cache, fallback, user)
│   (THIS DOCUMENT)       │    and validates the result
└────────┬────────────────┘
         │ image_manifest (path + status)
         ▼
┌─────────────────────────┐
│   UI Pipeline Plan      │ ← decides WHERE to put it (composition in templates,
│   (§theme + §audit)     │    visual audit checks, theme-specific image treatment)
└─────────────────────────┘
```

The three plans form a complete pipeline with clear interfaces between them:
- **Content Plan** → produces `image_prompt` and `image_role` per slide
- **Image Plan** → produces `image_manifest` (path + status per slide)
- **UI Plan** → consumes `image_manifest` in templates and validates visual result

> [!NOTE]
> **The single highest-priority fix in this plan is Phase 1** — reordering the pipeline and passing image_manifest to templates. Without it, the other two plans can't fully function: the Content Plan can define `image_role` but templates can't use it, and the UI Plan can audit images but they aren't composited into slides.
