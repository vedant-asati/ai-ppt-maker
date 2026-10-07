# Implementation Plan v4 — Premium Themes + Full QA Pipeline
## Complete, Exhaustive, Edge-Case-Aware

---

## 0. What Changes and Why

### Root problems being solved
| Problem | Root Cause | Fix |
|---------|-----------|-----|
| Themes feel AI-generated | AI picking arbitrary hex values | Curated palette library; AI only picks a name |
| No design feedback loop | Pipeline is fire-and-forget | 3-layer QA audit after every render |
| Cross-theme rendering breakage | CSS doesn't handle all layout × theme combos | Explicit 16-combination matrix coverage |
| Font failure in offline env | Google Fonts CDN loaded at render time | Font download at `init`; local `@font-face` fallback |
| Config typos silently ignored | Pure dict access on raw YAML | Pydantic `AppConfig` validation |
| Planner generates monotone decks | No inter-slide variety rules | Explicit layout-sequencing rules in system prompt |
| No way to verify visual quality | Pipeline has no introspection | Quality checker with DOM, PIL, and AI critic layers |

---

## 1. Config Validation — Pydantic `AppConfig`

**Current problem:** `config.get('key')` throughout codebase — any typo in YAML is silently ignored. User writes `audiences:` instead of `audience:` and gets wrong AI output with zero warning.

**Fix:** Replace raw dict with a validated `AppConfig` Pydantic model in `config_manager.py`.

```python
# config_manager.py — new AppConfig classes

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal

VALID_THEMES = Literal[
    'minimalist', 'glassmorphism', 'neo_brutalism', 'corporate_clean',
    'dark_neon', 'gradient_flow', 'editorial', 'aurora'
]

class PresentationGoals(BaseModel):
    audience: str = "General"
    duration_minutes: int = Field(default=10, ge=1, le=120)
    slide_count: Optional[int] = Field(default=None, ge=1, le=50)
    tone: Literal['professional', 'casual', 'academic', 'inspirational', 'humorous'] = 'professional'
    language: str = "English"
    call_to_action: Optional[str] = None

class DesignPreferences(BaseModel):
    theme_style: VALID_THEMES = 'corporate_clean'
    palette: Optional[str] = None       # explicit palette override (e.g. "cyber_cyan")
    primary_color: Optional[str] = Field(default=None, pattern=r'^#[0-9A-Fa-f]{6}$')
    font_size_scale: float = Field(default=1.0, ge=0.5, le=2.0)
    color_mode: Literal['auto', 'dark', 'light'] = 'auto'

class ImagePreferences(BaseModel):
    art_style: str = "realistic photography"
    generate_images: bool = True        # set false to skip image generation entirely

class OutputConfig(BaseModel):
    pdf_filename: str = "presentation.pdf"
    output_dir: str = "."
    export_speaker_notes: bool = True
    speaker_notes_filename: Optional[str] = None  # auto-derived if None

class PipelineConfig(BaseModel):
    preview_mode: bool = False          # render at 960×540, first 3 slides only
    audit_level: Literal['none', 'quick', 'full', 'ai'] = 'none'
    force_regenerate_images: bool = False
    skip_image_generation: bool = False
    renderer_timeout_ms: int = Field(default=15000, ge=5000, le=60000)

class AppConfig(BaseModel):
    source_text: Optional[str] = None
    source_file: Optional[str] = None
    presentation_goals: PresentationGoals = PresentationGoals()
    design_preferences: DesignPreferences = DesignPreferences()
    image_preferences: ImagePreferences = ImagePreferences()
    output: OutputConfig = OutputConfig()
    pipeline: PipelineConfig = PipelineConfig()
```

`ConfigManager.load_and_validate()` now returns a typed `AppConfig` object, not a raw dict. All downstream code uses `config.design_preferences.theme_style` instead of `config.get('design_preferences', {}).get('theme_style')`.

**Migration:** Update all call sites — `cli.py`, `planner.py`, `image_generator.py` etc. to use attribute access on `AppConfig`.

**Edge cases handled:**
- `tone: "aggressive"` → Pydantic ValidationError: "'aggressive' is not a valid tone"
- `primary_color: "blue"` → Pydantic ValidationError: "must match `#RRGGBB` format"
- `duration_minutes: -5` → Pydantic ValidationError: "must be ≥ 1"
- Missing required sections → defaults kick in, no crash

---

## 2. Curated Palette Library (`theme_palettes.py`)

### Full palette definition

```python
# theme_palettes.py

PALETTES = {
    "dark_neon": {
        "cyber_cyan":    {"--primary": "#00FFD1", "--primary-rgb": "0,255,209",
                          "--text": "#F0F0F0", "--text-secondary": "#888888", "--bg": "#050505"},
        "neon_magenta":  {"--primary": "#FF2D78", "--primary-rgb": "255,45,120",
                          "--text": "#F0F0F0", "--text-secondary": "#888888", "--bg": "#050505"},
        "electric_blue": {"--primary": "#00B4FF", "--primary-rgb": "0,180,255",
                          "--text": "#F0F0F0", "--text-secondary": "#777777", "--bg": "#040810"},
        "acid_lime":     {"--primary": "#AAFF00", "--primary-rgb": "170,255,0",
                          "--text": "#E8E8E8", "--text-secondary": "#666666", "--bg": "#050505"},
        "solar_orange":  {"--primary": "#FF6B00", "--primary-rgb": "255,107,0",
                          "--text": "#F0F0F0", "--text-secondary": "#888888", "--bg": "#080400"},
    },
    "gradient_flow": {
        "violet_sunset": {"--bg": "#0F0C29", "--bg-end": "#302B63",
                          "--primary": "#6C63FF", "--primary-rgb": "108,99,255",
                          "--text": "#FFFFFF", "--text-secondary": "rgba(255,255,255,0.65)"},
        "ocean_depth":   {"--bg": "#0D1B2A", "--bg-end": "#1B4F72",
                          "--primary": "#00C9FF", "--primary-rgb": "0,201,255",
                          "--text": "#FFFFFF", "--text-secondary": "rgba(255,255,255,0.65)"},
        "forest_dusk":   {"--bg": "#0B2027", "--bg-end": "#1B4332",
                          "--primary": "#40C9A2", "--primary-rgb": "64,201,162",
                          "--text": "#FFFFFF", "--text-secondary": "rgba(255,255,255,0.65)"},
        "ember_night":   {"--bg": "#1A0A00", "--bg-end": "#3D1C00",
                          "--primary": "#FF6B35", "--primary-rgb": "255,107,53",
                          "--text": "#FFFFFF", "--text-secondary": "rgba(255,255,255,0.65)"},
    },
    "editorial": {
        "crimson":    {"--primary": "#C0392B", "--primary-rgb": "192,57,43",
                       "--bg": "#F9F6F1", "--text": "#111111", "--text-secondary": "#555555"},
        "navy":       {"--primary": "#1A3A5C", "--primary-rgb": "26,58,92",
                       "--bg": "#F9F6F1", "--text": "#111111", "--text-secondary": "#555555"},
        "forest":     {"--primary": "#1E6B3C", "--primary-rgb": "30,107,60",
                       "--bg": "#F8F7F2", "--text": "#111111", "--text-secondary": "#555555"},
        "terracotta": {"--primary": "#CB4335", "--primary-rgb": "203,67,53",
                       "--bg": "#FAF6F0", "--text": "#1A0E0E", "--text-secondary": "#5A4A4A"},
        "slate":      {"--primary": "#2C3E50", "--primary-rgb": "44,62,80",
                       "--bg": "#F5F5F5", "--text": "#111111", "--text-secondary": "#555555"},
        "mustard":    {"--primary": "#B7950B", "--primary-rgb": "183,149,11",
                       "--bg": "#FAF8F0", "--text": "#1A1500", "--text-secondary": "#5A5230"},
    },
    "aurora": {
        "cosmic":    {"--aurora-1": "#6366F1", "--aurora-1-rgb": "99,102,241",
                      "--aurora-2": "#EC4899", "--aurora-2-rgb": "236,72,153",
                      "--primary": "#6366F1", "--text": "#FAFAFA",
                      "--text-secondary": "rgba(250,250,250,0.65)", "--bg": "#08080F"},
        "arctic":    {"--aurora-1": "#06B6D4", "--aurora-1-rgb": "6,182,212",
                      "--aurora-2": "#8B5CF6", "--aurora-2-rgb": "139,92,246",
                      "--primary": "#06B6D4", "--text": "#FAFAFA",
                      "--text-secondary": "rgba(250,250,250,0.65)", "--bg": "#05080F"},
        "wildfire":  {"--aurora-1": "#F59E0B", "--aurora-1-rgb": "245,158,11",
                      "--aurora-2": "#EF4444", "--aurora-2-rgb": "239,68,68",
                      "--primary": "#F59E0B", "--text": "#FAFAFA",
                      "--text-secondary": "rgba(250,250,250,0.65)", "--bg": "#0F0800"},
        "bio":       {"--aurora-1": "#10B981", "--aurora-1-rgb": "16,185,129",
                      "--aurora-2": "#3B82F6", "--aurora-2-rgb": "59,130,246",
                      "--primary": "#10B981", "--text": "#FAFAFA",
                      "--text-secondary": "rgba(250,250,250,0.65)", "--bg": "#040C08"},
    },
}

# Default palette per theme if AI doesn't specify or specifies invalid name
DEFAULT_PALETTE = {
    "dark_neon": "cyber_cyan",
    "gradient_flow": "violet_sunset",
    "editorial": "navy",
    "aurora": "cosmic",
}

# Whether a theme is dark (for audit threshold selection)
DARK_THEMES = {"dark_neon", "gradient_flow", "aurora", "glassmorphism", "neo_brutalism"}
LIGHT_THEMES = {"editorial", "corporate_clean", "minimalist"}
```

---

## 3. `ThemeResolver` — The Critical Bridge

This module sits between Planner output and Template rendering. It is the single place that handles all theme edge cases.

```python
# theme_resolver.py

import re
import math
from theme_palettes import PALETTES, DEFAULT_PALETTE, DARK_THEMES

class ThemeResolver:

    @staticmethod
    def hex_to_rgb(hex_color: str) -> tuple:
        h = hex_color.lstrip('#')
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    @staticmethod
    def rgb_to_str(rgb: tuple) -> str:
        return f"{rgb[0]},{rgb[1]},{rgb[2]}"

    @staticmethod
    def color_distance(c1: tuple, c2: tuple) -> float:
        """Perceptually weighted RGB distance (approximation of CIEDE2000)."""
        dr, dg, db = c1[0]-c2[0], c1[1]-c2[1], c1[2]-c2[2]
        return math.sqrt(2*dr**2 + 4*dg**2 + 3*db**2)

    @staticmethod
    def darken(hex_color: str, amount: float = 0.3) -> str:
        """Darken a hex color by [amount] (0.0–1.0)."""
        r, g, b = ThemeResolver.hex_to_rgb(hex_color)
        r = int(r * (1 - amount))
        g = int(g * (1 - amount))
        b = int(b * (1 - amount))
        return f"#{r:02X}{g:02X}{b:02X}"

    @classmethod
    def find_nearest_palette(cls, theme: str, user_hex: str) -> str:
        """Snap user's color to the nearest palette primary color."""
        user_rgb = cls.hex_to_rgb(user_hex)
        best, best_dist = DEFAULT_PALETTE[theme], float('inf')
        for name, vars in PALETTES.get(theme, {}).items():
            if '--primary' in vars:
                dist = cls.color_distance(user_rgb, cls.hex_to_rgb(vars['--primary']))
                if dist < best_dist:
                    best_dist, best = dist, name
        return best

    @classmethod
    def resolve(cls, structural_class: str, palette_name: str,
                ai_css_vars: dict, user_color: str = None) -> dict:
        """
        Merge palette + AI vars + user overrides into a final css_variables dict.

        Priority (highest wins):
          1. User's explicit primary_color in config → overrides --primary
          2. Curated palette for this theme
          3. AI-generated css_variables (used for themes without palette library)
        """
        # 1. Get palette variables (or default if AI picked an invalid name)
        theme_palettes = PALETTES.get(structural_class, {})
        if palette_name not in theme_palettes:
            palette_name = DEFAULT_PALETTE.get(structural_class, next(iter(theme_palettes), None))

        palette_vars = theme_palettes.get(palette_name, {}).copy() if palette_name else {}

        # 2. Start with AI-generated vars (for base vars not in palette)
        merged = {**ai_css_vars, **palette_vars}

        # 3. Apply user's color override
        if user_color:
            merged['--primary'] = user_color

        # 4. Auto-compute missing RGB variants
        for var in ['--primary', '--aurora-1', '--aurora-2']:
            rgb_var = f"{var}-rgb"
            if var in merged and rgb_var not in merged:
                try:
                    merged[rgb_var] = cls.rgb_to_str(cls.hex_to_rgb(merged[var]))
                except (ValueError, KeyError):
                    pass

        # 5. gradient_flow: compute --bg-end if missing
        if structural_class == 'gradient_flow' and '--bg-end' not in merged:
            bg = merged.get('--bg', '#0F0C29')
            merged['--bg-end'] = cls.darken(bg, 0.2)

        # 6. Validate aurora color distance (must be visually distinct)
        if structural_class == 'aurora':
            if '--aurora-1' in merged and '--aurora-2' in merged:
                dist = cls.color_distance(
                    cls.hex_to_rgb(merged['--aurora-1']),
                    cls.hex_to_rgb(merged['--aurora-2'])
                )
                if dist < 80:  # Too similar — swap to default
                    print(f"  [Warning] aurora-1 and aurora-2 are too similar (dist={dist:.0f}). "
                          f"Using default cosmic palette.")
                    merged.update(PALETTES['aurora']['cosmic'])

        # 7. editorial: validate primary vs bg contrast (decorative min 3:1)
        if structural_class == 'editorial' and '--primary' in merged and '--bg' in merged:
            # Simple luminance check
            pr, pg, pb = cls.hex_to_rgb(merged['--primary'])
            br, bg_b, bb = cls.hex_to_rgb(merged.get('--bg', '#F9F6F1'))
            lum_p = (0.299*pr + 0.587*pg + 0.114*pb) / 255
            lum_b = (0.299*br + 0.587*bg_b + 0.114*bb) / 255
            ratio = (max(lum_p, lum_b) + 0.05) / (min(lum_p, lum_b) + 0.05)
            if ratio < 3.0:
                print(f"  [Warning] editorial primary color has low contrast ({ratio:.1f}:1 vs bg). "
                      f"Falling back to navy palette.")
                merged.update(PALETTES['editorial']['navy'])

        return merged, palette_name
```

**Integration point:** Called in `cli.py` right after the Planner returns (and after validator), before templating:
```python
from theme_resolver import ThemeResolver
resolved_vars, resolved_palette = ThemeResolver.resolve(
    structural_class=master_plan.theme.structural_class,
    palette_name=master_plan.theme.palette,       # new field from schema
    ai_css_vars=master_plan.theme.css_variables,
    user_color=config.design_preferences.primary_color
)
master_plan.theme.css_variables = resolved_vars
master_plan.theme.palette = resolved_palette      # store resolved palette name
```

The enriched `master_plan` (with resolved CSS variables) is what gets saved to `master_plan.json` in dry-run mode — so `--offline-plan` gets the correct variables already baked in.

---

## 4. `schemas.py` — Extended

```python
class Theme(BaseModel):
    css_variables: dict[str, str]
    structural_class: Literal[
        'minimalist', 'glassmorphism', 'neo_brutalism', 'corporate_clean',
        'dark_neon', 'gradient_flow', 'editorial', 'aurora'
    ]
    palette: Optional[str] = None   # e.g. "cyber_cyan", resolved by ThemeResolver

class Slide(BaseModel):
    slide_number: int
    layout_type: Literal['cover', 'split', 'infographic', 'generic']
    layout_variant: Optional[Literal['reverse']] = None  # split layout: image on left
    title: str
    subtitle: Optional[str] = Field(default="")
    content_bullets: List[str]
    speaker_notes: str
    requires_image: bool
    image_prompt: Optional[str] = Field(default="")
```

`layout_variant: 'reverse'` allows the Planner to flip a split layout (image-left, text-right) for visual variety. The CSS handles it with `flex-direction: row-reverse`.

---

## 5. Design Token System — `base.html`

### Spacing & Type Tokens

```css
:root {
  /* Spacing scale — 8px base unit */
  --sp-1: 8px;    --sp-2: 16px;   --sp-3: 24px;   --sp-4: 32px;
  --sp-5: 48px;   --sp-6: 64px;   --sp-7: 96px;   --sp-8: 128px;
  --sp-9: 192px;

  /* Type scale — augmented fourth (×1.414) */
  --type-xs:  18px;   /* footer, captions */
  --type-sm:  24px;   /* body text */
  --type-md:  32px;   /* bullets */
  --type-lg:  48px;   /* subtitles */
  --type-xl:  64px;   /* slide titles (generic, split) */
  --type-2xl: 88px;   /* infographic heading */
  --type-3xl: 120px;  /* cover title */

  /* Theme structural variables — EVERY theme must define these */
  --card-bg:       transparent;
  --card-shadow:   none;
  --card-radius:   0px;
  --card-border:   none;
  --card-backdrop: none;
  --rule-color:    var(--primary);
  --rule-shadow:   none;
  --glow:          none;   /* neon/aurora themes override this */
  --title-glow:    none;
  --text-glow:     none;
}
```

### Theme Classes

#### `dark_neon`
```css
body.dark_neon {
  background-color: var(--bg, #050505);
  --card-bg:       rgba(255, 255, 255, 0.03);
  --card-shadow:   0 0 0 1px var(--primary), 0 0 30px -8px var(--primary);
  --card-radius:   4px;
  --card-border:   1px solid var(--primary);
  --card-backdrop: none;
  --glow:          0 0 8px var(--primary), 0 0 20px var(--primary);
  --title-glow:    0 0 20px rgba(var(--primary-rgb, 0,255,209), 0.35);
  --text-glow:     0 0 10px rgba(var(--primary-rgb, 0,255,209), 0.4);
}
/* footer/page-num glow */
body.dark_neon .footer,
body.dark_neon .page-num {
  color: var(--primary);
  opacity: 0.85;
  text-shadow: var(--text-glow);
}
/* Per-layout title glow */
body.dark_neon .cover-title,
body.dark_neon .generic-title,
body.dark_neon .split-title,
body.dark_neon .info-title {
  text-shadow: var(--title-glow);
  font-family: 'Space Grotesk', sans-serif;
}
/* Neon bullet markers */
body.dark_neon .generic-content li::before,
body.dark_neon .split-content li::before {
  content: "›";
  font-size: var(--type-lg);
  top: -12px;
  text-shadow: var(--glow);
}
/* Infographic number glow */
body.dark_neon .info-number {
  text-shadow: var(--title-glow);
}
```

#### `gradient_flow`
```css
body.gradient_flow {
  background: linear-gradient(135deg, var(--bg, #0F0C29) 0%, var(--bg-end, #302B63) 100%);
  --card-bg:       rgba(255, 255, 255, 0.07);
  --card-shadow:   0 8px 40px rgba(0, 0, 0, 0.4);
  --card-radius:   20px;
  --card-border:   1px solid rgba(255, 255, 255, 0.10);
  --card-backdrop: blur(20px) saturate(180%);
}
/* Gradient clip titles — with safe fallback */
body.gradient_flow .cover-title,
body.gradient_flow .generic-title,
body.gradient_flow .split-title {
  color: var(--text, #FFFFFF);                    /* fallback if clip fails */
  background: linear-gradient(90deg, #FFFFFF 0%, var(--primary) 100%);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  font-family: 'Plus Jakarta Sans', sans-serif;
}
/* Bullet pill markers */
body.gradient_flow .generic-content li::before,
body.gradient_flow .split-content li::before {
  content: "●";
  font-size: 22px;
  top: 4px;
  color: var(--primary);
}
body.gradient_flow .footer,
body.gradient_flow .page-num {
  color: rgba(255, 255, 255, 0.5);
}
```

#### `editorial`
```css
body.editorial {
  background-color: var(--bg, #F9F6F1);
  --card-bg:       transparent;
  --card-shadow:   none;
  --card-radius:   0px;
  --card-border:   none;
  --card-backdrop: none;
}
/* Typography blown up for editorial impact */
body.editorial .cover-title,
body.editorial .generic-title,
body.editorial .split-title { font-family: 'Playfair Display', serif; }
body.editorial .generic-title { font-size: 88px; letter-spacing: -0.02em; line-height: 1.05; }
body.editorial .cover-title  { font-size: 120px; letter-spacing: -0.03em; line-height: 1.0; }
body.editorial .split-title  { font-size: 68px; letter-spacing: -0.02em; }

/* Ghost giant numbers for infographic */
body.editorial .info-number {
  font-size: 128px;
  letter-spacing: -0.04em;
  color: var(--primary);
  opacity: 0.12;  /* ghost effect */
  position: absolute;
  top: -30px;
  right: 20px;
  font-family: 'Playfair Display', serif;
  pointer-events: none;
  user-select: none;
}
/* Actual label number */
body.editorial .info-card { position: relative; overflow: hidden; }
body.editorial .info-label {
  font-size: var(--type-sm);
  font-weight: 600;
  color: var(--primary);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-bottom: var(--sp-2);
  font-family: 'IBM Plex Sans', sans-serif;
}

/* Vertical rule bar — replaces horizontal rule via ::before on title */
body.editorial .generic-rule,
body.editorial .split-rule,
body.editorial .info-rule,
body.editorial .cover-rule { display: none; }   /* hide horizontal rules */

body.editorial .generic-title::before,
body.editorial .cover-title::before,
body.editorial .split-title::before,
body.editorial .info-title::before {
  content: '';
  display: block;
  width: 5px;
  height: 72px;
  background: var(--primary);
  margin-bottom: var(--sp-3);
}

/* Editorial bullets: em-dash */
body.editorial .generic-content li::before,
body.editorial .split-content li::before {
  content: "—";
  color: var(--primary);
  font-weight: 700;
  font-size: var(--type-md);
  top: 0;
  left: 0;
}
body.editorial .footer,
body.editorial .page-num { color: #AAAAAA; }
```

#### `aurora`
```css
body.aurora {
  background-color: var(--bg, #08080F);
  --card-bg:       rgba(255, 255, 255, 0.04);
  --card-shadow:   0 1px 40px rgba(0, 0, 0, 0.6);
  --card-radius:   16px;
  --card-border:   1px solid rgba(255, 255, 255, 0.07);
  --card-backdrop: blur(24px) saturate(200%);
}

/* Aurora shimmer — CSS only, no images, no external resources */
body.aurora::before {
  content: '';
  position: absolute;   /* NOT fixed — absolute works correctly in Playwright */
  inset: 0;
  background:
    radial-gradient(ellipse 80% 60% at 15% 40%,
      rgba(var(--aurora-1-rgb, 99,102,241), 0.18) 0%, transparent 65%),
    radial-gradient(ellipse 60% 80% at 85% 25%,
      rgba(var(--aurora-2-rgb, 236,72,153), 0.14) 0%, transparent 65%),
    radial-gradient(ellipse 40% 40% at 50% 85%,
      rgba(var(--aurora-1-rgb, 99,102,241), 0.07) 0%, transparent 60%);
  pointer-events: none;
  z-index: 0;
}
/* All direct body children must sit above aurora */
body.aurora > * { position: relative; z-index: 1; }

/* Gradient rule bar */
body.aurora .cover-rule,
body.aurora .generic-rule,
body.aurora .split-rule,
body.aurora .info-rule {
  background: linear-gradient(90deg, var(--aurora-1, #6366F1) 0%, var(--aurora-2, #EC4899) 100%);
  box-shadow: 0 0 15px rgba(var(--aurora-1-rgb, 99,102,241), 0.5);
}
/* Gradient bullet markers */
body.aurora .generic-content li::before,
body.aurora .split-content li::before {
  content: "●";
  font-size: 20px;
  top: 5px;
  background: linear-gradient(135deg, var(--aurora-1), var(--aurora-2));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
body.aurora .cover-title,
body.aurora .generic-title,
body.aurora .split-title,
body.aurora .info-title {
  font-family: 'Archivo Black', sans-serif;
  font-weight: 400;
  letter-spacing: -0.025em;
}
body.aurora .footer,
body.aurora .page-num { color: rgba(250, 250, 250, 0.4); }
```

---

## 6. Theme × Layout Edge Case Matrix (All 16 Combinations)

| Layout | Issue | Fix |
|--------|-------|-----|
| `cover` + no image + any dark theme | Slide is pitch black rectangle — no visual anchor | If `requires_image: false` and dark theme: add a subtle radial gradient fallback on the cover container |
| `cover` + no image + `editorial` | Works fine — editorial is text-dominant anyway | No fix needed |
| `cover` + very long title (>40 chars) + `editorial` | 120px × 3 lines overflows 1080px | Auto-reduce cover-title to 80px if title > 40 chars (via validator check) |
| `split` + no image + any theme | Right panel is empty white/dark space | If `requires_image: false`: fill right with a large decorative element (primary-colored background + subtitle text) |
| `split` + `editorial` | Thin ruled separator needs to look editorial | Column divider becomes a 1px line in `--primary` color |
| `split` + `layout_variant: reverse` | Image-left, text-right | `flex-direction: row-reverse` in CSS |
| `infographic` + 1 bullet | Single card in 3-column grid — looks wrong | Dynamic grid: 1 bullet = 1 col, 2 bullets = 2 cols, 3–6 = 3 cols |
| `infographic` + 6 bullets | 2 rows in grid — may overflow height | Cap infographic layout at 3 bullets in validator (different cap than generic) |
| `infographic` + `editorial` | Ghost numbers need position context | `.info-card` must be `position: relative; overflow: hidden` (already specified) |
| `infographic` + `dark_neon` | Neon number glow needs to not bleed into card border | Reduce glow opacity for infographic context |
| `generic` + `aurora` | Aurora `::before` must be below card content | Card gets `position: relative; z-index: 1` |
| `generic` + `gradient_flow` | Gradient-clip title text — need @supports fallback | Wrap in `@supports (-webkit-background-clip: text)` |
| `generic` + `editorial` | Vertical rule as `::before` on title — title must have no padding-top | Reset `padding-top: 0; margin-top: 0` on editorial title |
| `cover` + `gradient_flow` | Cover overlay `var(--bg)` is now a gradient start color, not solid | Change overlay to `linear-gradient(90deg, #000000 0%, #000000 40%, transparent 100%)` for gradient_flow |
| `cover` + `aurora` | The aurora shimmer is behind the overlay — overlay must be semi-transparent | Aurora cover overlay: `linear-gradient(90deg, rgba(8,8,15,0.95) 0%, rgba(8,8,15,0.7) 40%, transparent 100%)` |
| `cover` + `dark_neon` | Pure black overlay kills the image | Same semi-transparent treatment: `rgba(5,5,5,0.90)` to `transparent` |

### Validator Layout-Aware Caps

```python
# validator.py — layout-specific bullet caps
LAYOUT_BULLET_CAPS = {
    'cover':        0,   # bullets on cover are ignored anyway
    'split':        4,   # 4 bullets max in split (text + image sharing space)
    'infographic':  3,   # 3 cards max — keep one row, no overflow risk
    'generic':      6,   # standard cap
}
```

---

## 7. Conditional Font Loading + Offline Font Strategy

### Phase A (Immediate): Conditional CDN Loading

```html
<!-- base.html — load only fonts for the active theme -->
{% if theme.structural_class == 'dark_neon' %}
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;600;700&family=Space+Mono:ital,wght@0,400;0,700&display=swap" rel="stylesheet">
{% elif theme.structural_class == 'gradient_flow' %}
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
{% elif theme.structural_class == 'editorial' %}
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;0,900;1,400&family=IBM+Plex+Sans:wght@300;400;600&display=swap" rel="stylesheet">
{% elif theme.structural_class == 'aurora' %}
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Nunito:wght@300;400;600;700&display=swap" rel="stylesheet">
{% else %}
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Merriweather:ital,wght@0,300;0,400;0,700&display=swap" rel="stylesheet">
{% endif %}
```

### Phase B (Robust): Offline Font Download

A new `fonts` CLI subcommand downloads fonts at `init` time:

```bash
python cli.py fonts          # list available fonts per theme
python cli.py fonts download           # download all theme fonts
python cli.py fonts download --theme dark_neon   # download just one theme's fonts
```

`fonts download` uses the Google Fonts CSS2 API to get `@font-face` declarations with `.woff2` URLs, downloads them to `assets/fonts/`, and writes a local `assets/fonts/fonts.css` file.

`base.html` checks for the local fonts file first:
```html
{% if local_fonts_available %}
<link rel="stylesheet" href="../assets/fonts/fonts.css">
{% else %}
<!-- CDN fallback: [conditional font links above] -->
{% endif %}
```

`Templater` detects `assets/fonts/fonts.css` exists and passes `local_fonts_available=True` to the template context.

**Edge cases for font download:**
- Partial download (network cut mid-way): write a `fonts.lock` file only after ALL fonts succeed; templater only uses local fonts if `fonts.lock` exists
- Font file corrupted: checksums not practical; rely on Playwright's font rendering to fall back to system fonts gracefully

---

## 8. Renderer — Deep Fixes

### Fix 1: Playwright not installed
```python
# renderer.py — detect missing playwright at startup, not at render time
try:
    from playwright.sync_api import sync_playwright
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False

class Renderer:
    def __init__(self, ...):
        if not _PLAYWRIGHT_AVAILABLE:
            print("Error: playwright is not installed.")
            print("  Run: pip install playwright && playwright install chromium")
            sys.exit(1)
```

### Fix 2: Timeout on page.goto
```python
page.goto(file_url, wait_until='networkidle', timeout=config_timeout_ms)
# config_timeout_ms comes from pipeline.renderer_timeout_ms (default 15000)
# If networkidle times out (font CDN slow), catch TimeoutError and proceed:
try:
    page.goto(file_url, wait_until='networkidle', timeout=timeout_ms)
except Exception:
    page.goto(file_url, wait_until='domcontentloaded', timeout=5000)
    print(f"  [Warning] Slide {slide_num}: networkidle timeout — fonts may not be loaded.")
```

### Fix 3: DOM audit JavaScript (runs BEFORE screenshot)

The renderer now runs the DOM audit JS and stores results:

```python
def render_all(self, html_files, audit=False, timeout_ms=15000) -> tuple:
    """Returns (png_paths, dom_audit_results)"""
    png_files = []
    dom_audit_results = []

    DOM_AUDIT_JS = """
    (function() {
      // Disable CSS animations for stable audit
      const style = document.createElement('style');
      style.textContent = '*, *::before, *::after { animation-duration: 0s !important; transition-duration: 0s !important; }';
      document.head.appendChild(style);

      // Wait for fonts (already done by Playwright but belt-and-suspenders)
      const result = { warnings: [], info: [] };

      // 1. Text overflow (using scrollHeight — works even with overflow:hidden
      //    by temporarily removing overflow:hidden)
      document.querySelectorAll('[class*="-content"], [class*="-title"], [class*="-subtitle"]').forEach(el => {
        const original = el.style.overflow;
        el.style.overflow = 'auto';
        if (el.scrollHeight > el.clientHeight + 8) {
          result.warnings.push({
            type: 'OVERFLOW',
            element: el.className,
            excess_px: el.scrollHeight - el.clientHeight
          });
        }
        el.style.overflow = original;
      });

      // 2. Font size (min 18px, ignoring hidden elements)
      document.querySelectorAll('*').forEach(el => {
        const style = window.getComputedStyle(el);
        if (style.display === 'none' || style.visibility === 'hidden') return;
        if (el.children.length > 0 || !el.textContent.trim()) return;
        const size = parseFloat(style.fontSize);
        if (size > 0 && size < 18) {
          result.warnings.push({ type: 'FONT_TOO_SMALL', element: el.className || el.tagName, size_px: size.toFixed(1) });
        }
      });

      // 3. Broken images
      document.querySelectorAll('img').forEach(img => {
        if (!img.complete || img.naturalWidth === 0) {
          const isPlaceholder = img.src.includes('placeholder');
          result.warnings.push({
            type: isPlaceholder ? 'PLACEHOLDER_IMAGE' : 'BROKEN_IMAGE',
            src: img.src.split('/').pop()
          });
        }
      });

      // 4. Color info (for audit report)
      const body = document.body;
      const cs = window.getComputedStyle(body);
      result.info.push({ type: 'BODY_COLORS', bg: cs.backgroundColor, fg: cs.color });

      // 5. Content area coverage (text + content region)
      const container = document.querySelector('[class$="-container"]');
      if (container) {
        const rect = container.getBoundingClientRect();
        result.info.push({
          type: 'COVERAGE',
          width_pct: Math.round((rect.width / 1920) * 100),
          height_pct: Math.round((rect.height / 1080) * 100)
        });
      }

      return result;
    })()
    """

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            device_scale_factor=1,
        )
        page = context.new_page()

        for html_file in track(html_files, description="Rendering HTML to PNG..."):
            file_url = f"file://{os.path.abspath(html_file)}"
            slide_num = int(os.path.basename(html_file).split('_')[1].split('.')[0])

            try:
                page.goto(file_url, wait_until='networkidle', timeout=timeout_ms)
            except Exception:
                try:
                    page.goto(file_url, wait_until='domcontentloaded', timeout=5000)
                    print(f"  [Warning] Slide {slide_num}: Font CDN timeout — using system fonts.")
                except Exception as e:
                    print(f"  [Error] Could not load slide {slide_num}: {e}")
                    continue

            await_fonts = "document.fonts.ready.then(() => true)"
            try:
                page.evaluate(await_fonts)
            except Exception:
                pass

            # Run DOM audit before screenshot
            audit_result = {"slide_number": slide_num, "warnings": [], "info": []}
            if audit:
                try:
                    audit_result.update(page.evaluate(DOM_AUDIT_JS))
                    audit_result["slide_number"] = slide_num
                except Exception as e:
                    print(f"  [Warning] DOM audit failed for slide {slide_num}: {e}")

            dom_audit_results.append(audit_result)

            # Screenshot
            base_name = os.path.basename(html_file).replace('.html', '.png')
            out_path = os.path.join(self.images_dir, base_name)
            page.screenshot(path=out_path, full_page=False)
            png_files.append(out_path)

        browser.close()

    # Cache dom audit results for standalone `audit` command
    import json
    cache_path = os.path.join(self.build_dir, 'dom_audit.json')
    with open(cache_path, 'w') as f:
        json.dump(dom_audit_results, f, indent=2)

    return png_files, dom_audit_results
```

**Note:** `cli.py` must be updated to unpack the tuple: `png_files, dom_results = renderer.render_all(...)`.

---

## 9. `quality_checker.py` — Full Implementation Design

```python
# quality_checker.py

from dataclasses import dataclass, field
from typing import List, Optional, Literal
import json, os
import numpy as np
from PIL import Image, ImageFilter

@dataclass
class SlideAuditResult:
    slide_number: int
    slide_title: str = ""
    dom_warnings: List[dict] = field(default_factory=list)
    visual_metrics: dict = field(default_factory=dict)
    ai_scores: Optional[dict] = None
    overall_score: float = 0.0
    status: Literal['pass', 'warn', 'fail'] = 'pass'

    def compute_status(self):
        has_critical = any(w['type'] in ('OVERFLOW', 'BROKEN_IMAGE') for w in self.dom_warnings)
        has_warn = any(w['type'] in ('FONT_TOO_SMALL', 'PLACEHOLDER_IMAGE') for w in self.dom_warnings)
        if has_critical or self.overall_score < 4.0:
            self.status = 'fail'
        elif has_warn or self.overall_score < 6.5:
            self.status = 'warn'
        else:
            self.status = 'pass'
```

### Layer 2: Visual Metrics (PIL, no sklearn dependency)

```python
def analyze_png(png_path: str, is_dark_theme: bool = True) -> dict:
    img = Image.open(png_path).convert('RGB')
    arr = np.array(img, dtype=np.float32)
    gray = arr.mean(axis=2)

    # 1. Tonal contrast (P90 - P10 of brightness)
    contrast = float(np.percentile(gray, 90) - np.percentile(gray, 10))
    # Dark themes: good range 80–220. Light themes: 60–200.
    contrast_ok = (60 <= contrast <= 220)

    # 2. Mean brightness
    mean_bright = float(np.mean(gray))
    # Dark themes: expect 15–90. Light themes: expect 160–240.
    bright_ok = (15 <= mean_bright <= 90) if is_dark_theme else (160 <= mean_bright <= 240)

    # 3. Color diversity — without sklearn, use quantization
    quantized = img.quantize(colors=8, method=Image.Quantize.FASTOCTREE)
    palette = quantized.getpalette()[:8*3]  # 8 colors × RGB
    colors = [tuple(palette[i:i+3]) for i in range(0, len(palette), 3)]
    # Measure spread as avg pairwise distance between palette colors
    dists = []
    for i, c1 in enumerate(colors):
        for j, c2 in enumerate(colors):
            if i < j:
                dists.append(sum((a-b)**2 for a,b in zip(c1,c2))**0.5)
    diversity = float(np.mean(dists)) if dists else 0.0
    diversity_ok = diversity > 30  # > 30 = reasonably varied

    # 4. Edge density (content vs emptiness)
    edges = img.filter(ImageFilter.FIND_EDGES).convert('L')
    edge_arr = np.array(edges, dtype=np.float32)
    edge_density = float((edge_arr > 25).mean())
    # Good: 0.02–0.20. Too low = empty. Too high = cluttered.
    density_ok = 0.02 <= edge_density <= 0.20

    # 5. Left-right balance (is layout centered or lopsided?)
    left_mean = float(gray[:, :960].mean())
    right_mean = float(gray[:, 960:].mean())
    balance = left_mean / (right_mean + 1e-6)
    balance_ok = 0.65 <= balance <= 1.50  # some asymmetry is fine (split layout)

    # 6. Top-third focus (focal point check — titles should be top)
    top_edge = float((edge_arr[:360] > 25).mean())
    has_top_focus = top_edge > 0.03

    return {
        "contrast":       round(contrast, 1),
        "contrast_ok":    contrast_ok,
        "mean_brightness": round(mean_bright, 1),
        "brightness_ok":  bright_ok,
        "color_diversity": round(diversity, 1),
        "diversity_ok":   diversity_ok,
        "edge_density":   round(edge_density, 3),
        "density_ok":     density_ok,
        "balance_ratio":  round(balance, 2),
        "balance_ok":     balance_ok,
        "has_top_focus":  has_top_focus,
        # Composite metric score (0–10)
        "metric_score":   round(sum([contrast_ok, bright_ok, diversity_ok,
                                     density_ok, balance_ok, has_top_focus]) / 6 * 10, 1),
    }
```

### Layer 3: AI Design Critic

**Image preparation (downscale before API send):**
```python
def _prepare_image_for_api(png_path: str) -> bytes:
    """Downscale 1920×1080 → 960×540 JPEG for API. Reduces payload by ~75%."""
    img = Image.open(png_path).resize((960, 540), Image.LANCZOS)
    import io
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=85)
    return buf.getvalue()
```

**Multi-image API call (all slides in one request):**
```python
def run_ai_critique(png_paths: list, master_plan, client) -> dict:
    """Send all slides in one multi-image prompt for deck-level analysis."""
    # Prepare images
    images = [_prepare_image_for_api(p) for p in png_paths if os.path.exists(p)]
    if not images:
        return {}

    # Build contents: images interleaved with slide labels
    from google.genai import types
    contents = []
    for i, (img_bytes, path) in enumerate(zip(images, png_paths)):
        slide_num = int(os.path.basename(path).split('_')[1].split('.')[0])
        contents.append(f"=== Slide {slide_num} ===")
        contents.append(types.Part.from_bytes(data=img_bytes, mime_type='image/jpeg'))

    contents.append(CRITIC_PROMPT)

    response = client.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=contents,
        config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=4096)
    )
    # Parse JSON from response
    from planner import _extract_json
    raw = _extract_json(response.text)
    return json.loads(raw)
```

**Critic prompt** (tight JSON-only response):
```python
CRITIC_PROMPT = """
You are a senior presentation designer at a top design agency.
Analyze the slides shown above (in order) and respond ONLY with this JSON — no explanation:
{
  "deck": {
    "overall_score": <1-10 float>,
    "consistency": <1-10 float>,
    "strongest_slide": <int>,
    "weakest_slide": <int>,
    "deck_issue": "<the single most common problem across ALL slides in one sentence>",
    "deck_fix": "<one specific CSS or content change to apply deck-wide>"
  },
  "slides": [
    {
      "slide_number": <int>,
      "scores": { "hierarchy": <1-10>, "typography": <1-10>, "color": <1-10>, "balance": <1-10>, "consistency": <1-10> },
      "score": <average of above>,
      "strength": "<what works best on this slide>",
      "issue": "<the single most visible problem>",
      "fix": "<one concrete, implementable change — be specific, e.g. 'Increase subtitle to 42px' not 'improve readability'>"
    }
  ]
}
"""
```

---

## 10. Audit Report Format (`design_audit.md`)

```markdown
# Design Audit Report
**Generated:** 2026-07-18T12:00:00  
**Theme:** dark_neon (cyber_cyan palette)  
**Slides:** 5  
**Audit Level:** full (DOM + Visual Metrics)

---

## Overall Score: 7.2 / 10
*(Visual metrics composite only — AI critique not run. Use `--level ai` for full scoring.)*

## Deck Summary
| Check | Result |
|-------|--------|
| DOM Overflows | 1 slide (Slide 2) |
| Broken Images | 0 |
| Placeholder Images | 5 (expected — manual generation pending) |
| Contrast Issues | 0 |
| Layout Balance | 4 / 5 good |

---

## Per-Slide Results

### ✅ Slide 1 — "The Future of Pitching" (Cover)
| Metric | Value | Status |
|--------|-------|--------|
| Contrast | 182.4 | ✅ |
| Brightness | 42.1 | ✅ |
| Color Diversity | 87.3 | ✅ |
| Edge Density | 0.089 | ✅ |
| Balance Ratio | 1.02 | ✅ |
| **Score** | **9.2 / 10** | ✅ |

### ⚠️ Slide 2 — "The Old vs The New" (Split)
**DOM Warning:** OVERFLOW — `.split-content` excess 22px  
*→ Reduce from 5 bullets to 4, or shorten bullet text.*

| Metric | Value | Status |
|--------|-------|--------|
| Contrast | 142.1 | ✅ |
| Edge Density | 0.28 | ⚠️ too cluttered |
| Balance Ratio | 1.61 | ⚠️ lopsided |
| **Score** | **5.4 / 10** | ⚠️ |

---

## Actionable Recommendations
1. **Slide 2 overflow**: Remove 1 bullet from the split layout.  
2. **Slide 2 balance**: Image-heavy side dominates — consider `layout_variant: reverse`.  
3. **All slides**: 5/5 slides show PLACEHOLDER_IMAGE — generate real images using `assets/image_prompts.txt`.  

---
*Run `python cli.py audit --level ai` for AI design critique with per-slide improvement suggestions.*
```

---

## 11. Planner System Prompt — Full Rewrite

The system prompt is the most important piece for quality. Key additions:

```
THEME SELECTION GUIDE:
- dark_neon:      Tech/AI/developer content. Use palette: cyber_cyan (default), neon_magenta (creative), electric_blue (corporate tech)
- gradient_flow:  Startup/SaaS/marketing. Use palette: violet_sunset (default), ocean_depth (finance), forest_dusk (sustainability)
- editorial:      Design/journalism/academia. Use palette: navy (default), crimson (bold), terracotta (warm)
- aurora:         Luxury/portfolio/premium. Use palette: cosmic (default), arctic (science), wildfire (energy)
- glassmorphism:  Modern consumer products. Primary and background colors from user config.
- corporate_clean: Business/enterprise. Conservative, safe.
- minimalist:     Ultra-clean. One color max.
- neo_brutalism:  Bold/edgy/unconventional.

LAYOUT SEQUENCING RULES (CRITICAL):
1. Slide 1 MUST be layout_type: "cover"
2. Final slide SHOULD be layout_type: "generic" (for summary/CTA)
3. No more than 2 consecutive slides with the same layout_type
4. layout_type: "infographic" only for content with 3 distinct numbered/categorical points
5. layout_type: "split" only when you have a strong visual contrast to make
6. Vary requires_image — do NOT set it true for every slide
7. Target slide count by duration: <5min=4-5, 5-10min=6-8, 10-20min=8-12, 20+min=12-20

PALETTE SELECTION:
Output a "palette" field in the theme object. Match to the content's industry/tone using the guide above.
Only output these exact palette names — no invented names.

CSS VARIABLES TO OUTPUT (by theme):
- dark_neon/aurora: Only output structural_class and palette. ThemeResolver handles all colors.
- gradient_flow: Only output structural_class and palette.
- editorial: Only output structural_class and palette.
- glassmorphism/corporate_clean/minimalist/neo_brutalism: Output --bg, --primary, --text, --text-secondary as before.
```

---

## 12. `--preview` Mode

Fast iteration during theme development:
```bash
python cli.py generate --offline-plan master_plan.json --preview
```

- Renders at 960×540 (50% resolution) — 4× faster than full render
- Only renders first 3 slides
- Layer 1+2 audit always runs (fast, no API)
- Outputs `preview.pdf` in addition to or instead of `presentation.pdf`

Implementation in `renderer.py`:
```python
if preview_mode:
    context = browser.new_context(viewport={'width': 960, 'height': 540})
```

And in `cli.py`:
```python
if args.preview:
    html_files = html_files[:3]  # only first 3 slides
    pdf_path = pdf_path.replace('.pdf', '_preview.pdf')
```

---

## 13. Stale Image Asset Invalidation

**Current problem:** `slide_1.png` from `dark_neon` run is reused in an `editorial` run (wrong image for new theme).

**Fix:** Store a `.image_manifest.json` alongside the generated slides:
```json
{
  "theme": "dark_neon",
  "palette": "cyber_cyan",
  "art_style": "vector illustration",
  "generated_at": "2026-07-18T12:00:00",
  "slides": {
    "slide_1.png": { "prompt_hash": "abc123", "slide_title": "The Future..." },
    "slide_2.png": { ... }
  }
}
```

At the start of `ImageGenerator.generate_all()`:
```python
def _should_regenerate(self, slide, manifest, force):
    if force:
        return True
    if slide.slide_number not in manifest.get('slides', {}):
        return True  # new slide
    # Theme changed?
    if manifest.get('theme') != self.current_theme:
        return True
    # Prompt changed?
    import hashlib
    new_hash = hashlib.md5(slide.image_prompt.encode()).hexdigest()[:8]
    if manifest['slides'].get(f"slide_{slide.slide_number}.png", {}).get('prompt_hash') != new_hash:
        return True
    return False
```

This replaces the simple `os.path.exists()` check with content-aware invalidation.

---

## 14. `audit` CLI Subcommand

```bash
# In cli.py argparse:
audit_parser = subparsers.add_parser("audit", help="Run design audit on generated slides")
audit_parser.add_argument("--level", choices=["quick", "full", "ai"], default="full")
audit_parser.add_argument("--slides-dir", default="temp_build/images/")
audit_parser.add_argument("--plan", default="master_plan.json")
audit_parser.add_argument("--out", default="design_audit.md")
audit_parser.add_argument("--config", default="config.yaml")
```

Dependencies check at audit startup:
```python
elif args.command == "audit":
    # Verify prerequisites
    if not os.path.exists(args.slides_dir):
        print(f"Error: Slides directory '{args.slides_dir}' not found.")
        print("  → Run `python cli.py generate` first.")
        sys.exit(1)
    if not os.path.exists(args.plan):
        print(f"Error: Master plan '{args.plan}' not found.")
        print("  → Run `python cli.py generate --dry-run` to create one.")
        sys.exit(1)
    dom_cache = os.path.join('temp_build', 'dom_audit.json')
    if not os.path.exists(dom_cache):
        print("  [Info] No cached DOM audit data — Layer 1 will be skipped.")
        print("  (Run `python cli.py generate` to capture DOM audit data.)")
    if args.level == 'ai' and not os.environ.get('GEMINI_API_KEY'):
        print("  [Warning] GEMINI_API_KEY not set — downgrading to level 'full'.")
        args.level = 'full'
```

---

## 15. Planner Consistency — `--audit` Feedback Loop (Future)

The most powerful feature (future extension): use audit results to auto-fix the plan.

```bash
python cli.py generate --audit --auto-fix
```

Flow:
1. Generate → render → audit
2. If audit finds issues (overflow, poor contrast, etc.)
3. Feed audit report back to Planner: *"Re-plan slide 2 — current split layout overflows. Reduce bullets or switch to infographic."*
4. Regenerate only affected slides
5. Re-render and re-audit
6. Repeat until all slides pass (or max-iterations reached)

This closes the quality feedback loop completely without manual intervention.

---

## 16. Complete File Change List

| File | Action | Phase |
|------|--------|-------|
| `config_manager.py` | MODIFY: Add `AppConfig` Pydantic classes; `load_and_validate()` returns `AppConfig` | 1 |
| `theme_palettes.py` | NEW: Curated palette library | 1 |
| `theme_resolver.py` | NEW: Palette merge, RGB auto-compute, validation | 1 |
| `schemas.py` | MODIFY: 4 new structural_class values; `palette` field on Theme; `layout_variant` on Slide | 1 |
| `planner.py` | MODIFY: Full SYSTEM_INSTRUCTION rewrite; layout rules; palette selection guidance | 1 |
| `validator.py` | MODIFY: Layout-aware bullet caps; cover title length check; long title size reduction | 1 |
| `cli.py` | MODIFY: Use `AppConfig` throughout; ThemeResolver call; `--preview` flag; `audit` subcommand; unpack renderer tuple | 2 |
| `templates/base.html` | MODIFY: Token system; 4 new theme CSS blocks; per-layout theme overrides; conditional font loading | 2 |
| `templates/cover.html` | MODIFY: Token refs; per-theme overlay gradient; no-image dark fallback; long-title size reduction | 2 |
| `templates/split.html` | MODIFY: Token refs; `layout_variant: reverse` CSS; per-theme column divider; no-image right panel fallback | 2 |
| `templates/generic.html` | MODIFY: Token refs; per-theme bullet/rule/title overrides | 2 |
| `templates/infographic.html` | MODIFY: Token refs; dynamic grid columns (1/2/3); editorial ghost numbers; per-theme card treatments | 2 |
| `renderer.py` | MODIFY: Playwright not-found detection; goto timeout; DOM audit JS injection; `dom_audit.json` caching; preview mode resolution; return tuple | 3 |
| `image_generator.py` | MODIFY: `.image_manifest.json` for content-aware invalidation | 3 |
| `quality_checker.py` | NEW: `SlideAuditResult`; Layer 1 parser; Layer 2 PIL metrics; Layer 3 AI critic; report writer | 3 |
| `config_reference.yaml` | MODIFY: All 8 themes; all palette names; new config keys | 4 |
| `README.md` | MODIFY: Theme gallery; palette reference; audit docs; preview mode | 4 |
| `requirements.txt` | MODIFY: `numpy`, optional `scikit-learn` comment | 4 |
| `config_manager.py` | MODIFY: `init_config` updates theme options; `fonts download` subcommand | 4 |

---

## 17. Execution Phases

### Phase 1 — Foundation (invisible to user, all backend)
`theme_palettes.py` → `theme_resolver.py` → `schemas.py` → `config_manager.py` (AppConfig) → `planner.py` (system prompt + palette field) → `validator.py` (layout-aware caps) → `cli.py` (wire ThemeResolver, use AppConfig)

### Phase 2 — Visual Design (the fun part)
`templates/base.html` (tokens + 4 theme blocks) → 4 layout templates → visual test all 16 combos → iterate CSS → approval checkpoint

### Phase 3 — QA Pipeline
`renderer.py` (DOM audit, timeout fixes) → `quality_checker.py` (Layer 1+2) → `cli.py` (audit subcommand) → test audit report → Layer 3 AI critic

### Phase 4 — Polish
`image_generator.py` (manifest) → font download subcommand → preview mode → config_reference.yaml → README → requirements.txt

> [!IMPORTANT]
> **Phase 2 is the visual approval checkpoint.** After implementing all theme CSS but before building the QA pipeline, I will generate sample PDFs of all 4 new themes across multiple layout types and share them. You give CSS feedback, I iterate, then we move to Phase 3.

> [!NOTE]
> **The audit auto-fix loop** described in §15 is a future milestone — not in this plan's scope, but the architecture is designed to support it. The `audit` subcommand + structured `design_audit.md` format is the foundation.
