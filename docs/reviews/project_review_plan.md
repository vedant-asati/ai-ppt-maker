# AI Presentation Agency Engineering Review Plan

**24 November 2026** · Baseline revision `9e22972`

This review should answer whether `ai-ppt-maker` reliably gets a user from source material to a presentation they can deliver or edit, which AI features make that job easier, and where the project should invest next. Use the evidence to decide what can ship, which features should be defaults, and which roadmap items deserve further work.

The baseline includes the Code Review 02 remediation, Hero Statement and 40/60 Editorial Split layouts, and changes to headline guidance, text pruning, and Cloudflare image prompts. Reopen each earlier finding at this revision and verify it against its original failure condition. Use the existing reviews for reproduction notes and the architecture and roadmap documents for the project's stated intent. [Code Review 02](code/02_code_review.md) · [Architecture](../architecture.md) · [Roadmap](../future_prospects.md) · [Visual design plan](../ai_slop_improvement_plan.md)

## Review sequence

| Phase | Work | Evidence to retain |
| --- | --- | --- |
| 1. Establish the baseline | Pin the commit, Python and dependency versions, Chromium build, font bundle, and feature flags. Identify the core workflows and the product claims under review. Inventory prior findings and the changes that claim to address them. | Baseline manifest, feature inventory, and prior finding status. |
| 2. Trace the implementation | Follow a saved-plan run and one source-driven workflow from the public CLI to PDF, PPTX, and notes. Map network calls, file writes, schema conversions, and failure boundaries. Review package seams and run targeted fault checks. | Execution trace, stage inputs and outputs, and minimal regression fixtures. |
| 3. Measure the generated decks | Run offline artifact checks first. When a live provider environment is available, compare planners and visual options on matched inputs, inspect rendered artifacts, and collect human editing feedback. | Scenarios, run logs, model usage, artifacts, raw ratings, and repeatability data. |
| 4. Decide what to ship | Review failures by user impact, score usability and quality by workflow, and translate evidence into feature and roadmap decisions. | Release verdict, prioritized findings, and a roadmap with measurable exit criteria. |

## Review workstreams

### 1. Product purpose, usefulness, and development rationale

- Identify the strongest use case from the public workflow and sample decks. Compare an executive with existing notes, a technical presenter with structured source material, and a presenter starting from a topic. For each, define what a usable deliverable looks like and whether speaker notes, citations, visual quality, or PowerPoint editability matter most.
- Ask why each major design choice exists. The CLI and editable blueprint may favor repeatable local work. HTML rendering may favor visual fidelity. Native PowerPoint shapes may favor editing. Research and staged planning should earn their place by improving evidence or narrative. Record the intended benefit, measured benefit, and associated maintenance burden.
- Give users a complete task with a fixed brief. Measure setup time, time to an acceptable draft, substantive changes before delivery, and whether another presenter can use the notes. Compare with a simple reusable presentation template and manual drafting on a representative subset. Include editing time when calculating time saved.
- Record where the project fits best today and the evidence for that choice. [README workflows](../../README.md#L90) · [Example decks](../../examples/README.md)

### 2. Architecture, modularity, and extensibility

- Trace source ingestion and configuration → planning → `MasterPlan` → validation and imagery → HTML and DOM audit → refinement → exports. For every boundary, identify the owner, input and output contract, side effects, error behavior, and replay strategy.
- Check that the CLI handles user interaction and can delegate reusable orchestration. Review shared state, fallback imports, provider construction, direct filesystem access, and duplicate normalization between stages. Check how many modules a new layout, provider, or export format touches and how inconsistencies are detected.
- Inspect `MasterPlan`, `Slide`, `ContentBlock`, and blueprint schemas for stable slide identity, cardinality, content limits, layout compatibility, and backward compatibility. Replay a previously saved plan and trace unsupported or missing fields through both exporters.
- Deliver a boundary map and identify the few changes that would make testing, reuse, and later interface work easier. [CLI](../../ppt_maker/cli.py) · [Schemas](../../ppt_maker/core/schemas.py) · [Staged planner](../../ppt_maker/planning/multi_agent/orchestrator.py)

### 3. Feature behavior and usability

- Exercise the documented public paths for topic, research, YAML/text sources, supported document and media inputs, saved plans, preview, notes, audit, user imagery, standard PPTX, and native template injection. Check defaults and combinations such as preview with PPTX and offline plan with image skipping.
- For each feature, record its intended user, the task it completes, output guarantees, failure message, time and cost, and whether another feature already solves the same problem. Track partial implementations and documented promises that differ from CLI behavior.
- Recommend a disposition for each major feature using the evidence. Options are default, opt-in, experimental, or removal. Include the workflow that benefits and the condition for changing its status. [CLI entry points](../../ppt_maker/cli.py#L95) · [Reference configuration](../../config_reference.yaml)

### 4. AI planning, factual grounding, and refinement

- Compare single-shot and multi-agent planning on identical input, deck length, audience, and model where the adapters permit it. Trace long and multimodal sources through every stage. Inspect what each stage actually receives and whether recovered slides still have evidence and narrative context.
- Annotate source-supported claims in a few reference documents. Trace dates, numbers, units, attribution, and citations from source to plan, render, PowerPoint, and notes. Include conflicting evidence, explicit source gaps, and a model or provider error. Measure claim support and citation correctness separately from writing quality.
- Examine schema enforcement and recovery for invalid JSON, missing or duplicate slide IDs, incompatible content blocks, and model refusals. Check whether fallbacks produce helpful, visibly degraded outputs that preserve the source. Inspect headline, buzzword, and word-count rules for impact across legacy bullets, typed blocks, dense technical slides, quotes, and non-English text.
- Check the refinement loop before and after browser rendering. Compare final geometry and preserved facts, links, notes, and slide IDs. Record accepted changes, rejected changes, and unresolved overflow. [Single-shot planner](../../ppt_maker/planning/planner.py) · [Research](../../ppt_maker/research/agent.py) · [Content validation](../../ppt_maker/planning/validator.py) · [Refiner](../../ppt_maker/planning/refiner.py)

### 5. Implementation, visuals, and export fidelity

- Render the same plan in PDF and PPTX. Compare slide IDs and order, visible content, numbers and citations, notes, dimensions, and editable PowerPoint elements. Open the outputs in available viewers and record which elements remain editable. Compare standard PPTX and native master-template output using the same editing task.
- Review representative combinations of layout, theme, typography, and content load. Cover Hero Statement, both editorial split orientations, KPI and bento cards, long labels, missing imagery, and multilingual or long unbroken text. Test the viewport size shown in preview separately from the final page size.
- Review Cloudflare, Gemini, procedural gradients, and supplied assets on the same content. Check relevance, crop and focal point, text contrast, and fallback consistency. Compare the old and new copy and visual treatments independently where possible so improved images do not mask evidence loss or harder editing.
- Retain a small visual regression set with images and text extraction, plus artifact-level identity checks. [HTML templating](../../ppt_maker/rendering/templater.py) · [Chromium rendering](../../ppt_maker/rendering/renderer.py) · [PPTX exporter](../../ppt_maker/export/pptx_exporter.py) · [Template injector](../../ppt_maker/export/template_injector.py)

### 6. Reliability, performance, cost, and fault recovery

- Exercise provider timeouts and quota responses, invalid image data, missing fonts or assets, interrupted writes, browser launch failures, an undersized template, and a render failure in the middle of a deck. Verify retries end within a defined budget, failures identify the stage, and partial output has an explicit status. Compare clean, warm-cache, and concurrent runs using isolated output directories.
- Measure stage and end-to-end wall time, call counts, actual token usage where available, output sizes, and fallback frequency. Separate cold and warm runs. Report the sample size, median, and observed range. Use percentiles only when the sample supports them.
- Check whether one provider failure repeatedly adds delay on every slide, whether cache keys include the inputs that affect outputs, and whether preview avoids work beyond the slides it renders. Identify the dominant bottleneck per workflow. [Provider integration](../../ppt_maker/imaging/image_generator.py) · [Image cache](../../ppt_maker/imaging/image_cache.py) · [CLI export](../../ppt_maker/cli.py#L558)

### 7. Security, privacy, and distribution

- Verify sample config and the intended publish range with a scanner that redacts secrets. Record credential rotation or revocation as verified only when there is evidence independent of the source change. Inspect which parts of a user's input reach each provider and which stay in local plans, images, notes, logs, or temporary files.
- Review template theming, user-supplied files, URLs, browser asset loading, and output paths as trust boundaries. Check that explicit offline operation uses local fonts and assets with provider calls and unnecessary network access disabled. Use non-sensitive fixtures for remote runs.
- Build and install the wheel in a clean directory. Confirm packaged layouts, fonts and textures where promised, source-independent template discovery, CLI entry points, and browser prerequisites. Check asset provenance and distribution terms as part of release review. [Packaging](../../pyproject.toml) · [Theme resolver](../../ppt_maker/design/theme_resolver.py) · [CI](../../.github/workflows/ci.yml)

### 8. Evaluation quality, testing, and maintainability

- Label synthetic fixture results, rendered-deck checks, live model results, and human ratings separately. Verify each advertised metric maps to the real artifact, missing measurements are marked unavailable, and failures and fallback runs are visible in comparisons. Check that CI fails on relevant regressions and that browser setup is explicit.
- Use the ten existing evaluation scenarios as the initial set. Add holdout inputs for a long or multimodal source, uncertain evidence, multilingual output, and partial render recovery. For live comparisons, vary one factor at a time. Repeat a subset to measure output variance, blind reviewers to the variant, and record ties and disagreement.
- Judge structure and source faithfulness with automated signals where possible. Use the LLM judge as an adjunct and check its agreement against independently reviewed examples before using it for a roadmap decision. Include a regression test for any confirmed critical fault whose original reproduction fits an automated check. [Evaluation dataset](../../evals/dataset.json) · [Comparison harness](../../evals/compare_pipelines.py) · [Judge](../../evals/judge.py) · [Tests](../../tests/)

### 9. Current direction and roadmap

- Compare the current investment in layouts, imagery, and copy with demonstrated user friction. Evaluate these against stronger grounding, reliable editable export, and easier setup. Give each candidate initiative a user problem, evidence, estimated complexity, dependencies, and a measurable outcome.
- Test the main roadmap choices. Keep the staged planner behind a flag until paired runs show a repeatable benefit for an identifiable class of decks. Decide whether better visual layouts or better editing and factual integrity save more user time. Evaluate a UI or extra export format against the stability of the underlying configuration, plan, and artifact boundaries.
- Let release blockers set the order of work. Rank near-term improvements by measured user impact and give uncertain investments a specific experiment. [Roadmap](../future_prospects.md) · [Visual design plan](../ai_slop_improvement_plan.md) · [Prior review](code/02_code_review.md)

## Representative test matrix

| Scenario | Compare or vary | Evidence to check |
| --- | --- | --- |
| Three-slide executive brief from a one-line topic | Single-shot and staged planning | Requested count, decisive headline, coherent ending, and treatment of unsupported claims. |
| Ten-slide technical deck from a long source | Text and supported document input, with both planners | Coverage of late-source details, numeric fidelity, source references, and notes. |
| Research deck with conflicting or incomplete evidence | Sources available, sparse, and unreachable | Claim-level citations, uncertainty, and usable degradation. |
| Branded deck from a saved plan | Fresh checkout and installed wheel, local assets and supported offline settings | Plan compatibility, theme assets, expected browser requests, and three matching exports. |
| Stretched visual layouts | Hero Statement, 40/60 split, KPI and bento, mixed fonts and long strings | Final DOM bounds, readable typography, crop, and parity between preview and full output. |
| PowerPoint handoff | PDF, standard PPTX, native template, and notes | Correct order, matching content, editability, and clear handling of undersized templates. |
| Interrupted or degraded run | Provider failure, bad image, missing slide, and concurrent runs | Bounded retries, uncontaminated cache, correct result status, and no silent artifact loss. |

## Decision criteria and final deliverables

Use a 1–5 scale for narrative clarity, visual readability, editing usability, and usefulness. A **1** means the artifact requires substantial reconstruction, **3** means it is usable after targeted edits, and **5** means it is ready for the intended audience with routine personalization. Keep time-to-usable-deck, unsupported claims, citation accuracy, export completeness, and cost as separate measurements.

Resolve credential exposure before publishing. Block affected workflows on invented material facts presented as sourced, mismatched slide content, or silent artifact loss. Require every expected slide ID to appear once in order across the requested outputs. Use small-sample results to identify promising improvements and record uncertainty when they cannot support a general conclusion. Define numerical performance and cost targets against the pinned baseline and the workflow's time budget.

The completed review should produce a release verdict by workflow, a feature status matrix, an architecture and dependency map, and a ranked fault register with repro steps, impact, evidence, and acceptance checks. Close with a short roadmap that states which features should become defaults, which should stay opt-in, and what evidence would change the decision.
