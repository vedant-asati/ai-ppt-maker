# Changelog

All notable changes to **AI Presentation Agency (`ppt_maker`)** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [4.0.0] - 2026-10

### Added
- **Targeted Agentic Refinement Loop**: Closed-loop DOM overflow remediation engine (`RefinerEngine`). Uses Playwright to detect layout clipping and applies a 3-tier hierarchical critic-actor resolution:
  - *Tier 1 (Deterministic Micro-Fix)*: Trims padding and clamps redundant whitespace at 0ms latency and $0 cost.
  - *Tier 2 (Targeted Reflexion Patch)*: Sends slide JSON + DOM overflow warnings to Gemini Flash Lite for surgical ~350-token patches (vs. 6,000 tokens for full deck re-runs).
  - *Tier 3 (Algorithmic Speaker Note Offload)*: Preserves overflow content directly in presenter speaker notes if stubborn after two passes.
  - Enabled by default via `--auto-refine` (toggleable with `--no-auto-refine`).
- **Grounded Research Agent**: Autonomous multi-angle query decomposition, zero-key web retrieval via DuckDuckGo, metric extraction, and synthesis into cited presentations (`--research "Topic"`).
- **Footnote Citations**: Real-time extraction of source URLs rendered as clickable `.slide-citations` badges with hover tooltips across all 7 slide templates.
- **Offline Degradation Mode**: Graceful fallback to baseline model knowledge with an advisory disclaimer when offline or experiencing network timeouts.
- **GenAI Evaluation Framework & LLM-as-a-Judge**: Comprehensive evaluation suite (`evals/run.py`) benchmarking decks across 10 golden scenarios. Includes deterministic metrics (DOM overflow rate, layout monotony, word density, block diversity) and position-bias mitigated pairwise LLM judging with calibrated ground truth ($\ge 90\%$ agreement).
- **End-to-End Integration Test Suite**: Consolidated 95 automated unit, integration, and regression tests.

---

## [3.0.0] - 2026-08

### Added
- **Native PPTX Exporter**: Vector-accurate PowerPoint generation (`--pptx`) via `python-pptx` with editable text typography and isolated background plates to prevent double-text rendering.
- **3-Layer Design Quality Audit**: Real-time deck audit inspecting DOM overflow coordinates, PIL image quality/contrast, and typography density, outputting graded `design_audit.md` reports.
- **Vector PDF Compilation**: High-fidelity vector PDF compilation via Playwright's print engine, replacing legacy raster page stitching.
- **Speaker Notes Compiler**: Automatic synthesis of per-slide presenter scripts, verbal transition cues, and image prompt appendices.

### Fixed
- Fixed background plate isolation in PPTX exporter preventing doubled text boxes.
- Resolved relative file URI path resolution issues in headless Chromium on Linux and Windows.
- Corrected glassmorphism overlay opacity and contrast ratios on dark backgrounds.

---

## [2.0.0] - 2026-07

### Added
- **Design Token System**: Unified CSS variable design token architecture supporting 8 visual themes: `minimalist`, `glassmorphism`, `neo_brutalism`, `corporate_clean`, `dark_neon`, `gradient_flow`, `editorial`, and `aurora`.
- **7 Structured Content Blocks**: Pydantic schema-driven content types (`StatBlock`, `PullQuoteBlock`, `ComparisonBlock`, `StepBlock`, `CalloutBlock`, `KeyValueBlock`, `BulletBlock`) replacing flat bullet lists.
- **7 Narrative Arc Blueprints**: Dramatic storytelling models (`problem_solution`, `before_after`, `what_why_how`, `journey`, `contrast`, `inverted_pyramid`, `showcase`).
- **5 Audience Profiles**: Vocabulary and density tuners for `investor`, `technical`, `executive`, `academic`, and `general` audiences.
- **Smart Image Matching**: Gemini Vision integration (`--images-dir`) for semantic photo matching against generated slide layouts.
- **Procedural Gradient Engine**: Mathematical PIL fallback gradient generator for offline resilience and rate-limit mitigation.
- **Hindi & Indic Script Typography**: Noto Serif Devanagari font stack across all templates.

---

## [1.0.0] - 2026-07

### Added
- Initial release of AI Presentation Agency (`ppt_maker`).
- Multi-modal planning engine using Gemini Flash.
- Headless Chromium rendering engine using Playwright.
- Jinja2 HTML/CSS presentation templates.
- YAML configuration manager (`config.yaml`).
