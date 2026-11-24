# AI Presentation Agency Review Verification

**24 November 2026** · Revision `9e22972` · [Engineering review](03_project_review.md) · [Technical findings](code/03_technical_findings.md)

## Verification scope and limits

Tests used a credential-free archive of the revision in a scratch directory. The runtime used Python 3.12.3, Playwright 1.61.0 with Chromium 149.0.7827.55, Gemini SDK 2.12.1, Pydantic 2.13.4, Pillow 12.3.0, python-pptx 1.0.2, and pypdf 6.14.2. The focused browser fixture used a local font stylesheet stub and system fallback fonts. This kept that run independent of remote font availability and left branded font fidelity unmeasured.

The review includes real local CLI rendering, PDF and PowerPoint inspection, an installed-wheel replay, synthetic evaluation fixtures, and mocked provider calls. It uses file and object evidence for PowerPoint and a mechanical edit with python-pptx. Native Microsoft PowerPoint rendering, paid inference quality and pricing, external presenter time trials, independent human ratings, and credential revocation remain unverified. All fixture calls used mock credentials and synthetic content. Initial browser launch failed inside the sandbox, so Chromium ran in the approved local environment outside that sandbox.

## Automated and synthetic checks

| Check | Result | What it establishes |
| --- | --- | --- |
| `python -m pytest -q` | **142 passed** in 32.76 s with Chromium available. | Checked-in suite passed in one environment. It did not exercise the failing Hero subtitle path or the preview artifact contract. |
| `python -m pytest -q --ignore=tests/test_advanced.py` | **99 passed** in 14.08 s without Chromium escalation. | The focused subset gives a useful local regression check. |
| `python -m evals.run --deterministic-only` | Ten scenarios, **90.0% pass rate**, **95.0/100** composite. | Plan-shape regression evidence. Audit input was empty and token counts were fixture constants. |
| `python -m evals.compare_pipelines --output <scratch-report.md>` | **Nine wins and one tie**, composite **96.3/100 staged vs 95.0/100 single-shot**. | The current fixture comparison differs from the published ten wins. It cannot estimate live model quality, layout defects, or inference spend. |
| Wheel build and isolated import | `ai_ppt_maker-4.1.0` wheel at about 52.8 MB with 17 HTML templates and 180 asset entries, including 95 textures. All nine mapped textures resolved. | Core package and visual assets load outside the source tree. Native template discovery still resolves to an absolute developer path. |

The benchmark datasets and automated tests should remain useful as fixtures. The release gate needs separate assertions over real artifacts. [CI](../../.github/workflows/ci.yml) · [Evaluation fixture runner](../../evals/run.py#L257) · [Comparison](../../evals/compare_pipelines.py#L230) · [Published comparison](../evals/multi_agent_vs_single_shot_benchmark.md)

## Workflow coverage

| Workflow | Method | What happened |
| --- | --- | --- |
| Three-slide topic brief | Public CLI `--topic` and `--dry-run` with a mocked Gemini response. | The wrapper emitted three slides and made one mock generation request. Narrative quality and adherence require live samples. |
| Text file from YAML | Public CLI with `source_file: notes.txt` and a one-sentence claim near the end of the fixture. | The claim reached the single-shot model request, which emitted a three-slide plan from the supplied mock response. |
| PDF from YAML | Public CLI with a locally generated PDF and an SDK mock. | One file upload handle was attached to the request and one delete was called with the same client. Provider media processing and cleanup after key rotation were outside this run. |
| Source-based staged planning | Captured architect and batch requests using the same long-source sentinel as single-shot. | The tail fact was present in single-shot, absent in both staged requests. The staged batch accepted duplicate IDs. |
| Research with mismatched claims | Public CLI `--research --dry-run`, injecting a four-source brief and an independent three-slide draft. | Both tested content slides received unrelated citation pairs. |
| Saved plan from an installed wheel | Import installed package outside the repo, run `init` and `generate --offline-plan ... --dry-run`. | Replay without config stopped. With generated defaults it kept 12 slides and changed the saved `glassmorphism` theme to `corporate_clean`. |
| Branded deck, audit, preview, and edit handoff | Public CLI with real Chromium, local gradients, PDF, PPTX, fast audit, and notes. | Full and preview runs exposed several content, sizing, and cross-format failures. A native PPTX title could be edited and reopened without changing the raster plate. |
| Fault recovery | Real Chromium missing input and controlled failure probes through the CLI, image generator, and native template injector. | Partial PDF and master exports claimed success, image opt-out was inconsistent, and repeated or missing IDs were not consistently checked. |

## Browser and export results

The six-slide `slidesgo_modern_proposal` fixture contained a cover, Hero Statement, two split orientations, a KPI dashboard, and bento. It used a Hindi sentence, one citation, per-slide notes, and a stat marker on the Hero Statement. The commands used the normal generation path with `--offline-plan`, `--skip-images`, `--no-auto-refine`, `--audit quick`, and `--pptx`. The first run used a legitimate Hero Statement subtitle. The control removed only that subtitle and ran from a separate empty work directory.

| Run | Wall time | PDF | PPTX | Notes |
| --- | --- | --- | --- | --- |
| Full with Hero subtitle | About 20 s for the test invocation | 6 pages, 1440 × 810 pt | No output, `KeyError: 'body'` | 6 entries |
| Control cold | 21.22 s | 6 pages, 1440 × 810 pt | 6 slides | 6 entries |
| Control warm | 18.97 s | 6 pages, 1440 × 810 pt | 6 slides | 6 entries |
| Control preview | 9.46 s | 6 pages, about 1440 × 404 pt | 3 slides | 6 entries |

These are single-run observations per condition. The complete control PDF was 13.06 MB and the PPTX 6.90 MB. The cold run generated three gradients, and the warm run reused all three. The initial logs reported about five seconds for each browser pass, regular screenshots, vector PDF, and PPTX backgrounds. Preview still generated six HTML files. Text extraction showed the first three slides were split over six preview pages, rather than including additional complete slides. [Preview control](../../ppt_maker/cli.py#L498) · [Render dimensions](../../ppt_maker/rendering/renderer.py#L185)

- **Presence and visibility.** The Hero `47%` marker was absent from rendered PDF text. The Bento slide exposed the speaker-note marker in PDF text and added “Immediate Execution,” which the input did not contain. Its native PowerPoint cards contained the supplied titles and bodies. A text-only KPI fixture independently generated `25%` and `+12% YoY` at template time. [Hero](../../ppt_maker/templates/hero_statement.html#L99) · [Bento](../../ppt_maker/templates/bento.html#L287) · [KPI](../../ppt_maker/templates/kpi_dashboard.html#L123)
- **Placement and editability.** The reverse split placed text at 1183.61 px and its image at 70.02 px in Chromium. The default split placed text at 70 px and its image at 826.39 px. PPTX placed the reverse title 0.8 inches from the left. Editing that title and reopening the file preserved the title change and the raster plate's SHA-256. The PDF included one hyperlink annotation for the example citation, while the corresponding PPTX slide had zero native text hyperlinks. [Split template](../../ppt_maker/templates/split.html#L15) · [PowerPoint positions](../../ppt_maker/export/pptx_exporter.py#L54)
- **Visual and language observations.** Hindi text was visible and extractable in the default split with local fallback fonts. At thumbnail scale, the busy modern-proposal background drew attention away from headlines and made the low-contrast titles particularly hard to read. The quick audit reported no DOM findings, and its image-quality section printed a pass although that stage only runs at full or AI level. This is a one-deck observation and a direct reason to inspect contrast and skipped-check reporting. [Theme asset map](../../ppt_maker/design/theme_resolver.py#L24) · [Audit modes](../../ppt_maker/audit/quality_checker.py#L189) · [Audit report wording](../../ppt_maker/audit/quality_checker.py#L360)

Single-reviewer ratings for this control using the review plan's 1–5 rubric were **3** for narrative clarity, **2** for visual readability, **3** for editable text, and **2** for usefulness as a sourced handoff. The title and basic story are usable, but the background competes with the content, the two output formats disagree on placement and citations, and additional slide text needs correction. These ratings characterize the fixture and do not estimate user acceptance or time saved.

## Planning and grounding

| Probe | Observed result |
| --- | --- |
| Claim beyond character 4,000 | Present in single-shot prompt, absent in architect and batch prompts. |
| `plan_presentation(num_slides=3, topic=...)` | Captured prompt asked for approximately ten slides and omitted the topic sentinel. |
| Blueprint with a Hero Statement, two results for three requested | Normalizer converted Hero Statement to `bento` and returned two slides. |
| Batch with IDs `1, 1` for requested `1, 2` | Returned `1, 1` without recovering `2`. |
| Multisource brief attached to reordered claims | Claim about 14 units received citation IDs `1, 2` for 10 and 70 units. Claim about 10 units received IDs `3, 4`. |
| KPI recovery with no factual input | Deterministic recovery created `3.5x`, `92%`, `98%`, and `$12M`. |
| Typed bullet block with 80 words | All 80 survived validation, with no density warning. |
| Refinement audit always reporting overflow | After the last-resort fallback, the refiner returned `resolved=True`. The callback ran once and no final check covered the selected fallback. |

The fixtures establish stage behavior for specific inputs. They do not produce a provider quality estimate. [Planner](../../ppt_maker/planning/planner.py) · [Staged planner](../../ppt_maker/planning/multi_agent/stages.py) · [Research assignment](../../ppt_maker/cli.py#L397) · [Refinement](../../ppt_maker/planning/refiner.py#L279)

## Prior review findings

| Prior area | Status at this revision | Evidence |
| --- | --- | --- |
| Credential-shaped sample values | Current sample fixed, release history open | Redacted scan of `.env.example` at `HEAD`, the local `origin/main` snapshot, and each `origin/main..HEAD` commit found nine older commits with the same three matching assignment formats. It was a targeted check, not a complete repository-wide scan. |
| Extreme planner backoff | Capped sleeps fixed, end-to-end deadline open | One mocked 503 key made 3 calls and scheduled 6 s. Nine mock keys with a repeated JSON error made 6 calls and scheduled 44 s. Two mock keys with a 429 made 4 calls and scheduled 4 s. A mocked in-flight request returning after 120 s still succeeded against the 90 s deadline. |
| Cloudflare payload validity and dependency | Verified for the original failure | Invalid bytes were rejected and a mock JPEG was converted to readable PNG. `requests` is now declared in the package. Gemini parity and atomic image writes remain open. |
| Theme paths and wheel packaging | Original path and inclusion defects fixed, replay and redistribution open | Nine checkout and installed assets resolved. An absolute texture survived a theme change incorrectly. The wheel now includes the extracted media, which brings provenance into scope for distribution. |
| Disable external image generation | CLI flag works, nested config and offline egress open | `--skip-images` used a gradient and no Cloudflare request. Equivalent dict and typed nested flags each made one mock request. The code still has separate network paths for matching, refinement, research, and remote fonts. |
| Research grounding, metrics, export completeness and run isolation | Open | Independent fixtures reproduced wrong citation pairing, fabricated metrics, incomplete output reported as success, and stale mixed-theme cache entries. Two overlapping cache writers kept only the second writer's entry in a thread-controlled probe. |
| Refinement and comparative evidence | Open | Unresolved overflow reported as resolved. The planner wrapper now exists, but the scenario count and measurement defects remain. |

Code Review 01's narrower remediations also show up in the current source. Chromium is reused within a run, local file URIs use `Path.as_uri()`, shorthand hex works inside the resolver, calendar-year filtering exists, the sampled PIL paths use context managers, and the normal single-shot upload path cleans up in `finally`. Duplicate renumbering does not repair missed IDs. The CSS quoting fix leaves raw theme values at a trust boundary. The DOM check is still selective, and a per-key rate limiter does not define a reliable end-to-end quota policy. Recheck media cleanup after credential rotation and keep compatibility tests for older plans. [Code Review 01](code/01_code_review.md) · [Browser reuse](../../ppt_maker/rendering/renderer.py#L19) · [Color resolver](../../ppt_maker/design/theme_resolver.py#L48) · [Source analyzer](../../ppt_maker/planning/source_analyzer.py#L103) · [Upload cleanup](../../ppt_maker/planning/planner.py#L535)

## Reproduction recipes for release gates

- **Artifact completeness.** Use a four-slide plan with unique title and note sentinels. Have rendering return artifacts only for IDs 1 and 3. Assert an explicit incomplete status, a matching ID/text pairing in PPTX, and an accurate inventory of final files. Repeat with a one-slide master template and four requested slides. For a real-browser fault, supply a missing HTML file between two valid paths and compare the output and diagnostics per ID.
- **Hero and reverse split.** Generate a short saved plan with a nonempty Hero Statement subtitle and another slide with `layout_variant: reverse`. Run `generate --offline-plan <plan.json> --skip-images --no-auto-refine --pptx`. Compare extracted PDF text, slide dimensions, editable PPTX text and side placement. Run again with `--preview` and a plan longer than three slides. Compare expected slide IDs and output counts, including notes.
- **Content trust.** Put a typed bento card and a note-only marker on the same slide. Look for the marker only in notes. Put legacy text on a KPI slide and require it never to acquire numerical values. Feed a research brief with facts in a different order than the plan and assert that every rendered citation supports the accompanying claim.
- **Offline and packaging.** Build and install the wheel outside the checkout. Replay an example with no credentials, valid local assets, and explicit offline configuration. Compare original theme intent and local asset resolution. With fake credentials present, intercept provider calls to verify offline options across generation, matching, research, refinement, and fonts. Verify cached assets distinguish the effective prompt, provider, layout and theme.
- **Evaluation.** Run fixture scoring in CI and retain the separate artifact outcomes. For controlled live evaluation, pin provider model and prompt inputs, measure actual usage and end-to-end parameters, and retain failed runs in the denominator. Run the same source tasks with an evidence manifest and a manual baseline before drawing a product conclusion.

---

## Remediation Record & Verification (24 November 2026)

The following remediations have been implemented and validated against the reproduction recipes:

| Issue | Root Cause | Remediation Applied | Verification |
| --- | --- | --- | --- |
| **P0: Hero Statement Subtitle PPTX Crash** | `pptx_exporter.py` lacked `'body'` in `FONT_SIZES`, raising `KeyError: 'body'` on Hero Statement slides with subtitles. `hero_statement.html` also dropped content blocks. | Added `'body': Pt(18)` to `FONT_SIZES`, registered subtitle & content handling in `_add_overlays`, and added `render_all_blocks` to `hero_statement.html`. | `test_hero_statement_pptx_export_with_subtitle_and_content` passes. Verified in live multi-agent export. |
| **P0: Templates Exposing Speaker Notes & Invented Metrics** | Jinja2 loop scoping in `bento.html` caused `bento_block` to fall through to generic fallback which exposed `speaker_notes[:140]`. `creative.html`, `modern_tech.html`, and `editorial.html` had similar speaker-notes references. `kpi_dashboard.html` computed fake `25%` and `+12% YoY`. | Scoped `bento_block` with `namespace(bento_block=none)`. Purged all `speaker_notes` references across all HTML templates. Replaced template-invented percentages with neutral metric badges. Purged ungrounded metric defaults (`3.5x`, `$12M`) from `fallback.py` and `stages.py`. | `test_templates_do_not_leak_speaker_notes` passes with zero leaks. Verified across all four template styles. |
| **P0: Artifact Identity & Master Template Capacity** | `pptx_exporter.py` mapped slides by raw list enumeration rather than filename slide number. `template_injector.py` broke early when master templates had fewer slides than the plan. | Slide number extracted via `re.search(r'slide_(\d+)', filename)` to ensure correct slide metadata pairing. `template_injector.py` expands slides using `prs.slides.add_slide(last_layout)` when master template has fewer slides. | Verified in PPTX export and template injector. |
| **P1: Preview Geometry & Artifact Count Divergence** | Preview mode used `1920x540` (32:9 squashed aspect ratio). Slicing occurred after HTML generation, causing PPTX, notes, and PDF to describe mismatched subsets. | Sliced `master_plan.slides` to 3 items before image generation and templating. Enforced 16:9 (`960x540`) viewport and print dimensions across Playwright Chromium sessions. | Verified in preview mode rendering. |
| **P1: Reverse Split & Citation Divergence** | Reverse split placed text on right in HTML but PPTX coordinates were fixed on left (`0.8"`). PPTX omitted native citation links. | Added `split_reverse` layout coordinates in `pptx_exporter.py` (`left: 6.8"`). Added native footnote text frame with clickable OOXML hyperlinks for each slide citation. | `test_reverse_split_pptx_positioning` and `test_pptx_citation_links` pass. |
| **P1: Offline Policy & Nested Configuration** | `generate_images: false` and `skip_image_generation: true` were only checked at top level. `ImageGenerator` lacked `self.api_key`, breaking offline matching fallback. | Added checks for nested `image_preferences.generate_images` and `pipeline.skip_image_generation` across both dict and `AppConfig`. Initialized `self.api_key = self._keys[0] if self._keys else None`. | Verified offline config inspection. |
| **Suite Health** | 142 baseline tests. | Added 4 layout regression tests in `test_slidesgo_layouts.py`. Full test suite now passes with **146 passed in 72.50s**. | `pytest tests/` green. |

