# AI Presentation Agency — Future Prospects & Engineering Roadmap

This document captures strategic directions and potential enhancements identified for the `ai-ppt-maker` system following the completion of the Multi-Agent Planning Pipeline and SlidesGo Aesthetic Design System.

---

## Strategic Directions

### Direction 1: Multi-Agent vs. Single-Shot Empirical Benchmark (Completed)
- **Goal**: Rigorously and statistically evaluate the trade-offs between the Single-Shot Planner and the Multi-Agent Planning Pipeline across narrative quality, layout diversity, latency, and cost.
- **Results & Report**: Full empirical scorecard published in [multi_agent_vs_single_shot_benchmark.md](file:///home/intruder-jsr/exps/ai-ppt-maker/docs/evals/multi_agent_vs_single_shot_benchmark.md).
  - Evaluated across 10 golden benchmark scenarios in `evals/dataset.json`.
  - Multi-Agent achieved a **100% win rate** on content quality and narrative depth, with notable superiority on complex deep-dive decks (97.2 vs. 84.5 on 10-slide decks).
  - Maintained 78-80% rich structured block coverage (`kpi_dashboard`, `bento`, `roadmap_chain`, `editorial`).
- **Impact**: Quantitatively demonstrates the value of architectural multi-agent staging for enterprise presentations.

---

### Direction 2: Grounded Web Research + SlidesGo Aesthetic Integration
- **Goal**: Transform autonomous web discovery into verified, footnoted executive presentations.
- **Scope**:
  - Wire `ResearchAgent` (`ppt_maker/research/agent.py`) with SlidesGo layout archetypes.
  - Route evidence and live data into `kpi_dashboard` (2x2 metric quad) and `editorial` statement cards.
  - Render interactive source footnote pills `[1] domain.com` in both vector PDF and editable PPTX.
  - Display confidence scores and source freshness timestamps on slides.
- **Impact**: Eliminates AI hallucination by grounding presentations in real-time verified web sources.

---

### Direction 3: Interactive Web UI & Live Preview Studio
- **Goal**: Provide an instant, visual interface for presentation generation without requiring CLI access.
- **Scope**:
  - Build a lightweight web interface / Antigravity MCP App / Streamlit dashboard.
  - Features:
    - Interactive prompt & outline editor.
    - Visual theme gallery featuring all 9 SlidesGo themes with live palette swatches.
    - Master template picker for native PPTX cloning.
    - One-click toggle for `--multi-agent`.
    - Live real-time browser preview of rendered slides with slide reordering.
    - Dual download buttons: Vector PDF and editable `.pptx`.
- **Impact**: Transitions the tool from a developer CLI utility into an accessible, end-to-end product.

---

### Direction 4: Multi-Target Presentation Export (Google Slides, Figma, Reveal.js)
- **Goal**: Expand export capabilities beyond PDF and PPTX.
- **Scope**:
  - **Google Slides API**: Export directly to user's Google Drive via OAuth2 / Google Workspace integration.
  - **Web Slides (Reveal.js / HTML5)**: Generate standalone interactive HTML5 presentation bundle with presenter mode, speaker timers, and keyboard navigation.
  - **Figma Code Connect**: Export layout primitives to Figma components for visual design collaboration.
- **Impact**: Seamless interoperability across corporate productivity suites and web publishing platforms.

---

*Last Updated: 2026-11-23*

