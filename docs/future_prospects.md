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

### Direction 5: Anti-"AI Slop" Visual Overhaul & Multi-Provider Free Imagery (In Progress / Partially Completed)
- **Goal**: Eliminate the generic "AI slop" feeling (repetitive 3-column card grids, flat dead backgrounds, and synthetic gradient placeholders) by implementing human-designer standards from Slidesgo, Pitch.com, and Duarte Design.
- **Blueprint Document**: Full architectural strategy published in [ai_slop_improvement_plan.md](file:///home/intruder-jsr/exps/ai-ppt-maker/docs/ai_slop_improvement_plan.md).
- **Completed Deliverables**:
  - **Cloudflare Workers AI FLUX.1-schnell Engine**: Integrated free edge GPU inference (~2s latency, 1024x1024 resolution) using 10,000 free Neurons/day.
  - **SlidesGo Texture Layering**: Direct mapping of authentic extracted watercolor paper, carbon grids, and vintage grain textures into `--bg-texture`.
  - **Designer Micro-Accents**: 240pt watermark chapter digits (`02`, `03`...) at 4% opacity, and enforced hero imagery on cover and split slides.
- **Remaining Scope**:
  - Asymmetric layout archetypes (Hero Statement 100pt, 40/60 Editorial Split, 2:1 Bento Grid).
  - Anti-cliché copywriting guardrails (Takeaway Rule enforcement, banned buzzword filtering).
- **Impact**: Elevates visual quality from generic wireframes to studio-grade editorial decks.

---

*Last Updated: 2026-11-23*

