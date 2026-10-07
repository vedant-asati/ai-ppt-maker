# Content Generation Quality Improvement Plan
## Making Every Slide Feel Like a Designer + Writer Made It

---

## 0. The Problem Statement

Look at the current `master_plan.json` output. Every slide has the same structure:
- `title` → plain text
- `subtitle` → plain text
- `content_bullets` → a flat list of strings

**This is the content equivalent of a bulleted Word document.** Premium presentations don't work this way. Real McKinsey decks, Airbnb pitch decks, Apple keynotes — they use:
- Hero statistics with context ("$2.3B → 400% ROI")
- Pull quotes ("The best camera is the one you have with you — Steve Jobs")
- Before/After comparisons
- Process steps with connectors
- Single-idea "billboard" slides
- Data callouts (one big number, one sentence of context)
- Timeline narratives

**Premiumness = Content Type Variety × Narrative Arc × Information Density Control × Typography Diversity × Image Purposefulness**

This plan addresses all five dimensions.

---

## 1. The Five Dimensions of Premium Content

### Dimension 1: Content Type Variety
Bullet lists are the lowest-information-density content format for slides. They pack information linearly with no visual differentiation. Premium slides choose the *right content format* for each piece of information.

### Dimension 2: Narrative Arc
A premium deck tells a story with deliberate structure. The audience should feel a journey, not a data dump. Different presentation goals have different arc patterns.

### Dimension 3: Information Density Control
Every slide has one *primary message* — everything else is supporting. The "one idea per slide" principle with deliberate whitespace is a hallmark of professional design.

### Dimension 4: Typography Diversity
Not just font family — weight variation, size contrast, letter-spacing, line-height, and text role (heading vs. label vs. body vs. accent) all signal quality.

### Dimension 5: Image Purposefulness
Images should complement and reinforce the content semantically, not just fill whitespace. A chart image on a data slide, a human face on an empathy slide, an abstract texture on a concept slide — purposeful, not decorative.

---

## 2. Expanded Slide Schema — `schemas.py`

The biggest lever: give the Planner a richer vocabulary of what a slide can contain.

### 2A. Content Blocks (replace flat `content_bullets`)

Instead of a flat `List[str]`, slides get typed content blocks:

```python
# schemas.py

from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Union

class BulletBlock(BaseModel):
    block_type: Literal['bullets'] = 'bullets'
    items: List[str] = Field(description="Concise bullet points. Max 6 items, 120 chars each.")

class StatBlock(BaseModel):
    block_type: Literal['stat'] = 'stat'
    value: str         # e.g. "400%", "$2.3B", "10x"
    label: str         # e.g. "ROI Improvement", "Annual Revenue", "Speed Increase"
    context: Optional[str] = None   # e.g. "vs. industry average of 120%"

class PullQuoteBlock(BaseModel):
    block_type: Literal['pullquote'] = 'pullquote'
    quote: str         # the quote text
    attribution: Optional[str] = None   # "— Steve Jobs, Apple"

class ComparisonBlock(BaseModel):
    block_type: Literal['comparison'] = 'comparison'
    left_label: str    # e.g. "Before", "Traditional", "Competitor"
    left_items: List[str]
    right_label: str   # e.g. "After", "AI-Assisted", "Our Approach"
    right_items: List[str]

class StepBlock(BaseModel):
    block_type: Literal['steps'] = 'steps'
    steps: List[str]   # Ordered process steps (numbered automatically)
    connector_style: Literal['arrow', 'numbered', 'dotted'] = 'numbered'

class DataCalloutBlock(BaseModel):
    block_type: Literal['callout'] = 'callout'
    primary: str       # Big central message: "3x faster"
    secondary: str     # Supporting sentence: "vs. the previous workflow"

class KeyValueBlock(BaseModel):
    block_type: Literal['keyvalue'] = 'keyvalue'
    pairs: List[dict]  # [{"key": "Founded", "value": "2019"}, ...]

# Union type for all block types
ContentBlock = Union[
    BulletBlock, StatBlock, PullQuoteBlock, ComparisonBlock,
    StepBlock, DataCalloutBlock, KeyValueBlock
]
```

### 2B. Extended Slide Model

```python
class Slide(BaseModel):
    slide_number: int
    layout_type: Literal['cover', 'split', 'infographic', 'generic', 'quote', 'stat', 'timeline']
    layout_variant: Optional[Literal['reverse', 'wide', 'centered']] = None
    
    # Content
    title: str
    subtitle: Optional[str] = None
    eyebrow: Optional[str] = None   # small label above title: "CHAPTER 2 · CHALLENGES"
    content_blocks: List[ContentBlock] = []  # replaces content_bullets
    
    # Legacy fallback — kept for backward compat with existing master_plan.json files
    content_bullets: List[str] = []

    # Narrative metadata
    slide_purpose: Literal[
        'hook', 'context', 'problem', 'solution', 'evidence',
        'comparison', 'process', 'data', 'quote', 'summary', 'cta'
    ] = 'context'
    narrative_weight: Literal['heavy', 'medium', 'light'] = 'medium'
    # 'heavy' = lots of content, dense; 'light' = one idea, lots of whitespace

    # Speaker support
    speaker_notes: str
    talking_time_seconds: Optional[int] = None  # estimated speaking time for this slide
    
    # Visuals
    requires_image: bool
    image_prompt: Optional[str] = None
    image_role: Optional[Literal['background', 'supporting', 'data', 'decorative']] = None
    # image_role tells the renderer HOW the image should be composited:
    # 'background' = full bleed behind text
    # 'supporting' = shown alongside content (split layout)
    # 'data' = a chart or diagram that IS the content
    # 'decorative' = texture or abstract element
```

### New Layout Types

| Layout | Purpose |
|--------|---------|
| `quote` | Full-slide pull quote — large text, attribution, optional background image |
| `stat` | 1–3 large hero statistics centered on slide |
| `timeline` | Horizontal or vertical timeline with events and descriptions |
| (existing) `cover`, `split`, `infographic`, `generic` | Unchanged |

---

## 3. Narrative Arc System

### 3A. Arc Templates in Config

The user specifies a narrative arc in config — the Planner uses it to sequence slides purposefully:

```yaml
# config.yaml
presentation_goals:
  narrative_arc: "problem_solution"  # see options below
  key_message: "AI tools save 10x time on presentation creation"
  desired_outcome: "audience books a demo"
```

### 3B. Arc Library

```python
# narrative_arcs.py — used in planner.py system prompt

NARRATIVE_ARCS = {
    "problem_solution": {
        "description": "Classic persuasive structure",
        "sequence": ["hook", "context", "problem", "solution", "evidence", "cta"],
        "best_for": "pitches, proposals, advocacy"
    },
    "before_after_bridge": {
        "description": "Show the transformation",
        "sequence": ["hook", "before", "after", "how", "evidence", "cta"],
        "best_for": "product demos, case studies, personal stories"
    },
    "context_analysis_recommendation": {
        "description": "Executive consulting structure",
        "sequence": ["context", "data", "analysis", "insight", "recommendation", "next_steps"],
        "best_for": "board presentations, strategy decks, reports"
    },
    "five_acts": {
        "description": "Storytelling narrative",
        "sequence": ["setup", "conflict", "rising_action", "climax", "resolution"],
        "best_for": "keynotes, TEDx-style talks, brand stories"
    },
    "listicle": {
        "description": "Top N list format",
        "sequence": ["hook", "point_1", "point_2", "...", "summary"],
        "best_for": "educational content, listicle presentations"
    },
    "data_story": {
        "description": "Numbers-first narrative",
        "sequence": ["hook_stat", "context", "data_deep_dive", "insight", "implication", "cta"],
        "best_for": "quarterly reviews, analyst presentations, research"
    },
    "empathy_map": {
        "description": "Human-centered storytelling",
        "sequence": ["introduce_person", "their_problem", "their_feeling", "solution", "outcome"],
        "best_for": "UX research, nonprofit pitches, social impact"
    },
}
```

### 3C. Slide Purpose → Content Type Mapping

The Planner uses this matrix to pick the right content block for each slide's purpose:

| Slide Purpose | Preferred Content Types | Avoid |
|--------------|------------------------|-------|
| `hook` | `callout`, `pullquote`, single hero `stat` | Long bullet lists |
| `problem` | `comparison` (before/after), `bullets` (pain points) | Stats without context |
| `solution` | `steps`, `bullets` (benefits) | `pullquote` |
| `evidence` | `stat` × 3, `comparison`, `data` image | Bullets alone |
| `data` | `stat`, `keyvalue`, data-heavy image | Dense paragraph text |
| `quote` | `pullquote` exclusively | Any other block |
| `process` | `steps`, `infographic` layout | `pullquote` |
| `cta` | `callout` (big text), single `stat` | Long bullets |
| `summary` | `bullets` (3 max), `keyvalue` | New information |

---

## 4. Information Density Control

### 4A. `narrative_weight` Field

Each slide has a `narrative_weight: 'heavy' | 'medium' | 'light'`.

Templates adapt:
- **`light`**: Larger title, minimal content, maximum whitespace. One idea only.
  - Padding: 15% of slide area on each side
  - Max content: 1 block, 3 bullets
- **`medium`**: Standard layout. Current behavior.
- **`heavy`**: Tighter padding, can support 2 blocks side-by-side (e.g., bullets + stat).
  - Padding: 8% of slide area
  - Max content: 2 blocks, 6 bullets total

### 4B. Density Rules in Validator

```python
# validator.py — density-aware validation

DENSITY_RULES = {
    # (layout_type, narrative_weight): max_total_words
    ('cover',        'light'):  12,
    ('cover',        'medium'): 25,
    ('quote',        'light'):  40,  # quote text can be longer
    ('stat',         'light'):  15,  # label + context only
    ('stat',         'medium'): 30,
    ('generic',      'light'):  60,
    ('generic',      'medium'): 120,
    ('generic',      'heavy'):  200,
    ('infographic',  'light'):  90,
    ('infographic',  'medium'): 150,
    ('split',        'medium'): 100,
    ('timeline',     'medium'): 200,
}

def count_words_in_slide(slide: Slide) -> int:
    total = len(slide.title.split())
    if slide.subtitle:
        total += len(slide.subtitle.split())
    if slide.eyebrow:
        total += len(slide.eyebrow.split())
    for block in slide.content_blocks:
        if hasattr(block, 'items'):
            total += sum(len(b.split()) for b in block.items)
        if hasattr(block, 'quote'):
            total += len(block.quote.split())
        # etc.
    return total

# Check in validate_and_prune:
for slide in master_plan.slides:
    key = (slide.layout_type, slide.narrative_weight)
    max_words = DENSITY_RULES.get(key)
    if max_words and count_words_in_slide(slide) > max_words:
        print(f"  [Warning] Slide {slide.slide_number}: {count_words_in_slide(slide)} words "
              f"exceeds density limit of {max_words} for {slide.layout_type}/{slide.narrative_weight}.")
        # Auto-truncate content_blocks or warn user
```

### 4C. Deck-Level Balance Checker

```python
# In validator.py — after processing all slides:
def check_deck_balance(master_plan: MasterPlan):
    layout_counts = Counter(s.layout_type for s in master_plan.slides)
    total = len(master_plan.slides)

    # Generic shouldn't dominate (>50%)
    if layout_counts.get('generic', 0) / total > 0.5:
        print(f"  [Warning] Deck balance: {layout_counts['generic']}/{total} slides are 'generic' layout."
              f" Consider adding infographic or stat slides for variety.")

    # Should have at least one light-weight slide (breathing room)
    light_slides = sum(1 for s in master_plan.slides if s.narrative_weight == 'light')
    if light_slides == 0 and total > 4:
        print(f"  [Warning] No 'light' slides in deck. Add a quote or callout slide for pacing.")

    # Check for consecutive same-layout (already in planner prompt, but double-check)
    for i in range(1, len(master_plan.slides)):
        if (master_plan.slides[i].layout_type == master_plan.slides[i-1].layout_type
                and master_plan.slides[i].layout_type == 'generic'):
            print(f"  [Info] Slides {i} and {i+1} are both 'generic'. "
                  f"Consider breaking with an infographic or quote slide.")
```

---

## 5. Typography Diversity in Templates

### 5A. The Eyebrow Label

Every template should support an `eyebrow` — a small all-caps label above the title:

```
CHAPTER 2 · CHALLENGES
━━━━━━━━━━━━━━━━━━━━━━
The Problem No One Talks About
```

This is used heavily in McKinsey, BCG, and premium keynote decks to provide context without cluttering the title.

```html
<!-- In generic.html, split.html, etc. -->
{% if slide.eyebrow %}
<div class="slide-eyebrow">{{ slide.eyebrow }}</div>
{% endif %}
```

```css
.slide-eyebrow {
  font-size: var(--type-xs);  /* 18px */
  font-weight: 600;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--primary);
  margin-bottom: var(--sp-2);
  opacity: 0.9;
}
/* Theme-specific eyebrow styles */
body.dark_neon .slide-eyebrow { color: var(--primary); text-shadow: var(--text-glow); }
body.editorial .slide-eyebrow { color: var(--primary); font-family: 'IBM Plex Sans', sans-serif; }
```

### 5B. Talking-Time Pacing Indicator (Speaker Notes)

Each slide gets an estimated `talking_time_seconds`. The Planner calculates this based on `narrative_weight` and content density:
- `light` slide: 30–45 seconds
- `medium` slide: 60–90 seconds
- `heavy` slide: 90–150 seconds
- `quote`/`stat` slide: 20–30 seconds (pause for impact)

The speaker notes export shows this as a time budget:

```markdown
## Slide 2 — "The Old vs. The New" ⏱ ~75s
**Image:** split_comp_before_after.png [NEEDS GENERATION]
...
```

### 5C. New Template Files

#### `templates/quote.html` — Full-slide pull quote

```html
{% extends "base.html" %}
{% block extra_head %}
<style>
.quote-container {
  width: 1920px; height: 1080px;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  padding: var(--sp-9);
  box-sizing: border-box;
  text-align: center;
  position: relative;
}
.quote-mark {
  font-size: 200px;
  line-height: 0.7;
  color: var(--primary);
  opacity: 0.15;
  font-family: Georgia, serif;
  position: absolute;
  top: 80px;
  left: 120px;
}
.quote-text {
  font-size: var(--type-2xl);  /* 88px */
  font-weight: 300;
  line-height: 1.3;
  letter-spacing: -0.02em;
  color: var(--text);
  max-width: 1400px;
  position: relative;
  z-index: 1;
}
.quote-attribution {
  font-size: var(--type-sm);  /* 24px */
  font-weight: 500;
  color: var(--primary);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-top: var(--sp-5);
}
/* Decorative rule */
.quote-rule {
  width: 60px; height: 3px;
  background: var(--primary);
  margin: var(--sp-4) auto;
}
</style>
{% endblock %}

{% block content %}
<div class="quote-container">
  {% if slide.image_prompt and has_image %}
  <div class="quote-bg" style="position:absolute;inset:0;background:url({{ image_path }}) center/cover;opacity:0.15;"></div>
  {% endif %}
  <div class="quote-mark">"</div>
  {% for block in slide.content_blocks %}
    {% if block.block_type == 'pullquote' %}
    <div class="quote-text">{{ block.quote }}</div>
    <div class="quote-rule"></div>
    {% if block.attribution %}
    <div class="quote-attribution">{{ block.attribution }}</div>
    {% endif %}
    {% endif %}
  {% endfor %}
</div>
{% endblock %}
```

#### `templates/stat.html` — Hero statistics

```html
{% extends "base.html" %}
{% block extra_head %}
<style>
.stat-container {
  width: 1920px; height: 1080px;
  display: flex; flex-direction: column;
  justify-content: center;
  padding: var(--sp-8) var(--sp-9);
  box-sizing: border-box;
}
.stat-grid {
  display: flex;
  gap: var(--sp-7);
  align-items: center;
  justify-content: center;
}
.stat-item {
  flex: 1;
  text-align: center;
  background: var(--card-bg);
  border-radius: var(--card-radius);
  box-shadow: var(--card-shadow);
  border: var(--card-border);
  backdrop-filter: var(--card-backdrop);
  padding: var(--sp-7) var(--sp-6);
  display: flex; flex-direction: column;
  align-items: center;
}
.stat-value {
  font-size: 120px;   /* deliberately large — this IS the content */
  font-weight: 700;
  line-height: 1.0;
  letter-spacing: -0.04em;
  color: var(--primary);
}
.stat-label {
  font-size: var(--type-md);
  font-weight: 500;
  color: var(--text);
  margin-top: var(--sp-3);
  text-align: center;
}
.stat-context {
  font-size: var(--type-xs);
  color: var(--text-secondary);
  margin-top: var(--sp-2);
  text-align: center;
  opacity: 0.8;
}
/* Dividers between stats */
.stat-divider {
  width: 1px;
  height: 200px;
  background: var(--primary);
  opacity: 0.2;
  flex-shrink: 0;
}
</style>
{% endblock %}

{% block content %}
<div class="stat-container">
  <div class="stat-eyebrow">{{ slide.eyebrow or '' }}</div>
  <div class="stat-title">{{ slide.title }}</div>
  <div class="stat-grid">
    {% for block in slide.content_blocks %}
      {% if block.block_type == 'stat' %}
        {% if not loop.first %}<div class="stat-divider"></div>{% endif %}
        <div class="stat-item">
          <div class="stat-value">{{ block.value }}</div>
          <div class="stat-label">{{ block.label }}</div>
          {% if block.context %}
          <div class="stat-context">{{ block.context }}</div>
          {% endif %}
        </div>
      {% endif %}
    {% endfor %}
  </div>
</div>
{% endblock %}
```

#### `templates/timeline.html` — Horizontal timeline

```html
{% extends "base.html" %}
{% block extra_head %}
<style>
.timeline-container {
  width: 1920px; height: 1080px;
  padding: var(--sp-8) var(--sp-7);
  box-sizing: border-box;
}
.timeline-track {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 0;
  margin-top: var(--sp-6);
}
.timeline-track::before {
  content: '';
  position: absolute;
  top: 20px;   /* center of dot */
  left: 0; right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--primary) 0%, rgba(var(--primary-rgb, 0,0,0), 0.2) 100%);
}
.timeline-event {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding-top: 40px;  /* below the track line */
  position: relative;
}
.timeline-dot {
  position: absolute;
  top: 10px;  /* centered on track */
  left: 0;
  width: 20px; height: 20px;
  border-radius: 50%;
  background: var(--primary);
  box-shadow: 0 0 0 4px rgba(var(--primary-rgb, 0,0,0), 0.2);
  z-index: 1;
}
.timeline-date {
  font-size: var(--type-xs);
  font-weight: 700;
  color: var(--primary);
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: var(--sp-2);
}
.timeline-label {
  font-size: var(--type-sm);
  font-weight: 600;
  color: var(--text);
  line-height: 1.3;
}
.timeline-desc {
  font-size: var(--type-xs);
  color: var(--text-secondary);
  margin-top: var(--sp-1);
  line-height: 1.5;
}
</style>
{% endblock %}

{% block content %}
<div class="timeline-container">
  {% if slide.eyebrow %}<div class="slide-eyebrow">{{ slide.eyebrow }}</div>{% endif %}
  <div class="generic-title">{{ slide.title }}</div>
  <div class="timeline-track">
    {% for block in slide.content_blocks %}
      {% if block.block_type == 'steps' %}
        {% for step in block.steps %}
        <div class="timeline-event">
          <div class="timeline-dot"></div>
          <div class="timeline-date">Step {{ loop.index }}</div>
          <div class="timeline-label">{{ step }}</div>
        </div>
        {% endfor %}
      {% endif %}
    {% endfor %}
  </div>
</div>
{% endblock %}
```

---

## 6. Rich Content Blocks in Templates

The existing templates need to render the new content block types. The `generic.html` template handles the most variety:

```html
<!-- generic.html content block renderer -->
{% for block in slide.content_blocks %}

  {% if block.block_type == 'bullets' %}
  <div class="generic-content">
    <ul>
      {% for item in block.items %}
      <li>{{ item }}</li>
      {% endfor %}
    </ul>
  </div>

  {% elif block.block_type == 'callout' %}
  <div class="callout-block">
    <div class="callout-primary">{{ block.primary }}</div>
    <div class="callout-secondary">{{ block.secondary }}</div>
  </div>

  {% elif block.block_type == 'comparison' %}
  <div class="comparison-block">
    <div class="comparison-col comparison-left">
      <div class="comparison-label">{{ block.left_label }}</div>
      {% for item in block.left_items %}
      <div class="comparison-item comparison-item-left">{{ item }}</div>
      {% endfor %}
    </div>
    <div class="comparison-divider">VS</div>
    <div class="comparison-col comparison-right">
      <div class="comparison-label">{{ block.right_label }}</div>
      {% for item in block.right_items %}
      <div class="comparison-item comparison-item-right">{{ item }}</div>
      {% endfor %}
    </div>
  </div>

  {% elif block.block_type == 'keyvalue' %}
  <div class="keyvalue-block">
    {% for pair in block.pairs %}
    <div class="kv-row">
      <div class="kv-key">{{ pair.key }}</div>
      <div class="kv-sep">—</div>
      <div class="kv-value">{{ pair.value }}</div>
    </div>
    {% endfor %}
  </div>

  {% elif block.block_type == 'steps' %}
  <div class="steps-block">
    {% for step in block.steps %}
    <div class="step-item">
      <div class="step-number">{{ "%02d" | format(loop.index) }}</div>
      <div class="step-text">{{ step }}</div>
    </div>
    {% if not loop.last %}<div class="step-arrow">→</div>{% endif %}
    {% endfor %}
  </div>

  {% endif %}
{% endfor %}
```

### CSS for New Block Types

```css
/* Callout block — big central message */
.callout-block {
  text-align: center;
  padding: var(--sp-7) var(--sp-8);
}
.callout-primary {
  font-size: 96px;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--primary);
  line-height: 1.0;
}
.callout-secondary {
  font-size: var(--type-lg);
  color: var(--text-secondary);
  margin-top: var(--sp-3);
  font-weight: 300;
}

/* Comparison block */
.comparison-block {
  display: flex;
  gap: 0;
  width: 100%;
  background: var(--card-bg);
  border-radius: var(--card-radius);
  overflow: hidden;
}
.comparison-col {
  flex: 1;
  padding: var(--sp-6);
}
.comparison-label {
  font-size: var(--type-sm);
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--primary);
  margin-bottom: var(--sp-4);
}
.comparison-item-left  { opacity: 0.7; }  /* 'before' = muted */
.comparison-item-right { font-weight: 600; }  /* 'after' = emphasized */
.comparison-divider {
  width: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--type-xl);
  font-weight: 800;
  color: var(--primary);
  opacity: 0.3;
  background: rgba(var(--primary-rgb, 0,0,0), 0.04);
}

/* Steps block — horizontal process */
.steps-block {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  flex-wrap: nowrap;
}
.step-item {
  flex: 1;
  background: var(--card-bg);
  border: var(--card-border);
  border-radius: var(--card-radius);
  padding: var(--sp-5);
}
.step-number {
  font-size: var(--type-2xl);
  font-weight: 700;
  color: var(--primary);
  opacity: 0.3;
  letter-spacing: -0.04em;
}
.step-text {
  font-size: var(--type-sm);
  font-weight: 500;
  margin-top: var(--sp-2);
}
.step-arrow {
  font-size: 36px;
  color: var(--primary);
  opacity: 0.5;
  flex-shrink: 0;
}

/* Key-Value block */
.keyvalue-block { width: 100%; }
.kv-row {
  display: flex;
  gap: var(--sp-4);
  align-items: baseline;
  padding: var(--sp-3) 0;
  border-bottom: 1px solid rgba(var(--primary-rgb, 0,0,0), 0.08);
}
.kv-key   { font-size: var(--type-sm); color: var(--text-secondary); min-width: 200px; }
.kv-sep   { color: var(--primary); opacity: 0.4; }
.kv-value { font-size: var(--type-sm); font-weight: 600; color: var(--text); }
```

---

## 7. Planner System Prompt — Content Quality Additions

The biggest single change to content quality is an upgraded system prompt. Current prompt is ~300 words. This adds critical content quality rules:

```
CONTENT QUALITY RULES (these are non-negotiable):

RULE 1 — ONE IDEA PER SLIDE:
Each slide must communicate ONE primary message. If you have two ideas, make two slides.
The title should state the insight, not just the topic:
  BAD:  "AI Tools"
  GOOD: "AI Tools Cut Prep Time by 10x"

RULE 2 — CONTENT BLOCK SELECTION:
Choose the right content block type for the information:
  - Numbers/metrics → StatBlock (never put stats in bullets)
  - Famous quote or insight → PullQuoteBlock (dedicate a full slide to it)
  - Before/After, Pros/Cons, Old/New → ComparisonBlock
  - Sequential process, how-to steps → StepBlock
  - Single powerful message → DataCalloutBlock (large text, brief context)
  - Structured facts (date, founder, location) → KeyValueBlock
  - Everything else → BulletBlock (4 items max, each under 100 chars)

RULE 3 — NARRATIVE WEIGHT:
Assign narrative_weight deliberately:
  - 'light': Quote slides, stat slides, transition slides. Impact through simplicity.
  - 'heavy': Only when data truly demands it (never exceed 200 words total on slide)
  - 'medium': Standard default.
  At least 1 in 5 slides must be 'light' weight.

RULE 4 — EYEBROW LABELS:
Add eyebrow to slides that are part of a sequence or section:
  "PROBLEM STATEMENT", "KEY FINDING", "STEP 3 OF 5", "CHAPTER 2 · THE DATA"
  Use eyebrow sparingly — only on slides where context is needed.

RULE 5 — SLIDE TITLE IS THE INSIGHT:
Title should complete this sentence: "After seeing this slide, the audience now knows..."
  BAD: "Market Overview" → audience knows nothing specific
  GOOD: "The Market Grew 340% — But Most Players Missed It"

RULE 6 — IMAGE ROLE:
When requires_image: true, specify image_role:
  - 'background': Only if text can overlay it (high contrast needed). Use for cover, quote.
  - 'supporting': For split layouts — image paired WITH text, not under it
  - 'data': When the image IS a chart, diagram, or screenshot
  - 'decorative': Abstract texture or pattern — never use for key information

RULE 7 — TALKING TIME:
Set talking_time_seconds based on slide weight:
  light: 30, medium: 75, heavy: 120, quote/stat: 25

RULE 8 — ARC ADHERENCE:
If the user specified a narrative_arc, follow its sequence.
Every slide must have a slide_purpose that maps to that arc position.
The deck must feel like ONE coherent story, not a collection of slides.

RULE 9 — VARIETY IN LAYOUT:
Never use the same layout_type more than 3 times in a row.
A 10-slide deck should have: 1 cover, 1-2 quote or stat, 2-3 generic, 2 split or infographic, 1 timeline or comparison, 1 cta/summary.

RULE 10 — SPEAKER NOTES ARE A SCRIPT:
Speaker notes should be a verbatim speaking script (not bullets). Write as if speaking naturally aloud.
Include a transition sentence at the end of each note that bridges to the next slide.
```

---

## 8. Image Quality & Purposefulness

### 8A. Image Role → Prompt Engineering

The image prompt should reflect the `image_role`:

```python
# image_generator.py — image_role-aware prompt enrichment

ROLE_PREFIXES = {
    'background': (
        "Full-bleed 1920×1080 background image designed for text overlay. "
        "Keep the center-left area free of strong focal points. "
        "The image will be behind white/dark text — use soft gradients or blurred zones in center. "
        "No text, no watermarks, no UI elements. "
    ),
    'supporting': (
        "1920×1080 landscape photograph or illustration, designed to sit on the RIGHT HALF "
        "of a split-layout presentation slide. The left half will be covered by text. "
        "Composition should have strong visual interest on the RIGHT side. "
        "No text, no watermarks. "
    ),
    'data': (
        "Clean, minimalist infographic or diagram at 1920×1080. "
        "White or very light background (or matching the slide's background color). "
        "Clear, readable labels. No decorative elements. "
        "Suitable for display as a primary data visual on a presentation slide. "
    ),
    'decorative': (
        "Abstract artistic texture or pattern at 1920×1080. "
        "Subtle, not distracting. Should complement the slide's color scheme. "
        "Semi-transparent or low-saturation preferred. No representational objects. "
    ),
}

def build_image_prompt(slide, config, total_slides):
    role = slide.image_role or 'background'
    role_prefix = ROLE_PREFIXES.get(role, ROLE_PREFIXES['background'])

    theme = config.design_preferences.theme_style
    audience = config.presentation_goals.audience
    art_style = config.image_preferences.art_style

    full_prompt = (
        f"{role_prefix}"
        f"Slide context: '{slide.title}' (Slide {slide.slide_number} of {total_slides}). "
        f"Audience: {audience}. "
        f"Presentation theme: {theme}. "
        f"Art style: {art_style}. "
        f"Specific image direction: {slide.image_prompt}"
    )
    return full_prompt
```

### 8B. Slide-to-Image Semantic Matching

The validator checks for semantic mismatches:

```python
# validator.py — semantic image check

MISMATCHES = [
    # (slide_purpose, image_role) pairs that don't make sense
    ('quote', 'data'),       # data visual on a quote slide
    ('data', 'decorative'),  # decorative on a data slide is misleading
    ('cta', 'background'),   # background on CTA is fine but should be flagged if no text overlay contrast
]

def check_image_semantics(slide):
    if not slide.requires_image:
        return
    combo = (slide.slide_purpose, slide.image_role)
    if combo in MISMATCHES:
        print(f"  [Warning] Slide {slide.slide_number}: image_role='{slide.image_role}' "
              f"may be inappropriate for slide_purpose='{slide.slide_purpose}'.")
```

---

## 9. Content Continuity — Deck-Level Intelligence

### 9A. Transition Sentences

Each slide's speaker notes should end with a transition to the next slide. The Planner is instructed to write these, but they're validated:

```python
# validator.py
TRANSITION_SIGNALS = [
    "so let's", "which brings us", "next,", "now,", "moving to",
    "with that in mind", "let's look at", "turning to", "this is why"
]

def check_speaker_note_transition(slide):
    note = slide.speaker_notes.lower()
    if not any(signal in note for signal in TRANSITION_SIGNALS):
        if slide.slide_number < len(all_slides):  # not the last slide
            print(f"  [Info] Slide {slide.slide_number} speaker note doesn't have "
                  f"a transition sentence to the next slide.")
```

### 9B. Concept Repetition Detection

```python
# If the same key noun appears in >50% of slide titles, the deck is repetitive
from collections import Counter
import re

def check_title_repetition(slides):
    words = []
    for s in slides:
        # Extract nouns (simple heuristic: words > 4 chars, not stopwords)
        STOPWORDS = {'about', 'their', 'which', 'there', 'these', 'those', 'your', 'from', 'with'}
        words += [w.lower() for w in re.findall(r'\b[A-Za-z]{5,}\b', s.title)
                  if w.lower() not in STOPWORDS]
    counter = Counter(words)
    for word, count in counter.most_common(3):
        if count > len(slides) * 0.5:
            print(f"  [Warning] The word '{word}' appears in {count}/{len(slides)} slide titles. "
                  f"Consider more specific language.")
```

---

## 10. Config Additions for Content Quality

```yaml
# config.yaml — new content quality parameters

presentation_goals:
  audience: "Series A investors"
  duration_minutes: 12
  slide_count: 10
  tone: "confident"          # confident | casual | academic | inspirational | humorous
  language: "English"
  narrative_arc: "problem_solution"   # NEW: drives slide sequencing
  key_message: "Our platform cuts customer churn by 40%"  # NEW: the ONE thing to remember
  call_to_action: "Book a 30-minute demo at demo.acme.com"
  desired_outcome: "audience books a demo within 48 hours"  # NEW: success criterion

content_guidelines:
  max_words_per_slide: 120     # NEW: hard cap across all slides
  allow_heavy_slides: false    # NEW: force light/medium density throughout
  require_eyebrow_labels: false # NEW: auto-generate eyebrow labels for section slides
  use_variety_check: true      # NEW: validator checks deck balance
  transition_sentences: true   # NEW: require speaker note transitions

data_and_evidence:
  has_statistics: true         # NEW: hint to Planner to use StatBlocks where evidence slides appear
  has_quotes: false            # NEW: hint to use PullQuoteBlocks
  has_before_after: true       # NEW: hint to use ComparisonBlocks
  has_process: true            # NEW: hint to use StepBlocks or timeline layout
```

---

## 11. Backward Compatibility — `content_bullets` Migration

The existing `master_plan.json` and `--offline-plan` workflow uses `content_bullets: List[str]`. We need backward compat:

```python
# validator.py — migrate legacy content_bullets to content_blocks

def migrate_legacy_bullets(slide: Slide) -> Slide:
    """
    If a slide has content_bullets but no content_blocks,
    convert bullets to a BulletBlock automatically.
    """
    if slide.content_bullets and not slide.content_blocks:
        slide.content_blocks = [BulletBlock(items=slide.content_bullets)]
        slide.content_bullets = []  # clear legacy field
    return slide
```

This runs at the start of `validate_and_prune()` — transparent to the user.

---

## 12. Speaker Notes Export Enhancement

The current export is minimal. Enhanced format:

```markdown
# Speaker Notes — AI Presentation Tools Showcase
**Theme:** dark_neon (cyber_cyan) | **Duration:** ~8 min | **Arc:** problem_solution

---

## Slide 1 — Cover ⏱ ~30s  [LIGHT]
**Layout:** Cover | **Purpose:** hook
**Image:** `assets/slide_1.png` ✓ ready

> The Future of Pitching

*Notes:*
"Good morning everyone. Today I want to show you something that's going to fundamentally change how you think about presentations. Not the tools — the mindset. [pause] Let's start with a question..."

*→ Transition: "But first — why does this even matter?"*

---

## Slide 2 — "AI Tools Cut Prep Time by 10x" ⏱ ~75s  [MEDIUM]
**Layout:** Stat | **Purpose:** evidence
**Image:** `assets/slide_2.png` ⚠ NEEDS GENERATION
**Content blocks:** 2× StatBlock

Stats on this slide:
- **10×** — Speed improvement over manual workflow
- **94%** — of users reported higher confidence in output quality
- **3 min** — average time to first draft with AI

*Notes:*
"These aren't marketing numbers. These are from a study of 2,400 professional presenters across 18 industries. [pause at each stat] Ten times faster. Ninety-four percent..."

*→ Transition: "So what's actually happening under the hood? Let's look at the workflow."*
```

---

## 13. Implementation Phases

### Phase 1 — Schema Extension (invisible to user)
1. Add `ContentBlock` union types to `schemas.py`
2. Add `slide_purpose`, `narrative_weight`, `eyebrow`, `image_role`, `talking_time_seconds` to `Slide`
3. Add `narrative_arc`, `key_message`, `desired_outcome`, `content_guidelines`, `data_and_evidence` to `AppConfig`
4. Add `NarrativeArc` library to `narrative_arcs.py`
5. Backward compat migration in `validator.py`

### Phase 2 — Planner Upgrade
6. Rewrite `SYSTEM_INSTRUCTION` with all 10 content quality rules
7. Update JSON format example to show `content_blocks` instead of `content_bullets`
8. Wire `narrative_arc` + `key_message` into the prompt
9. Wire `data_and_evidence` hints into the prompt
10. Dry-run test: verify Planner generates diverse content_block types

### Phase 3 — Template Extensions
11. Add eyebrow CSS + HTML to all existing templates
12. Add content block renderers (callout, comparison, steps, keyvalue) to `generic.html`
13. Create `templates/quote.html`
14. Create `templates/stat.html`
15. Create `templates/timeline.html`
16. Visual test: all new templates × all themes

### Phase 4 — Validator Upgrades
17. `count_words_in_slide()` density checker
18. `check_deck_balance()` layout variety checker
19. `check_title_repetition()` concept overlap detector
20. `check_speaker_note_transition()` continuity checker
21. `check_image_semantics()` purposefulness checker

### Phase 5 — Image Generator Upgrade
22. `image_role`-aware prompt prefixes in `image_generator.py`
23. Prompt now includes slide_purpose and narrative context

### Phase 6 — Speaker Notes & Export Enhancement
24. Enhanced speaker notes format with time estimates
25. Image readiness status in notes

---

## 14. File Change List

| File | Action | Description |
|------|--------|-------------|
| `schemas.py` | MODIFY | New ContentBlock union types; extended Slide fields |
| `narrative_arcs.py` | NEW | Arc library definitions |
| `config_manager.py` | MODIFY | New AppConfig sections for content quality |
| `planner.py` | MODIFY | Full system prompt rewrite with 10 content quality rules |
| `validator.py` | MODIFY | Content density, deck balance, title repetition, image semantics, legacy migration |
| `image_generator.py` | MODIFY | image_role-aware prompt building |
| `compiler.py` | MODIFY | Enhanced speaker notes export with time estimates and image status |
| `templates/generic.html` | MODIFY | ContentBlock renderers (callout, comparison, steps, keyvalue); eyebrow |
| `templates/cover.html` | MODIFY | Eyebrow; talking_time display in notes |
| `templates/split.html` | MODIFY | ContentBlock renderers; eyebrow |
| `templates/infographic.html` | MODIFY | ContentBlock renderers; eyebrow |
| `templates/quote.html` | NEW | Full-slide pull quote layout |
| `templates/stat.html` | NEW | Hero statistics layout (1–3 big numbers) |
| `templates/timeline.html` | NEW | Horizontal timeline layout |
| `config_reference.yaml` | MODIFY | Document all new config keys |
| `README.md` | MODIFY | Content quality section; new layout types; arc docs |

---

# Part 2 — Deep Refinement: What the Plan Above Misses

The sections above define *what* content types exist and *how* templates render them. But premium content quality depends on dimensions the plan doesn't yet address:

1. **Prose quality** — the actual words inside each block (grammar, voice, parallelism)
2. **Multi-pass refinement** — one Planner call produces mediocre content; real decks need editing passes
3. **Source material intelligence** — how to extract premium material from wildly different inputs
4. **Block × Layout compatibility** — not all combos make sense; invalid combos need to be prevented
5. **Content consistency** — tone, terminology, and grammatical patterns must be uniform across the deck
6. **Audience-specific patterns** — investor decks, academic talks, and sales pitches have different expected structures
7. **Content scoring** — measuring quality quantitatively, separate from visual audit
8. **Edge case catalog** — every way content generation can go wrong

---

## 15. Prose Quality Engine

The current plan says "bullets should be concise" but never defines what good prose looks like on a slide. This is the difference between:

```
BAD:  "The implementation of our solution across enterprise environments has demonstrated substantial improvements"
GOOD: "Enterprise rollout: 40% faster deployments"
```

### 15A. Writing Rules for the Planner System Prompt

Add these as **RULE 11–16** in the system prompt:

```
RULE 11 — ACTIVE VOICE:
All content must use active voice. The subject does the action.
  BAD:  "Revenue was increased by 40%"
  GOOD: "Revenue grew 40%"
  BAD:  "The platform is used by 500 teams"
  GOOD: "500 teams rely on the platform"

RULE 12 — PARALLEL GRAMMATICAL STRUCTURE:
All bullet items in a BulletBlock MUST follow the same grammatical pattern.
If bullet 1 starts with a verb, ALL bullets must start with a verb.
If bullet 1 starts with a noun, ALL bullets must start with a noun.
  BAD:  ["Faster deployment", "We reduced costs", "Security is improved"]
  GOOD: ["Faster deployments", "Lower costs", "Stronger security"]
  GOOD: ["Deploy 3× faster", "Cut costs by 40%", "Eliminate 90% of breaches"]

RULE 13 — STAT FORMATTING RULES:
When using StatBlock, follow these formatting conventions:
  - Percentages: "340%" not "three hundred and forty percent"
  - Money: "$2.3B" not "$2,300,000,000" (abbreviate with K/M/B)
  - Multiples: "10×" not "ten times" or "10 times"
  - Counts: "1.2M users" not "1,200,000 users"
  - Time: "< 3 min" not "less than three minutes"
  - Always include a comparison baseline in `context`:
    "vs. industry avg of 12%" or "up from 2× last year"
  - The `value` field must be 1–6 characters. If longer, it's not a stat — it's body text.

RULE 14 — TITLE LENGTH:
  - Cover title: 2–7 words. Punchy. No subtitle needed if title is strong.
  - Generic/Split title: 4–12 words. Should contain the insight, not just the topic.
  - Infographic title: 3–8 words. Acts as a section header.
  - Quote slide: No title needed (the quote IS the content). Use eyebrow instead.
  - Stat slide: 3–8 words. Frames what the numbers mean.

RULE 15 — BULLET TEXT DENSITY:
Each bullet should be 6–18 words. Under 6 is a label (use KeyValueBlock instead).
Over 18 is a paragraph (split into two bullets or move detail to speaker notes).
  BAD: "Speed" → too vague, not informative
  BAD: "Our platform leverages cutting-edge machine learning algorithms to deliver unprecedented speed improvements across all deployment environments" → move to speaker notes
  GOOD: "3× faster deployments with zero-downtime rolling updates"

RULE 16 — FORBIDDEN FILLER WORDS:
Never use these words in slide content (speaker notes are fine):
  "leverage", "utilize", "synergy", "paradigm", "innovative", "cutting-edge",
  "best-in-class", "world-class", "next-generation", "game-changing",
  "revolutionize", "disrupt", "ecosystem", "holistic", "empower"
These are corporate filler — they communicate nothing specific.
Replace with concrete claims:
  "leverage AI" → "use GPT-4 to classify tickets in < 2s"
  "innovative solution" → "first platform to combine X and Y"
```

### 15B. Validator Prose Quality Checks

```python
# validator.py — prose quality analysis

import re

FILLER_WORDS = {
    'leverage', 'utilize', 'synergy', 'paradigm', 'innovative',
    'cutting-edge', 'best-in-class', 'world-class', 'next-generation',
    'game-changing', 'revolutionize', 'disrupt', 'ecosystem', 'holistic',
    'empower', 'streamline', 'optimize', 'robust', 'scalable'
}

PASSIVE_PATTERNS = [
    r'\b(?:is|are|was|were|been|being)\s+\w+ed\b',  # "was implemented"
    r'\b(?:is|are|was|were)\s+\w+en\b',               # "was driven"
]

def check_prose_quality(slide):
    issues = []
    all_text = []

    for block in slide.content_blocks:
        if hasattr(block, 'items'):
            all_text.extend(block.items)
        if hasattr(block, 'quote'):
            all_text.append(block.quote)
        if hasattr(block, 'primary'):
            all_text.append(block.primary)

    # 1. Filler word detection
    for text in all_text:
        words = set(text.lower().split())
        found = words & FILLER_WORDS
        if found:
            issues.append(f"  [Style] Slide {slide.slide_number}: "
                          f"filler word(s) detected: {', '.join(found)}")

    # 2. Passive voice detection
    for text in all_text:
        for pattern in PASSIVE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                issues.append(f"  [Style] Slide {slide.slide_number}: "
                              f"possible passive voice: \"{text[:60]}...\"")
                break

    # 3. Parallel structure check (for bullet blocks only)
    for block in slide.content_blocks:
        if hasattr(block, 'items') and len(block.items) >= 2:
            # Check if first words are same part of speech (simple heuristic: same pattern)
            first_words = [item.split()[0].lower() if item.split() else '' for item in block.items]
            # Check if they all start with verbs (end in common verb suffixes or are common verbs)
            patterns = []
            for fw in first_words:
                if fw.endswith(('ing', 'ize', 'ate', 'ify', 'uce', 'ect', 'end')):
                    patterns.append('verb')
                elif fw[0].isupper() and not fw.isupper():
                    patterns.append('noun')
                elif fw.isdigit() or fw[0].isdigit():
                    patterns.append('number')
                else:
                    patterns.append('other')
            if len(set(patterns)) > 1 and len(patterns) >= 3:
                issues.append(f"  [Style] Slide {slide.slide_number}: "
                              f"bullets may lack parallel structure "
                              f"(starts: {', '.join(first_words[:4])})")

    # 4. Stat value length check
    for block in slide.content_blocks:
        if hasattr(block, 'value') and len(block.value) > 6:
            issues.append(f"  [Fix] Slide {slide.slide_number}: "
                          f"stat value \"{block.value}\" is {len(block.value)} chars — "
                          f"too long for a hero stat. Max 6 chars (e.g., '340%', '$2.3B').")

    return issues
```

---

## 16. Multi-Pass Content Refinement

### The Problem

A single Planner API call does too much at once: narrative design, content writing, layout selection, image prompting, and theming. This produces mediocre results on each dimension because the model is spread thin.

### The Solution: 3-Pass Pipeline

```
Pass 1: OUTLINE (structure only)        → light, fast, cheap
Pass 2: CONTENT FILL (write the blocks) → heavy, creative
Pass 3: EDIT (tighten + consistency)     → light, precise
```

### Implementation

```python
# planner.py — multi-pass generation

class Planner:

    def generate_master_plan(self, config: AppConfig) -> MasterPlan:
        # Decide pass strategy based on config
        if config.pipeline.planner_mode == 'single':
            return self._single_pass(config)
        else:
            return self._multi_pass(config)

    def _multi_pass(self, config: AppConfig) -> MasterPlan:
        # ── Pass 1: Outline ──────────────────────────────
        print("Pass 1/3: Generating narrative outline...")
        outline = self._pass_outline(config)
        # outline is a lightweight JSON:
        # { "arc": "problem_solution",
        #   "slides": [
        #     { "slide_number": 1, "layout_type": "cover",
        #       "purpose": "hook", "weight": "light",
        #       "one_sentence_summary": "Introduce the 10× speed claim",
        #       "content_block_types": ["callout"],
        #       "requires_image": true, "image_role": "background" },
        #     ...
        #   ]
        # }

        # ── Pass 2: Content Fill ─────────────────────────
        print("Pass 2/3: Writing slide content...")
        filled = self._pass_content_fill(config, outline)
        # filled is the full MasterPlan JSON with content_blocks populated

        # ── Pass 3: Edit ─────────────────────────────────
        print("Pass 3/3: Editing for quality and consistency...")
        edited = self._pass_edit(config, filled)
        # edited is the final MasterPlan with tightened prose

        return edited
```

### Pass 1: Outline Prompt

```
You are a senior presentation strategist. Given the user's source material
and goals, output ONLY a structural outline — no slide content yet.

For each slide, specify:
- slide_number, layout_type, purpose (from the narrative arc), weight (light/medium/heavy)
- one_sentence_summary: what insight this slide communicates
- content_block_types: which block types this slide should use (bullets, stat, comparison, etc.)
- requires_image, image_role

Rules:
- Follow the "{narrative_arc}" arc pattern: {arc_sequence}
- Target {slide_count} slides for {duration} minutes
- Vary layouts: max 2 consecutive same type
- At least 1 in 5 slides must be weight: "light"

Output only JSON. No prose.
```

**Why this is better:** The model focuses entirely on structure, not writing. It can reason about the full arc, pacing, and variety without the cognitive load of composing actual text. The outline is tiny (~500 tokens) so cheap and fast.

### Pass 2: Content Fill Prompt

```
You are a world-class presentation copywriter. Below is a structural outline
for a {slide_count}-slide deck. Your job: write the content for EACH slide.

For each slide, the outline tells you:
- What layout and content_block_types to use
- What one_sentence_summary the slide must communicate
- What purpose this slide serves in the narrative arc

Write content following these rules:
[RULES 1–16 from sections 7 and 15]

Also write:
- image_prompt: detailed, role-aware (the outline tells you image_role)
- speaker_notes: natural speaking script with transition sentence

You MUST output every slide from the outline. Do not skip any.
Output full MasterPlan JSON.
```

**Why this is better:** The model now has BOTH the user's source material AND the structural outline as context. It knows the narrative purpose of every slide before writing the first word. This prevents the common failure mode where the AI writes slide 1 without knowing what slide 5 will say.

### Pass 3: Edit Prompt

```
You are a ruthless presentation editor. Below is a complete deck.
Your job: improve it WITHOUT changing the structure.

Check and fix:
1. Parallel grammatical structure in all bullet lists
2. Active voice (rewrite any passive constructions)
3. Remove filler words: {FILLER_WORDS}
4. Ensure every title states an INSIGHT, not a topic
5. Ensure stat values are ≤ 6 characters with comparison context
6. Ensure speaker notes end with a transition sentence
7. Ensure terminology is consistent (same concept = same word throughout)
8. Ensure total words per slide respect density limits

Output the COMPLETE corrected MasterPlan JSON. Change only text content.
Do not change layout_type, slide_number, or content_block_types.
```

**Why this is better:** Editing is a fundamentally different cognitive task than writing. The model can now focus entirely on prose quality without the structural burden. This is how professional writing works: write first, edit second.

### Config Control

```yaml
# config.yaml
pipeline:
  planner_mode: "multi"     # "single" = one-shot (current behavior), "multi" = 3-pass
  # "single" is cheaper (1 API call); "multi" is higher quality (3 API calls)
```

### Cost Analysis

| Mode | API Calls | Approx Tokens | Approx Cost (Flash Lite) |
|------|-----------|---------------|--------------------------|
| single | 1 | ~6K | ~$0.001 |
| multi (3-pass) | 3 | ~15K | ~$0.003 |
| multi + AI audit | 4 | ~20K | ~$0.004 |

The cost increase is trivial. The quality improvement is substantial.

---

## 17. Source Material Intelligence

### The Problem

The current Planner receives source text in one undifferentiated blob. Whether the user provides a 10-word prompt or a 50-page PDF, the same system prompt processes it. This leads to two failure modes:

1. **Thin input** (one sentence): The Planner hallucinates facts, invents statistics, and generates generic content
2. **Thick input** (long document): The Planner tries to summarize everything, producing a flat, even distribution of information rather than finding the "golden nuggets"

### Solution: Source Material Pre-Processing

A new `source_analyzer.py` module runs BEFORE the Planner and produces a structured content brief:

```python
# source_analyzer.py

class SourceAnalyzer:
    """
    Pre-processes raw source material into a structured content brief
    that the Planner can use more effectively than raw text.
    """

    @classmethod
    def analyze(cls, source_text: str, config: AppConfig) -> dict:
        """
        Returns a content brief with extracted nuggets.
        Runs LOCALLY — no API calls. Uses heuristic extraction.
        """
        brief = {
            "source_length": len(source_text.split()),
            "source_type": cls._classify_source(source_text),
            "extracted_stats": cls._extract_statistics(source_text),
            "extracted_quotes": cls._extract_quotes(source_text),
            "key_terms": cls._extract_key_terms(source_text),
            "structure_hints": cls._detect_structure(source_text),
        }
        return brief

    @staticmethod
    def _classify_source(text: str) -> str:
        words = len(text.split())
        if words < 30:
            return "prompt"        # user gave a topic, not content
        elif words < 200:
            return "brief"         # short outline or abstract
        elif words < 2000:
            return "article"       # article-length content
        else:
            return "document"      # long-form document

    @staticmethod
    def _extract_statistics(text: str) -> list:
        """Find all numbers with context — these become StatBlock candidates."""
        import re
        patterns = [
            r'(\d+(?:\.\d+)?)\s*(%|percent)',           # "40%" or "40 percent"
            r'\$\s*(\d+(?:\.\d+)?)\s*([KMBkmb])',       # "$2.3B"
            r'(\d+(?:\.\d+)?)\s*[×x]\s',                # "10×"
            r'(\d{1,3}(?:,\d{3})+)',                     # "1,200,000"
            r'(\d+)\s*(?:out of|/)\s*(\d+)',             # "8 out of 10"
        ]
        stats = []
        for pattern in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                # Get surrounding context (±50 chars)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].strip()
                stats.append({
                    "raw_value": match.group(0),
                    "context": context
                })
        return stats[:10]  # cap at 10 to keep brief manageable

    @staticmethod
    def _extract_quotes(text: str) -> list:
        """Find quoted text — these become PullQuoteBlock candidates."""
        import re
        quotes = re.findall(r'["\u201C]([^"\u201D]{20,200})["\u201D]', text)
        return quotes[:5]

    @staticmethod
    def _extract_key_terms(text: str) -> list:
        """Find repeated important terms — these become the deck's vocabulary."""
        import re
        from collections import Counter
        STOPWORDS = {
            'about', 'their', 'which', 'there', 'these', 'those', 'your',
            'from', 'with', 'that', 'this', 'have', 'will', 'been', 'more',
            'than', 'other', 'some', 'also', 'into', 'over', 'would', 'could',
            'should', 'through', 'after', 'before', 'between', 'under', 'using'
        }
        words = re.findall(r'\b[A-Za-z]{4,}\b', text)
        filtered = [w.lower() for w in words if w.lower() not in STOPWORDS]
        counter = Counter(filtered)
        return [term for term, count in counter.most_common(15) if count >= 2]

    @staticmethod
    def _detect_structure(text: str) -> dict:
        """Detect if source has inherent structure (bullet lists, numbered items, headers)."""
        import re
        has_bullets = bool(re.search(r'^\s*[-•*]\s', text, re.MULTILINE))
        has_numbered = bool(re.search(r'^\s*\d+[.)]\s', text, re.MULTILINE))
        has_headers = bool(re.search(r'^#{1,3}\s', text, re.MULTILINE))
        has_sections = has_headers or bool(re.search(r'\n\n[A-Z][A-Za-z ]{5,}:\n', text))
        return {
            "has_bullets": has_bullets,
            "has_numbered_list": has_numbered,
            "has_headers": has_headers,
            "has_sections": has_sections,
        }
```

### Injecting the Brief into the Planner Prompt

```python
# In planner.py, before composing the prompt:
brief = SourceAnalyzer.analyze(source_text, config)

# Append to prompt:
prompt += "\n\n--- CONTENT BRIEF (auto-extracted from source) ---\n"
prompt += f"Source type: {brief['source_type']} ({brief['source_length']} words)\n"

if brief['extracted_stats']:
    prompt += "\nSTATISTICS FOUND IN SOURCE (use as StatBlocks where relevant):\n"
    for stat in brief['extracted_stats']:
        prompt += f"  • {stat['raw_value']} — context: \"{stat['context']}\"\n"

if brief['extracted_quotes']:
    prompt += "\nQUOTES FOUND IN SOURCE (use as PullQuoteBlocks where relevant):\n"
    for q in brief['extracted_quotes']:
        prompt += f"  • \"{q[:100]}...\"\n"

prompt += f"\nKEY TERMS (use consistently throughout deck): {', '.join(brief['key_terms'][:10])}\n"

# Source-type-specific instruction:
if brief['source_type'] == 'prompt':
    prompt += ("\nIMPORTANT: Source is a short prompt, not detailed content. "
               "You MUST expand it into a full presentation. "
               "Do NOT invent specific statistics — use qualitative claims instead. "
               "Do NOT fabricate quotes from real people. "
               "If you need data, use words like 'significant', 'substantial', "
               "or frame as questions: 'What if you could reduce churn by half?'")
elif brief['source_type'] == 'document':
    prompt += ("\nIMPORTANT: Source is a long document. "
               "Do NOT try to cover everything. "
               "Identify the 3–5 most impactful points and build the deck around them. "
               "Move supporting detail to speaker_notes, not to slide content.")
```

### Hallucination Guard

When source material is thin (`source_type == 'prompt'`), the Planner is explicitly told not to fabricate statistics. But what if it does anyway?

```python
# validator.py — hallucination check for thin sources

def check_stat_hallucination(slide, source_brief):
    """
    If source was a short prompt with no statistics,
    flag any StatBlocks with specific numbers as potentially hallucinated.
    """
    if source_brief['source_type'] != 'prompt':
        return []

    source_stats = {s['raw_value'] for s in source_brief.get('extracted_stats', [])}
    issues = []

    for block in slide.content_blocks:
        if hasattr(block, 'value'):
            # Check if the stat value appears anywhere in source material
            if not any(block.value in s for s in source_stats):
                issues.append(
                    f"  [Warning] Slide {slide.slide_number}: "
                    f"stat \"{block.value}\" not found in source material — "
                    f"may be hallucinated. Consider replacing with qualitative claim."
                )
    return issues
```

---

## 18. Content Block × Layout Compatibility Matrix

Not all content block types work in all layouts. The Planner needs to know which combinations are valid, and the Validator needs to enforce them.

### 18A. Compatibility Rules

| Layout | Valid Block Types | Invalid (breaks layout) | Notes |
|--------|-----------------|------------------------|-------|
| `cover` | — (no content blocks) | ALL | Cover uses only title, subtitle, eyebrow |
| `generic` | `bullets`, `callout`, `comparison`, `steps`, `keyvalue` | `pullquote` (use `quote` layout) | Most flexible layout |
| `split` | `bullets`, `keyvalue`, `callout` | `comparison` (split IS the comparison), `steps` (no room) | Text side only |
| `infographic` | `stat` × 1–3 | `comparison`, `steps`, `pullquote` | Cards contain stat blocks |
| `quote` | `pullquote` × 1 | ALL others | Quote layout = one quote only |
| `stat` | `stat` × 1–3 | `bullets`, `comparison`, `pullquote` | Stats-only layout |
| `timeline` | `steps` × 1 | `stat`, `comparison`, `pullquote` | Steps become timeline events |

### 18B. Multi-Block Rules

When can a slide have more than one content block?

| # Blocks | When Allowed | Layout | Example |
|----------|-------------|--------|---------|
| 0 | Cover, quote with title-only | `cover` | Title + subtitle only |
| 1 | Standard (most common) | All except `cover` | One BulletBlock on generic |
| 2 | `narrative_weight: 'heavy'` only | `generic` | BulletBlock + StatBlock sidebar |
| 3 | `stat` layout only | `stat` | Three StatBlocks displayed as grid |

### 18C. Validator Enforcement

```python
# validator.py — block compatibility check

VALID_BLOCKS_PER_LAYOUT = {
    'cover':       set(),                                    # no content blocks on cover
    'generic':     {'bullets', 'callout', 'comparison', 'steps', 'keyvalue'},
    'split':       {'bullets', 'keyvalue', 'callout'},
    'infographic': {'stat'},                                 # stat blocks render as info cards
    'quote':       {'pullquote'},
    'stat':        {'stat'},
    'timeline':    {'steps'},
}

MAX_BLOCKS_PER_LAYOUT = {
    'cover': 0, 'generic': 2, 'split': 1, 'infographic': 3,
    'quote': 1, 'stat': 3, 'timeline': 1,
}

def check_block_compatibility(slide):
    issues = []
    valid_types = VALID_BLOCKS_PER_LAYOUT.get(slide.layout_type, set())
    max_blocks = MAX_BLOCKS_PER_LAYOUT.get(slide.layout_type, 1)

    for block in slide.content_blocks:
        if block.block_type not in valid_types:
            issues.append(
                f"  [Warning] Slide {slide.slide_number}: "
                f"block_type '{block.block_type}' is invalid for layout '{slide.layout_type}'. "
                f"Valid: {valid_types}"
            )

    if len(slide.content_blocks) > max_blocks:
        issues.append(
            f"  [Fix] Slide {slide.slide_number}: "
            f"{len(slide.content_blocks)} content blocks exceeds max of {max_blocks} "
            f"for layout '{slide.layout_type}'. Truncating."
        )

    return issues
```

---

## 19. Content Consistency Engine

### The Problem

The Planner generates each slide somewhat independently. This causes:
- **Tone drift**: Slide 1 is formal ("Our organization has identified..."), slide 4 is casual ("So basically what happens is...")
- **Terminology inconsistency**: Slide 2 says "AI tools", slide 4 says "machine learning platforms", slide 6 says "intelligent automation" — all meaning the same thing
- **Formatting inconsistency**: Slide 2 bullets start with verbs, slide 4 bullets start with nouns

### 19A. Terminology Registry

The source analyzer extracts key terms. The Planner system prompt enforces them:

```
RULE 17 — TERMINOLOGY CONSISTENCY:
When the source material uses a specific term, use THAT term throughout.
  - If source says "AI tools", every slide must say "AI tools" (not "ML platforms" or "intelligent automation")
  - If source says "customer churn", don't switch to "attrition" or "retention loss"
  - Exception: the very first mention on the cover slide may use a more impactful synonym

Key terms from source (use these consistently): {key_terms}
```

### 19B. Tone Detection and Enforcement

```python
# validator.py — tone consistency

TONE_MARKERS = {
    'professional': {
        'positive': ['demonstrate', 'significant', 'strategic', 'implement', 'optimize'],
        'negative': ['basically', 'stuff', 'cool', 'awesome', 'totally', 'gonna'],
    },
    'casual': {
        'positive': ['check out', 'here is', 'let us', 'imagine', 'picture this'],
        'negative': ['heretofore', 'notwithstanding', 'pursuant to', 'aforementioned'],
    },
    'academic': {
        'positive': ['evidence suggests', 'research indicates', 'methodology', 'findings'],
        'negative': ['super', 'awesome', 'game-changing', 'killer feature'],
    },
}

def check_tone_consistency(slides, target_tone: str):
    issues = []
    negative_markers = TONE_MARKERS.get(target_tone, {}).get('negative', [])

    for slide in slides:
        all_text = slide.title + ' ' + (slide.subtitle or '')
        for block in slide.content_blocks:
            if hasattr(block, 'items'):
                all_text += ' ' + ' '.join(block.items)

        text_lower = all_text.lower()
        for marker in negative_markers:
            if marker in text_lower:
                issues.append(
                    f"  [Tone] Slide {slide.slide_number}: "
                    f"'{marker}' is inappropriate for '{target_tone}' tone."
                )
    return issues
```

### 19C. Cross-Slide Consistency Checks (Post-Planner)

```python
def check_cross_slide_consistency(master_plan: MasterPlan):
    """Run after Planner returns — checks deck-level consistency."""
    issues = []

    # 1. Title casing consistency
    title_cases = []
    for slide in master_plan.slides:
        words = slide.title.split()
        if all(w[0].isupper() for w in words if len(w) > 3):
            title_cases.append('title_case')
        elif words[0][0].isupper() and all(w[0].islower() for w in words[1:] if len(w) > 3):
            title_cases.append('sentence_case')
        else:
            title_cases.append('mixed')

    case_counts = Counter(title_cases)
    dominant_case = case_counts.most_common(1)[0]
    if dominant_case[1] < len(master_plan.slides):
        issues.append(
            f"  [Consistency] Title casing is mixed: {dict(case_counts)}. "
            f"Consider standardizing to {dominant_case[0]}."
        )

    # 2. Subtitle usage consistency
    has_subtitle = [bool(s.subtitle) for s in master_plan.slides if s.layout_type != 'cover']
    if 0 < sum(has_subtitle) < len(has_subtitle):
        issues.append(
            f"  [Consistency] Some slides have subtitles and some don't. "
            f"Consider adding/removing for uniformity."
        )

    # 3. Speaker notes length variance
    note_lengths = [len(s.speaker_notes.split()) for s in master_plan.slides]
    if note_lengths:
        avg = sum(note_lengths) / len(note_lengths)
        for slide in master_plan.slides:
            ratio = len(slide.speaker_notes.split()) / (avg + 1)
            if ratio < 0.3:
                issues.append(
                    f"  [Consistency] Slide {slide.slide_number} speaker notes are very short "
                    f"({len(slide.speaker_notes.split())} words vs avg {avg:.0f})."
                )
            elif ratio > 2.5:
                issues.append(
                    f"  [Consistency] Slide {slide.slide_number} speaker notes are very long "
                    f"({len(slide.speaker_notes.split())} words vs avg {avg:.0f}). "
                    f"Consider moving detail to a heavy-weight slide or splitting."
                )

    return issues
```

---

## 20. Audience-Specific Content Patterns

Different audiences expect different content patterns. A pitch to investors should have a TAM slide; an academic talk should cite methodology; a sales demo should have social proof. These patterns should be encoded as templates the Planner can draw from.

### 20A. Audience Profiles

```python
# audience_profiles.py

AUDIENCE_PROFILES = {
    "investors": {
        "expected_slides": [
            {"purpose": "hook", "must_have": "A surprising stat or bold claim about market opportunity"},
            {"purpose": "problem", "must_have": "Customer pain point with size/cost of problem"},
            {"purpose": "solution", "must_have": "Product demo or how-it-works (use split + image_role:'data')"},
            {"purpose": "data", "must_have": "TAM/SAM/SOM or market size stats (use stat layout)"},
            {"purpose": "evidence", "must_have": "Traction metrics: revenue, users, growth rate"},
            {"purpose": "comparison", "must_have": "Competitive advantage vs alternatives"},
            {"purpose": "context", "must_have": "Team slide or credibility indicators (keyvalue block)"},
            {"purpose": "cta", "must_have": "Ask (funding amount, next steps, timeline)"},
        ],
        "forbidden": ["long technical deep-dives", "more than 2 text-heavy slides in a row"],
        "tone": "confident",
        "stat_density": "high",  # investors want numbers
        "max_slides": 12,
    },
    "academic": {
        "expected_slides": [
            {"purpose": "context", "must_have": "Research question and motivation"},
            {"purpose": "context", "must_have": "Literature review or prior work (keyvalue block with citations)"},
            {"purpose": "process", "must_have": "Methodology (steps block or timeline)"},
            {"purpose": "data", "must_have": "Key results with statistical significance"},
            {"purpose": "evidence", "must_have": "Data visualization (image_role: 'data')"},
            {"purpose": "summary", "must_have": "Limitations and future work"},
        ],
        "forbidden": ["marketing language", "unsupported claims", "filler words"],
        "tone": "academic",
        "stat_density": "medium",
        "max_slides": 20,
    },
    "sales": {
        "expected_slides": [
            {"purpose": "hook", "must_have": "Customer pain point story (empathy-first)"},
            {"purpose": "solution", "must_have": "Product demo screenshots (image_role: 'data')"},
            {"purpose": "evidence", "must_have": "Social proof: logos, testimonials (pullquote), case study stats"},
            {"purpose": "comparison", "must_have": "Feature comparison vs competitor (comparison block)"},
            {"purpose": "data", "must_have": "ROI or cost savings stats"},
            {"purpose": "cta", "must_have": "Clear next step with URL/contact"},
        ],
        "forbidden": ["internal jargon", "technical architecture", "slides without clear benefit statement"],
        "tone": "professional",
        "stat_density": "high",
        "max_slides": 10,
    },
    "internal": {
        "expected_slides": [
            {"purpose": "context", "must_have": "Project status or OKR progress"},
            {"purpose": "data", "must_have": "Key metrics dashboard-style (multiple stat blocks)"},
            {"purpose": "problem", "must_have": "Blockers or risks (comparison: expected vs actual)"},
            {"purpose": "process", "must_have": "Next sprint plan or timeline"},
        ],
        "forbidden": ["excessive context the team already knows", "motivational fluff"],
        "tone": "casual",
        "stat_density": "high",
        "max_slides": 8,
    },
    "keynote": {
        "expected_slides": [
            {"purpose": "hook", "must_have": "Provocative question or surprising fact (callout block)"},
            {"purpose": "quote", "must_have": "At least one powerful quote slide"},
            {"purpose": "context", "must_have": "Personal story or anecdote (in speaker notes)"},
            {"purpose": "evidence", "must_have": "One powerful stat (stat layout, single number)"},
            {"purpose": "summary", "must_have": "Memorable takeaway (callout block)"},
        ],
        "forbidden": ["bullet-heavy slides", "more than 3 generic layouts", "data tables"],
        "tone": "inspirational",
        "stat_density": "low",  # few stats, but each one is impactful
        "max_slides": 15,
    },
}
```

### 20B. Config Integration

```yaml
# config.yaml
presentation_goals:
  audience_type: "investors"  # matches AUDIENCE_PROFILES keys
  audience: "Series A VCs at a demo day"  # free-text detail
```

If the user doesn't specify `audience_type`, we infer it:

```python
# In source_analyzer.py:
def infer_audience_type(config: AppConfig) -> str:
    """Heuristic inference of audience type from config clues."""
    audience_text = (config.presentation_goals.audience or '').lower()
    if any(w in audience_text for w in ['investor', 'vc', 'angel', 'funding', 'pitch']):
        return 'investors'
    if any(w in audience_text for w in ['professor', 'academic', 'conference', 'thesis', 'research']):
        return 'academic'
    if any(w in audience_text for w in ['customer', 'client', 'prospect', 'sales', 'demo']):
        return 'sales'
    if any(w in audience_text for w in ['team', 'sprint', 'standup', 'internal', 'manager']):
        return 'internal'
    if any(w in audience_text for w in ['keynote', 'ted', 'summit', 'festival']):
        return 'keynote'
    return 'general'  # no specific profile; use default behavior
```

### 20C. Planner Prompt Injection

The audience profile is injected into the system prompt dynamically:

```python
if audience_profile:
    prompt += f"\n\n--- AUDIENCE-SPECIFIC REQUIREMENTS ---\n"
    prompt += f"Audience type: {audience_type}\n"
    prompt += f"Expected slide types:\n"
    for req in audience_profile['expected_slides']:
        prompt += f"  • {req['purpose']}: {req['must_have']}\n"
    prompt += f"Avoid: {', '.join(audience_profile['forbidden'])}\n"
    prompt += f"Stat density: {audience_profile['stat_density']}\n"
    prompt += f"Max slides: {audience_profile['max_slides']}\n"
```

---

## 21. Content Quality Scoring

Separate from the visual audit (which checks rendering), content scoring measures the *substance and craft* of the text.

### 21A. Scoring Rubric

| Metric | Weight | How Measured | 0 (fail) | 5 (mediocre) | 10 (excellent) |
|--------|--------|-------------|----------|--------------|-----------------|
| **Insight density** | 20% | % of titles that contain specific claims, not just topics | "Overview", "Introduction" | "Market Growth" | "Market Grew 340% — Most Players Missed It" |
| **Content variety** | 15% | Number of distinct content block types used | All bullets | 2 types (bullets + stats) | 4+ types mixed appropriately |
| **Narrative flow** | 15% | All slides have a purpose mapping to the arc; transitions present | Random order, no arc | Some arc, some orphans | Clean arc, all transitions |
| **Density compliance** | 15% | % of slides within word count limits | >50% over limit | 80% compliant | 100% compliant |
| **Prose quality** | 15% | Filler words, passive voice, parallel structure | Multiple violations per slide | Occasional violations | Zero violations |
| **Stat credibility** | 10% | Stats have context; no hallucinated numbers from thin sources | Fabricated stats | Stats present but no context | All stats with source context |
| **Pacing** | 10% | Mix of light/medium/heavy; no 3+ consecutive same-weight | All medium | Some variety | Deliberate light/heavy alternation |

### 21B. Automated Scorer

```python
# content_scorer.py

def score_deck_content(master_plan: MasterPlan, source_brief: dict) -> dict:
    scores = {}

    # 1. Insight density (% of titles that contain numbers, comparisons, or strong verbs)
    insightful = 0
    for slide in master_plan.slides:
        title = slide.title
        has_number = bool(re.search(r'\d', title))
        has_strong_verb = any(v in title.lower() for v in
            ['cut', 'grew', 'doubled', 'reduced', 'saved', 'eliminated',
             'launched', 'built', 'discovered', 'proved', 'surpassed'])
        has_contrast = any(c in title.lower() for c in
            ['but', 'yet', 'despite', 'however', 'vs', 'versus', 'not'])
        if has_number or has_strong_verb or has_contrast:
            insightful += 1
    scores['insight_density'] = round(insightful / len(master_plan.slides) * 10, 1)

    # 2. Content variety
    block_types_used = set()
    for slide in master_plan.slides:
        for block in slide.content_blocks:
            block_types_used.add(block.block_type)
    variety_map = {1: 2, 2: 4, 3: 6, 4: 8, 5: 9, 6: 10, 7: 10}
    scores['content_variety'] = variety_map.get(len(block_types_used), 10)

    # 3. Narrative flow
    has_arc = all(hasattr(s, 'slide_purpose') and s.slide_purpose for s in master_plan.slides)
    has_transitions = sum(
        1 for s in master_plan.slides
        if any(t in s.speaker_notes.lower() for t in
               ['let\'s', 'which brings', 'next', 'moving to', 'now,', 'turning to'])
    )
    transition_ratio = has_transitions / max(len(master_plan.slides) - 1, 1)
    scores['narrative_flow'] = round((5 if has_arc else 0) + (transition_ratio * 5), 1)

    # 4. Density compliance
    compliant = 0
    for slide in master_plan.slides:
        words = count_words_in_slide(slide)
        limit = DENSITY_RULES.get(
            (slide.layout_type, getattr(slide, 'narrative_weight', 'medium')),
            200  # generous default
        )
        if words <= limit:
            compliant += 1
    scores['density_compliance'] = round(compliant / len(master_plan.slides) * 10, 1)

    # 5. Prose quality (count violations)
    total_violations = 0
    for slide in master_plan.slides:
        issues = check_prose_quality(slide)
        total_violations += len(issues)
    # Scale: 0 violations = 10, 1 per slide = 5, 2+ per slide = 2
    violation_ratio = total_violations / len(master_plan.slides)
    scores['prose_quality'] = round(max(0, 10 - violation_ratio * 3), 1)

    # 6. Stat credibility
    if source_brief['source_type'] == 'prompt':
        hallucination_issues = 0
        for slide in master_plan.slides:
            hallucination_issues += len(check_stat_hallucination(slide, source_brief))
        scores['stat_credibility'] = round(max(0, 10 - hallucination_issues * 2), 1)
    else:
        scores['stat_credibility'] = 8.0  # assume OK for rich sources

    # 7. Pacing
    weights = [getattr(s, 'narrative_weight', 'medium') for s in master_plan.slides]
    weight_variety = len(set(weights))
    consecutive_same = max(
        sum(1 for _ in g) for _, g in itertools.groupby(weights)
    ) if weights else 0
    pacing_score = 10
    if weight_variety == 1:
        pacing_score -= 5
    if consecutive_same >= 4:
        pacing_score -= 3
    elif consecutive_same >= 3:
        pacing_score -= 1
    scores['pacing'] = max(0, pacing_score)

    # Composite
    weights_map = {
        'insight_density': 0.20, 'content_variety': 0.15, 'narrative_flow': 0.15,
        'density_compliance': 0.15, 'prose_quality': 0.15, 'stat_credibility': 0.10,
        'pacing': 0.10,
    }
    scores['composite'] = round(
        sum(scores[k] * weights_map[k] for k in weights_map), 1
    )

    return scores
```

### 21C. Score Display

Included in the `--dry-run` output and the `audit` command:

```
Content Quality Score: 7.4 / 10
  Insight density:     8.0  (4/5 titles contain specific claims)
  Content variety:     6.0  (3 block types used: bullets, stat, comparison)
  Narrative flow:      9.0  (all slides have purpose; 4/4 transitions)
  Density compliance: 10.0  (all slides within word limits)
  Prose quality:       6.0  (2 filler words detected, 1 passive voice)
  Stat credibility:    8.0  (all stats from source material)
  Pacing:              5.0  (all slides are 'medium' weight — add a light slide)
```

---

## 22. Comprehensive Edge Case Catalog

### Source Material Edge Cases

| Scenario | Risk | Mitigation |
|----------|------|------------|
| Source is 1 sentence: "make a ppt about climate change" | Planner hallucinates everything | `source_type: 'prompt'` → disable StatBlock generation; force qualitative language; warn user |
| Source is 100K words (full book) | Planner context window overflow; monotone summary | Truncate to first 8K tokens + last 2K tokens; extract stats/quotes from FULL text first |
| Source is non-English but `language: English` | Mixed-language output | Detect language mismatch; add explicit "Translate all content to {language}" to prompt |
| Source has contradictory claims | Planner picks one arbitrarily | Source analyzer flags contradictions; Planner told to present both sides or pick the more recent claim |
| Source is a PDF with tables/images | `genai.files.upload` sends it, but tables may not parse | Pre-extract text from PDF using `pymupdf` as fallback; send both raw upload AND extracted text |
| User provides both `source_text` AND `source_file` | Which takes priority? | Concatenate: source_text first, then file content. Make this explicit in config docs. |
| Source contains profanity or controversial content | Gemini safety filters block the request | Catch safety block error; suggest user sanitize source; retry with lower temperature |

### Content Generation Edge Cases

| Scenario | Risk | Mitigation |
|----------|------|------------|
| Planner generates 0 slides | `MasterPlan.slides` is empty → crash in templater | Validator checks `len(slides) >= 1`; error message |
| Planner generates 50 slides for a 5-min talk | Way too many slides | Config `slide_count` enforced; Planner prompt says "strictly {n} slides"; validator truncates |
| Planner generates `layout_type: "billboard"` (invalid) | Pydantic validation catches it | Already handled by `Literal[...]` in schema — but retry on ValidationError (already in retry loop) |
| Planner generates `content_blocks` with wrong discriminator | Union deserialization fails silently or picks wrong type | Use Pydantic discriminated unions with `block_type` as discriminator field |
| All slides have `requires_image: true` | API rate limit on image generation (5 slides = 5 API calls) | Validator warns if >60% of slides require images; suggest reducing |
| StatBlock has `value: "Approximately 45 percent"` | Not formatted as hero stat | Validator checks `len(value) <= 6`; auto-fix attempt: extract number + symbol |
| ComparisonBlock has 5 left items, 1 right item | Visual imbalance in rendered comparison | Validator checks `abs(len(left) - len(right)) <= 1`; truncates longer side |
| StepBlock has 8 steps | Horizontal overflow in timeline/steps layout | Validator caps at 5 steps per StepBlock; extra steps moved to a second slide |
| PullQuoteBlock quote is 300 chars | Text overflow in quote template at 88px font | Validator auto-reduces font class (add `quote-long` CSS class if >150 chars) |
| KeyValueBlock has 10 pairs | Vertical overflow | Cap at 6 pairs; move rest to speaker notes |

### Planner API Edge Cases

| Scenario | Risk | Mitigation |
|----------|------|------------|
| Multi-pass mode: Pass 1 succeeds but Pass 2 fails (rate limit) | Partial state — outline exists but no content | Save outline to `outline.json` after Pass 1; allow `--offline-outline` flag to resume from Pass 2 |
| Multi-pass: Edit pass changes structure (adds/removes slides) | Breaks the outline contract | Edit prompt explicitly says "Do NOT change structure — only text content" |
| Model returns content_bullets instead of content_blocks (old format) | Template can't render | Legacy migration runs in validator; converts bullets → BulletBlock automatically |
| Model returns both content_bullets AND content_blocks | Duplicate content | Validator prioritizes content_blocks; clears content_bullets if both present |

### Template Rendering Edge Cases

| Scenario | Risk | Mitigation |
|----------|------|------------|
| `generic` layout with `callout` block + `bullets` block (2 blocks) | Both try to fill the same container → overlap | Template uses flexbox column; callout renders first (centered), bullets below |
| `stat` layout with 1 StatBlock | Single card centered looks odd without dividers | Template detects `stat_count == 1` → removes dividers, increases stat-value font to 160px |
| `stat` layout with 3 StatBlocks where values are different lengths ("$2.3B" vs "3") | Uneven visual weight | Template uses `flex: 1` so cards are equal width regardless of content length |
| `timeline` with 2 steps | Too few for a horizontal timeline | Template falls back to vertical layout if `steps <= 2`; adds more padding |
| `timeline` with 6 steps | Horizontal overflow | Template wraps to 2 rows if >4 steps; or validator caps at 5 |
| `quote` layout with very short quote (10 chars) | Huge font on tiny text looks wrong | Template adds `quote-short` class if < 40 chars; increases font to 128px |

---

## 23. Updated Implementation Phases (Revised)

### Phase 1 — Schema & Foundation
1. Add `ContentBlock` union types to `schemas.py` (with discriminated union on `block_type`)
2. Add `slide_purpose`, `narrative_weight`, `eyebrow`, `image_role`, `talking_time_seconds`, `layout_variant` to `Slide`
3. Add `narrative_arc`, `key_message`, `desired_outcome`, `audience_type`, `content_guidelines`, `data_and_evidence` to `AppConfig`
4. Add `narrative_arcs.py` (arc library)
5. Add `audience_profiles.py` (audience-specific patterns)
6. Add `source_analyzer.py` (pre-processing + nugget extraction)
7. Backward compat migration in `validator.py` (content_bullets → content_blocks)

### Phase 2 — Planner Upgrade
8. Implement `_multi_pass()` in `planner.py` (outline → fill → edit)
9. Rewrite `SYSTEM_INSTRUCTION` with all 17 content quality rules
10. Wire source brief (stats, quotes, key terms) into planner prompt
11. Wire audience profile into planner prompt
12. Wire narrative arc into planner prompt
13. Add `planner_mode: single|multi` config support
14. Dry-run test: verify 3-pass generates diverse, high-quality content

### Phase 3 — Template Extensions
15. Add eyebrow CSS + HTML to all existing templates
16. Add content block renderers (callout, comparison, steps, keyvalue) to `generic.html` and `split.html`
17. Create `templates/quote.html`
18. Create `templates/stat.html`
19. Create `templates/timeline.html`
20. Handle edge cases: single-stat, long-quote, 2-step-timeline, multi-block generic
21. Visual test all new layouts × all existing + new themes

### Phase 4 — Validator Deep Upgrade
22. Block × Layout compatibility checks
23. Density-aware word count validation
24. Deck balance checker (layout variety, weight pacing)
25. Prose quality checks (filler words, passive voice, parallel structure)
26. Title repetition / terminology consistency
27. Speaker note transition checker
28. Image semantic checks (purpose vs role mismatch)
29. Stat hallucination guard (for thin sources)
30. ComparisonBlock symmetry check
31. StepBlock/KeyValueBlock length caps
32. PullQuoteBlock length → font class

### Phase 5 — Content Scoring & Image Upgrade
33. `content_scorer.py` — 7-metric scoring rubric
34. Score display in `--dry-run` output
35. `image_role`-aware prompt prefixes in `image_generator.py`
36. Image prompts include slide_purpose, narrative context, audience

### Phase 6 — Speaker Notes & Export Enhancement
37. Enhanced speaker notes format with time estimates, transitions, image status
38. Content quality score in the notes header
39. Block-type summary per slide in notes

### Phase 7 — Polish & Documentation
40. `config_reference.yaml` — document all new config keys
41. `README.md` — content quality section, arc/audience docs, multi-pass docs
42. Add `--audit content` subcommand flag for content-only scoring

---

## 24. Updated File Change List

| File | Action | Description |
|------|--------|-------------|
| `schemas.py` | MODIFY | ContentBlock discriminated union; extended Slide fields; new layout types |
| `narrative_arcs.py` | NEW | 7 arc templates with sequences and best-for descriptions |
| `audience_profiles.py` | NEW | 5 audience profiles with expected slides, forbidden patterns, tone, stat density |
| `source_analyzer.py` | NEW | Pre-processor: source classification, stat/quote/term extraction, structure detection |
| `content_scorer.py` | NEW | 7-metric content quality scoring rubric + composite score |
| `config_manager.py` | MODIFY | New AppConfig sections: audience_type, content_guidelines, data_and_evidence, planner_mode |
| `planner.py` | MODIFY | Multi-pass pipeline; 17 content rules; source brief injection; audience profile injection |
| `validator.py` | MODIFY | Block compatibility; density; prose quality; tone consistency; cross-slide consistency; stat hallucination; legacy migration |
| `image_generator.py` | MODIFY | image_role-aware prompt building with audience/purpose context |
| `compiler.py` | MODIFY | Enhanced speaker notes with time estimates, block summaries, content score, image status |
| `cli.py` | MODIFY | `--audit content` flag; `planner_mode` wiring; source brief passing; score display in dry-run |
| `templates/generic.html` | MODIFY | ContentBlock renderers; eyebrow; multi-block layout; narrative_weight padding |
| `templates/cover.html` | MODIFY | Eyebrow support |
| `templates/split.html` | MODIFY | ContentBlock renderers; eyebrow; layout_variant:reverse |
| `templates/infographic.html` | MODIFY | StatBlock rendering in info cards; eyebrow |
| `templates/quote.html` | NEW | Full-slide pull quote layout with background image support |
| `templates/stat.html` | NEW | Hero statistics layout (1–3 StatBlocks) with adaptive grid |
| `templates/timeline.html` | NEW | Horizontal timeline with StepBlock rendering |
| `templates/base.html` | MODIFY | New block-type CSS; eyebrow CSS; narrative_weight padding classes |
| `config_reference.yaml` | MODIFY | All new config keys documented |
| `README.md` | MODIFY | Content quality, arcs, audience profiles, multi-pass, scoring |

---

> [!IMPORTANT]
> **Priority order if implementing incrementally:**
> 1. **Planner system prompt rewrite** (Rules 1–17) — biggest bang for zero new code
> 2. **Source analyzer** — makes the Planner dramatically better with pre-extracted nuggets
> 3. **ContentBlock schema + validator migration** — enables template rendering of rich types
> 4. **3 new templates** (quote, stat, timeline) — makes new content types visible
> 5. **Multi-pass pipeline** — only after single-pass with new rules is validated
> 6. **Content scoring** — useful for iteration but not blocking

> [!NOTE]
> The multi-pass pipeline (§16) and the content scorer (§21) together form a **closed-loop content quality system**: generate → score → if score < threshold, re-run edit pass with score feedback. This is the content-quality equivalent of the visual audit auto-fix loop described in the UI plan. Both plans are designed to compose together.
