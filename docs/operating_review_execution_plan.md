# Execution plan for the monthly operating review pilot

**Proposed scope, 24 November 2026.** Deliver one five-slide monthly update that a business operations lead can correct, approve, open in PowerPoint and use in a leadership meeting. Prove the workflow on a second reporting period before investing in a broader product. The [product direction](product_direction.md) explains the choice of user. The [testing plan](evals/presentation_testing_plan.md) defines the wider regression suite.

## Start here

On day one, the product lead should sit with a person who prepares the monthly review and watch them update last month’s deck. Ask them to show where each value came from, which commentary they habitually rewrite, and what their approver sent back last time. Time the work from opening the inputs through the final correction. Obtain a sanitized prior deck, two period extracts and the related written commentary for local pilot use. The first decision is whether there is enough repeated checking and editorial work to justify automating it.

In parallel, the engineering lead can establish the current baseline with the commands below. Run from a checkout with the project’s local environment installed. The scratch directory isolates the tests and generated plan from existing presentation files.

```bash
set -eu
repo=$(git rev-parse --show-toplevel)
pilot_dir=$(mktemp -d)
git -C "$repo" archive HEAD cli.py config.yaml ppt_maker tests examples/sample_master_plan.json | tar -x -C "$pilot_dir"
cd "$pilot_dir"
"$repo/.venv/bin/python" -m pytest -q tests/test_slidesgo_layouts.py
"$repo/.venv/bin/python" cli.py generate --config config.yaml --offline-plan examples/sample_master_plan.json --dry-run
"$repo/.venv/bin/python" -c 'import json; from pathlib import Path; p=json.loads(Path("master_plan.json").read_text()); assert p["slides"]; print(len(p["slides"]), "slides in saved plan")'
```

At `44ab332`, this yielded **nine passing layout tests and a 12-slide saved plan**. It verifies the starting interface. The first new engineering deliverable is a five-slide, two-period fixture with independently written expected answers.

## Scope, owners and timing

Use one manually mapped team template, a small CSV of approved metrics, a short commentary file, and the last approved version of the mapped deck. Hand-map the initial five slides and record that labor. Use a simple local review form or editable review file during the pilot. A nontechnical owner must be able to approve an update without editing application JSON. Additional template families, arbitrary PowerPoint import, web research and a general-purpose editor can wait for evidence from the pilot.

Budget **four engineering weeks for a first usable build**, assuming one engineering lead, part-time design/QA support, and access to one presenter and a PowerPoint client. Treat this as a planning estimate. Observe two real updates per team on their reporting calendar. Historical replay can accelerate engineering feedback, while voluntary use at the next deadline provides the adoption evidence. One person can cover multiple roles, but someone other than the generator author should verify the fixture answers.

| Window | Accountable role | Work item | Exit evidence |
| --- | --- | --- | --- |
| Days 1–3 | Product lead | Recruit three operations owners, observe at least one baseline workflow, collect one complete pair of sanitized inputs, and identify a reader and approver. | Timing sheet, list of recurring corrections, agreed five slide roles and reader questions. If no team will provide comparable inputs, keep work on synthetic fixtures and revisit recruitment before building custom integrations. |
| Week 1 | Engineering lead and designer | Build the first fixture, map one prior deck and agree the reference compositions. | A runnable fixture, source-to-slide answer key, five approved slide sketches and one deliberately bad version. |
| Week 2 | Engineering lead | Compare periods, flag dependent copy, and implement author decisions. | A replay shows each changed fact and affected slot. A stale approval, incompatible definition and missing source are all caught. |
| Week 3 | Export maintainer | Produce a candidate PDF and PPTX from the approved revision. Validate the actual files and the promised edits. | Five matching slides in both formats, client-rendered evidence, edit-and-reopen result and a failed-export recovery test. |
| Week 4 | QA lead and presenter | Rehearse with a withheld period, inject known faults, run independent reader tasks, then make a release decision for the first team. | Per-slide findings, corrections, reviewed final files and a signed-off pilot run. A failed required check goes back to its owner. |
| Next two reporting updates | Product lead | Repeat with three teams. Record adoption, correction effort and support cost. | A per-team scorecard and a decision to continue, change direction or stop. |

## Implementation backlog

### 1. Create a two-period fixture and map the prior deck

Deliver a proposed `tests/fixtures/operating_review/` directory with synthetic prior/current CSVs, commentary, a reusable local template, the approved prior plan and an answer key. Keep actual pilot inputs outside version control. Give every metric an identifier, source location, period, unit and definition version. Give every logical slide and editable slot a persistent identifier. Keep display order separate. On initial mapping, record which headings and commentary have already been approved by the owner. A later run must be able to reuse that mapping.

Design five slides around reader questions. **Decision** states what leadership needs to decide. **Trend** shows comparable reporting periods. **Variance** pairs an actual with its baseline and labels the unit. **Explanation** distinguishes sourced interpretation from open questions. **Action** names an owner and a due date, or visibly marks these as pending. For each slide, the designer supplies a readable reference, the expected answer, and one misleading alternative. Use the existing slide and content-block types where they carry the meaning through both exports. [Slide schemas](../ppt_maker/core/schemas.py) · [Layout tests](../tests/test_slidesgo_layouts.py)

### 2. Implement the period comparison before drafting copy

Build a deterministic comparison over metric ID, unit, period and definition version. For the pilot input columns, use `metric_id,period,value,unit,definition_version,source_ref`. Reject duplicate keys and incompatible units. Keep numeric zero distinct from blank. Keep decimal precision and define display rounding once. Attach supporting commentary separately with its source reference. The input owner verifies the mapping when a new source first appears.

Use retention as the acceptance case. Prior **134%** and current **121%** with matching definitions yield **−13 percentage points**. Both values and their periods must be visible. If the definition changed, preserve the reported values, flag the break in comparability, and withhold the like-for-like conclusion. If the owner has supplied no explanation, leave the cause open. Tests must exercise all three cases plus a genuine zero and an absent current value. Existing recovery and normalization paths are important regression targets. [Staged normalization](../ppt_maker/planning/multi_agent/stages.py) · [Fallback](../ppt_maker/planning/multi_agent/fallback.py)

### 3. Put the proposed changes in front of the author

For each affected slide, show the prior wording, proposed wording, supporting values, source passage and reason for review. Expose **accept**, **edit**, **keep** and **mark unresolved**. Retaining an unsupported headline leaves the issue open. Persist decisions against the revision of the source and slide. A later source correction invalidates only affected approvals, including a summary headline elsewhere in the deck. Preserve unrelated approved edits.

Start with deterministic proposed wording for the fixture. Once that path passes, allow a model to draft a concise alternative from the same approved facts and commentary. Validate its factual claims before displaying it. On model failure, the author can still complete the review using the deterministic comparison. Before release, replay the approved version with automated copy refinement disabled and verify the outputs contain the author’s exact correction. [Current replay and theme handling](../ppt_maker/cli.py) · [Refinement](../ppt_maker/planning/refiner.py)

**PowerPoint handoff rule for the pilot.** Let presenters make final edits in their normal client. At the next cycle, ask for the file they actually approved, compare its mapped text and values against the last export, and have the owner reconcile changed slots before refresh. An unexpected structural edit goes to manual mapping. Archive the original. Measure reconciliation time as part of the workflow. This avoids silently replacing the very edits the pilot is intended to preserve.

### 4. Export and verify the same approved revision

Adapt the current saved-plan path to consume the approved review, capture the effective theme, and write each run into a fresh directory. Record the source and plan hashes, ordered slide identifiers, required outputs and artifact paths. Make both output files pass the same manifest check before publishing the pair. Check the template-injection route if the chosen pilot template needs it. Keep the previous approved files recoverable when a render fails. [CLI](../ppt_maker/cli.py) · [Compiler](../ppt_maker/export/compiler.py) · [Editable export](../ppt_maker/export/pptx_exporter.py) · [Template injection](../ppt_maker/export/template_injector.py)

Use the following existing CLI invocation **after** the fixture task supplies `pilot.yaml`, `approved-plan.json`, local assets and fonts. Run from a fresh pilot directory with the candidate package installed. This exercises the render path. The comparison, approval and publication checks above still need implementation.

```sh
ppt-maker generate --config pilot.yaml --offline-plan approved-plan.json \
  --skip-images --no-auto-refine --audit quick --pptx
```

QA reopens both files and checks five slides in the expected order, complete page geometry, correct values attached to their labels and no delivery cues on the audience canvas. Rasterize the PDF and render the PPTX in LibreOffice for routine comparison. Open the candidate in the team’s PowerPoint client, edit an agreed object, save and reopen. If the team edits chart data, a native editable series is part of this milestone. A different supported client requires its own recorded check. Confirm that audience-distributed files exclude private notes and that the presenter copy retains approved notes.

### 5. Prove the workflow can reject a bad result

Use four one-change variants for the first gate. Put a white headline on white, change a percentage-point difference into a percent change, leave a required card empty, and leak a private note. Each must fail on the correct slide and format. Then duplicate a plate while keeping the total slide count correct, change a source after approval, and interrupt the second export. Each must prevent publication of the candidate pair. Keep a correct alternate cover as a control against over-sensitive visual scoring.

Have a reader open the exported deck without seeing the answer key. Ask what changed, whether the periods are comparable, and what action leadership should take. Record the answer and the slide region they used. A critical wrong answer, unreadable required figure, unsupported claim or missing client check keeps that candidate out of the pilot meeting. Reproduce the smallest failing case, correct the earliest faulty stage and rerun both output formats. [Observed failure cases](reviews/05_testing_and_visual_quality.md) · [Full acceptance method](evals/presentation_testing_plan.md)

## Operating each pilot update

1. **Intake.** The operations owner gives the prior approved file, current extract, commentary and meeting date. The pilot lead identifies the audience, the approval owner and the decision the deck should support.
2. **Prepare and review.** The operator maps any new fields, runs the comparison and records setup time. The author resolves flagged items or explicitly approves wording that discloses uncertainty. No unresolved material inconsistency can pass into the meeting copy.
3. **Handoff.** QA verifies the export pair. The operations owner opens the PPTX, makes a representative edit, and approves the version that will be used. If the final PPTX changed, regenerate the matching PDF from that approved file and recheck both before delivery.
4. **Observe and repeat.** Log preparation, verification, formatting, corrections and support separately. Ask the reader the fixture-specific decision question. Offer the normal manual workflow for the second update and record which approach the owner chooses. Keep team-specific sources and review files local to the agreed pilot environment.

## Investment decision

For each team, keep a row with baseline hands-on minutes for a comparable five-slide update, pilot hands-on minutes through approval, elapsed approval time, operator setup/support minutes, critical errors before and after review, reader outcome, and voluntary second use. Calculate each owner’s time saving as `(baseline − pilot) / baseline`, then take the median across owners with comparable observations. Report missing observations and show the three individual results. Count manual reconciliation and post-export fixes in the pilot time.

**Continue** if at least two of three owners voluntarily return, median hands-on time falls by about one-third, final deliverables have zero unresolved material errors, and repeat usage can recover onboarding effort. Estimate break-even updates as one-time setup cost divided by per-update savings after support and inference costs, using consistent cost units. A zero or negative saving cannot recover setup cost. These are proposed pilot thresholds. A team without a second reporting opportunity is still pending.

**Change direction** if users chiefly value finding stale claims or visual defects in a deck they already assembled. Test pre-send review on their existing files and measure issues caught and triage effort. **Stop expanding the generator** if the owners prefer their existing linked templates and the pilot yields little net saving. In every case, retain a sanitized before-and-after example, the fixture that reproduces the most consequential defect, and a short decision record.

