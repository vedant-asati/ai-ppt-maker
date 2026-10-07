# Master Execution Plan — Phase-Wise Implementation
## Unifying UI, Content Quality, and Image Pipeline Plans

---

## 0. Current Codebase Inventory

Before we begin, here is exactly what exists and what each phase will touch:

### Existing Files (14 source files + 5 templates)

| File | Lines | Role | Status After All Phases |
|------|-------|------|------------------------|
| [schemas.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/schemas.py) | 21 | Pydantic data models | **HEAVY MODIFY** → ~120 lines |
| [config_manager.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/config_manager.py) | 59 | YAML loader | **HEAVY MODIFY** → ~150 lines |
| [planner.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/planner.py) | 187 | Gemini AI planner | **HEAVY MODIFY** → ~350 lines |
| [validator.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/validator.py) | 69 | Post-plan checks | **HEAVY MODIFY** → ~250 lines |
| [templater.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/templater.py) | 47 | Jinja2 HTML gen | **MODERATE MODIFY** → ~80 lines |
| [image_generator.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/image_generator.py) | 157 | Image gen/fallback | **HEAVY MODIFY** → ~300 lines |
| [renderer.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/renderer.py) | 38 | Playwright screenshots | **MODERATE MODIFY** → ~100 lines |
| [compiler.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/compiler.py) | 71 | PNG→PDF + notes | **MODERATE MODIFY** → ~120 lines |
| [cli.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/cli.py) | 179 | CLI entrypoint | **HEAVY MODIFY** → ~280 lines |
| [templates/base.html](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/templates/base.html) | 101 | Base HTML template | **HEAVY MODIFY** → ~350 lines |
| [templates/cover.html](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/templates/cover.html) | ~40 | Cover slide | **MODERATE MODIFY** |
| [templates/generic.html](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/templates/generic.html) | ~40 | Generic slide | **HEAVY MODIFY** |
| [templates/split.html](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/templates/split.html) | ~50 | Split slide | **HEAVY MODIFY** |
| [templates/infographic.html](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/templates/infographic.html) | ~40 | Infographic slide | **MODERATE MODIFY** |

### New Files to Create (12 files)

| File | Est. Lines | Created In Phase |
|------|-----------|-----------------|
| `theme_palettes.py` | ~100 | Phase 1A |
| `theme_resolver.py` | ~120 | Phase 1B |
| `narrative_arcs.py` | ~80 | Phase 3A |
| `audience_profiles.py` | ~70 | Phase 3A |
| `source_analyzer.py` | ~150 | Phase 3B |
| `content_scorer.py` | ~100 | Phase 5B |
| `gradient_generator.py` | ~150 | Phase 2C |
| `image_cache.py` | ~60 | Phase 2A |
| `image_validator.py` | ~80 | Phase 4B |
| `quality_checker.py` | ~200 | Phase 4A |
| `templates/quote.html` | ~60 | Phase 3C |
| `templates/stat.html` | ~60 | Phase 3C |
| `templates/timeline.html` | ~70 | Phase 3C |

---

## Dependency Graph

Understanding what depends on what is critical for ordering:

```
schemas.py ──────────────────────┐
  │                              │
  ├──→ config_manager.py         │
  │      │                       │
  │      ├──→ cli.py             │
  │      │     │                 │
  │      │     ├──→ planner.py ──┤
  │      │     │                 │
  │      │     ├──→ validator.py │
  │      │     │                 │
  │      │     ├──→ image_generator.py ──→ image_cache.py
  │      │     │     │                     gradient_generator.py
  │      │     │     │                     image_validator.py
  │      │     │     │
  │      │     ├──→ templater.py ──→ templates/*.html
  │      │     │
  │      │     ├──→ renderer.py ──→ quality_checker.py
  │      │     │
  │      │     └──→ compiler.py
  │      │
  │      └──→ theme_resolver.py ──→ theme_palettes.py
  │
  └──→ narrative_arcs.py
       audience_profiles.py
       source_analyzer.py
       content_scorer.py
```

**Critical path:** `schemas.py` → `config_manager.py` → `theme_palettes.py` → `theme_resolver.py` → `cli.py` pipeline reorder → everything else.

---

## Code Generation Strategy

> [!IMPORTANT]
> **Part-by-part generation rule:** Each sub-phase generates at most **2-3 files** and each file is written in a **single focused pass**. No sub-phase attempts to write more than ~300 lines of new code. If a file is large, it is split across sub-phases (e.g., `base.html` theme CSS is written theme-by-theme across Phase 2D).

---

## Phase 1 — Foundation (Backend, No Visual Changes)

**Goal:** Update the data layer so the rest of the pipeline can consume new schema fields, validated config, and curated theme palettes. The pipeline should still produce the SAME output as before at the end of this phase (backward compatible).

---

### Phase 1A — Schema Extension + Theme Palettes

**Source Plans:** UI Plan §4, Content Plan §2

**Files:**
- `[MODIFY]` [schemas.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/schemas.py)
- `[NEW]` `theme_palettes.py`

**Changes to `schemas.py`:**
1. Add `palette: Optional[str]` to `Theme` model
2. Expand `structural_class` Literal to include `dark_neon`, `gradient_flow`, `editorial`, `aurora`
3. Add `layout_variant: Optional[Literal['reverse']]` to `Slide`
4. Add `eyebrow: Optional[str]` to `Slide`
5. Add `slide_purpose: Optional[str]` to `Slide`
6. Add `image_role: Optional[Literal['background', 'supporting', 'data', 'decorative']]` to `Slide`
7. Add `narrative_weight: Optional[Literal['light', 'standard', 'heavy']]` to `Slide`
8. Add `content_blocks: Optional[List[ContentBlock]]` to `Slide` (ContentBlock = discriminated union)
9. Define `BulletBlock`, `StatBlock`, `PullQuoteBlock`, `ComparisonBlock`, `StepBlock`, `CalloutBlock`, `KeyValueBlock`
10. Keep `content_bullets` as a legacy field with deprecation path

**Changes to `theme_palettes.py`:**
- Full `PALETTES` dict with all 4 new themes × their palettes
- `DEFAULT_PALETTE` mapping
- `DARK_THEMES` / `LIGHT_THEMES` sets

**Verification:**
```bash
python -c "from schemas import MasterPlan, Slide, Theme; print('Schema OK')"
python -c "from theme_palettes import PALETTES, DEFAULT_PALETTE; print(f'{sum(len(v) for v in PALETTES.values())} palettes loaded')"
```

**Backward compat:** All new fields are `Optional` with defaults. Existing `master_plan.json` files parse without error.

---

### Phase 1B — Theme Resolver + Config Validation

**Source Plans:** UI Plan §1, §3

**Files:**
- `[NEW]` `theme_resolver.py`
- `[MODIFY]` [config_manager.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/config_manager.py)

**Changes to `theme_resolver.py`:**
- `ThemeResolver.resolve()` — merges palette + AI vars + user overrides
- `ThemeResolver.find_nearest_palette()` — snaps user color to nearest palette
- Helper methods: `hex_to_rgb`, `rgb_to_str`, `color_distance`, `darken`
- Aurora color distance validation
- Editorial contrast validation

**Changes to `config_manager.py`:**
- Add Pydantic `AppConfig` with sub-models: `PresentationGoals`, `DesignPreferences`, `ImagePreferences`, `OutputConfig`, `PipelineConfig`
- `load_and_validate()` returns `AppConfig` (typed) instead of raw dict
- Backward compat: if validation fails, fall back to raw dict with warning
- Update `DEFAULT_CONFIG_CONTENT` to list all 8 themes
- Keep `init_config()` working

**Verification:**
```bash
python -c "from config_manager import ConfigManager; c = ConfigManager.load_and_validate('config.yaml'); print(type(c))"
python -c "from theme_resolver import ThemeResolver; v, n = ThemeResolver.resolve('dark_neon', 'cyber_cyan', {}); print(f'Resolved {n}: {len(v)} vars')"
```

---

### Phase 1C — CLI + Pipeline Wiring (Foundation)

**Source Plans:** UI Plan §3 integration point, Image Plan §1A-1B

**Files:**
- `[MODIFY]` [cli.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/cli.py)

**Changes:**
1. Import and use `AppConfig` (with fallback to dict for backward compat)
2. Wire `ThemeResolver.resolve()` call between Phase 2 (Validation) and Phase 3 (Templating)
3. **Reorder pipeline:** Move image generation BEFORE templating
4. Add `--preview` flag (stub — just sets a flag, implementation in Phase 4)
5. Add `--clean-images` flag (stub)
6. Add `audit` subcommand (stub — parser only, no implementation)
7. Pass `image_manifest` to templater (empty dict for now until Phase 2A)

**The corrected pipeline order in cli.py:**
```
Phase 1: Planning     → master_plan (MasterPlan)
Phase 2: Validation   → validated master_plan
Phase 2.5: Theme Resolution → resolved CSS variables
Phase 3: Images       → image_manifest dict    ← MOVED UP
Phase 4: Templating   → HTML files (receives image_manifest)
Phase 5: Rendering    → PNG files
Phase 6: Compilation  → PDF + speaker notes
```

**Verification:**
```bash
python cli.py generate --offline-plan master_plan.json --dry-run  # should still work
python cli.py generate --help  # should show new flags
python cli.py audit --help  # should show audit subcommand
```

---

### Phase 1D — Validator Foundation Upgrade

**Source Plans:** UI Plan §6, Content Plan §22-31

**Files:**
- `[MODIFY]` [validator.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/validator.py)

**Changes:**
1. Layout-aware bullet caps: `cover=0, split=4, infographic=3, generic=6`
2. Cover title length check (>40 chars → warn about overflow)
3. `content_blocks` ↔ `content_bullets` migration: if `content_blocks` is empty but `content_bullets` exists, auto-wrap into a `BulletBlock`
4. Block × Layout compatibility checks (e.g., `ComparisonBlock` not on `cover`)
5. `requires_image=True` + `image_role` validation (set default role based on layout)

**Verification:**
```bash
python -c "
from schemas import MasterPlan
import json
with open('master_plan.json') as f:
    mp = MasterPlan(**json.load(f))
from validator import ContentValidator
mp2 = ContentValidator.validate_and_prune(mp)
print(f'Validated {len(mp2.slides)} slides')
"
```

**End of Phase 1 checkpoint:** The pipeline produces identical output to before. All new fields are optional. No visual changes. Run full generation to verify nothing is broken:
```bash
python cli.py generate --offline-plan master_plan.json
# Should produce the same PDF as before
```

---

## Phase 2 — Image Pipeline Overhaul

**Goal:** Fix the three broken things in image generation: pipeline ordering, caching, and offline fallback quality.

---

### Phase 2A — Image Cache + Manifest

**Source Plans:** Image Plan §3

**Files:**
- `[NEW]` `image_cache.py`
- `[MODIFY]` [image_generator.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/image_generator.py) (first pass — cache integration only)

**Changes to `image_cache.py`:**
- `ImageCache` class with `_load()`, `save()`, `_hash_prompt()`, `is_current()`, `record()`
- Stores `.image_cache.json` in `assets/`
- Checks prompt hash + file existence

**Changes to `image_generator.py` (pass 1):**
- Import and use `ImageCache`
- `generate_all()` now returns `image_manifest` dict
- Check cache before generating (skip if prompt unchanged)
- Check for user-provided images (`user_slide_N.{ext}`)
- Record every result (api/cache/fallback/user) in cache

**Verification:**
```bash
# Run generation twice — second run should show "[Cache] prompt unchanged"
python cli.py generate --offline-plan master_plan.json
python cli.py generate --offline-plan master_plan.json
# Check cache file exists:
cat assets/.image_cache.json
```

---

### Phase 2B — Rate Limiter + Priority Generation

**Source Plans:** Image Plan §6

**Files:**
- `[MODIFY]` [image_generator.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/image_generator.py) (second pass — rate limiting)

**Changes:**
1. Add `RateLimiter` class (token bucket, max_per_minute, max_wait_seconds)
2. `wait_if_needed()` — blocks or returns False
3. `record_success()`, `record_429()` with exponential backoff
4. Priority-based generation order: P0 (cover/split) → P1 (data images) → P2 (generic bg) → P3 (decorative, skip to fallback)
5. Post-generation summary with stats (API calls, cached, fallback, user)

**Verification:**
- Manually test by setting `max_per_minute=1` and generating a 5-slide deck
- Verify priority ordering: cover images generated first

---

### Phase 2C — Beautiful Offline Fallbacks

**Source Plans:** Image Plan §4

**Files:**
- `[NEW]` `gradient_generator.py`
- `[MODIFY]` [image_generator.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/image_generator.py) (third pass — replace `_generate_fallback`)

**Changes to `gradient_generator.py`:**
- `GradientGenerator.generate()` — theme-aware gradient with pattern overlay
- `_draw_gradient()` — linear gradient at any angle
- Pattern methods: `_add_circles` (glassmorphism), `_add_grid` (brutalism), `_add_dots` (corporate), `_add_glow` (dark_neon), `_add_shimmer` (aurora)
- Preset lookup per structural class

**Changes to `image_generator.py` (pass 3):**
- Replace `_generate_fallback()` → call `GradientGenerator.generate()`
- Pass theme info (structural_class, primary_color) to gradient generator
- Enhanced `_export_prompts()` with role-aware composition instructions

**Verification:**
```bash
# Generate with no API key → should produce beautiful gradients, not grey rectangles
GEMINI_API_KEY="" python cli.py generate --offline-plan master_plan.json --force-images
# Inspect assets/slide_1.png — should be a gradient, not grey
```

---

### Phase 2D — Templater Image Integration

**Source Plans:** Image Plan §1C, §2

**Files:**
- `[MODIFY]` [templater.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/templater.py)
- `[MODIFY]` [cli.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/cli.py) (wire image_manifest to templater)

**Changes to `templater.py`:**
- `generate_html()` accepts `image_manifest` parameter
- For each slide: extract `has_image`, `image_path`, `image_status`, `image_role` from manifest
- Pass these to template context
- Detect `assets/fonts/fonts.css` → pass `local_fonts_available`

**Changes to `cli.py`:**
- Pass `image_manifest` from `img_gen.generate_all()` to `templater.generate_html()`

**Verification:**
```bash
python cli.py generate --offline-plan master_plan.json
# Check temp_build/slide_001.html — should contain has_image-related conditionals
```

**End of Phase 2 checkpoint:** Images are generated BEFORE templates. Cache works. Fallbacks are beautiful gradients. Templates know which images exist.

---

## Phase 3 — Content Intelligence Engine

**Goal:** Make the AI Planner generate dramatically better content — richer content types, narrative structure, audience awareness, and source pre-processing.

---

### Phase 3A — Narrative Arcs + Audience Profiles

**Source Plans:** Content Plan §4, §5

**Files:**
- `[NEW]` `narrative_arcs.py`
- `[NEW]` `audience_profiles.py`

**Changes to `narrative_arcs.py`:**
- 7 arc templates: `problem_solution`, `before_after`, `what_why_how`, `journey`, `contrast`, `inverted_pyramid`, `showcase`
- Each has: name, best_for list, sequence (list of slide purposes), opening_move, closing_move

**Changes to `audience_profiles.py`:**
- 5 profiles: `investor`, `technical`, `executive`, `academic`, `general`
- Each has: expected_slides range, tone, stat_density, forbidden_patterns, preferred_blocks, image_style

**Verification:**
```bash
python -c "from narrative_arcs import ARCS; print(f'{len(ARCS)} arcs loaded')"
python -c "from audience_profiles import PROFILES; print(f'{len(PROFILES)} profiles loaded')"
```

---

### Phase 3B — Source Analyzer

**Source Plans:** Content Plan §6

**Files:**
- `[NEW]` `source_analyzer.py`

**Changes:**
- `SourceAnalyzer.analyze(source_text)` → `SourceBrief`
- Extracts: statistics (regex), quoted text, proper nouns, section headings, approximate word count
- Classifies source type: `thin_prompt`, `outline`, `article`, `data_heavy`, `narrative`
- Returns a `SourceBrief` dict that gets injected into the Planner prompt

**Verification:**
```bash
python -c "
from source_analyzer import SourceAnalyzer
brief = SourceAnalyzer.analyze('AI will transform 85% of industries by 2030, says McKinsey. Revenue grew from \$2B to \$8B.')
print(brief)
# Should extract: stats=['85%', '\$2B', '\$8B'], entities=['McKinsey'], source_type='thin_prompt'
"
```

---

### Phase 3C — Planner System Prompt Rewrite

**Source Plans:** Content Plan §3, §15-17; UI Plan §11

**Files:**
- `[MODIFY]` [planner.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/planner.py)

**Changes (this is the single most impactful change):**
1. Complete `SYSTEM_INSTRUCTION` rewrite with:
   - Theme selection guide (8 themes + palette names)
   - Layout sequencing rules (no 2 consecutive same layouts, cover first, etc.)
   - 17 content quality rules (active voice, no filler, parallel structure, etc.)
   - ContentBlock output format (typed blocks instead of flat bullets)
   - `image_role` assignment rules
   - `slide_purpose` assignment (opening_hook, problem, evidence, solution, etc.)
   - `eyebrow` usage guidance
   - `narrative_weight` assignment rules
2. Inject `SourceBrief` into the prompt (if available)
3. Inject audience profile constraints
4. Inject narrative arc sequence as guidance
5. Updated JSON output schema to include all new fields

**Verification:**
```bash
# Dry-run and inspect the master_plan.json
python cli.py generate --dry-run
cat master_plan.json | python -m json.tool | head -50
# Should show: palette, content_blocks, slide_purpose, image_role, eyebrow
```

> [!WARNING]
> **This is the riskiest change.** The system prompt rewrite may cause the AI to produce JSON that doesn't validate. Run multiple dry-run tests with different configs before proceeding. If the AI struggles with the expanded schema, simplify by making more fields optional.

---

### Phase 3D — New Templates (quote, stat, timeline)

**Source Plans:** Content Plan §9-11

**Files:**
- `[NEW]` `templates/quote.html`
- `[NEW]` `templates/stat.html`
- `[NEW]` `templates/timeline.html`

**Changes to `quote.html`:**
- Full-slide pull quote with large serif typography
- Attribution line below
- Background image support (image_role: background with heavy overlay)
- Eyebrow support
- Handles long quotes (>200 chars) with smaller font class

**Changes to `stat.html`:**
- 1-3 hero statistics layout with adaptive grid (1 stat = centered, 2 = side-by-side, 3 = row)
- Large `value` text + small `label` + optional `context`
- Accent color on value, muted on context

**Changes to `timeline.html`:**
- Horizontal timeline with connected nodes
- Each node from a `StepBlock` (step_number, title, description)
- 2-5 steps supported, auto-scales spacing
- Responsive to theme (neon glow on nodes for dark_neon, etc.)

**Verification:**
```bash
# Create a test master_plan.json with the new layout types and render
python cli.py generate --offline-plan test_new_layouts.json
# Visually inspect the output PDF
```

---

## Phase 4 — Visual Design System

**Goal:** Implement the 4 new advanced themes, design tokens, and the QA/audit layer.

---

### Phase 4A — Design Tokens + Base Template Overhaul

**Source Plans:** UI Plan §5

**Files:**
- `[MODIFY]` [templates/base.html](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/templates/base.html)

**Changes (generate in 2 parts to stay under token limits):**

**Part 1 — Design tokens + existing themes:**
- Add spacing scale (`--sp-1` through `--sp-9`)
- Add type scale (`--type-xs` through `--type-3xl`)
- Add structural variables (`--card-bg`, `--card-shadow`, `--card-radius`, `--card-border`, `--card-backdrop`, `--rule-color`, `--glow`, `--title-glow`, `--text-glow`)
- Update existing 4 themes (minimalist, glassmorphism, neo_brutalism, corporate_clean) to use token system
- Conditional font loading (per-theme Google Fonts links)

**Part 2 — New themes + new element styles:**
- `dark_neon` CSS block (glow effects, neon markers, Space Grotesk font)
- `gradient_flow` CSS block (gradient background, gradient-clip titles, Plus Jakarta Sans)
- `editorial` CSS block (Playfair Display, vertical rules, ghost numbers, em-dash bullets)
- `aurora` CSS block (shimmer radial gradients, Archivo Black, gradient rule bars)
- Eyebrow CSS (`.slide-eyebrow`)
- ContentBlock CSS (`.callout-block`, `.comparison-block`, `.stat-value`, etc.)

**Verification:**
```bash
# Render with each of the 8 themes and visually inspect
for theme in minimalist glassmorphism neo_brutalism corporate_clean dark_neon gradient_flow editorial aurora; do
  echo "Testing theme: $theme"
  # (would need a test plan with each structural_class set)
done
```

---

### Phase 4B — Existing Template Updates

**Source Plans:** UI Plan §6, Image Plan §2

**Files (each updated separately):**
- `[MODIFY]` [templates/cover.html](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/templates/cover.html)
- `[MODIFY]` [templates/generic.html](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/templates/generic.html)
- `[MODIFY]` [templates/split.html](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/templates/split.html)
- `[MODIFY]` [templates/infographic.html](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/templates/infographic.html)

**Changes per template:**

| Template | Image Composition | Content Blocks | Theme Edge Cases |
|----------|------------------|----------------|------------------|
| `cover.html` | No-image dark theme fallback (radial gradient); per-theme overlay gradients | Eyebrow support | Long title auto-shrink; gradient_flow overlay; aurora overlay; dark_neon overlay |
| `generic.html` | 4 image composition modes (background, supporting, data, decorative) | BulletBlock, StatBlock, CalloutBlock, ComparisonBlock, KeyValueBlock renderers | Aurora z-index; gradient_flow @supports; editorial padding reset |
| `split.html` | No-image fallback (full-width text); `layout_variant: reverse` | BulletBlock, CalloutBlock, StepBlock renderers | Editorial column divider; reverse flex-direction |
| `infographic.html` | Data image mode (replaces card grid) | StatBlock in info cards; dynamic grid (1/2/3 cols) | Editorial ghost numbers; dark_neon glow cap |

**Code generation order (one template per pass):**
1. `cover.html` — smallest changes
2. `split.html` — reverse layout + no-image fallback
3. `infographic.html` — dynamic grid + stat cards
4. `generic.html` — most complex (all content block renderers + all image modes)

**Verification after each template:**
```bash
python cli.py generate --offline-plan master_plan.json
# Visually inspect the specific slide that uses that template
```

---

### Phase 4C — QA & Design Audit Pipeline

**Source Plans:** UI Plan §8, §9, §10, §14

**Files:**
- `[MODIFY]` [renderer.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/renderer.py)
- `[NEW]` `quality_checker.py`
- `[NEW]` `image_validator.py`

**Changes to `renderer.py`:**
1. Detect missing Playwright at import time (not at render time)
2. Timeout handling: `networkidle` with fallback to `domcontentloaded`
3. DOM audit JavaScript injection (runs BEFORE screenshot)
4. Returns tuple: `(png_paths, dom_audit_results)`
5. Cache DOM audit to `temp_build/dom_audit.json`
6. Preview mode: 960×540 resolution, first 3 slides only

**Changes to `quality_checker.py`:**
- `SlideAuditResult` dataclass
- Layer 1: DOM audit parser (from cached `dom_audit.json`)
- Layer 2: PIL visual metrics (contrast, brightness, color diversity, edge density, balance, top-focus)
- Layer 3: AI design critic (Gemini multi-image prompt — optional, triggered by `--level ai`)
- Report writer: generates `design_audit.md` with per-slide tables

**Changes to `image_validator.py`:**
- `ImageValidator.validate()` — dimension, aspect ratio, brightness, contrast, center complexity, file size checks
- `ImageValidator.auto_fix()` — resize, crop to 16:9
- Integration: called in `image_generator.py` after every API-generated image

**Changes to `cli.py` (wire audit):**
- Implement `audit` subcommand (parser was stubbed in Phase 1C)
- `--level quick|full|ai`
- `--preview` flag implementation
- Unpack renderer tuple: `png_files, dom_results = renderer.render_all(...)`

**Verification:**
```bash
python cli.py generate --offline-plan master_plan.json
python cli.py audit --level full
cat design_audit.md
```

---

## Phase 5 — Content Quality Refinement

**Goal:** Close the loop on content quality with scoring, prose checks, and enhanced speaker notes.

---

### Phase 5A — Validator Deep Upgrade

**Source Plans:** Content Plan §22-31

**Files:**
- `[MODIFY]` [validator.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/validator.py)

**Changes:**
1. Prose quality checks: filler word detection (list of ~30 banned phrases), passive voice detector (regex-based), parallel structure check
2. Density-aware word count validation (title max 8 words, bullet max 25 words)
3. Deck balance checker: no more than 2 consecutive same layout_type, weight pacing
4. Title repetition detector (flag if >30% word overlap between slide titles)
5. Speaker note transition checker (adjacent slides should have "next"/"now"/"let's" connectors)
6. Stat hallucination guard: if source is `thin_prompt` and slide has StatBlock, warn
7. ComparisonBlock symmetry check (left_items and right_items should have same count)
8. PullQuoteBlock length → font class mapping (<80 chars = large, 80-150 = medium, >150 = small)

---

### Phase 5B — Content Scoring

**Source Plans:** Content Plan §21

**Files:**
- `[NEW]` `content_scorer.py`

**Changes:**
- 7-metric rubric: content_type_variety, narrative_coherence, information_density, typography_diversity, image_purposefulness, prose_quality, audience_alignment
- Each metric scored 1-10
- Composite score = weighted average
- Score display in `--dry-run` output
- Score included in speaker notes header

---

### Phase 5C — Enhanced Speaker Notes & Export

**Source Plans:** Content Plan §37-39

**Files:**
- `[MODIFY]` [compiler.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/compiler.py)

**Changes:**
1. Speaker notes format upgrade: time estimates per slide (based on word count), transition phrases between slides
2. Block-type summary per slide
3. Image status per slide (API/cache/fallback/user)
4. Content quality score in the notes header
5. Dry-run image status display

---

## Phase 6 — Polish & Documentation

**Goal:** Update docs, config reference, README, and ensure everything is production-ready.

---

### Phase 6A — Config & Documentation

**Files:**
- `[MODIFY]` [config_reference.yaml](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/config_reference.yaml) — all new keys documented
- `[MODIFY]` [README.md](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/README.md) — theme gallery, audit docs, content quality section
- `[MODIFY]` `requirements.txt` — add `numpy` (for quality_checker)

### Phase 6B — Font Download Subcommand

**Source Plans:** UI Plan §7 Phase B

**Files:**
- `[MODIFY]` [cli.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/cli.py) — `fonts` subcommand
- `[MODIFY]` [config_manager.py](file:///home/intruder-jsr/exps/text-extraction/misc/ppt-maker/config_manager.py) — font download logic

### Phase 6C — Final Integration Test

**Verification matrix:**
```
8 themes × 4 layouts = 32 combinations to test
+ 3 new templates × 8 themes = 24 more
= 56 total visual combinations

Test with:
- --dry-run (schema validation)
- --offline-plan (full render, no API)
- --force-images (regeneration)
- --preview (half-res, 3 slides)
- audit --level full (QA pipeline)
```

---

## Summary: Execution Order with Estimated Effort

| Phase | Sub-Phase | Files | New Lines (est.) | Depends On |
|-------|-----------|-------|-----------------|------------|
| **1A** | Schema + Palettes | 2 | ~220 | — |
| **1B** | ThemeResolver + Config | 2 | ~270 | 1A |
| **1C** | CLI Wiring | 1 | ~100 | 1A, 1B |
| **1D** | Validator Foundation | 1 | ~100 | 1A |
| | | | | |
| **2A** | Image Cache | 2 | ~160 | 1C |
| **2B** | Rate Limiter | 1 | ~100 | 2A |
| **2C** | Gradient Fallbacks | 2 | ~200 | 2A |
| **2D** | Templater Integration | 2 | ~50 | 2A, 2C |
| | | | | |
| **3A** | Arcs + Profiles | 2 | ~150 | 1A |
| **3B** | Source Analyzer | 1 | ~150 | — |
| **3C** | Planner Rewrite | 1 | ~200 | 1A, 3A, 3B |
| **3D** | New Templates | 3 | ~190 | 1A, 4A |
| | | | | |
| **4A** | Design Tokens + base.html | 1 | ~250 | 1A, 1B |
| **4B** | Template Updates | 4 | ~300 | 4A, 2D |
| **4C** | QA Pipeline | 3+1 | ~380 | 4B |
| | | | | |
| **5A** | Validator Deep Upgrade | 1 | ~180 | 1D, 3C |
| **5B** | Content Scoring | 1 | ~100 | 5A |
| **5C** | Enhanced Notes | 1 | ~50 | 5B |
| | | | | |
| **6A** | Docs | 3 | ~200 | all |
| **6B** | Font Download | 2 | ~80 | 4A |
| **6C** | Integration Test | — | — | all |

**Total: ~3,430 new/modified lines across 12 new files + 14 modified files**

---

## Parallel vs. Sequential Tracks

Some phases can be done in parallel:

```
TRACK A (Data + Pipeline):          TRACK B (Content Intelligence):
  Phase 1A (Schema)                   Phase 3A (Arcs + Profiles)
       ↓                              Phase 3B (Source Analyzer)
  Phase 1B (ThemeResolver)                  ↓
       ↓                              Phase 3C (Planner Rewrite)
  Phase 1C (CLI Wiring)                     ↓
       ↓                              Phase 3D (New Templates)
  Phase 1D (Validator)                      ↓
       ↓                              Phase 5A (Validator Deep)
  Phase 2A-2D (Image Pipeline)        Phase 5B (Content Scoring)
       ↓                              Phase 5C (Enhanced Notes)
  Phase 4A (Design Tokens)
       ↓
  Phase 4B (Template Updates)
       ↓                         ←── both tracks merge here
  Phase 4C (QA Pipeline)
       ↓
  Phase 6 (Polish)
```

> [!TIP]
> **Recommended execution:** Do Track A first (Phases 1→2→4), then Track B (Phases 3→5), then Phase 6. This way you always have a working, renderable pipeline at every checkpoint.

---

## Checkpoint Gates

After each major phase, we verify the pipeline still works:

| Gate | Test Command | Expected Result |
|------|-------------|-----------------|
| After Phase 1 | `python cli.py generate --offline-plan master_plan.json` | Same PDF as before (backward compat) |
| After Phase 2 | Same + `--force-images` with no API key | Beautiful gradient fallbacks instead of grey |
| After Phase 3 | `python cli.py generate --dry-run` | master_plan.json has content_blocks, image_role, eyebrow |
| After Phase 4 | Render with `--offline-plan` using each theme | All 8 themes render correctly |
| After Phase 5 | `python cli.py generate --dry-run` | Content quality score printed |
| After Phase 6 | `python cli.py audit --level full` | design_audit.md generated with per-slide scores |

---

> [!IMPORTANT]
> **Code generation chunking rule:** When implementing, each sub-phase is a single focused coding session. Never attempt to write more than 2-3 files or ~300 lines in one pass. If a file is larger (like `base.html` at ~350 lines), split across two passes (tokens first, then theme CSS blocks one-by-one).
