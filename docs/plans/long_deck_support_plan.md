# Plan: 10-15 Slide Deck Support & Customizable Slide Count

**Status**: Designed — pending implementation  
**Session**: July 2026  
**Trigger**: User regularly needs 10-15 slide decks; current default is ~5-6.

---

## Background

The pipeline already has `slide_count` in config schema (`ge=1, le=50`) and page numbering
that works for any count. The gap is in **design guidance, token budgets, and validation**
for longer decks — without changes, longer decks suffer from layout monotony, arc
overflow, and potential JSON truncation.

---

## What Already Works (No Changes Needed)
- `slide_count` field exists in config schema ✅
- Planner formula: `max(6, duration)` when not specified ✅
- Page numbering: `"02 / 15"` format works for any count ✅
- `total_slides` injected into Jinja2 context ✅

---

## Edge Cases

### 🔴 Critical

| Edge Case | Root Cause | Fix |
|-----------|-----------|-----|
| **Token truncation** — 15 slides × ~800 tokens each = 12K+ output tokens | `max_output_tokens=12000` | Dynamic budget: `12000 if n≤8 else 20000` |
| **Image rate limit stall** — 15 images at 5 RPM = 3-min pipeline stall | Hard 5 RPM cap | Smart budget: API only for P0+P1 (top 8), rest to gradient |
| **Layout monotony** — Planner reuses `generic`/`split` for 80% of slides | Rule 14 only bans 3-consecutive | Scale-aware rule: no 2-consecutive for 8+ slides; 5+ layout types for 10+ |
| **Narrative arc too short** — Arcs have 6-8 roles, 15-slide deck has no guidance for slots 9-15 | Arcs not scaled | Add `extended_roles` to each arc; inject when `slide_count > base_count` |

### 🟡 Important

| Edge Case | Root Cause | Fix |
|-----------|-----------|-----|
| **Config not visible** — `slide_count` hidden in config_reference.yaml only | Init template omits it | Add `slide_count: 10` to `DEFAULT_CONFIG_CONTENT` |
| **Source analyzer overrides user count** — estimates 5 slides for short text, planner follows that | Prompt injection conflict | When user specifies count, replace "Suggested: N" with "Suggested: {user_count} (user-specified)" |
| **Validator too lenient** — only checks "3 consecutive same" layouts | Fixed threshold | Add n-aware checks: min variety threshold, min light slides |
| **Quality scorer doesn't scale** — `unique_layouts * 2` gives max score at 5 unique, ignores 15-slide context | Fixed formula | Scale scoring: for 10+ slides, need 7 unique for max score |
| **Image matcher token budget** — 15 slides + 15 images = ~25K vision tokens in one call | No limit | Cap at 12 images per call; batch if more |
| **No gradient variety** — 15 gradient fallbacks same color | Fixed primary color | Rotate gradient style (diagonal/radial/horizontal/vertical) by slide position |

### 🟢 Minor
- Speaker notes file grows large (15 slides × 5 sentences) — acceptable, no fix needed
- PDF file size ~10MB for 15 slides — acceptable
- `--preview` renders first 3 slides — works fine for any count

---

## Proposed Changes

### 1. CLI & Config — Visibility

**File**: `cli.py`
```python
gen_parser.add_argument("--slides", type=int, default=None,
                        help="Number of slides (overrides config). Range: 3-20.")
# In handler:
if args.slides:
    config.setdefault('presentation_goals', {})['slide_count'] = args.slides
```

**File**: `config_manager.py` — Update `DEFAULT_CONFIG_CONTENT`:
```yaml
presentation_goals:
  audience: "General"
  duration_minutes: 10
  slide_count: 10        # 3–20 slides. Leave blank for auto (1 per minute).
```

---

### 2. Planner — Smart Prompting for Long Decks

**File**: `planner.py`

**A. Dynamic token budget:**
```python
target_slides = slide_count or max(6, duration)
max_tokens = 12000 if target_slides <= 8 else 20000
```

**B. Layout rhythm guide** — new function `_layout_rhythm_guide(n)`:

For 10 slides:
```
Pos 1:  cover
Pos 2:  split or generic        ← exposition
Pos 3:  stat or infographic     ← first impact moment
Pos 4:  generic or split        ← core argument
Pos 5:  quote                   ← breathing room (narrative_weight=light)
Pos 6:  split or generic        ← deeper dive
Pos 7:  infographic or timeline ← structured data / process
Pos 8:  stat or quote           ← second impact moment (narrative_weight=light)
Pos 9:  generic or split        ← synthesis / implications
Pos 10: split or generic        ← call to action
```

For 13-15 slides, the pattern scales by inserting extra exposition/evidence blocks
in the middle, keeping the rhythm of "2-3 content slides → 1 breathing room slide".

**C. Scale-aware Rule 14 replacement:**
```
LAYOUT VARIETY RULES (scale-aware):
- For 5-7 slides:  No 3 consecutive same layouts. Use ≥3 layout types.
- For 8-12 slides: No 2 consecutive same layouts. Use ≥5 layout types.
                   Include ≥2 slides with narrative_weight='light'.
- For 13+ slides:  No 2 consecutive same layouts. Use ≥6 layout types.
                   Include ≥3 slides with narrative_weight='light'.
                   Group into 3-4 thematic sections using consistent eyebrow labels.
```

**D. Section guidance for 10+ slides** (injected into prompt):
```
SECTION STRUCTURE FOR {n}-SLIDE DECK:
Organize into 3-4 named sections. Each section: 2-4 slides.
Use consistent eyebrow labels per section (e.g. "Context", "Evidence", "Impact", "Next Steps").
Each section should open with a different layout than the previous section ended with.
```

**E. Source analyzer override:**
```python
if slide_count and source_analysis_block:
    source_analysis_block = source_analysis_block.replace(
        f"Suggested slide count: {signals.estimated_slides}",
        f"Suggested slide count: {slide_count} (user-specified — follow this exactly)"
    )
```

---

### 3. Narrative Arcs — Extended Roles

**File**: `narrative_arcs.py`

Add `extended_roles` to each arc for 10-15 slide decks. Updated `arc_for_prompt(arc_name, slide_count)` uses extended roles when needed.

Example for `problem_solution`:
```python
"extended_roles": [
    "problem_deep_dive",      # expand on problem with more evidence
    "evidence_2",             # secondary evidence / different angle
    "solution_demo",          # show it working in practice
    "competitive_landscape",  # how alternatives fall short
    "implementation_steps",   # practical steps / timeline
    "team_or_credibility",    # why this team/you can deliver
    "summary",                # recap before CTA
]
```

Merge strategy: base roles 1..N-1 + extended roles + base role N (CTA always last).

---

### 4. Validator — Scale-Aware Checks

**File**: `validator.py`

In `_check_deck_structure()`:
```python
n = len(slides)

# For 10+ slides: minimum layout variety
if n >= 10:
    unique_layouts = len(set(s.layout_type for s in slides))
    min_variety = 5 if n <= 12 else 6
    if unique_layouts < min_variety:
        print(f"  [Warn] {n}-slide deck: only {unique_layouts} layout types (need ≥{min_variety}).")

# For 10+ slides: minimum breathing room
if n >= 10:
    light = sum(1 for s in slides if s.narrative_weight == 'light')
    min_light = 2 if n <= 12 else 3
    if light < min_light:
        print(f"  [Warn] {n}-slide deck: {light} light slides (need ≥{min_light}).")

# For 8+ slides: warn on 2 consecutive same layouts (not just 3)
if n >= 8:
    for i in range(len(slides) - 1):
        if slides[i].layout_type == slides[i+1].layout_type:
            print(f"  [Warn] Slides {slides[i].slide_number}-{slides[i+1].slide_number}: "
                  f"2 consecutive '{slides[i].layout_type}' layouts.")
```

---

### 5. Image Generator — Budget & Gradient Variety

**File**: `image_generator.py`

**A. Smart image budget for large decks:**
```python
api_budget = min(8, len(slides_needing_images)) if len(slides_needing_images) > 8 else None
# Sort by priority; only top api_budget slides get API calls
```

**B. Gradient variety:**
The `GradientGenerator` uses `slide_number` as seed. Add `gradient_style` cycling
(diagonal/radial/horizontal/vertical) so 15 gradient fallbacks look visually distinct.

---

### 6. Image Matcher — Batching for Large Decks

**File**: `image_matcher.py`

For 15+ images, vision token budget can be ~25K+. Add batching:
```python
MAX_IMAGES_PER_CALL = 12
if len(images) > MAX_IMAGES_PER_CALL:
    # Split into two calls; merge results, keeping highest-confidence assignments
    batch1 = images[:MAX_IMAGES_PER_CALL]
    batch2 = images[MAX_IMAGES_PER_CALL:]
    result1 = self._match_with_gemini(batch1, slides, ...)
    result2 = self._match_with_gemini(batch2, slides, ...)
    # Merge: for slides matched by both, keep higher confidence
```

---

### 7. Quality Checker — Scale-Aware Scoring

**File**: `quality_checker.py`

In `_score_deck_design()`:
```python
# Layout variety — scale-aware
unique_layouts = len(set(layouts))
if n <= 7:
    variety_score = min(10, unique_layouts * 2)       # 5 unique = 10/10
else:
    target = 7 if n >= 13 else 5                       # needs 7 for 10/10 in long decks
    variety_score = min(10, int(unique_layouts / target * 10))
```

---

## File Change Summary

| File | Change Type | Key Change |
|------|------------|-----------|
| `cli.py` | MODIFY | `--slides N` flag |
| `config_manager.py` | MODIFY | `slide_count: 10` in init template |
| `planner.py` | MODIFY | Dynamic tokens, layout rhythm guide, scale-aware rules, source override |
| `narrative_arcs.py` | MODIFY | `extended_roles` per arc + scaled `arc_for_prompt()` |
| `validator.py` | MODIFY | Scale-aware structural checks |
| `image_generator.py` | MODIFY | Smart image budget + gradient variety |
| `image_matcher.py` | MODIFY | Batch calls for 12+ images |
| `quality_checker.py` | MODIFY | Scale-aware layout variety scoring |

---

## Verification

### Tests to Add (`tests/test_pdf_quality.py`)
- `test6_tech_12slides` — 12-slide technical deck, assert:
  - ≥5 layout types used
  - No 2+ consecutive same layouts
  - ≥2 breathing room slides
  - No JSON truncation

### Manual Checks
1. `python cli.py generate --slides 12` → verify PDF visual variety
2. `python cli.py generate --slides 15 --pptx` → verify PPTX has all 15 slides
3. Run regression: existing 5-slide decks still A+
4. Confirm `--slides 5` produces identical result to omitting the flag
