# Plan 01: Code Review Remediation & Stability Hardening

- **Plan ID**: `PLAN-01`
- **Correlated Review**: [Architectural Code Review #01 (CR-01)](../../reviews/code/01_code_review.md)
- **Created**: 2026-10-16T22:15:00+05:30
- **Status**: Ready for Implementation
- **Target Package**: `ppt_maker/`

---

## Executive Summary

This remediation plan tracks the implementation of all 14 actionable findings identified in [Architectural Code Review #01](../../reviews/code/01_code_review.md). The findings span cross-platform compatibility, Jinja auto-escaping, validator integrity, rate limiting scaling, type safety, resource leaks, and browser rendering efficiency.

To minimize regression risk and preserve test stability throughout execution, changes are organized into 4 sequential phases. All changes will be verified against existing test suites (`test_features.py` and `test_advanced.py`), with new unit test cases added for each resolved defect.

---

## Remediation Matrix

| ID | Severity | Component | Finding | Phase | Status |
|---|:---:|---|---|:---:|:---:|
| `SEC-01 / BUG-01` | **CRITICAL** | `ppt_maker/templates/base.html` | CSS variables auto-escaped inside `<style>` blocks | Phase 1 | Completed |
| `BUG-02` | **HIGH** | `ppt_maker/rendering/templater.py` | Non-portable `file://` URI formatting on Windows | Phase 1 | Completed |
| `BUG-03` | **HIGH** | `ppt_maker/planning/validator.py` | Duplicate slide numbers detected but not re-indexed | Phase 1 | Completed |
| `TYPE-01` | **MEDIUM** | `ppt_maker/core/schemas.py`, `ppt_maker/export/pptx_exporter.py` | `KeyValueBlock.pairs` loose typing causes crash on string items | Phase 1 | Completed |
| `BUG-05` | **HIGH** | `ppt_maker/imaging/image_generator.py` | Key rotation on HTTP 429 abandons failing slide to gradient | Phase 2 | Completed |
| `PERF-01` | **MEDIUM** | `ppt_maker/imaging/image_generator.py` | Static `_RateLimiter` limits throughput regardless of key count | Phase 2 | Completed |
| `LOGIC-01` | **MEDIUM** | `ppt_maker/planning/validator.py` | Validator forces images on self-contained slides, penalizing audit score | Phase 2 | Completed |
| `LOGIC-02` | **MEDIUM** | `ppt_maker/planning/planner.py` | Deterministic safety filter errors trigger useless 105s retries | Phase 2 | Completed |
| `BUG-04` | **HIGH** | `ppt_maker/rendering/renderer.py` | DOM audit JS skips elements with standard `overflow` values | Phase 3 | Completed |
| `NLP-01` | **LOW** | `ppt_maker/planning/source_analyzer.py` | Calendar years (1900–2099) misidentified as key metrics | Phase 3 | Completed |
| `BUG-06` | **LOW** | `ppt_maker/design/theme_resolver.py` | 3-character hex shorthand colors crash `hex_to_rgb` | Phase 3 | Completed |
| `LEAK-01` | **LOW** | `ppt_maker/imaging/image_matcher.py`, `ppt_maker/export/compiler.py` | Unclosed PIL Image file handles leak descriptors | Phase 4 | Pending |
| `LEAK-02` | **LOW** | `ppt_maker/planning/planner.py` | Uploaded multimodal files not deleted in `finally` block | Phase 4 | Pending |
| `PERF-02` | **MEDIUM** | `ppt_maker/rendering/renderer.py` | Triple Chromium process launches during full presentation render | Phase 4 | Pending |

---

## Phase 1: Critical Security & Core Stability

Focuses on preventing template rendering errors, cross-platform path failures, silent slide overwrites, and unhandled data structure crashes during export.

### 1.1 `SEC-01 / BUG-01`: Mark CSS Variables as `| safe` in Jinja Template
- **Files**: [`ppt_maker/templates/base.html`](file:///home/intruder-jsr/exps/ai-ppt-maker/ppt_maker/templates/base.html#L59)
- **Problem**: Jinja2 with `autoescape=True` escapes quotes in CSS values (e.g. font family names become `&#34;Space Grotesk&#34;`), corrupting browser CSS parsing.
- **Action**: Add `| safe` filter to CSS variable values:
  ```jinja2
  {% for key, val in theme.css_variables.items() %}
    {{ key }}: {{ val | safe }};
  {% endfor %}
  ```
- **Verification**: Render a slide with a multi-word font family and assert output does not contain `&#34;`.
- **Status**: [x] Completed

### 1.2 `BUG-02`: Cross-Platform RFC 8089 File URIs
- **Files**: [`ppt_maker/rendering/templater.py`](file:///home/intruder-jsr/exps/ai-ppt-maker/ppt_maker/rendering/templater.py#L65)
- **Problem**: `f"file://{os.path.abspath(raw_image_path)}"` produces invalid URIs on Windows (e.g. `file://C:\path\to\image.png`), causing Chromium 404s.
- **Action**: Use standard `pathlib.Path.resolve().as_uri()`:
  ```python
  from pathlib import Path
  image_path = Path(raw_image_path).resolve().as_uri()
  ```
- **Verification**: Test with Windows-style path string simulation; verify valid `file:///` format.
- **Status**: [x] Completed

### 1.3 `BUG-03`: Enforce Sequential Slide Renumbering
- **Files**: [`ppt_maker/planning/validator.py`](file:///home/intruder-jsr/exps/ai-ppt-maker/ppt_maker/planning/validator.py#L48-L55)
- **Problem**: Non-sequential or duplicate slide numbers (e.g. `[1, 2, 2, 3]`) are warned but not corrected, causing downstream HTML, image, and PPTX collisions.
- **Action**: After sorting slides, re-index `slide.slide_number = idx` sequentially:
  ```python
  master_plan.slides.sort(key=lambda s: s.slide_number)
  for idx, slide in enumerate(master_plan.slides, start=1):
      if slide.slide_number != idx:
          slide.slide_number = idx
          issues += 1
  ```
- **Verification**: Pass a deck with duplicate/gap numbers (`[1, 1, 4]`) into validator; assert output has numbers `[1, 2, 3]`.
- **Status**: [x] Completed

### 1.4 `TYPE-01`: KeyValueBlock Schema & Guard
- **Files**: [`ppt_maker/core/schemas.py`](file:///home/intruder-jsr/exps/ai-ppt-maker/ppt_maker/core/schemas.py#L58), [`ppt_maker/export/pptx_exporter.py`](file:///home/intruder-jsr/exps/ai-ppt-maker/ppt_maker/export/pptx_exporter.py#L351)
- **Problem**: `pairs: List[dict]` allows invalid structures or plain strings; `pair.get()` crashes during PPTX generation.
- **Action**:
  1. Add typed `KeyValuePair(BaseModel)` with `key: str` and `value: str`.
  2. In `pptx_exporter.py`, support both `KeyValuePair` objects and dicts safely:
     ```python
     if isinstance(pair, dict):
         k, v = pair.get('key', ''), pair.get('value', '')
     elif hasattr(pair, 'key'):
         k, v = pair.key, pair.value
     else:
         k, v = str(pair), ''
     ```
- **Verification**: Pass non-dict pairs into PPTX export without exceptions.
- **Status**: [x] Completed

---

## Phase 2: Rate Limiting & Execution Logic

Focuses on multi-key scaling, graceful rate limit recovery without discarding slides, and avoiding contradictory image requirements.

### 2.1 `BUG-05`: Retry Current Slide Upon Key Rotation
- **Files**: [`ppt_maker/imaging/image_generator.py`](file:///home/intruder-jsr/exps/ai-ppt-maker/ppt_maker/imaging/image_generator.py#L267-L275)
- **Problem**: When hitting HTTP 429, key is rotated but method returns `False`, causing caller to permanently degrade current slide to a gradient fallback.
- **Action**: Implement immediate retry loop over configured keys for the failing slide before defaulting to gradient.
- **Verification**: Mock a 429 on Key #1 and success on Key #2; assert slide is generated with image, not gradient.
- **Status**: [x] Completed

### 2.2 `PERF-01`: Dynamic Multi-Key Rate Limiting
- **Files**: [`ppt_maker/imaging/image_generator.py`](file:///home/intruder-jsr/exps/ai-ppt-maker/ppt_maker/imaging/image_generator.py#L27)
- **Problem**: Static `max_per_minute=5` limits throughput even with multiple API keys, causing unnecessary delays and timeouts.
- **Action**: Scale rate limit: `effective_rpm = max(5, 5 * len(self._keys))`.
- **Verification**: Test rate limiter capacity with multiple keys configured.
- **Status**: [x] Completed

### 2.3 `LOGIC-01`: Align Image Requirement Rules with Content Scorer
- **Files**: [`ppt_maker/planning/validator.py`](file:///home/intruder-jsr/exps/ai-ppt-maker/ppt_maker/planning/validator.py#L122-L128)
- **Problem**: Validator forces `requires_image=True` on all layouts (`stat`, `quote`, `timeline`), causing >90% image coverage and penalizing deck quality scores.
- **Action**: Only force `requires_image=True` on layouts that require visual imagery (`split`). Let self-contained layouts retain the planner's original requirement.
- **Verification**: Validate a master plan with text-only stat slides; assert `requires_image` remains `False`.
- **Status**: [x] Completed

### 2.4 `LOGIC-02`: Remove Safety Filters from Retryable Errors
- **Files**: [`ppt_maker/planning/planner.py`](file:///home/intruder-jsr/exps/ai-ppt-maker/ppt_maker/planning/planner.py#L146)
- **Problem**: Safety violations are deterministic; retrying 4 times wastes 105 seconds of backoff sleep.
- **Action**: Remove `"safety"` from `RETRYABLE_ERRORS` and fail immediately with actionable user guidance.
- **Verification**: Verify safety exception raises immediately without sleep.
- **Status**: [x] Completed

---

## Phase 3: Audit Accuracy & NLP Extraction Polish

Focuses on correcting DOM overflow inspection, improving heuristic source analysis, and theme parsing flexibility.

### 3.1 `BUG-04`: Fix DOM Audit Script Overflow Inspection
- **Files**: [`ppt_maker/rendering/renderer.py`](file:///home/intruder-jsr/exps/ai-ppt-maker/ppt_maker/rendering/renderer.py#L250-L254)
- **Problem**: Script skips `overflow === 'visible'` and `'hidden'`, skipping virtually 100% of standard presentation elements.
- **Action**: Target content containers directly (`.split-content, .generic-content, .card, .block-bullets, .block-comparison`) and check for `scrollHeight > clientHeight + 4`.
- **Verification**: Create a mock slide with overflowing text; assert audit reports `OVERFLOW` warning.
- **Status**: [x] Completed

### 3.2 `NLP-01`: Filter Calendar Years from Key Statistics
- **Files**: [`ppt_maker/planning/source_analyzer.py`](file:///home/intruder-jsr/exps/ai-ppt-maker/ppt_maker/planning/source_analyzer.py#L44)
- **Problem**: 4-digit numbers match large-number pattern, extracting years like `2024` as business stats.
- **Action**: Exclude numbers in range 1900–2099 from `_STAT_PATTERN` matches unless accompanied by currency or percentage symbols.
- **Verification**: Run analyzer on text with "In 2024, revenue grew 45%"; assert `2024` is not in extracted statistics.
- **Status**: [x] Completed

### 3.3 `BUG-06`: Support 3-Character Hex Shorthand Colors
- **Files**: [`ppt_maker/design/theme_resolver.py`](file:///home/intruder-jsr/exps/ai-ppt-maker/ppt_maker/design/theme_resolver.py#L27)
- **Problem**: `hex_to_rgb` strictly requires length 6; shorthand like `#FFF` or `#369` crashes with `ValueError`.
- **Action**: Expand 3-char hex strings into 6-char strings (`#FFF` $\rightarrow$ `#FFFFFF`).
- **Verification**: Test `hex_to_rgb("#FFF")` and `hex_to_rgb("#123")`.
- **Status**: [x] Completed

---

## Phase 4: Resource Management & Memory Hygiene

Focuses on file handle lifecycles, cloud file cleanup on abort, and rendering process efficiency.

### 4.1 `LEAK-01`: Wrap PIL Image Handles in Context Managers
- **Files**: [`ppt_maker/imaging/image_matcher.py`](file:///home/intruder-jsr/exps/ai-ppt-maker/ppt_maker/imaging/image_matcher.py#L301), [`ppt_maker/export/compiler.py`](file:///home/intruder-jsr/exps/ai-ppt-maker/ppt_maker/export/compiler.py#L25-L33)
- **Problem**: Calling `Image.open(p)` without closing leaks file descriptors during large image scans.
- **Action**: Use `with Image.open(...) as img:` across matcher and compiler.
- **Verification**: Verify all image opens are closed after use.
- **Status**: [ ] Not Started

### 4.2 `LEAK-02`: Ensure Cloud Multi-Modal File Cleanup in `finally`
- **Files**: [`ppt_maker/planning/planner.py`](file:///home/intruder-jsr/exps/ai-ppt-maker/ppt_maker/planning/planner.py#L295)
- **Problem**: Early abort or unexpected exceptions can leave uploaded files on Google servers.
- **Action**: Wrap multi-modal planning in a `try ... finally` block ensuring `client.files.delete` is executed.
- **Verification**: Test mock file upload and assert deletion is called on error.
- **Status**: [ ] Not Started

### 4.3 `PERF-02`: Consolidate Playwright Browser Instances
- **Files**: [`ppt_maker/rendering/renderer.py`](file:///home/intruder-jsr/exps/ai-ppt-maker/ppt_maker/rendering/renderer.py)
- **Problem**: Three separate browser launches for PDF, PNG screenshots, and background plates.
- **Action**: Support an optional shared browser session or unified render flow to eliminate redundant browser start/stops.
- **Verification**: Measure total render time on 5-slide deck before and after.
- **Status**: [ ] Not Started

---

## Test & Verification Protocol

After each phase, execute the comprehensive test suites:

```bash
# 1. Modular feature tests (12 tests)
pytest tests/test_features.py -v

# 2. End-to-end and mock pipeline tests (44 tests)
pytest tests/test_advanced.py -v
```

Every phase completion will be committed with a descriptive git commit message and pushed to GitHub.
