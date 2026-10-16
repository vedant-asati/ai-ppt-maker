# AI Presentation Agency — Documentation Hub

Welcome to the documentation hub for **AI Presentation Agency (`ppt_maker`)**. This directory contains the system architecture specifications, design review audits, engineering roadmaps, feature proposals, and post-mortem issue analyses.

---

## 🗺️ Documentation Sitemap

### Core Architecture & Code Reviews (`reviews/code/`)
| Document | Description |
|---|---|
| **[System Architecture](architecture.md)** | Complete end-to-end technical specification: 7-phase generation pipeline, Pydantic V2 domain schemas, theme resolution, vector PDF rendering, and dual export. |
| **[Architectural Code Review #01](reviews/code/01_code_review.md)** | In-depth 14-dimension architectural code review, vulnerability assessment, and quality health scorecard. |

---

### Bug-Fixing & Remediation Plans (`plans/bug-fixing/`)
Sequential remediation execution plans directly correlated with architectural reviews:

- **[Plan 01: Code Review Remediation](plans/bug-fixing/01_code_review_remediation.md)**: Phased checklist addressing all 14 findings (`SEC-01` through `LEAK-02`) from Architectural Code Review #01.

---

### Subsystem Design & Improvement Plans (`plans/features/`)
Detailed technical RFCs and implementation proposals for pipeline subsystems:

- **[Content Quality Improvement Plan](plans/features/content_quality_improvement_plan.md)**: Narrative arc integration, audience registers, heuristic source analysis, and content scoring rubrics.
- **[UI Pipeline Improvement Plan](plans/features/ui_pipeline_improvement_plan.md)**: Design system tokens, typographic scale, CSS glassmorphism/aurora effects, and layout templates.
- **[Image Pipeline Plan](plans/features/image_pipeline_plan.md)**: Gemini Vision photo semantic matching, Imagen API orchestration, rate limiting, and procedural gradient fallbacks.
- **[Editable Output Plan](plans/features/editable_output_plan.md)**: Native PowerPoint (`.pptx`) export architecture using background isolation plates to prevent text duplication.
- **[Long Deck Support Plan](plans/features/long_deck_support_plan.md)**: Structural strategies for handling 10–15+ slide decks without visual fatigue or narrative collapse.

---

### Roadmap & Milestones (`plans/roadmap/`)
- **[Bridge to Excellence](plans/roadmap/bridge_to_excellence.md)**: Strategic roadmap for elevating presentation aesthetics from MVP quality to human agency caliber.
- **[Execution Phases](plans/roadmap/execution_phases.md)**: Step-by-step phase tracking and implementation milestones.

---

### Issues & Post-Mortems (`issues/`)
Root-cause analyses and verification steps for resolved and open pipeline issues:

- **[Issues Index & Severity Guide](issues/README.md)**: Catalog of all tracked issues, severity levels, and resolution priorities.
- **Notable Analyses**:
  - `ISS-001`: Stat, infographic, and timeline template background depth.
  - `ISS-002`: ThemeResolver glassmorphism dark-background contrast rules.
  - `ISS-003`: PPTX multi-layout mapping.
  - `ISS-006`: Vector PDF relative path rendering resolution.
  - `ISS-007`: PPTX text-box duplication and background plate isolation.
  - `ISS-REF`: Excellence analysis benchmark (Panch Parivartan case study).

---

### Session Retrospectives (`retrospectives/`)
- **[Session Summary — July 2026](retrospectives/session_july2026_summary.md)**: Initial pipeline stabilization, Playwright rendering, and test suite establishment.
- **[Session Summary — August 2026](retrospectives/session_august2026_summary.md)**: PPTX export engine, 3-layer design quality audit, and vector PDF compilation.

---

### Technical Reference (`reference/`)
- **[Gemini Models Reference](reference/gemini_models_reference.py)**: Rate limits (RPM/TPM/RPD), token limits, and pricing reference for Gemini text and multimodal models.
