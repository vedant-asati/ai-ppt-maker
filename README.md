# AI Presentation Agency

An autonomous, multi-stage presentation pipeline that uses Gemini and Playwright to generate beautifully themed PDF presentations from a single config file.

## Features

- **Elite Planner (Gemini Flash)** — Acts simultaneously as Narrative Designer, Art Director, and CSS Themer. Uses a 17-rule "Elite Presentation Agency" system prompt and injects narrative arc blueprints, audience profiles, and source signal analysis for content far beyond generic bullet points.
- **8 Visual Themes** — `minimalist`, `glassmorphism`, `neo_brutalism`, `corporate_clean`, `dark_neon`, `gradient_flow`, `editorial`, `aurora` — each with curated named palettes and full CSS design token system.
- **7 Layout Templates** — `cover`, `split`, `generic`, `infographic`, `quote`, `stat`, `timeline` — purpose-built for different content types, not one-size-fits-all slides.
- **7 Content Block Types** — Typed schema blocks (`stat`, `pullquote`, `comparison`, `steps`, `callout`, `keyvalue`, `bullets`) replace flat strings and unlock richer visual rendering.
- **7 Narrative Arc Blueprints** — `problem_solution`, `before_after`, `what_why_how`, `journey`, `contrast`, `inverted_pyramid`, `showcase` — the Planner uses these to order slides with intentional story structure.
- **5 Audience Profiles** — `investor`, `technical`, `executive`, `academic`, `general` — each tunes writing style, vocabulary, and slide density.
- **Smart Image Matching** — Dump photos in a folder, point the pipeline at it with `--images-dir`, and Gemini Vision analyzes every image and assigns the best one to each slide based on visual content, topic relevance, and layout suitability.
- **AI Image Generation** — Generates slide-specific images using `gemini-3.1-flash-image`. Smart caching (re-uses if slide content unchanged), rate-limit handling with gradient fallbacks, and theme-coherent gradient backgrounds when the API is unavailable.
- **API Key Rotation** — Multiple `GEMINI_API_KEY` / `GEMINI_API_KEY_2` keys auto-rotate on 429 rate limits. 2 keys = 2× effective quota.
- **PPTX Export** — `--pptx` flag generates an editable PowerPoint file alongside the PDF, with full PNG backgrounds + speaker notes.
- **Hindi/Devanagari Support** — Noto Serif Devanagari font loaded across all templates. Titles and content can use Sanskrit, Hindi, or any Indic script.
- **3-Layer Design Audit** — DOM overflow detection (Playwright), PIL image quality analysis, and deck-level scoring across 7 dimensions. Outputs a graded `design_audit.md` report.
- **Content Quality Scorer** — Real-time per-slide scoring across title quality, content substance, visual intent, metadata completeness, and speaker notes. Grade A–F with actionable flags.
- **Multi-Modal Sources** — `.pdf`, `.txt`, `.md`, `.mp3`, `.mp4`, `.jpg`, `.png` — all supported via Gemini Files API.
- **Offline Font Bundle** — One command downloads all 6 Google Fonts for fully offline Playwright rendering.
- **Rich Speaker Notes** — Per-slide presenter scripts with content summaries, transition prompts keyed to slide purpose, and an image prompt appendix.

---

## Quick Start

```bash
cd ppt-maker/
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Set your API key(s)
echo "GEMINI_API_KEY=your-key-here" > .env
echo "GEMINI_API_KEY_2=optional-second-key" >> .env  # doubles quota

# Create your config
python cli.py init

# Generate
python cli.py generate
```

---

## Installation

### 1. Virtual environment + dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 2. API key(s)

```bash
# ppt-maker/.env
GEMINI_API_KEY=your-primary-key
GEMINI_API_KEY_2=your-second-key    # optional — doubles effective quota
```

Get free keys at [aistudio.google.com](https://aistudio.google.com). Each key has independent rate limits — the pipeline auto-rotates to the next key on 429 errors.

> **Image generation** (`gemini-3.1-flash-image`) requires an upgraded API tier. On the free tier, the pipeline auto-generates theme-coherent gradient backgrounds and saves all prompts to `assets/image_prompts.txt` for manual generation.

### 3. (Optional) Download fonts for offline rendering

```bash
python cli.py fonts
```

Downloads all 6 fonts used by the templates (Inter, Merriweather, Space Grotesk, DM Serif Display, Playfair Display, Noto Serif Devanagari) into `assets/fonts/` for fully offline, reproducible rendering.

---

## Commands

| Command | Description |
|---|---|
| `python cli.py init` | Create a starter `config.yaml` |
| `python cli.py generate` | Full pipeline → PDF |
| `python cli.py generate --pptx` | Full pipeline → PDF + editable PPTX |
| `python cli.py generate --images-dir ./photos` | Use your own photos (auto-matched to slides) |
| `python cli.py generate --dry-run` | Plan only → save `master_plan.json` |
| `python cli.py generate --offline-plan plan.json` | Render without re-planning |
| `python cli.py generate --force-images` | Re-generate all images (bypass cache) |
| `python cli.py generate --preview` | Render 3 slides at half resolution |
| `python cli.py generate --audit full` | Generate + design audit report |
| `python cli.py generate --score` | Print per-slide content scores |
| `python cli.py audit --level full` | Standalone audit on existing slides |
| `python cli.py audit --level ai` | Audit + Gemini visual review |
| `python cli.py audit --score` | Audit + per-slide content scoring |
| `python cli.py fonts` | Download Google Fonts offline bundle |

---

## Typical Workflow

### A. Fully automated (one shot)

```bash
python cli.py generate --pptx
```

### B. Review plan before rendering (recommended for important decks)

```bash
# Step 1: Plan only — cheap, fast
python cli.py generate --dry-run

# Step 2: Open master_plan.json and edit any slides

# Step 3: Render without re-calling the AI
python cli.py generate --offline-plan master_plan.json --pptx
```

### C. Generate + audit quality

```bash
python cli.py generate --audit full --score
```

This generates the full PDF, then runs a 3-layer design audit:

- **Layer 1** (DOM): Overflow, broken images, font size violations
- **Layer 2** (PIL): Image brightness, contrast, center clutter
- **Layer 3** (Score): Deck design scoring across 7 dimensions

Outputs `design_audit.md` and prints per-slide content scores to the terminal.

### D. Use your own photos

```bash
# Dump any photos into a folder (any filenames)
ls ./my_photos/
  sunset.jpg  IMG_20240315.jpg  chart_q3.png  temple.jpg

# The pipeline uses Gemini Vision to match them to slides
python cli.py generate --images-dir ./my_photos
```

The image matcher:
- Sends ALL images + ALL slide metadata in **one API call** to Gemini Vision
- Matches based on visual content, topic relevance, AND layout suitability
- Cover slides get dramatic landscapes, quote slides get atmospheric scenes
- Confidence threshold (40%) — a good gradient beats a bad photo
- Falls back to PIL heuristics + filename keywords when offline

---

## Manual Image Workflow (Free Tier)

When image generation is blocked (free tier), the pipeline saves all AI-crafted prompts to `assets/image_prompts.txt`. Use them with any image generator:

1. Run `python cli.py generate` as usual (gradient placeholders are used automatically)
2. Open `assets/image_prompts.txt` and copy each prompt
3. Generate images using Gemini ([gemini.google.com](https://gemini.google.com)) or ChatGPT
4. Save generated images as `assets/slide_1.png`, `assets/slide_2.png`, etc.
5. Re-run: `python cli.py generate --offline-plan master_plan.json`

The cache system detects your images and uses them automatically.

---

## Configuration

See `config_reference.yaml` for the complete reference. Key options:

```yaml
source_text: "Your topic, outline, or raw research here"
# source_file: "path/to/notes.pdf"   # .pdf .txt .md .mp3 .mp4 .jpg .png

presentation_goals:
  audience: "Software Engineers"
  audience_type: technical # investor | technical | executive | academic | general
  duration_minutes: 10
  tone: "confident and precise"
  narrative_arc:
    what_why_how # problem_solution | before_after | what_why_how |
    # journey | contrast | inverted_pyramid | showcase

design_preferences:
  theme_style:
    dark_neon # minimalist | glassmorphism | neo_brutalism |
    # corporate_clean | dark_neon | gradient_flow |
    # editorial | aurora
  palette: cyber_cyan # see config_reference.yaml for full palette list
  primary_color: null # optional hex override: "#FF3366"

image_preferences:
  art_style: "cinematic 3D render, volumetric lighting, dark background"
```

---

## Architecture

```
ppt-maker/
├── cli.py                  ← Entry point, subcommands, .env loading
├── config_manager.py       ← YAML loader + Pydantic validation + init template
├── config_reference.yaml   ← Full option documentation (read-only reference)
├── schemas.py              ← Pydantic models: MasterPlan, Slide, ContentBlocks (7 types)
│
├── narrative_arcs.py       ← 7 narrative blueprints injected into Planner prompt
├── audience_profiles.py    ← 5 audience style profiles
├── source_analyzer.py      ← Signal extraction: stats, quotes, comparisons
├── planner.py              ← Gemini Flash Lite: 17-rule Elite Planner system prompt
│
├── validator.py            ← Post-generation pruning, filler detection, deck checks
├── content_scorer.py       ← Per-slide content quality scoring (5 dims, 50 pts max)
│
├── theme_palettes.py       ← Named palette definitions for 4 premium themes
├── theme_resolver.py       ← Resolves palette → CSS variables for Jinja2 context
│
├── image_cache.py          ← Content-hash cache: skip unchanged slides
├── gradient_generator.py   ← PIL-based theme-coherent gradient fallback images
├── image_generator.py      ← Gemini image API + rate limiting + cache + fallback
├── image_matcher.py        ← Smart image-to-slide matching (Gemini Vision + PIL fallback)
│
├── api_keys.py             ← Multi-key rotation: GEMINI_API_KEY, GEMINI_API_KEY_2, ...
│
├── templater.py            ← Jinja2 HTML builder: 7 templates + image manifest
├── renderer.py             ← Playwright headless render + DOM audit injection
├── compiler.py             ← PIL PDF stitcher + rich speaker notes export
├── pptx_exporter.py        ← Editable PPTX export (PNG backgrounds + text overlays)
│
├── image_validator.py      ← PIL image quality analysis (brightness, contrast, clutter)
├── quality_checker.py      ← 3-layer audit orchestrator → design_audit.md
├── font_downloader.py      ← Google Fonts offline bundle downloader
│
├── templates/
│   ├── base.html           ← Full design token system, 8 themes, aurora/neon effects
│   ├── _blocks.html        ← Jinja2 macro library for 7 content block types
│   ├── cover.html          ← Title slide
│   ├── split.html          ← Text + image two-column
│   ├── generic.html        ← Full-width content
│   ├── infographic.html    ← 3-column stats/cards
│   ├── quote.html          ← Full-slide pull quote
│   ├── stat.html           ← Hero number layout
│   └── timeline.html       ← Horizontal step-by-step flow
│
├── assets/                 ← Generated images, gradient fallbacks, image_prompts.txt
└── temp_build/             ← Intermediate HTML, PNG renders, DOM audit cache
```

---

## Visual Themes

| Theme | Description | Best For |
|---|---|---|
| `minimalist` | Clean whitespace, restrained typography | Academic, editorial |
| `glassmorphism` | Frosted glass, blur, translucency | Tech, product |
| `neo_brutalism` | Hard shadows, bold borders, Space Grotesk | Startup, creative |
| `corporate_clean` | Soft shadows, rounded, boardroom-safe | Executive, B2B |
| `dark_neon` | Dark bg + glowing neon accent | Pitch decks, tech demos |
| `gradient_flow` | Smooth gradient bg + glass panels | Marketing, product launch |
| `editorial` | Serif typography, magazine layout | Thought leadership |
| `aurora` | Dark bg + glowing ethereal blobs | Brand, luxury, creative |

### Named Palettes (dark_neon)

`cyber_cyan` · `neon_magenta` · `electric_blue` · `acid_lime` · `solar_orange`

---

## Content Block Types

| Block | Schema | Rendered As |
|---|---|---|
| `bullets` | `items: [...]` | Styled bullet list |
| `stat` | `value`, `label`, `context` | Hero number with label |
| `pullquote` | `quote`, `attribution` | Styled blockquote |
| `comparison` | `left_label`, `left_items`, `right_label`, `right_items` | Side-by-side comparison |
| `steps` | `steps: [...]`, `step_labels: [...]` | Numbered flow |
| `callout` | `text`, `callout_type` | Highlighted callout card |
| `keyvalue` | `pairs: [{key, value}]` | Key-value table |

---

## Layout Types

| Layout | Description |
|---|---|
| `cover` | Full-page title slide with optional background image |
| `split` | Text left + image right (reversible with `layout_variant: reverse`) |
| `generic` | Full-width text + content panel |
| `infographic` | 3-column stats/cards grid |
| `quote` | Full-slide pull quote with giant decorative quotation mark |
| `stat` | Hero number (200px) left + supporting stats/content right |
| `timeline` | Horizontal step flow with alternating above/below cards |

---

## Hindi / Devanagari Support

All templates include Noto Serif Devanagari in the font stack. You can use Hindi, Sanskrit, or any Indic script in titles, subtitles, bullets, and quotes:

```yaml
source_text: |
  Topic: वसुधैव कुटुम्बकम् (Vasudhaiva Kutumbakam)
  The world is one family. Explore Indian Knowledge Systems...
```

---

## Requirements

- Python 3.10+
- `google-genai` — Gemini API client
- `Pillow` — Image processing, PDF compilation
- `playwright` — Headless rendering
- `python-pptx` — PPTX export
- `Jinja2` — HTML template engine
- `pyyaml` — Config file parsing
- `python-dotenv` — `.env` file loading
- `rich` — Progress bars and terminal UI
- `pydantic` — Schema validation
