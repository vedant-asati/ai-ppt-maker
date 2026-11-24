# Presentation quality testing plan

**Proposed on 24 November 2026, using revision `44ab332` as the baseline.** The last review found 146 passing tests alongside unreadable headlines, incorrect metrics and empty cards in delivered files. The first milestone is a test run that reliably rejects those defects and accepts a sound deck with a different visual style. The baseline results and sample file fingerprints are recorded in the [testing and visual quality review](../reviews/05_testing_and_visual_quality.md).

## 1. Define the release decision

A deck is ready for its intended audience when readers can recover its key message and evidence, required facts survive each advertised export, and a presenter can perform the promised edits. A release decision needs evidence at three levels.

| Decision | Required evidence | Who makes the call |
| --- | --- | --- |
| Can we merge this change? | Fast unit checks plus a reproducible artifact test for each affected path. A shared renderer or exporter change exercises both pilot decks in both formats. | Engineering |
| Can we ship this output format? | Each required slide appears once and in order. Required facts, units, visibility, notes policy and format-specific interactions pass in the delivered file. A supported presentation client opens the PPTX. | Export maintainer |
| Is the result suitable for this audience? | A reader can answer the brief-specific question using the deck. A designer checks hierarchy and legibility. Both cite specific slides or regions for material defects. | Product owner with designer and audience reviewer |

Record **pass**, **fail**, **unmeasured** or **not applicable** per required check, slide and format. A missing browser, font, render, reviewer or artifact leaves the corresponding required check unmeasured and the release decision pending. A detected defect in a required check fails that gate regardless of the average. Reserve *not applicable* for exclusions declared in the fixture before running it, such as native text editability for a PDF.

## 2. Build a small fixture set with independently authored answers

Start with the board and startup cases below. Author short, distributable source briefs and local assets. Commit their expected outcomes with the fixtures. The files in `outputs/samples/` are useful examples of failure and are Git-ignored. A clean CI checkout must be able to reproduce the new cases. Have a domain reviewer verify the expected values against the source before generating outputs.

| Fixture and reader | Facts or behavior to preserve | Reader task and pass condition |
| --- | --- | --- |
| **Board update** for a CFO | $14.2M ARR, 134% net retention, and capital allocated 45% to R&D, 35% to sales and marketing, 20% to reserves. Include one genuine zero in the invented source table and an explicitly missing prior-period value. | Identify the largest allocation and its share. Read the zero as zero and distinguish it from the unavailable value. All required labels and values must be legible on the intended slides in PDF and PPTX. |
| **Seed pitch** for an investor | 14,000 developers, 82 design partners, 10× query speed, $48B addressable market, $4.5M ask. Give the deck a traction slide and a separate ask slide. | Recover the four quantities with their units and distinguish traction from market opportunity. In PPTX, edit the ask to $5M, save, reopen, and confirm unrelated metrics and backgrounds survive. |
| **Engineering briefing** for a principal engineer | Distinguish a 42% latency reduction from a sub-50ms target. Include a labeled request path, a failure branch, and a source that makes no availability claim. | Trace the failure path and explain which result is measured. Reject a slide that uses latency as evidence for “99.99% reliability,” even when each label fits. |
| **Brand launch** for a retail buyer | A three-season rollout has distinct dates, regions and sales channels. Include a private delivery cue and an approved cover that uses generous whitespace. | Recover where and when the launch begins. The cue belongs in presenter notes. Two materially different covers can both pass when the hierarchy, audience fit and reading task hold. |
| **Research update** for an analyst | Two near-matching sources differ by region or direction. A third supports the exact claim. Include a late-document qualification and a calculated metric with two source inputs. | Follow the exported citation to the correct passage, identify the qualification and reproduce the calculation. Unsupported alternatives must remain visibly unresolved or be omitted. |
| **Native-template handoff** for a presenter | Use a small redistributable master with title, chart or table labels, authoring instructions, and speaker notes. Include a narrow text box and a long replacement title. | Reopen and edit a content slide. Check every slide for visible setup instructions, broken wrapping, stale labels and missing notes. Track the specific client and version used. |

Each fixture needs a source, audience and task, approved plan for deterministic replay, theme and font assets, expected slide order, allowed paraphrases, facts tied to source locations and slide roles, required interactions, and forbidden audience-visible text. Lock numeric meaning and units while allowing equivalent formatting such as “14k” and “14,000.” Record what may vary, including the position of optional decoration. Keep at least one independent brief and one visual family out of prompt tuning and judge calibration.

For example, the proposed pitch expectation below lets a test report *which* fact was lost. These fields belong to the test fixture and can be introduced before the application has stable slide IDs.

```yaml
slide_role: traction
source_location: "Pitch brief / Traction / Design partners"
expected_fact:
  label: Design partners
  value: 82
  unit: organizations
  period: current public preview
required_in: [pdf, editable_pptx]
reader_question: How many organizations are design partners?
```

## 3. Exercise the path from source to final file

| Stage | Tests to implement | Evidence and acceptance |
| --- | --- | --- |
| Ingest, plan and normalize | Use text and a local PDF table with the decisive footnote on the last page. Run single-shot and staged paths with recorded provider replies. Include zero, missing, malformed, contradictory and duplicate responses. | Compare the accepted plan with source spans for entity, period, unit, direction and actual versus forecast. No unsupported fallback figure, silently dropped required claim, or duplicated slide. |
| Refine and replay | Force overflow, run refinement, then render the final revision. Replay an edited saved plan under default config and explicit overrides. | Approved claims, manual edits and source links survive. Verify fit on the final artifact. Record changed fields and effective theme. With the deterministic fixture, deny network access and surface any attempted call. |
| HTML and browser | Render through the public CLI with the normal templates, local fonts and controlled images. Inspect heading and card geometry after fonts and media settle. | Capture per-slide DOM results and an image. Test text crossing its box, text occluding other text, empty required cards, missing glyphs, and contrast over the actual painted surface. Allow authored overlaps such as a caption on an image. |
| PDF | Reopen the merged file, count pages, inspect dimensions, extract visible text positions and link destinations, and rasterize each page. | One complete page per expected slide. Required facts appear together with their labels, in bounds and readable on the raster. A hidden text layer or text elsewhere in the file cannot satisfy a visible slot. |
| Editable PPTX | Inspect shape text, bounds, hyperlinks and notes parts. Render the saved file with pinned LibreOffice for routine CI. Open a representative deck in the declared Microsoft PowerPoint client for release and perform the edit task. | Match each required claim, visible object and slide to PDF and source. Confirm chart or table data is editable wherever advertised. Preserve or exclude notes according to the deliverable. Record Office-only checks as unmeasured when that client is unavailable. |
| CLI, packaging and recovery | Test preview at 1, 3, 4 and 6 slides using saved plans. Install the wheel in a clean directory. Exercise missing fonts/assets, provider timeout, corrupt image, partial export and concurrent runs. | Preview yields `min(3, N)` complete pages in its own output path. Detect missing, duplicate or stale artifacts even when counts match. Failure cannot report a complete deck or replace the last good output. Package tests use portable fixtures. |

For the two pilot decks, run the same brief in two ways. A saved approved plan isolates template and export errors. A separate run from source with recorded provider responses exercises claim selection, normalization and refinement. Keep a snapshot of the accepted plan, DOM capture, final PDF, final PPTX, and PPTX rendered by a presentation client. If a value changes between adjacent stages, the failure report should name the earliest stage at which it differs. [CLI](../../ppt_maker/cli.py) · [Renderer](../../ppt_maker/rendering/renderer.py) · [PPTX exporter](../../ppt_maker/export/pptx_exporter.py) · [Refinement](../../ppt_maker/planning/refiner.py)

For the first replay, install the candidate wheel into the test environment and copy the fixture into an empty working directory as `brief.yaml` and `approved-plan.json`. Supply the fixture's fonts locally, give the YAML a run-local output directory, and run the installed entry point there. Repeat in a second empty directory with `--preview` appended. Capture exit status, log, files and per-page checks for both runs.

```sh
ppt-maker generate --config brief.yaml --offline-plan approved-plan.json \
  --skip-images --no-auto-refine --audit quick --pptx
```

## 4. Test the detectors with deliberately damaged slides

Create each variant from a known-good fixture, change one thing, and assert the expected defect, slide, format and severity. Keep the original beside it. Run both through the same grading path used for an ordinary candidate.

| Deliberate change | Expected result |
| --- | --- |
| Put a white headline on white. Put a second paragraph across it in a separate variant. | Block on invisible required text and on obstructed text respectively. Neither case requires vertical overflow. |
| Shrink the headline to 8 CSS pixels. Separately constrain its card to four pixels high. | The existing small-font and overflow warnings both reach the per-slide result and release decision. |
| Remove the contents of a required KPI card but keep its background. Insert the correct text behind an opaque shape in another variant. | Both fail visible-content validation. Counting shapes or finding text in the file cannot pass either variant. |
| Replace 82 design partners with 100%, swap two metric labels, or use the wrong source for a plausible value. | Report the wrong unit, association or supporting passage individually. The slide can pass all geometric checks and still fail content integrity. |
| Copy the speaker cue onto the canvas. Insert template setup copy into a content slide. | Fail audience-visible text checks. A presenter edition may retain approved notes in its notes part. |
| Send background plates 1, 1, 3 for a three-slide export. Drop slide 2 only from PDF. | Identify the duplicate or missing slide and the affected format. Fail publication even if another format succeeded. |
| Recolor an approved cover or change its decorative image while keeping contrast, facts and hierarchy. | Show the visual difference to the reviewer. Accept the alternative once the audience task and required checks pass. Preserve this case to detect over-sensitive grading. |

Use rendered regions as evidence. Compare text geometry with neighboring objects and the viewport, then inspect the final pixels around flagged regions. For known fixtures, compare a targeted crop with an approved reference at a pinned font and viewport. Use OCR or a second extraction path to corroborate a missing label where helpful. Low-confidence extraction goes to inspection. Tune crop tolerances using both legitimate font-rendering variation and a seeded defect. Store the threshold and its reference examples before applying it to held-out decks. [Current DOM audit](../../ppt_maker/rendering/renderer.py#L333) · [Current scoring](../../evals/metrics.py#L346)

## 5. Evaluate visual design semantics with readers

Show a designer and a representative reader the same anonymized final deck at presentation size. Give the reader the audience and task first. Keep the answer key and generator identity hidden until they record what they understood. Then give the designer the brief, approved facts and neighboring slides. Ask both reviewers to work independently before resolving disagreements. For comparisons, randomize candidate order and permit a tie or “neither is usable.”

| Dimension | Question and evidence to record |
| --- | --- |
| Takeaway and narrative | After a short first look, ask the reader to state the slide’s claim. After the deck, ask what decision or next action follows. Record their words and compare with the accepted answers. |
| Evidence and visual encoding | Ask the reader to point to the number, comparison or diagram edge supporting the headline. Record wrong associations, missing denominators, reversed sequences or misleading emphasis. |
| Hierarchy and readability | Record the first element the reader noticed and the one they needed. Identify a specific region where type, contrast, wrapping or background competition changed what they could read. |
| Language, imagery and audience fit | Ask whether the wording belongs in a board meeting, an engineering briefing or a presenter’s private notes. Ask what the image contributes. A repeated slogan or unrelated photo needs a slide-specific explanation. |
| Handoff effort | Time the reader task and the presenter edit. Record corrections required, whether they found the source, and whether their edit survives reopening. Compare against an approved baseline on the same task. |

Score each dimension as **2** for independently correct, **1** for correct after prompting or a material reread, or **0** for wrong or impossible. Record an observation with every 0 or 1. Under the proposed pilot rule, a wrong decision-critical fact, exposed private cue, or unreadable required claim blocks release. A 1 on a decision-critical reader task requires correction or documented adjudication. A stylistic preference with a correct, readily understood answer is advisory. Maintain case-specific answers so stylistic conformity cannot stand in for comprehension.

Introduce a vision judge in advisory mode after reviewer-labeled examples exist. Give it rendered slides from both formats, audience, source, task and slide sequence. Require a finding with a location, severity and rationale, and allow abstention. On a held-out set, report serious misses per known serious defect and false alarms per accepted slide, with counts by format and layout. Compare against human disagreement, include approved redesigns, and rerun calibration when the judge or prompt changes. Keep ambiguous narrative decisions with the reviewers. [Existing text judge and calibration](../../evals/judge.py) · [Current visual audit](../../ppt_maker/audit/quality_checker.py#L225)

## 6. Schedule the work and report failures

| When | Scope | Output or decision |
| --- | --- | --- |
| Every pull request | Existing unit suite, schema and legacy fixtures, seeded defects for the changed layer, and deterministic pilot renders for affected export paths. Use pinned fonts, browser and presentation renderer. | Machine-readable result plus a before/after crop, relevant source excerpt and replay command for each failure. Required failures or unmeasured required checks return a nonzero job status. |
| Nightly or on renderer/theme changes | Rotate through layout × theme × text length × script, including RTL, long translated labels, missing font, light/dark backgrounds, both split orientations and preview. Exercise cold/warm caches and overlapping runs. | Matrix of measured combinations and trends in failures, runtime and output size. Preserve the first failure on retry and classify nondeterminism. |
| On model, prompt or retrieval changes | Compare single-shot and staged generation on identical briefs across repeated runs. Use a separately budgeted live evaluation. Include unsuccessful calls, abstentions, retries and manual correction time. | Paired per-brief outcomes, input/output tokens, elapsed time and failure counts. Report recorded or synthetic runs separately. An unavailable provider leaves live performance unmeasured. |
| Before release | Run all required fixtures on the candidate wheel. Inspect final PPTX in the supported client, complete audience and edit tasks, and review severe unresolved findings. | Format-specific release decision with reviewer, client, revision and remaining limitations. |

Each result should identify the source and plan hashes, code revision, generator mode, template/theme, fonts, renderer and client versions, slide role or ID, format, check, expected value, observed value, and evidence location. Publish a coverage denominator such as “10 of 10 required slide-format pairs inspected.” Archive local synthetic artifacts for reproducibility. On a regression, add the smallest reproducible example, fix the earliest faulty stage, and recheck both downstream formats. Update visual baselines only after a reviewer records why the change is acceptable. [Current CI workflow](../../.github/workflows/ci.yml) · [Evaluation entry point](../../evals/run.py)

## 7. Implementation order and exit criteria

1. **Make the current results trustworthy.** The test maintainer replaces silent fixture returns with explicit outcomes, removes developer-specific paths, distinguishes missing DOM data from measured zero, and gives required failures an effective exit status. Exit when a missing measurement and a deliberately failed scenario both prevent a green required job.
2. **Land the board and pitch fixtures.** The export and evaluation maintainers run both from a clean checkout, compare facts and units through PDF and PPTX, and retain artifacts on failure. Exit when both approved decks pass and wrong units, empty cards, invisible headings and leaked notes each fail for the correct reason.
3. **Validate visual judgment.** The designer and audience reviewers label the pilot pairs and at least one acceptable redesign. Extend to brand, engineering and research briefs. Exit when each task has an answer key and adjudicated examples, and a reviewer can trace every serious finding to the rendered slide.
4. **Expand compatibility and decide what to automate.** Add native-template, packaging, script/font and failure-recovery coverage. Establish latency and cost budgets from observed runs. Adopt a judge threshold only after publishing held-out errors and the sample size. Revisit the fixture set whenever a presenter finds a material defect that the release checks accepted.

The first deliverable is a reproducible board-and-pitch report showing two clean decks, damaged variants rejected for specific reasons, and the reader’s answers. That report makes the testing plan itself verifiable before the team invests in a larger benchmark.
