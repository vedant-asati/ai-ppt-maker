# AI Presentation Agency

An autonomous, multi-stage presentation pipeline that uses Gemini and Playwright to generate beautifully themed PDF presentations from a single config file.

## Features

- **Targeted Agentic Refinement Loop** — Autonomous closed-loop Playwright DOM overflow remediation. Hierarchically applies deterministic micro-fixes, single-slide JSON reflexion patches via Gemini (~350 tokens vs. 6,000 for full deck), and algorithmic speaker note offloading. Enabled by default (`--auto-refine`).
- **Grounded Research Agent** — Pass `--research "Topic"` to generate cited, fact-grounded decks directly from high-level topics without manual source files. Decomposes queries across 3 orthogonal angles, retrieves verified web sources via DuckDuckGo, synthesizes structured briefs, and renders clickable footnote citations. Gracefully falls back to baseline knowledge with a cover disclaimer when offline.
- **GenAI Evaluation Framework & LLM-as-a-Judge** — Offline evaluation harness (`evals/run.py`) benchmarking decks across DOM overflow rates, layout monotony, word density, structured block diversity, and telemetry/costs. Includes position-bias mitigated pairwise comparison and calibrated ground-truth scoring against pre-labeled slides.
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
git clone https://github.com/vedant-asati/ai-ppt-maker.git
cd ai-ppt-maker/
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .                 # or: pip install -r requirements.txt
playwright install chromium

# Set your free Gemini API key from https://aistudio.google.com
echo "GEMINI_API_KEY=your-key-here" > .env
```

---

## 🎯 How to Generate: Choose Your Path

There are **3 simple ways** to create presentations depending on what you need:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│ 1. Instant One-Liner (Fastest)                                                  │
│    python cli.py generate --topic "AI in Healthcare" --pptx                     │
│    → No config file needed. Just give a topic and get a themed PDF + PPTX.      │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 2. Live Web Research (Current Facts & Footnotes)                                │
│    python cli.py generate --research "Solid State Batteries 2026" --pptx        │
│    → The agent searches the web, synthesizes facts, and adds clickable sources. │
├─────────────────────────────────────────────────────────────────────────────────┤
│ 3. Custom Config File (Full Fine-Tuning)                                        │
│    python cli.py init  &&  python cli.py generate --pptx                        │
│    → Fine-tune theme, palette, audience tone, or paste large meeting notes.   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Path 1: Instant Topic (Fastest — 10 seconds)
Pass your topic directly in the terminal. No config editing required:

```bash
python cli.py generate --topic "Future of Quantum Computing" --pptx
```
> 💡 **Tip:** Want a specific number of slides? Add `--slides 6` (supports 3–20 slides).

### Path 2: Autonomous Web Research (Deep Facts + Footnote Citations)
No existing notes? Let the Research Agent search the live web, extract verified metrics, and synthesize a cited deck:

```bash
python cli.py generate --research "2026 Commercial Viability of Solid-State EV Batteries" --pptx
```
> 🔍 **What happens:** The agent breaks the topic into 3 research angles, retrieves articles via DuckDuckGo, extracts verified metrics, and renders clickable footnote citations on each slide.

### Path 3: Custom Config File (Detailed Notes, Custom Themes & Audiences)
Best when you have detailed meeting notes, a custom outline, or want to pick an exact visual theme:

```bash
# Step 1: Create a starter config file
python cli.py init

# Step 2: Open config.yaml and edit:
#   source_text: "Paste your raw notes, outline, or document text here"
#   design_preferences:
#     theme_style: dark_neon   # minimalist | glassmorphism | neo_brutalism | corporate_clean | dark_neon | gradient_flow | editorial | aurora
#   presentation_goals:
#     audience_type: executive # investor | technical | executive | academic | general

# Step 3: Generate the presentation
python cli.py generate --pptx
```
> 💡 **Where does the content come from in `python cli.py generate --pptx`?**  
> When run without `--topic` or `--research`, it reads the presentation topic, notes, and theme directly from `config.yaml`.

---

## Command Reference

Instead of a confusing wall of options, commands are grouped by your goal:

### 🚀 Daily Generation (90% of use cases)
| Command | What It Does | When to Use |
|---|---|---|
| `python cli.py generate --topic "Topic" --pptx` | Instant topic $\rightarrow$ Themed PDF + editable PPTX | Fastest path: zero config files needed |
| `python cli.py generate --research "Topic" --pptx` | Web research $\rightarrow$ Cited PDF + editable PPTX | When you need current facts and verified sources |
| `python cli.py init` | Creates starter `config.yaml` | When you want full control over fonts, colors, and notes |
| `python cli.py generate --pptx` | Builds presentation from `config.yaml` | After editing `source_text` in `config.yaml` |

### 🎨 Customization & Previews
| Command | What It Does | When to Use |
|---|---|---|
| `--slides N` | Sets exact slide count (3–20) | Add to any generate command to control deck length |
| `--images-dir ./photos` | Matches your photos to slides via Gemini Vision | When you have a folder of product/team photos |
| `--preview` | Renders first 3 slides at half resolution | Quick 5-second aesthetic preview |
| `--dry-run` | Stops after planning $\rightarrow$ saves `master_plan.json` | Review or edit slide text before browser rendering |
| `--offline-plan master_plan.json --pptx` | Renders existing JSON without calling AI | Free, instant re-renders after manual JSON edits |
| `python cli.py fonts` | Downloads offline Google Fonts bundle | Run once for fully offline rendering (e.g. on airplanes) |

### 🔬 Quality Audits & Evals (Advanced / Developers)
| Command | What It Does | When to Use |
|---|---|---|
| `python cli.py generate --audit full --score` | Generates deck + `design_audit.md` + scores | Inspect DOM overflow, image contrast, and typography |
| `python evals/run.py` | Runs deterministic benchmark across 10 golden scenarios | Regression test deck quality across 4 metric dimensions |
| `python evals/run.py --judge` | Pairwise LLM-as-a-Judge with position-bias mitigation | A/B compare slide quality against rubric standards |
| `python evals/run.py --calibrate` | Validates LLM judge against pre-labeled ground truth | Benchmark judge agreement rate ($\ge 90\%$) |

---

## Helpful Workflows

### A. Review or Edit the Plan Before Rendering
```bash
# Step 1: Generate the plan JSON only (cheap, fast, no browser rendering)
python cli.py generate --topic "Microservices Architecture" --dry-run

# Step 2: Open master_plan.json, edit any bullet or title

# Step 3: Render to PDF + PPTX without re-calling the AI
python cli.py generate --offline-plan master_plan.json --pptx
```

### B. Use Your Own Photos (Auto-Matched by Vision AI)
```bash
# Put any photos in a folder:
ls ./my_photos/
  team.jpg  datacenter.png  founder.jpg

# Gemini Vision analyzes all images and assigns the best one to each slide:
python cli.py generate --topic "Company Overview" --images-dir ./my_photos --pptx
```

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

The project is structured as a production-grade, modular Python package (`ppt_maker`) with decoupled domain subpackages, standard `pyproject.toml` configuration, and comprehensive documentation:

```
ai-ppt-maker/
├── pyproject.toml                 ← PEP 517/621 packaging metadata & CLI entrypoints
├── requirements.txt               ← Pinned dependencies
├── cli.py                         ← Root CLI entrypoint (delegates to ppt_maker.cli)
├── config.yaml                    ← Active user configuration
├── master_plan.json               ← Canonical presentation blueprint
│
├── ppt_maker/                     ← Core Python Package
│   ├── __init__.py                ← High-level public API exports
│   ├── cli.py                     ← Rich command-line interface & subcommands
│   │
│   ├── core/                      ← Data models, schemas & configuration
│   │   ├── schemas.py             ← Pydantic V2 models: MasterPlan, Slide, ContentBlocks
│   │   ├── config_manager.py      ← YAML loader, schema validation & defaults
│   │   └── api_keys.py            ← Multi-key rotation pool & quota resilience
│   │
│   ├── planning/                  ← AI narrative planning & integrity validation
│   │   ├── planner.py             ← Gemini Flash multimodal planner & agency prompt
│   │   ├── refiner.py             ← Targeted agentic reflexion loop & DOM overflow patcher
│   │   ├── validator.py           ← Integrity rules, bullet pruning & auto-repair
│   │   ├── content_scorer.py      ← Per-slide content quality rubric (5 dims, 50 pts)
│   │   ├── source_analyzer.py     ← Heuristic signal extraction (stats, quotes, steps)
│   │   ├── narrative_arcs.py      ← 7 proven storytelling dramatic structures
│   │   └── audience_profiles.py   ← 5 audience registers & vocabulary tuners
│   │
│   ├── research/                  ← Autonomous web research & grounding agent
│   │   ├── agent.py               ← Multi-query research orchestrator & fallback handler
│   │   ├── searcher.py            ← Query decomposition (3 angles) & DuckDuckGo search
│   │   └── synthesizer.py         ← HTML cleaner, GroundedBrief & citation extraction
│   │
│   ├── design/                    ← Visual theming, color palettes & typography
│   │   ├── theme_resolver.py      ← Dynamic CSS variable engine & contrast guards
│   │   ├── theme_palettes.py      ← Curated color palettes & brand archetypes
│   │   ├── gradient_generator.py  ← Procedural PIL fallback backgrounds
│   │   └── font_downloader.py     ← Google Fonts offline bundle downloader
│   │
│   ├── imaging/                   ← Asset generation, semantic matching & cache
│   │   ├── image_generator.py     ← Imagen API client & rate-limited orchestration
│   │   ├── image_matcher.py       ← Gemini Vision semantic photo matcher
│   │   ├── image_cache.py         ← Content-hash & theme-aware asset cache
│   │   └── image_validator.py     ← PIL histogram, brightness & contrast analyzer
│   │
│   ├── rendering/                 ← HTML templating & headless browser engine
│   │   ├── templater.py           ← Jinja2 builder: 7 templates + single-slide generator
│   │   └── renderer.py            ← Playwright headless Chromium runner & single-slide re-render
│   │
│   ├── export/                    ← Multi-format compilation engines
│   │   ├── compiler.py            ← Vector PDF merger & rich speaker notes compiler
│   │   └── pptx_exporter.py       ← Native editable PowerPoint generator
│   │
│   ├── audit/                     ← Multi-layer design assurance
│   │   └── quality_checker.py     ← 3-layer audit orchestrator → design_audit.md
│   │
│   └── templates/                 ← HTML templates & shared design system
│       ├── base.html              ← Design token system, 8 themes, CSS variables, footnotes
│       ├── _blocks.html           ← Jinja2 macros for 7 content block types
│       ├── cover.html, split.html, infographic.html, timeline.html, quote.html, stat.html, generic.html
│
├── evals/                         ← GenAI Evaluation Harness & Benchmarking
│   ├── dataset.json               ← 10 curated benchmark evaluation scenarios
│   ├── calibration_slides.json    ← Pre-labeled ground-truth calibration dataset
│   ├── metrics.py                 ← Deterministic metrics (overflow, monotony, density, cost)
│   ├── judge.py                   ← Position-bias mitigated pairwise LLM-as-a-Judge
│   └── run.py                     ← CLI evaluation runner & scorecard exporter
│
├── examples/                      ← Showcase presentations & sample blueprints
│   ├── ai_presentation_tools_showcase.pdf
│   ├── ai_presentation_tools_showcase.pptx
│   ├── ai_presentation_tools_showcase_speaker_notes.md
│   └── README.md
│
├── docs/                          ← Architecture specifications & engineering roadmaps
│   ├── README.md                  ← Documentation hub & navigation index
│   ├── architecture.md            ← System Architecture & Technical Specification
│   ├── code_review.md             ← 14-Dimension Code Review & Quality Audit
│   ├── plans/                     ← Feature proposals (features/) & roadmaps (roadmap/)
│   ├── issues/                    ← Tracked issues & root-cause post-mortems
│   └── retrospectives/            ← Development session summaries
│
├── tests/                         ← Automated test suites (96 tests, 100% passing)
│   ├── test_features.py           ← Feature test suite (12 tests)
│   ├── test_advanced.py           ← Edge case & pipeline integration suite (44 tests)
│   ├── test_evals.py              ← Deterministic evals metrics suite (12 tests)
│   ├── test_refiner.py            ← Targeted agentic refinement suite (8 tests)
│   ├── test_judge.py              ← LLM judge & calibration suite (6 tests)
│   ├── test_research.py           ← Grounded research agent suite (9 tests)
│   └── test_genai_e2e.py          ← Consolidated end-to-end integration suite (5 tests)
│
├── assets/                        ← Generated assets, fonts bundle & image cache
└── output/                        ← Generated presentation builds (gitignored)
```

For complete architectural details, see the **[Documentation Hub](docs/README.md)**.

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
