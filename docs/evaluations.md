# GenAI Evaluation Framework & LLM-as-a-Judge

An empirical evaluation framework designed to benchmark, guardrail, and measure presentation generation quality across models, prompt revisions, and visual themes without relying on ad-hoc human visual inspection.

---

## 🎯 Motivation

In autonomous generative pipelines, silent quality regressions are common:
- A prompt adjustment can cause text bloat, triggering DOM overflow and text clipping.
- Model upgrades can lead to repetitive layout choices or generic bullet lists.
- Token and latency costs can surge without measurable aesthetic gains.

The evaluation framework provides quantitative, reproducible scorecards across **deterministic structural metrics** and **calibrated LLM-as-a-Judge comparisons**.

---

## 📊 Evaluation Architecture

```
                  ┌──────────────────────────────────────────────┐
                  │      Golden Dataset (10 Scenarios)           │
                  │             evals/dataset.json               │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │       Generation Pipeline (MasterPlan)       │
                  │   Planner -> Validator -> Jinja2 -> Chromium  │
                  └──────────────────────┬───────────────────────┘
                                         │
                  ┌──────────────────────┴───────────────────────┐
                  │                                              │
                  ▼                                              ▼
   ┌──────────────────────────────┐              ┌──────────────────────────────┐
   │ Deterministic Metrics Engine │              │   Pairwise LLM-as-a-Judge    │
   │       evals/metrics.py       │              │        evals/judge.py        │
   │                              │              │                              │
   │ • DOM Overflow Rate (%)      │              │ • Dual-Order Evaluation      │
   │ • Layout Monotony Penalty    │              │   (A vs B and B vs A)        │
   │ • Information Word Density   │              │ • Position-Bias Mitigation   │
   │ • Structured Block Diversity │              │ • Calibrated Rubric Scoring  │
   │ • Telemetry / Cost ($/deck)  │              │   (≥90% Human Agreement)     │
   └──────────────┬───────────────┘              └──────────────┬───────────────┘
                  │                                              │
                  └──────────────────────┬───────────────────────┘
                                         │
                                         ▼
                  ┌──────────────────────────────────────────────┐
                  │   Scorecard Exporter (Terminal + Markdown)   │
                  │                evals/run.py                  │
                  └──────────────────────────────────────────────┘
```

---

## 📏 Deterministic Metric Dimensions

All deterministic metrics run with zero LLM API calls and execution latency < 50ms per deck:

| Metric | Target | Formula / Logic | What It Catches |
|---|:---:|---|---|
| **DOM Overflow Rate** | `0%` | $\frac{\text{slides with clipping}}{\text{total slides}} \times 100$ | Detects text exceeding card boundaries or canvas viewports in headless Chromium. |
| **Layout Monotony** | `< 0.20` | Normalized penalty for consecutive identical slide layouts (e.g., 3 consecutive generic slides). | Prevents visual fatigue and ensures rhythmic variety. |
| **Word Density** | `15–55 words/slide` | Slide content token/word count within optimal presentation thresholds. | Penalizes walls of text (>65 words) or empty/sparse slides (<10 words). |
| **Block Diversity** | `≥ 75%` | Ratio of slides using rich blocks (`stat`, `comparison`, `steps`, `quote`) vs flat bullets. | Guards against regression into generic bullet-point presentations. |
| **System Telemetry** | Monitored | End-to-end latency, tokens per second, and estimated inference cost ($/deck). | Ensures pipeline cost and speed stay within production SLAs. |

---

## ⚖️ Pairwise LLM-as-a-Judge

For semantic and aesthetic quality comparison between model versions (e.g. Gemini 2.5 Flash vs Gemini 3.1 Flash Lite):

1. **Position-Bias Mitigation**: The judge evaluates candidates in dual order ($A \text{ vs } B$ and $B \text{ vs } A$). If the evaluator prefers whichever option is presented first regardless of quality, the judgment is rejected as an order artifact.
2. **5-Dimension Rubric**:
   - *Narrative Clarity*: Logical progression and story arc coherence.
   - *Information Architecture*: Information hierarchy and cognitive chunking.
   - *Visual Intent*: Appropriateness of the selected layout and content blocks.
   - *Audience Calibration*: Tone, vocabulary, and technical density.
   - *Actionable Substance*: Specific facts, metrics, and takeaways.

---

## 🎯 Ground Truth Calibration

To prevent "the judge grading its own homework," the evaluation harness includes a pre-labeled benchmark dataset (`evals/calibration_slides.json`):
- 10 curated slides with verified human ground-truth labels (flawed vs. pristine slides).
- Run `python evals/run.py --calibrate` to benchmark judge reliability.
- **Result**: The LLM judge achieves **$\ge 90\%$ agreement** with human ground truth before being trusted in production comparisons.

---

## 🚀 Running Evaluations

```bash
# 1. Deterministic offline benchmark (0 API cost, ~2 seconds)
python evals/run.py --deterministic-only

# 2. Evaluate a specific scenario from the golden dataset
python evals/run.py --deterministic-only --scenario tech_microservices

# 3. Run full evaluation with live Gemini model
python evals/run.py --model gemini-2.5-flash --limit 3

# 4. Run Pairwise Judge comparing two generation runs
python evals/run.py --judge

# 5. Run Calibration Benchmark against pre-labeled slides
python evals/run.py --calibrate
```

### Benchmark Scorecard (Golden Dataset — 10 Scenarios)

```
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━┳━━━━━┳━━━━━┳━━━━━┳━━━━┳━━━━━┳━━━━┳━━━━━┳━━━━┓
┃ ID                        ┃ Cat ┃ Sli ┃ Ovr ┃ Mon ┃ Wd ┃ Blk ┃ Sc ┃ Grd ┃ St ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━╇━━━━━╇━━━━━╇━━━━━╇━━━━╇━━━━━╇━━━━╇━━━━━╇━━━━┩
│ exec_q3_board             │ exe │   5 │   0 │ 0.0 │ 23 │ 80% │ 95 │  A  │ PASS
│ tech_microservices        │ tec │   6 │   0 │ 0.0 │ 24 │ 83% │ 96 │  A  │ PASS
│ pitch_saas                │ saa │   5 │   0 │ 0.0 │ 23 │ 80% │ 95 │  A  │ PASS
│ research_solid_state      │ res │   5 │   0 │ 0.0 │ 23 │ 80% │ 95 │  A  │ PASS
│ incident_postmortem       │ ops │   5 │   0 │ 0.0 │ 23 │ 80% │ 95 │  A  │ PASS
│ internal_training         │ trn │   4 │   0 │ 0.0 │ 24 │ 75% │ 94 │  A  │ PASS
│ consulting_transformation │ con │   5 │   0 │ 0.0 │ 23 │ 80% │ 95 │  A  │ PASS
│ express_pitch_3slide      │ exp │   3 │   0 │ 0.0 │ 21 │ 67% │ 93 │  A  │ PASS
│ deep_dive_10slide         │ dep │   8 │   0 │ 0.1 │ 25 │ 88% │ 89 │  B  │ PASS
│ sparse_messy              │ raw │   4 │   0 │ 0.0 │ 24 │ 75% │ 94 │  A  │ PASS
└───────────────────────────┴─────┴─────┴─────┴─────┴────┴─────┴────┴─────┴────┘

Pass Rate: 100.0%  |  Average Score: 94.1/100 (Grade A)  |  Est. Cost: $0.0034/deck
```
