# Bridge to Excellence — Deep Execution Guide
## From Q=31 to Q=80+ (Reference: Panch Parivartan at Q=100)

> **Date:** 2026-08-03  
> **Scope:** Every layer of the pipeline — planner → schema → templater → templates → image_generator → renderer → PPTX exporter  
> **Method:** Traced every relevant variable through the full data flow to identify exactly what changes where

---

## Part 1: The Data Flow (as it is today)

Understanding the exact flow is essential before changing anything. Here is how a slide goes from concept to pixel:

```
User config.yaml
  ↓
cli.py (orchestrator)
  ↓
┌────────────────────────────────────────────────────┐
│ Phase 1: planner.py                                │
│   Input:  user source text, system prompt          │
│   Output: master_plan.json (MasterPlan model)      │
│   Schema: schemas.py → Slide, Theme, ContentBlock  │
│                                                    │
│   The planner emits per slide:                     │
│     slide_purpose:   "problem_statement" | etc.    │
│     layout_type:     "generic" | "split" | etc.    │
│     requires_image:  true | false                  │
│     image_role:      "background" | "supporting"   │
│     image_prompt:    "Abstract background..."      │
│     content_blocks:  [BulletBlock, StatBlock, ...]  │
│     eyebrow:         "THE PROBLEM"                 │
└────────────────────────────────────────────────────┘
  ↓  master_plan.json
┌────────────────────────────────────────────────────┐
│ Phase 2.5: theme_resolver.py                       │
│   Merges AI CSS vars + curated palette + user hex  │
│   Writes final CSS vars into master_plan.theme     │
│   Output: resolved_vars dict                       │
└────────────────────────────────────────────────────┘
  ↓  master_plan (with resolved CSS vars)
┌────────────────────────────────────────────────────┐
│ Phase 3: image_generator.py                        │
│   For each slide where requires_image=True:        │
│     - Check cache → user image → API → gradient    │
│     - ALL images are 1920×1080 landscape           │
│     - Saves to assets/slide_N.png                  │
│   Output: image_manifest dict                      │
│     { slide_number → { path, status, role } }      │
└────────────────────────────────────────────────────┘
  ↓  image_manifest
┌────────────────────────────────────────────────────┐
│ Phase 4: templater.py                              │
│   For each slide:                                  │
│     - Picks template: templates/{layout_type}.html │
│     - Passes to Jinja2: slide, theme, has_image,   │
│       image_path (absolute file://), image_role,   │
│       total_slides                                 │
│   Output: temp_build/slide_NNN.html                │
│                                                    │
│   ⚠️ NOT passed: slide_purpose, card_tone,         │
│      engagement_prompt, section_name               │
└────────────────────────────────────────────────────┘
  ↓  html_files
┌────────────────────────────────────────────────────┐
│ Phase 5: renderer.py (Playwright)                  │
│   Opens each HTML in headless Chromium             │
│   page.pdf()  → per-slide vector PDF               │
│   page.screenshot() → per-slide PNG (if --audit)   │
│                                                    │
│   For PPTX: render_background_only()               │
│     Injects CSS: color:transparent on all text     │
│     screenshot() → text-free background PNG        │
└────────────────────────────────────────────────────┘
  ↓  pdf_slide_files / bg_png_files
┌────────────────────────────────────────────────────┐
│ Phase 6: compiler.py + pptx_exporter.py            │
│   compiler: merge per-slide PDFs into one          │
│   pptx: bg_png + text overlays per layout_type     │
│   Output: presentation.pdf, presentation.pptx      │
└────────────────────────────────────────────────────┘
```

---

## Part 2: The 12 Interventions — Exact File + Line

Each intervention is numbered, with the exact file, the exact function, the exact variables involved, and the exact code change.

---

### INT-01: Pass `slide_purpose` and `card_tone` to templates

**Why:** The planner already emits `slide_purpose` (e.g. `"problem_statement"`) but the templater never passes it to the HTML. The templates can't colour cards semantically because they don't know the slide's role.

**Data flow trace:**
```
planner.py  →  Slide.slide_purpose = "problem_statement"     ✅ EXISTS
schemas.py  →  slide_purpose: Optional[str]                  ✅ EXISTS
templater.py L58 → template.render(slide=slide, ...)         ✅ slide object includes it
templates/*.html → {{ slide.slide_purpose }}                  ⚠️ NEVER USED
base.html body class → <body class="{{ theme.structural_class }}">  ⚠️ NO PURPOSE CLASS
```

**Change in `templater.py` L56-67:**
```python
# CURRENT:
html_content = template.render(
    slide=slide,
    theme=master_plan.theme,
    total_slides=total_slides,
    has_image=has_image,
    image_path=image_path,
    image_status=image_status,
    image_role=image_role,
    local_fonts_available=local_fonts_available,
)

# NEW — add card_tone:
PURPOSE_TO_TONE = {
    'problem_statement': 'tone-problem',
    'challenge':         'tone-problem',
    'evidence':          'tone-evidence',
    'call_to_action':    'tone-action',
    'solution':          'tone-action',
    'social_proof':      'tone-evidence',
}
card_tone = PURPOSE_TO_TONE.get(slide.slide_purpose or '', '')

html_content = template.render(
    slide=slide,
    theme=master_plan.theme,
    total_slides=total_slides,
    has_image=has_image,
    image_path=image_path,
    image_status=image_status,
    image_role=image_role,
    card_tone=card_tone,                    # ← NEW
    local_fonts_available=local_fonts_available,
)
```

**Change in `base.html` L539:**
```html
<!-- CURRENT -->
<body class="{{ theme.structural_class }}">

<!-- NEW — add card_tone class -->
<body class="{{ theme.structural_class }} {{ card_tone }}">
```

**Change in `base.html` — add CSS after L328 (after .page-num):**
```css
/* ─── Semantic card tone overrides ────────────────────────────────────── */
body.tone-problem .generic-content,
body.tone-problem .split-content,
body.tone-problem .block-comparison .comparison-col:first-child {
  background: var(--card-problem, rgba(0,0,0,0.80));
  color: var(--text-on-dark, #F0F0F0);
}
body.tone-problem .block-bullets li { color: var(--text-on-dark, #F0F0F0); border-color: rgba(255,255,255,0.15); }
body.tone-problem .block-bullets li::before { background: var(--primary); }

body.tone-action .generic-content,
body.tone-action .split-content {
  background: var(--card-action, rgba(var(--primary-rgb), 0.12));
  border-left: 4px solid var(--primary);
}

body.tone-evidence .generic-content,
body.tone-evidence .split-content {
  border-top: 3px solid var(--primary);
}
```

**Dependency:** Requires INT-06 (add `--card-problem`, `--card-action`, `--text-on-dark` to theme palettes).

**Risk:** CSS specificity — `body.tone-problem .generic-content` must win over `body.dark_neon` defaults. Using two classes on body ensures this.

---

### INT-02: Dynamic footer — section label + page numbers

**Current state:** `base.html` L543: `<div class="footer">AI PRESENTATION AGENCY</div>` — hardcoded.

**The page number already works** (L544) — it uses `slide.slide_number` and `total_slides`, both of which are passed by the templater. But the footer text is static.

**Change in `base.html` L543:**
```html
<!-- CURRENT -->
<div class="footer">AI PRESENTATION AGENCY</div>

<!-- NEW -->
<div class="footer">
  {% if slide.eyebrow %}{{ slide.eyebrow }}{% endif %}
  {% if slide.title %} · {{ slide.title }}{% endif %}
</div>
```

**No schema change needed** — `slide.eyebrow` and `slide.title` are already available.

**Risk:** None. Pure template change.

---

### INT-03: Eyebrow accent rule (horizontal line)

**Current state:** The `.accent-rule` class exists in base.html (L92-97) and is used by `generic.html` (L87) and `split.html` (L86) — as a `<div>`. But it's a separate element. The reference PDF has it as a short coloured line **above** the eyebrow text, integrated into the eyebrow itself.

**Change in `base.html` L81-89 — add `::before` pseudo-element:**
```css
/* CURRENT */
.eyebrow {
  display: inline-block;
  font-size: var(--type-micro);
  font-weight: 600;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--primary);
  margin-bottom: var(--space-sm);
}

/* NEW — add rule mark above eyebrow */
.eyebrow {
  display: inline-block;
  font-size: var(--type-micro);
  font-weight: 600;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--primary);
  margin-bottom: var(--space-sm);
  padding-top: 18px;        /* space for the rule above */
  position: relative;
}
.eyebrow::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 48px;
  height: 3px;
  background: var(--primary);
  border-radius: 2px;
}
body.aurora .eyebrow::before {
  background: linear-gradient(90deg, var(--aurora-1), var(--aurora-2));
}
body.dark_neon .eyebrow::before {
  box-shadow: 0 0 12px rgba(var(--primary-rgb), 0.6);
}
```

**Risk:** The `cover.html` template has its own eyebrow positioning (L69-71). The `::before` needs to not interfere. Since cover uses `.cover-content .eyebrow`, specificity is safe.

---

### INT-04: Right-panel image mode for `generic.html`

This is the **single highest-impact change**. The reference uses a right-side portrait image panel on 70% of slides. Currently, `generic.html` only uses images as a low-opacity decorative background (`opacity: 0.08`).

**How the image_role flows today:**
```
planner → slide.image_role = "supporting" | "background" | "decorative" | "data"
image_generator → image_manifest[N]['role'] = slide.image_role
templater L56 → image_role = img_info.get('role', ...)
template → {% if has_image and image_role == 'decorative' %} <img> {% endif %}
```

Currently, `generic.html` L78 checks `image_role == 'decorative'` — every other role is **ignored**. The image exists on disk but is never rendered.

**New image_role value needed:** `'panel'` — tells the template to use a side-panel layout.

**Change in `schemas.py` L176:**
```python
# CURRENT
image_role: Optional[Literal['background', 'supporting', 'data', 'decorative']]

# NEW — add 'panel'
image_role: Optional[Literal['background', 'supporting', 'data', 'decorative', 'panel']]
```

**Change in `generic.html` — complete rewrite of the `{% block content %}` section:**

```html
{% block content %}
{% if has_image and image_role == 'panel' %}
{# ── PANEL MODE: 63% text left + 37% image right ── #}
<div class="generic-wrap generic-panel slide-content">
  <div class="panel-left">
    {% if slide.eyebrow %}
      <div class="eyebrow">{{ slide.eyebrow }}</div>
    {% endif %}
    <div class="accent-rule"></div>
    <div class="generic-title">{{ slide.title }}</div>
    {% if slide.subtitle %}
      <div class="generic-subtitle">{{ slide.subtitle }}</div>
    {% endif %}

    <div class="generic-content {{ card_tone }}">
      {{ render_all_blocks(slide, gap='var(--space-lg)') }}
    </div>
  </div>

  <div class="panel-right">
    <img src="{{ image_path }}" class="panel-image" alt=""
         onerror="this.parentElement.classList.add('panel-fallback')">
    <div class="panel-frame"></div>
  </div>
</div>

{% else %}
{# ── EXISTING MODE: full-width content ── #}
<div class="generic-wrap slide-content">
  {% if has_image and image_role == 'decorative' %}
    <img src="{{ image_path }}" class="generic-bg" alt="">
  {% endif %}
  ...existing layout...
</div>
{% endif %}
{% endblock %}
```

**New CSS in `generic.html` `<style>` block:**
```css
/* ── Panel mode ── */
.generic-panel {
  display: flex;
  flex-direction: row;
}
.panel-left {
  width: 63%;
  height: 1080px;
  padding: 70px 80px 80px 120px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  box-sizing: border-box;
  position: relative;
  z-index: 1;
}
.panel-right {
  width: 37%;
  height: 1080px;
  position: relative;
  overflow: hidden;
}
.panel-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center center;
}
/* Subtle inner frame border like the reference's ornamental border */
.panel-frame {
  position: absolute;
  inset: 12px;
  border: 2px solid rgba(var(--primary-rgb), 0.2);
  pointer-events: none;
  z-index: 2;
}
/* Gradient bleed from panel into content zone */
.panel-right::after {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 40px;
  background: linear-gradient(to right, var(--bg), transparent);
  z-index: 3;
}
/* Fallback when image fails to load */
.panel-right.panel-fallback {
  background: linear-gradient(135deg,
    rgba(var(--primary-rgb), 0.15),
    rgba(var(--primary-rgb), 0.05));
}
```

**Templater change in `templater.py`:** Need to pass `card_tone` (from INT-01). Already handled.

**Image generation impact:** When `image_role == 'panel'`, the image should be portrait (see INT-08). But even without that change, a 1920×1080 landscape image in a 37%-width panel with `object-fit: cover` will crop to the centre portion — still usable, just not optimal.

---

### INT-05: Apply panel mode to `infographic.html` and `timeline.html`

These templates currently have **zero image support** (ISS-001). Same panel pattern as INT-04:

```html
{% if has_image and image_role == 'panel' %}
  <!-- Panel mode: content left, image right -->
  <div class="...-panel">
    <div class="panel-left">...infographic content...</div>
    <div class="panel-right">...image...</div>
  </div>
{% else %}
  <!-- existing layout -->
{% endif %}
```

The CSS is identical to INT-04's panel CSS — could be factored into `base.html` or a shared `_panel.html` include.

**Decision:** Factor panel CSS into `base.html` so all templates share it. The panel CSS is generic enough (flexbox, percentage widths, object-fit). Template-specific overrides go in each template's `<style>`.

---

### INT-06: Add semantic card colours to theme palettes

**Current state:** `theme_palettes.py` defines colours like `--bg`, `--primary`, `--text` per palette. No semantic card colours exist.

**New variables to add to every palette in `theme_palettes.py`:**

```python
# For each palette in PALETTES[theme_name][palette_name], add:
'--card-problem':  '...',    # dark card for problem/challenge slides
'--card-action':   '...',    # accent card for CTA/action slides
'--card-positive': '...',    # green/positive card for solution slides
'--text-on-dark':  '...',    # legible text colour for dark cards
```

**Values per theme family:**

| Theme | `--card-problem` | `--card-action` | `--card-positive` | `--text-on-dark` |
|-------|------------------|-----------------|--------------------|--------------------|
| dark_neon | `rgba(0,0,0,0.85)` | `rgba(var(--primary-rgb),0.12)` | `rgba(0,200,120,0.12)` | `#E0E0E0` |
| gradient_flow | `rgba(15,12,41,0.92)` | `rgba(108,99,255,0.18)` | `rgba(0,200,120,0.15)` | `#FFFFFF` |
| editorial | `#2C1810` | `#8B3820` | `#1B5E3B` | `#F5EDD8` |
| aurora | `rgba(8,8,15,0.90)` | `rgba(167,139,250,0.15)` | `rgba(6,182,212,0.12)` | `#F5F3FF` |
| glassmorphism | `rgba(0,0,0,0.65)` | `rgba(var(--primary-rgb),0.15)` | `rgba(16,185,129,0.12)` | `#F0F0F0` |
| corporate_clean | `#1A1A2E` | `rgba(var(--primary-rgb),0.08)` | `rgba(16,185,129,0.08)` | `#FAFAFA` |

**Implementation detail:** The `rgba(var(--primary-rgb), 0.12)` syntax requires `--primary-rgb` to exist. The ThemeResolver already computes this (L146-153). Safe.

**But:** `theme_palettes.py` stores raw CSS value strings. These get injected into `:root { ... }` via base.html L58-60. The `var()` references inside a `var()` definition work in CSS: `:root { --card-action: rgba(var(--primary-rgb), 0.12); }` is valid because the browser resolves `var(--primary-rgb)` at computed-value time, not at parse time.

---

### INT-07: `engagement_prompt` — Mirror Moment CTA card

**Schema change in `schemas.py` — add field to `Slide` (after L183):**
```python
engagement_prompt: Optional[str] = Field(
    default=None,
    description=(
        "A short reflective question for the audience. Max 120 chars. "
        "Connects the slide's content to the viewer's experience."
    )
)
```

**Planner prompt change:** Add to `_SYSTEM_CORE` in `planner.py` (after rule 17):
```
18. ENGAGEMENT PROMPT. For content slides (not cover), add an optional
    "engagement_prompt" — a single reflective question the presenter can
    ask the audience. It should connect the slide content to the viewer's 
    personal experience. Keep under 120 characters.
    Example: "When did you last spend hours just formatting a deck?"
```

**Also add to the JSON schema section:**
```json
      "engagement_prompt": "Optional personal question for audience. Max 120 chars."
```

**Template rendering — add to `_blocks.html` (new macro after L113):**
```html
{% macro mirror_moment(prompt) %}
{% if prompt %}
<div class="mirror-moment">
  <div class="mm-icon">◉</div>
  <div class="mm-body">
    <div class="mm-label">REFLECT</div>
    <div class="mm-text">{{ prompt }}</div>
  </div>
</div>
{% endif %}
{% endmacro %}
```

**Use in `generic.html` — add after the content block, before closing `</div>`:**
```html
    {{ mirror_moment(slide.engagement_prompt) }}
```

**CSS in `base.html` — add after card tone overrides:**
```css
/* ─── Mirror Moment CTA ──────────────────────────────────────────────── */
.mirror-moment {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  background: var(--card-action, rgba(var(--primary-rgb), 0.10));
  border-left: 4px solid var(--primary);
  border-radius: 0 8px 8px 0;
  padding: 16px 24px;
  margin-top: auto;   /* push to bottom of flex column */
  max-width: 1000px;
}
.mm-icon {
  font-size: 18px;
  color: var(--primary);
  flex-shrink: 0;
  margin-top: 2px;
}
.mm-label {
  font-size: 11px;
  letter-spacing: 0.18em;
  font-weight: 700;
  color: var(--primary);
  margin-bottom: 4px;
}
.mm-text {
  font-size: 16px;
  font-style: italic;
  color: var(--text);
  opacity: 0.8;
  line-height: 1.5;
}
```

**PPTX exporter:** The `engagement_prompt` text should also appear as a text box in the PPTX. Add to `pptx_exporter.py` — a new text box at the bottom of the slide in a distinct colour.

---

### INT-08: Portrait-ratio image generation for panel mode

**Current state:** `image_generator.py` L419: `"Dimensions: 1920 x 1080px (16:9 landscape)"` — hardcoded. And `gradient_generator.py` L16-17: `WIDTH = 1920; HEIGHT = 1080` — hardcoded.

**When `image_role == 'panel'`, we need ~900×1080 (portrait ~5:6).**

**Change in `image_generator.py` — define size map:**
```python
IMAGE_DIMENSIONS = {
    'background':  (1920, 1080),   # full-bleed landscape
    'panel':       (900, 1080),    # portrait for right-side panel
    'supporting':  (1920, 1080),   # landscape (existing split template)
    'data':        (1920, 1080),
    'decorative':  (1920, 1080),
}
```

**Change in `_build_prompt_entry` (L419):**
```python
# CURRENT:
f"  - Dimensions: 1920 x 1080px (16:9 landscape)",

# NEW:
dims = IMAGE_DIMENSIONS.get(image_role, (1920, 1080))
orientation = "portrait (taller than wide)" if dims[0] < dims[1] else "landscape (wider than tall)"
f"  - Dimensions: {dims[0]} x {dims[1]}px ({orientation})",
```

**Change in `gradient_generator.py` — make dimensions parametric:**
```python
# CURRENT:
WIDTH  = 1920
HEIGHT = 1080

# NEW: accept target_size parameter
def generate(self, structural_class, primary_hex, out_path, seed=0, target_size=None):
    width, height = target_size or (1920, 1080)
    img = Image.new('RGB', (width, height))
    ...
```

**Change in `image_generator.py` `_generate_gradient` (L322-336):**
```python
# Pass target_size based on image_role
dims = IMAGE_DIMENSIONS.get(image_role, (1920, 1080))
self._gradient_gen.generate(
    structural_class=structural_class,
    primary_hex=primary_color or None,
    out_path=out_path,
    seed=seed,
    target_size=dims,
)
```

**The API call (`_generate_with_api`):** The Gemini image API generates images at its own resolution. The prompt text already includes dimensions — the API will try to respect them but may not exactly. The generated image is then used with `object-fit: cover` in the template, so aspect ratio mismatches are handled by CSS cropping. This is acceptable.

---

### INT-09: Force `requires_image=True` in planner for all content slides

**Current state:** The planner sometimes sets `requires_image=False` for content slides (5 of 12 in the test plan). This means the slide has no visual material.

**Two approaches:**

**Option A — Fix in planner prompt:** Add to system prompt rules:
```
19. IMAGE REQUIREMENT. Set requires_image=true for EVERY slide except 
    'quote' layout (which uses CSS decoration). Every slide deserves 
    visual material. Set image_role to 'panel' for generic, infographic, 
    timeline, stat layouts. Set it to 'background' for cover. Set it to 
    'supporting' for split.
```

**Option B — Fix in validator/post-processing:** In `cli.py` or `validator.py`, force the field:
```python
# After master_plan is loaded/generated:
for slide in master_plan.slides:
    if slide.layout_type != 'quote' and not slide.requires_image:
        slide.requires_image = True
        slide.image_role = slide.image_role or 'panel'
        if not slide.image_prompt:
            slide.image_prompt = f"Editorial illustration related to: {slide.title}. Warm tones, no text."
```

**Recommendation:** Do BOTH. The prompt guides the AI to generate good `image_prompt` text. The post-processing catches any that slip through. Option B goes in `validator.py`'s `validate_and_prune()` method.

---

### INT-10: Better image prompt engineering

**Current output from planner:**
```json
"image_prompt": "Abstract digital landscape with soft blue gradients and floating geometric shapes"
```

**Target output:**
```json
"image_prompt": "Editorial illustration of a team reviewing a digital dashboard, warm amber and teal palette, flat design style with fine details, vertical composition for right-side panel, center of frame clear. No text, logos, or watermarks."
```

**Change in planner system prompt rule 15:**
```
15. IMAGE PROMPTS. When requires_image=true, write a SPECIFIC, CINEMATIC prompt:
    MUST include all 6 elements:
    a) Subject: what is depicted (people, objects, scene) — concrete, not abstract
    b) Style: "editorial illustration" | "watercolor" | "photorealistic" | "flat design"
    c) Palette: specific colours matching the theme mood
    d) Composition: "vertical/portrait for right-side panel" or "landscape, center clear"
    e) Detail level: "fine linework" | "bold shapes" | "textured brush strokes"
    f) Exclusions: "No text, logos, watermarks, or UI elements."

    BAD: "Abstract background."
    GOOD: "Editorial illustration of a factory floor with robotic arms assembling 
           electronics, warm amber highlights against steel grey, fine linework, 
           portrait composition for panel. No text or logos."
```

---

### INT-11: New theme `editorial_warm` (closest to reference aesthetic)

**The reference uses:** parchment `#F5EDD8`, deep brown `#2C1810`, rust `#C4531F`, forest green `#1B5E3B`.

This doesn't match any existing theme. The `editorial` theme has palette options (navy, crimson, forest, terracotta, slate, mustard) but none match the warm parchment look.

**Add to `theme_palettes.py`:**
```python
# In PALETTES['editorial']:
'parchment': {
    '--bg':              '#F5EDD8',
    '--bg-rgb':          '245,237,216',
    '--primary':         '#C4531F',
    '--primary-rgb':     '196,83,31',
    '--text':            '#2C1810',
    '--text-secondary':  '#6B4A35',
    '--card-problem':    '#2C1810',
    '--card-action':     '#8B3820',
    '--card-positive':   '#1B5E3B',
    '--text-on-dark':    '#F5EDD8',
},
```

**Add to `schemas.py` structural_class Literal:** No change needed — `editorial` already exists, this is just a new palette.

**Add to `GRADIENT_FALLBACK_PRESETS` in `theme_palettes.py`:** Add parchment-toned gradient presets for the editorial theme to ensure offline gradient images match the warm palette.

---

### INT-12: Comparison layout semantic colouring (Two Futures)

The reference's slide 13 uses two columns: near-black (negative) vs forest green (positive), with an "or" badge at the centre.

**Current `ComparisonBlock` rendering in `_blocks.html` L34-52:**
Both columns use `background: var(--card-bg)` — same colour.

**Change — apply semantic colours to comparison columns:**
```html
{% elif block.block_type == 'comparison' %}
<div class="block-comparison">
  <div class="comparison-col comparison-col--left">
    <div class="comparison-col-label">{{ block.left_label }}</div>
    ...
  </div>
  <div class="comparison-col comparison-col--right">
    <div class="comparison-col-label" style="color:var(--primary)">{{ block.right_label }}</div>
    ...
  </div>
</div>
```

**New CSS in `base.html`:**
```css
/* Semantic comparison columns — problem vs solution */
body.tone-problem .comparison-col--left {
  background: var(--card-problem, rgba(0,0,0,0.80));
  color: var(--text-on-dark, #F0F0F0);
}
body.tone-problem .comparison-col--right {
  background: var(--card-positive, rgba(0,200,100,0.10));
}
body.tone-problem .comparison-col--left .comparison-col-label {
  color: var(--text-on-dark, #F0F0F0);
  border-bottom-color: rgba(255,255,255,0.2);
}
```

This automatically fires when the slide has `slide_purpose = "problem_statement"` (via INT-01 setting `body.tone-problem`).

---

## Part 3: Dependency Graph

```
INT-01 (card_tone)  ←── INT-06 (palette vars) ←── INT-11 (parchment palette)
   ↓                       ↑
INT-12 (comparison)    INT-04 (panel layout) ←── INT-08 (portrait images)
                           ↓
                       INT-05 (infographic/timeline panels)
                       
INT-02 (footer)      — independent
INT-03 (eyebrow)     — independent
INT-07 (mirror moment) ←── planner schema change
INT-09 (force images)  — independent (validator post-processing)
INT-10 (prompt eng.)   — independent (planner prompt text)
```

**Safe parallelisation:**
- **Group A (independent):** INT-02, INT-03, INT-09, INT-10 — can all be done simultaneously
- **Group B (palette + wiring):** INT-06 first, then INT-01, then INT-12
- **Group C (templates):** INT-04 first (generic panel), then INT-05 (infographic/timeline panels)
- **Group D (schema):** INT-07 (engagement_prompt), INT-08 (portrait images), INT-11 (parchment palette)

---

## Part 4: Execution Sequence

```
Day 1 — Zero-risk CSS/template changes (Group A)
  ✅ INT-02  Dynamic footer text                      → base.html L543 (1 line)
  ✅ INT-03  Eyebrow accent rule ::before              → base.html L81-89 (10 lines CSS)
  ✅ INT-09  Force requires_image in validator          → validator.py (5 lines Python)
  ✅ INT-10  Better image prompts in planner prompt     → planner.py _SYSTEM_CORE (20 lines text)
  
  VERIFY: Run pipeline, check footer renders, eyebrow has line mark, all slides get images

Day 2 — Semantic colour system (Group B)
  ✅ INT-06  Add semantic vars to all palettes          → theme_palettes.py (add 4 vars × ~15 palettes)
  ✅ INT-01  Pass card_tone to templates, body class    → templater.py (8 lines), base.html (35 lines CSS)
  ✅ INT-12  Comparison columns get semantic colours     → _blocks.html + base.html CSS

  VERIFY: Run pipeline on editorial theme, problem slides should have dark cards

Day 3 — Panel layout (Group C) — highest visual impact
  ✅ INT-04  Right-panel mode in generic.html           → generic.html (60 lines HTML/CSS)
  ✅ INT-05  Right-panel mode in infographic/timeline   → 2 templates (similar pattern)
  ✅ schemas.py: add 'panel' to image_role Literal

  VERIFY: Run pipeline, generic slides should show 63/37 split with image on right

Day 4 — Schema + engagement + images (Group D)
  ✅ INT-07  engagement_prompt field + mirror moment    → schemas.py, planner.py, _blocks.html, base.html
  ✅ INT-08  Portrait image dimensions for panel         → image_generator.py, gradient_generator.py
  ✅ INT-11  editorial/parchment palette                 → theme_palettes.py

  VERIFY: Full pipeline run with editorial/parchment theme, check mirror moment renders
```

---

## Part 5: What Could Go Wrong (and mitigations)

### 5A. Panel layout breaks on slides with too much content

If a slide has 5+ bullet items + a subtitle + an engagement prompt, the 63% panel-left won't fit at 1080px height. The content will overflow.

**Mitigation:**
- Add `overflow: hidden` to `.panel-left` (already standard)
- The planner prompt already limits bullets to 5 items max (rule 6)
- Add a content scoring check: if `narrative_weight == 'heavy'`, force `image_role = 'decorative'` instead of `'panel'` — heavy slides use full width

### 5B. Semantic card colours clash with theme-specific card overrides

`body.glassmorphism` sets `--card-bg: rgba(255,255,255,0.12)` with `backdrop-filter: blur(16px)`. If `body.tone-problem` then overrides `background: var(--card-problem)`, the blur might create unexpected visual results on a solid dark card.

**Mitigation:**
- For `body.glassmorphism.tone-problem`, explicitly set `backdrop-filter: none` on the dark card
- Dark solid cards don't need the glass effect — they ARE the visual contrast

### 5C. Portrait image generation may look cropped when API returns landscape

The API might ignore the portrait dimension request and return a 1024×1024 or 1920×1080 image. The CSS `object-fit: cover` on the panel will crop it.

**Mitigation:**
- This is acceptable — cropped landscape still looks better than no image
- The gradient fallback generator WILL respect the target size (it's procedural)
- Add to the API prompt: "IMPORTANT: Generate in portrait orientation (taller than wide)"

### 5D. Engagement prompts may be empty for existing cached plans

If using `--offline-plan master_plan.json`, the existing plan won't have `engagement_prompt` fields. The Pydantic schema defaults it to `None`, so the template's `{% if prompt %}` guard handles this gracefully. No breakage.

### 5E. PPTX exporter needs updating for panel layout

The PPTX exporter uses `LAYOUT_POSITIONS` with hardcoded text box positions per layout type. With panel mode, the text boxes should be confined to the left 63% of the slide.

**Mitigation:**
- Add a `'generic_panel'` key to `LAYOUT_POSITIONS` with positions in the left 63%
- Check `image_role` in the exporter to decide which position set to use

---

## Part 6: Expected Quality Trajectory

After each day's changes, expected Q-score improvement:

| After | Changes | Expected Avg Q | Why |
|-------|---------|---------------|-----|
| Baseline | None | 31 | Current state |
| Day 1 | Footer, eyebrow rule, more images, better prompts | 38–42 | More slides have images, slightly richer pixel mass |
| Day 2 | Semantic card colours | 48–55 | Dark cards on problem slides add huge pixel variation |
| Day 3 | **Panel layout** | **65–78** | Portrait images fill 37% of slide with rich content |
| Day 4 | Mirror moment, portrait images, parchment theme | 75–85 | Amber CTA card, better image composition, warm palette |

**The inflection point is Day 3.** Panel layout is the single largest source of visual richness in the reference PDF. It converts 37% of the slide from flat CSS background colour to a photographic/illustrated image — which is exactly what drives the std_dev from 10 to 74.6.

---

## Part 7: The Fundamental Limit

Even after all 12 interventions, our pipeline will not reach Q=100 consistently. The reference achieves Q=100 because every image is a **purpose-made narrative illustration** in a unified visual style. Our pipeline generates images from text prompts, which means:

1. **Style consistency across slides** — each API call may return a different visual style. The reference has one art director maintaining one style. We'd need style-reference-image-guided generation or a LoRA.

2. **Cultural resonance** — the reference's images are deeply tied to Indian heritage aesthetics (Madhubani, miniature painting, folk art). A generic "editorial illustration" prompt won't produce this.

3. **Compositional awareness** — the reference's images are composed specifically for the right panel (subject in the centre, ornamental border frame). API-generated images have random composition.

**Strategies to close this gap (beyond the 12 interventions):**

| Strategy | Effort | Impact | Feasibility |
|----------|--------|--------|-------------|
| Style reference image in API prompt | Low | Medium | Gemini supports image-conditioned generation |
| Curated asset library per theme | Medium | High | Pre-generate 20-30 illustrations per theme |
| `image_override_path` field in schema | Low | High for specific decks | Let user drop in custom images |
| Fine-tuned LoRA for illustration style | High | Very High | Requires training pipeline |
| Post-generation style transfer | Medium | Medium | Apply art style filter to API output |

The most practical near-term strategy: **curated asset library** — for the `editorial/parchment` theme, pre-generate 20 heritage-style illustrations covering common topics (education, environment, family, governance, technology), stored in `assets/library/editorial/`. The planner selects from these by topic match rather than generating from scratch.
