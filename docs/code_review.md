# AI Presentation Agency — Comprehensive Code Review & Quality Audit

**Repository**: `ai-ppt-maker`  
**Review Type**: Exhaustive Architecture, Code Quality, Security & Performance Review  
**Date**: October 2026  
**Status**: Complete  

---

## Table of Contents

1. [Executive Summary & Health Matrix](#1-executive-summary--health-matrix)
2. [Summary of Findings](#2-summary-of-findings)
3. [Critical & High Severity Findings](#3-critical--high-severity-findings)
   - [SEC-01 / BUG-01: Jinja2 Auto-Escape Corrupts Theme CSS Variables](#sec-01--bug-01-jinja2-auto-escape-corrupts-theme-css-variables)
   - [BUG-02: Non-Portable File URIs Break Chromium on Windows](#bug-02-non-portable-file-uris-break-chromium-on-windows)
   - [BUG-03: Duplicate Slide Numbers Cause Silent Content Loss](#bug-03-duplicate-slide-numbers-cause-silent-content-loss)
   - [BUG-04: Defective Overflow Detection in DOM Audit Script](#bug-04-defective-overflow-detection-in-dom-audit-script)
   - [BUG-05: Key Rotation in Image Generator Abandons Slides to Fallbacks](#bug-05-key-rotation-in-image-generator-abandons-slides-to-fallbacks)
4. [Medium Severity Issues & Logic Flaws](#4-medium-severity-issues--logic-flaws)
   - [LOGIC-01: Validator Forces Images on Self-Contained Slides, Penalizing Audit Scores](#logic-01-validator-forces-images-on-self-contained-slides-penalizing-audit-scores)
   - [PERF-01: Static Rate Limiter Stifles Multi-Key Scaling & Causes Timeouts](#perf-01-static-rate-limiter-stifles-multi-key-scaling--causes-timeouts)
   - [TYPE-01: Unvalidated `KeyValueBlock.pairs` Causes Potential PPTX Crash](#type-01-unvalidated-keyvalueblockpairs-causes-potential-pptx-crash)
   - [LOGIC-02: Deterministic Safety Filter Violations Trigger Unnecessary Backoff Sleep](#logic-02-deterministic-safety-filter-violations-trigger-unnecessary-backoff-sleep)
   - [NLP-01: Calendar Years Misidentified as Key Statistics](#nlp-01-calendar-years-misidentified-as-key-statistics)
   - [BUG-06: 3-Character Shorthand Hex Colors Crash `ThemeResolver`](#bug-06-3-character-shorthand-hex-colors-crash-themeresolver)
5. [Resource Management & Performance Optimizations](#5-resource-management--performance-optimizations)
   - [PERF-02: Triple Chromium Browser Spawning in Render Pipeline](#perf-02-triple-chromium-browser-spawning-in-render-pipeline)
   - [LEAK-01: Unclosed PIL Image File Descriptors](#leak-01-unclosed-pil-image-file-descriptors)
   - [LEAK-02: Unhandled Multi-Modal File Cleanup on Early Abort](#leak-02-unhandled-multi-modal-file-cleanup-on-early-abort)
6. [Component-by-Component Review](#6-component-by-component-review)
7. [Prioritized Remediation Plan](#7-prioritized-remediation-plan)

---

## 1. Executive Summary & Health Matrix

The `ai-ppt-maker` codebase is a thoughtfully architected, highly capable autonomous presentation generation pipeline. Its multi-role agency model (Narrative Architect, Art Director, CSS Themer), structured JSON contracts via Pydantic, and dual vector PDF / editable PPTX output targets place it well ahead of basic script wrappers.

However, a deep examination of edge cases, multi-platform environments, error handling, and resource lifecycles reveals several actionable bugs, performance bottlenecks, and architectural contradictions that impact production stability.

### System Health Scorecard

| Domain | Rating | Assessment |
|---|:---:|---|
| **System Architecture & Design** | **A-** | Excellent separation of concerns, strong domain models (`MasterPlan`, `Slide`, `ContentBlock`), well-defined pipeline phases. |
| **Visual Design & Typography** | **A** | Outstanding CSS design tokens, 8 coherent themes, Indic font support, WCAG contrast checking. |
| **Reliability & Resilience** | **B** | Good multi-key rotation and gradient fallbacks; hindered by unhandled slide renumbering and dead-end image generation rotation. |
| **Performance & Resource Hygiene** | **B-** | Triple Playwright launches per deck; static token bucket bottlenecking multi-key setups; unclosed PIL handles. |
| **Cross-Platform Compatibility** | **B-** | `file://` URI formatting assumes Unix forward-slashes; fails on Windows absolute paths with drive letters. |
| **Code Hygiene & Type Safety** | **B+** | Strong Pydantic foundations; a few loosely typed fields (`pairs: List[dict]`) and unused function arguments. |

---

## 2. Summary of Findings

| ID | Severity | Component | Issue Description | Impact |
|---|:---:|---|---|---|
| **SEC-01 / BUG-01** | **CRITICAL** | `templates/base.html`, `templater.py` | Jinja2 autoescape converts quotes to `&#34;` inside `<style>` blocks. | Invalid CSS injected into DOM when CSS variables contain quotes (e.g. font names). |
| **BUG-02** | **HIGH** | `templater.py` | Manual `file://{abspath}` string formatting is non-portable on Windows. | Local image assets fail to resolve in Chromium on Windows (`net::ERR_FILE_NOT_FOUND`). |
| **BUG-03** | **HIGH** | `validator.py` | Duplicate slide numbers detected by validator are logged but never re-indexed. | HTML slides, PNGs, and PPTX overlays silently overwrite each other, dropping slides. |
| **BUG-04** | **HIGH** | `renderer.py` | `_DOM_AUDIT_JS` skips elements where `overflow === 'visible'` or `'hidden'`. | Overflow detection fails to catch overflowing text on almost all standard HTML elements. |
| **BUG-05** | **HIGH** | `image_generator.py` | Key rotation on HTTP 429 returns `False`, causing immediate gradient fallback. | Rotating keys does not benefit the failing slide; that slide is permanently degraded to a gradient. |
| **LOGIC-01** | **MEDIUM** | `validator.py`, `quality_checker.py` | Validator forces `requires_image=True` on all layouts, conflicting with quality scorer. | Over-generates images, exhausts quota, and directly lowers deck audit score (<70% target). |
| **PERF-01** | **MEDIUM** | `image_generator.py` | `_RateLimiter` hardcodes `max_per_minute=5` regardless of how many API keys exist. | Multiple keys do not increase image throughput; causes 60s test timeouts on 10-slide decks. |
| **TYPE-01** | **MEDIUM** | `schemas.py`, `pptx_exporter.py` | `KeyValueBlock.pairs` typed as `List[dict]`; `pair.get()` crashes if items are strings. | Unhandled exception and failed PPTX export if LLM outputs string pairs. |
| **LOGIC-02** | **MEDIUM** | `planner.py` | `"safety"` included in `RETRYABLE_ERRORS`. | Deterministic safety filter blocks stall the pipeline for 105 seconds across 4 useless retries. |
| **NLP-01** | **LOW** | `source_analyzer.py` | `_STAT_PATTERN` regex matches any 4-digit number (`\d[\d,]{3,}`). | Calendar years (e.g. `2024`, `2025`) are extracted as statistics and featured in stat slides. |
| **BUG-06** | **LOW** | `theme_resolver.py` | `hex_to_rgb` strictly requires `len(h) == 6`, rejecting 3-char shorthand hex. | Shorthand colors like `#FFF` or `#000` raise `ValueError` instead of expanding to 6 characters. |
| **PERF-02** | **MEDIUM** | `renderer.py` | Separate Playwright Chromium instances launched for PDF, PNG, and PPTX backgrounds. | 3× browser process launch overhead and 3× DOM navigations per slide. |
| **LEAK-01** | **LOW** | `image_matcher.py`, `compiler.py` | `Image.open()` called without context manager or `close()`. | Unclosed PIL image file handles accumulate across large image sets. |
| **LEAK-02** | **LOW** | `planner.py` | `client.files.delete` not in a `finally` block during multi-modal planning. | Uploaded audio/video/PDF source files remain on Google servers if exceptions occur. |

---

## 3. Critical & High Severity Findings

### SEC-01 / BUG-01: Jinja2 Auto-Escape Corrupts Theme CSS Variables

- **Location**: [`templates/base.html:59`](file:///home/intruder-jsr/exps/ai-ppt-maker/templates/base.html#L59) and [`templater.py:31`](file:///home/intruder-jsr/exps/ai-ppt-maker/templater.py#L31)
- **Severity**: **Critical**
- **Description**:
  In `templater.py`, Jinja2 is initialized with `autoescape=True`:
  ```python
  self.env = jinja2.Environment(loader=template_loader, autoescape=True)
  ```
  In `templates/base.html`, dynamic CSS variables are rendered into the `<style>` block:
  ```html
  {% for key, val in theme.css_variables.items() %}
  {{ key }}: {{ val }};
  {% endfor %}
  ```
  Because autoescaping is active, any string variable containing quotes or ampersands is HTML-escaped. For example, if a font family is specified as `'"Space Grotesk", sans-serif'`, Jinja outputs:
  ```css
  --font-family: &#34;Space Grotesk&#34;, sans-serif;
  ```
  Browsers cannot parse HTML entities inside `<style>` tags. The CSS rule becomes invalid and is silently dropped by the browser's CSS parser.
- **Remediation**:
  Mark variable values as safe in `base.html`:
  ```diff
  -  {{ key }}: {{ val }};
  +  {{ key }}: {{ val | safe }};
  ```

---

### BUG-02: Non-Portable File URIs Break Chromium on Windows

- **Location**: [`templater.py:65`](file:///home/intruder-jsr/exps/ai-ppt-maker/templater.py#L65)
- **Severity**: **High**
- **Description**:
  When passing image paths to Jinja templates, `templater.py` builds file URIs using manual string interpolation:
  ```python
  image_path = f"file://{os.path.abspath(raw_image_path)}"
  ```
  On Windows systems, `os.path.abspath` returns Windows-style paths with backslashes and drive letters (e.g. `C:\Users\Project\assets\slide_1.png`). The resulting string:
  ```
  file://C:\Users\Project\assets\slide_1.png
  ```
  is not a valid RFC 8089 file URI. Chromium requires forward slashes and three initial slashes (e.g. `file:///C:/Users/Project/assets/slide_1.png`). On Windows, this causes image loading to fail silently with `net::ERR_FILE_NOT_FOUND`, triggering the image `onerror` handler and rendering blank or grey backgrounds.
- **Remediation**:
  Use standard library `pathlib.Path.resolve().as_uri()`:
  ```diff
  -  image_path = f"file://{os.path.abspath(raw_image_path)}"
  +  from pathlib import Path
  +  image_path = Path(raw_image_path).resolve().as_uri()
  ```

---

### BUG-03: Duplicate Slide Numbers Cause Silent Content Loss

- **Location**: [`validator.py:48-55`](file:///home/intruder-jsr/exps/ai-ppt-maker/validator.py#L48-L55)
- **Severity**: **High**
- **Description**:
  The LLM occasionally outputs non-sequential or duplicate slide numbers (e.g., slides numbered `[1, 2, 2, 3]`). `ContentValidator` detects this:
  ```python
  seen_numbers = set()
  for slide in master_plan.slides:
      if slide.slide_number in seen_numbers:
          print(f"  [Warning] Duplicate slide_number {slide.slide_number} detected.")
          issues += 1
      seen_numbers.add(slide.slide_number)
  master_plan.slides.sort(key=lambda s: s.slide_number)
  ```
  Crucially, it **only logs a warning and does not re-index the slides**. Downstream systems depend on unique slide numbers:
  1. `templater.py` writes to `temp_build/slide_{slide.slide_number:03d}.html`. Slide 2b overwrites Slide 2a.
  2. `image_generator.py` writes to `assets/slide_{slide.slide_number}.png`. Slide 2b overwrites Slide 2a.
  3. `pptx_exporter.py` builds `slides_map = {s.slide_number: s for s in master_plan.slides}`, dropping Slide 2a entirely.
- **Remediation**:
  Enforce sequential renumbering in `ContentValidator`:
  ```diff
  -  master_plan.slides.sort(key=lambda s: s.slide_number)
  +  master_plan.slides.sort(key=lambda s: s.slide_number)
  +  for idx, slide in enumerate(master_plan.slides, start=1):
  +      if slide.slide_number != idx:
  +          slide.slide_number = idx
  +          issues += 1
  ```

---

### BUG-04: Defective Overflow Detection in DOM Audit Script

- **Location**: [`renderer.py:250-254`](file:///home/intruder-jsr/exps/ai-ppt-maker/renderer.py#L250-L254)
- **Severity**: **High**
- **Description**:
  The DOM audit JavaScript injected into Playwright before screenshotting contains a logical flaw:
  ```javascript
  const all = document.querySelectorAll('*');
  for (const el of all) {
    const style = window.getComputedStyle(el);
    if (style.overflow === 'hidden' || style.overflow === 'visible') continue;
    if (el.scrollHeight > el.clientHeight + 4) {
      warnings.push({ ... });
    }
  }
  ```
  In CSS, the initial default value for `overflow` on all HTML elements is `'visible'`. Presentation slide containers explicitly use `'hidden'` to prevent scrollbars.
  By skipping any element where `overflow === 'visible' || overflow === 'hidden'`, the script **skips virtually 100% of the elements in the DOM**. The check only ever executes on elements styled with `overflow: scroll` or `overflow: auto`, which do not exist in presentation slide designs. Consequently, text overflowing card containers is never detected.
- **Remediation**:
  Detect child bounding boxes extending outside parent bounds or check client height on card and text blocks:
  ```javascript
  // Target cards, text containers, and blocks directly
  const containers = document.querySelectorAll('.split-content, .generic-content, .card, .block-bullets, .block-comparison');
  for (const el of containers) {
    if (el.scrollHeight > el.clientHeight + 4) {
      warnings.push({
        type: 'OVERFLOW',
        selector: el.className || el.tagName,
        excess_px: el.scrollHeight - el.clientHeight,
        message: `Content container ${el.className} overflows by ${el.scrollHeight - el.clientHeight}px`
      });
    }
  }
  ```

---

### BUG-05: Key Rotation in Image Generator Abandons Slides to Fallbacks

- **Location**: [`image_generator.py:371-379`](file:///home/intruder-jsr/exps/ai-ppt-maker/image_generator.py#L371-L379) and [`image_generator.py:267-275`](file:///home/intruder-jsr/exps/ai-ppt-maker/image_generator.py#L267-L275)
- **Severity**: **High**
- **Description**:
  When `_generate_with_api` hits an HTTP 429 rate limit:
  ```python
  if len(self._keys) > 1:
      old_idx = self._key_idx
      self._key_idx = (self._key_idx + 1) % len(self._keys)
      from api_keys import get_client
      self.client, self._key_idx = get_client(self._key_idx)
      rprint(f"  [RateLimit] Key #{old_idx+1} → key #{self._key_idx+1}")
      return False, 2  # Short retry delay since we switched keys
  ```
  The method rotates `self.client`, but **returns `False` to the caller**. In `generate_all`:
  ```python
  success, retry_delay = self._generate_with_api(raw_prompt, out_path)
  if success:
      ...
  else:
      # Immediately generates gradient fallback for this slide!
      self._generate_gradient(current_theme, primary_color, out_path, slide.slide_number)
      image_manifest[slide.slide_number] = {'path': out_path, 'status': 'fallback', ...}
  ```
  The caller does not retry the current slide with the new key! It instantly marks the slide as a fallback gradient. The second API key is only used for subsequent slides, leaving the slide that triggered the rotation permanently un-generated.
- **Remediation**:
  Implement a key-rotation retry loop directly inside `_generate_with_api` or `generate_all`:
  ```python
  max_attempts = len(self._keys)
  for attempt in range(max_attempts):
      success, retry_delay = self._generate_with_api(raw_prompt, out_path)
      if success:
          break
      if retry_delay == 2 and attempt < max_attempts - 1:
          continue  # Key was rotated, retry current slide immediately
      # Normal rate limit backoff or permanent failure
      break
  ```

---

## 4. Medium Severity Issues & Logic Flaws

### LOGIC-01: Validator Forces Images on Self-Contained Slides, Penalizing Audit Scores

- **Location**: [`validator.py:122-128`](file:///home/intruder-jsr/exps/ai-ppt-maker/validator.py#L122-L128) vs [`content_scorer.py:226`](file:///home/intruder-jsr/exps/ai-ppt-maker/content_scorer.py#L226) vs [`quality_checker.py:101-109`](file:///home/intruder-jsr/exps/ai-ppt-maker/quality_checker.py#L101-L109)
- **Severity**: **Medium**
- **Description**:
  There is a direct architectural contradiction between the validator, scorer, and quality checker:
  1. `validator.py` forces `slide.requires_image = True` for **every non-cover layout** (`generic`, `split`, `stat`, `quote`, `timeline`, `infographic`).
  2. `content_scorer.py` specifies that layouts in `_SELF_CONTAINED = {'stat', 'timeline', 'infographic', 'quote'}` look better without images.
  3. `quality_checker.py` scores image coverage with:
     ```python
     # Ideal: 40–70% of slides have images
     if 0.4 <= img_pct <= 0.7:
         img_score = 10
     elif 0.7 < img_pct <= 0.8:
         img_score = 7
     else:
         img_score = 6
     ```
  Because `validator.py` forces 100% of slides to have images, every presentation has `img_pct >= 90%`. This triggers unnecessary image API quota usage, slows generation down, forces gradient fallbacks, and causes `quality_checker.py` to deduct points from its own deck score.
- **Remediation**:
  Only force images on layouts that structurally require them (such as `split`). Allow `stat`, `quote`, `timeline`, and `infographic` to remain `requires_image = False` if the planner did not request an image.

---

### PERF-01: Static Rate Limiter Stifles Multi-Key Scaling & Causes Timeouts

- **Location**: [`image_generator.py:27`](file:///home/intruder-jsr/exps/ai-ppt-maker/image_generator.py#L27) and [`image_generator.py:95`](file:///home/intruder-jsr/exps/ai-ppt-maker/image_generator.py#L95)
- **Severity**: **Medium**
- **Description**:
  The `_RateLimiter` class is initialized with a static default:
  ```python
  self._rate_limiter = _RateLimiter(max_per_minute=5, max_wait_seconds=120)
  ```
  Even when the user configures multiple API keys (`GEMINI_API_KEY`, `GEMINI_API_KEY_2`), the rate limiter still enforces a hard limit of 5 calls per minute across the entire process.
  On a standard 10-slide presentation where 9 slides request images, the 6th slide is guaranteed to hit the rate limiter and block for 60 seconds. In automated test environments (such as `tests/test_advanced.py`), this causes `subprocess.TimeoutExpired` failures at the 60-second mark.
- **Remediation**:
  Scale the quota proportionally to the number of configured keys:
  ```diff
  -  self._rate_limiter = _RateLimiter(max_per_minute=5, max_wait_seconds=120)
  +  effective_rpm = max(5, 5 * len(self._keys))
  +  self._rate_limiter = _RateLimiter(max_per_minute=effective_rpm, max_wait_seconds=120)
  ```

---

### TYPE-01: Unvalidated `KeyValueBlock.pairs` Causes Potential PPTX Crash

- **Location**: [`schemas.py:58`](file:///home/intruder-jsr/exps/ai-ppt-maker/schemas.py#L58) and [`pptx_exporter.py:351`](file:///home/intruder-jsr/exps/ai-ppt-maker/pptx_exporter.py#L351)
- **Severity**: **Medium**
- **Description**:
  In `schemas.py`, `KeyValueBlock` defines:
  ```python
  class KeyValueBlock(BaseModel):
      block_type: Literal['keyvalue'] = 'keyvalue'
      pairs: List[dict] = Field(...)
  ```
  `List[dict]` does not enforce the schema of the inner dictionaries. If Gemini outputs a list of strings (`["Key: Value"]`) or objects with missing keys, Pydantic validation passes.
  However, in `pptx_exporter.py`:
  ```python
  elif bt == 'keyvalue' and block.pairs:
      for pair in block.pairs:
          k = pair.get('key', '')
          v = pair.get('value', '')
  ```
  If `pair` is a string, `pair.get('key')` raises `AttributeError: 'str' object has no attribute 'get'`, causing the entire PPTX export process to crash.
- **Remediation**:
  Define a strongly typed child model:
  ```python
  class KeyValuePair(BaseModel):
      key: str
      value: str

  class KeyValueBlock(BaseModel):
      block_type: Literal['keyvalue'] = 'keyvalue'
      pairs: List[KeyValuePair]
  ```

---

### LOGIC-02: Deterministic Safety Filter Violations Trigger Unnecessary Backoff Sleep

- **Location**: [`planner.py:146`](file:///home/intruder-jsr/exps/ai-ppt-maker/planner.py#L146) and [`planner.py:434-472`](file:///home/intruder-jsr/exps/ai-ppt-maker/planner.py#L434-L472)
- **Severity**: **Medium**
- **Description**:
  In `planner.py`:
  ```python
  RETRYABLE_ERRORS = (
      "429", "quota", "resource_exhausted",
      "extra data", "json", "jsondecode",
      "validationerror", "validation error",
      "safety",
  )
  ```
  When Gemini blocks content due to safety filters:
  ```python
  if response.candidates and response.candidates[0].finish_reason.name == 'SAFETY':
      raise ValueError("Response blocked by safety filters. Try rephrasing your source material.")
  ```
  Because `"safety"` is listed in `RETRYABLE_ERRORS`, the exception handler treats this as a retryable error. It waits 15 seconds, 30 seconds, and 60 seconds, retrying the **exact same prompt** 4 times.
  Because Gemini's safety filters are deterministic, the retries always fail, forcing the user to wait 105 seconds before finally terminating.
- **Remediation**:
  Remove `"safety"` from `RETRYABLE_ERRORS` and fail immediately with clear guidance to rephrase source material.

---

### NLP-01: Calendar Years Misidentified as Key Statistics

- **Location**: [`source_analyzer.py:44`](file:///home/intruder-jsr/exps/ai-ppt-maker/source_analyzer.py#L44)
- **Severity**: **Low**
- **Description**:
  In `source_analyzer.py`, `_STAT_PATTERN` matches large numbers with:
  ```python
  | \d[\d,]{3,}                   # Large number: 10,000+
  ```
  `\d[\d,]{3,}` matches any 4-digit number. In historical, technical, or corporate source texts, calendar years (e.g., `2021`, `2024`, `2025`, `2030`) match this pattern.
  As a result, `source_analyzer.py` extracts years as "Key Statistics", injecting:
  ```
  === SOURCE PRE-ANALYSIS ===
  Key Statistics: 2024, 2025
  ```
  into the Planner prompt, encouraging the LLM to generate `StatBlock` instances displaying hero numbers like "2024" instead of actual business metrics.
- **Remediation**:
  Filter out 4-digit numbers in the range 1900–2099 from the stat extractor:
  ```python
  def _is_year(s: str) -> bool:
      cleaned = s.replace(',', '').strip()
      return cleaned.isdigit() and 1900 <= int(cleaned) <= 2099
  ```

---

### BUG-06: 3-Character Shorthand Hex Colors Crash `ThemeResolver`

- **Location**: [`theme_resolver.py:27`](file:///home/intruder-jsr/exps/ai-ppt-maker/theme_resolver.py#L27)
- **Severity**: **Low**
- **Description**:
  In `ThemeResolver.hex_to_rgb`:
  ```python
  h = hex_color.lstrip('#')
  if len(h) != 6:
      raise ValueError(f"Invalid hex color: '{hex_color}'")
  ```
  If a user specifies a valid 3-character CSS shorthand hex color (e.g. `primary_color: "#F50"` or `"#FFF"`), `ThemeResolver` raises `ValueError` rather than expanding it to 6 characters (`#FF5500`, `#FFFFFF`).
- **Remediation**:
  Expand 3-character hex strings:
  ```python
  h = hex_color.lstrip('#')
  if len(h) == 3:
      h = ''.join(c * 2 for c in h)
  elif len(h) != 6:
      raise ValueError(f"Invalid hex color: '{hex_color}'")
  ```

---

## 5. Resource Management & Performance Optimizations

### PERF-02: Triple Chromium Browser Spawning in Render Pipeline

- **Location**: [`renderer.py:31`](file:///home/intruder-jsr/exps/ai-ppt-maker/renderer.py#L31), [`renderer.py:103`](file:///home/intruder-jsr/exps/ai-ppt-maker/renderer.py#L103), [`renderer.py:189`](file:///home/intruder-jsr/exps/ai-ppt-maker/renderer.py#L189)
- **Severity**: **Medium**
- **Description**:
  In `renderer.py`, three separate methods each instantiate and tear down their own Chromium process:
  1. `render_to_pdf(html_files)`: Launches Chromium $\rightarrow$ loops through all slides $\rightarrow$ closes Chromium.
  2. `render_all(html_files)`: Launches Chromium $\rightarrow$ loops through all slides $\rightarrow$ closes Chromium.
  3. `render_background_only(html_files)`: Launches Chromium $\rightarrow$ loops through all slides $\rightarrow$ closes Chromium.
  When a user runs `python cli.py generate --pptx --audit full`, the pipeline launches Chromium 3 consecutive times and loads every single slide 3 times. Spawning Chromium incurs a ~1.5s overhead per launch, plus network/font re-initialization.
- **Remediation**:
  Consolidate rendering into a single persistent browser session or context manager:
  ```python
  class PlaywrightSession:
      def __enter__(self):
          self.p = sync_playwright().start()
          self.browser = self.p.chromium.launch(headless=True)
          return self.browser
      def __exit__(self, *args):
          self.browser.close()
          self.p.stop()
  ```

---

### LEAK-01: Unclosed PIL Image File Descriptors

- **Location**: [`image_matcher.py:301`](file:///home/intruder-jsr/exps/ai-ppt-maker/image_matcher.py#L301), [`compiler.py:25-33`](file:///home/intruder-jsr/exps/ai-ppt-maker/compiler.py#L25-L33), [`image_validator.py:65`](file:///home/intruder-jsr/exps/ai-ppt-maker/image_validator.py#L65)
- **Severity**: **Low**
- **Description**:
  Several modules open images using `Image.open(path)` without wrapping them in context managers (`with Image.open(...) as img:`) or calling `img.close()`.
  In `image_matcher.py`, when scanning 50 user photos, 50 unclosed file descriptors persist in memory until garbage collection.
- **Remediation**:
  Always use context managers or explicit `.close()` calls:
  ```python
  with Image.open(path) as img:
      rgb_img = img.convert('RGB')
  ```

---

### LEAK-02: Unhandled Multi-Modal File Cleanup on Early Abort

- **Location**: [`planner.py:295`](file:///home/intruder-jsr/exps/ai-ppt-maker/planner.py#L295) and [`planner.py:446`](file:///home/intruder-jsr/exps/ai-ppt-maker/planner.py#L446)
- **Severity**: **Low**
- **Description**:
  When a user supplies a large audio, video, or PDF file via `source_file`, `planner.py` uploads it to the Gemini Files API (`client.files.upload`).
  While deletion is attempted upon successful JSON parsing and in the outer exception block, an unexpected process kill (`SIGINT`, uncaught exception during prompt construction) will leave the file hosted on Google's cloud storage indefinitely.
- **Remediation**:
  Wrap the planning execution in a `try ... finally` block:
  ```python
  try:
      # Upload and generate content
      ...
  finally:
      if uploaded_file:
          try:
              self.client.files.delete(name=uploaded_file.name)
          except Exception:
              pass
  ```

---

## 6. Component-by-Component Review

### `cli.py` & `config_manager.py`
- **Strengths**: Pre-flight validation prevents burning API tokens on invalid inputs. The dual-path fallback in `config_manager.py` (Pydantic object vs raw dict) is resilient to partial YAML configurations.
- **Improvements**:
  - The `--score` flag on `generate` prints the score table, but still proceeds through image generation and PDF rendering. Users running `cli.py generate --score` often only want the score. Add `--score` as an option to `--dry-run` or support an independent `cli.py score` command.
  - `pre_flight_validation` checks `len(source_text) < 200`, but ignores word count. A 5-word text with lots of spaces can pass. Use `len(source_text.split()) < 30`.

### `schemas.py`
- **Strengths**: Excellent discriminated union implementation for `ContentBlock`. The separation of `Theme`, `Slide`, and `MasterPlan` provides a clean serialization boundary.
- **Improvements**:
  - Replace `pairs: List[dict]` with strongly typed `KeyValuePair` models.
  - Add validator to ensure `layout_variant` is only set on layouts that support it (currently only `split` supports `reverse`).

### `planner.py`
- **Strengths**: The 19-rule prompt is exceptionally well-crafted. Dynamic layout variety rules and layout rhythm guides adapt cleanly to slide count.
- **Improvements**:
  - Increase retry wait times dynamically based on remaining quota headers if available.
  - Decouple safety filter errors from retryable errors.

### `theme_resolver.py` & `theme_palettes.py`
- **Strengths**: Excellent color math (luminance, CIEDE2000-approximated distance, WCAG contrast verification). The automatic darkening of light backgrounds for `glassmorphism` prevents low-contrast washed-out cards.
- **Improvements**:
  - Support 3-character hex shorthand colors.
  - Automatically update `--text-rgb` and `--text-secondary-rgb` whenever `--text` is overridden.

### `image_matcher.py` & `image_generator.py`
- **Strengths**: Multimodal batch matching via Gemini Vision is state-of-the-art. Priority-based image generation queuing (P0 to P3) optimizes quota allocation.
- **Improvements**:
  - Scale `_RateLimiter` quota with the number of available API keys.
  - Implement immediate retry with the newly rotated key on HTTP 429 errors.

### `templater.py` & `templates/`
- **Strengths**: Clean modular design with `base.html` and `_blocks.html`. Absolute `file://` URI conversion prevents 404s in Chromium.
- **Improvements**:
  - Use `pathlib.Path.resolve().as_uri()` for cross-platform Windows compatibility.
  - Mark CSS variables as `| safe` in `base.html` to avoid `&#34;` corruption.

### `renderer.py` & `compiler.py`
- **Strengths**: Vector PDF output via Chromium's printing engine produces crisp, selectable text. Background-only rendering for PPTX neatly solves the double-text overlay problem.
- **Improvements**:
  - Fix the DOM audit script overflow detection logic.
  - Combine browser launches to reduce process spawning overhead.

### `pptx_exporter.py`
- **Strengths**: Precise coordinate mapping (`LAYOUT_POSITIONS`) matches HTML layouts closely. Native text frames allow full post-export editing.
- **Improvements**:
  - Support theme-appropriate fonts instead of hardcoding `Calibri`.
  - Validate `pair` structure before calling `.get()` in key-value blocks.

---

## 7. Prioritized Remediation Plan

### Phase 1: Immediate Critical Fixes (Sprint 1)
1. **Fix CSS Variable Autoescape**: Add `| safe` to `theme.css_variables` in `templates/base.html`.
2. **Fix Cross-Platform URI Generation**: Replace manual `file://` string formatting with `Path.resolve().as_uri()` in `templater.py`.
3. **Enforce Sequential Slide Renumbering**: Update `validator.py` to re-index `slide.slide_number = idx` sequentially.
4. **Fix Key Rotation in Image Generator**: Allow the rotated key to be attempted immediately on the current slide before falling back to a gradient.
5. **Fix DOM Overflow Script**: Correct `_DOM_AUDIT_JS` in `renderer.py` so standard HTML elements are properly audited.

### Phase 2: Reliability & Performance Enhancements (Sprint 2)
1. **Scale Rate Limiter with Key Count**: Dynamically set `max_per_minute = 5 * len(self._keys)` in `image_generator.py`.
2. **Align Image Requirements**: Remove the aggressive `requires_image = True` force in `validator.py` for self-contained layouts (`stat`, `quote`, `timeline`).
3. **Safeguard KeyValueBlock**: Replace `List[dict]` with `List[KeyValuePair]` in `schemas.py` and guard `.get()` in `pptx_exporter.py`.
4. **Remove Safety from Retries**: Fail immediately without exponential backoff on Gemini safety filter violations.
5. **Filter Calendar Years from Stat Extractor**: Ignore 1900–2099 numbers in `source_analyzer.py`.

### Phase 3: Ergonomic & Architectural Polish (Sprint 3)
1. **Consolidate Playwright Browser Instances**: Use a single browser context across PDF, PNG, and PPTX background rendering.
2. **Support Shorthand Hex**: Normalize 3-character hex codes in `theme_resolver.py`.
3. **Dynamic PPTX Fonts**: Map theme structural classes to appropriate typography in `pptx_exporter.py`.
4. **File Handle Context Managers**: Audit all `Image.open` and `PdfWriter` calls to ensure context managers are used.
