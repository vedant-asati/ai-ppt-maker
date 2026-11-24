# Product direction for recurring operating reviews

**Decision proposal · 24 November 2026.** Assuming the goal is a product people choose for real work, I would spend the next development cycle helping one operating team prepare its monthly leadership review. The first user would be the business operations lead who owns the deck. Give them a way to turn an approved prior review, this month’s figures and the team’s written explanations into an editable update they can defend in the meeting.

## Why this job

The most revealing failure in the sample pitch was a slide that assigned **100%** to developer count, partner count, speedup and market size. The file opened, contained four labels and had a credible headline. The investor still could not answer a basic traction question. Conversely, the brand cover used generous whitespace effectively. Applying one rule about density to both slides would teach the system the wrong lesson. Design quality depends on what the person looking at the slide needs to understand. [Sample deck review](reviews/05_testing_and_visual_quality.md)

An operating review gives us a previous deck the audience accepted, source figures with an owner, and a next meeting where we can see whether the work was useful. It also gives us a demanding baseline. Copying last month’s PowerPoint preserves the organization’s language, formatting and edits for free. The product earns its place only if it reduces the work of finding changes, explaining them, checking them and getting sign-off. Start with an internal monthly review so there are repeated opportunities to learn before taking on a board handoff.

## Where the market sets the bar

Microsoft already documents generating a presentation inside PowerPoint from a reference document and using an organization’s template. Gamma already exports editable PowerPoint tables. Recurring report generation is also established. For example, think-cell fills PowerPoint templates from Excel or JSON and updates chart annotations. Those products are credible alternatives. A pilot still needs to establish which alternative the team uses and where it falls short. [Microsoft PowerPoint](https://support.microsoft.com/en-gb/powerpoint/copilot/create-a-new-presentation-with-copilot-in-powerpoint) · [Gamma export](https://help.gamma.app/en/articles/8022861-what-s-the-easiest-way-to-export-my-gamma) · [think-cell report automation](https://www.think-cell.com/en/resources/manual/introductionautomation)

The opportunity worth testing is the editorial work **after the numbers change**. Imagine retention moves from 134% to 121%. A linked table can show 121%. The slide title may still say “Expansion accelerated,” and the account owner may have written that a reporting-definition change affects comparability. The useful product finds the dependent headline, surfaces the qualification, proposes an accurate visual comparison, and asks the owner what conclusion they can support. If the reason is unknown, that uncertainty belongs in the review. This is a hypothesis about unmet demand, and it needs testing against the team’s actual workflow.

## What to build first

The [pilot execution plan](operating_review_execution_plan.md) assigns owners, sequences the implementation and defines how to run the first two reporting updates.

1. **Support one approved five-slide review.** Use a small set of editable layouts for a decision, a trend, a variance, an explanation and an action. Map one team’s approved template and metric definitions by hand for the pilot. This bounds the engineering work and exposes how much setup each new customer would require.
2. **Let the author review what changed.** Show the old and new values, period, units, supporting passage and affected wording. Preserve approved commentary and edits. If a source changes a denominator or conflicts with another source, request a decision before publishing. Use deterministic code for values and calculations. Give the model the editorial jobs of proposing a headline, summarizing an explanation and choosing a suitable composition.
3. **Design for the reader’s question.** A trend needs a comparable time series. A variance needs a baseline and a visible unit. A decision needs the proposed action, owner and unresolved issue. Fund a few human-designed examples of each, including counterexamples. A clean title page can stay quiet. On a comparison slide the numbers and their relationship must dominate the image.
4. **Deliver in the team’s existing workflow.** The editable PowerPoint and its matching PDF are the deliverables. Use a simple review surface for proposed changes and leave final editing in PowerPoint. Verify content, slide identity and readability on the exported files. Reuse the CLI and saved-plan pipeline for the pilot. Decide where a native chart or table is needed by asking which objects the presenter actually edits. [Testing plan](evals/presentation_testing_plan.md) · [Blueprint critique](reviews/04_blueprint_review.md)

Defer a general-purpose canvas, new export platforms, more theme families, open-web research and additional agent roles for this cycle. Revisit an item when a pilot user hits a concrete limitation it would resolve. Keep the general-purpose generator available as an experimental path. Publish a worked before-and-after deck, its source brief and known limitations as the first product demonstration.

## How to decide whether to continue

Recruit three people who personally prepare recurring operating reviews. Ask each for two consecutive sanitized reporting periods and their last accepted deck. Watch them update one section using their normal process, including spreadsheets, linked charts and existing AI tools. Record where time goes. If most effort is negotiating the explanation with stakeholders, a faster renderer will deliver little value.

Run a hands-on pilot over two updates per team. Measure active preparation, fact-checking, formatting and correction time through approval. Track our own setup and support time separately so manual work behind the scenes stays visible. Have a reader identify the change and the decision from the final deck. Keep consequential errors as a separate release gate.

As a **proposed investment threshold**, look for at least two of three owners choosing the tool for a second update, a median reduction of roughly one-third in their hands-on time against their own baseline, and zero unresolved material fact or readability errors in the deliverables. Check that onboarding effort is recoverable across repeat updates. These proposed rules guide a small pilot. Market demand and willingness to pay remain open questions.

If users repeatedly bring an existing deck and mainly value catching stale claims, missing units and unreadable slides, test a standalone **pre-send PowerPoint review** as the next direction. If linked templates already save as much time and users will not come back for editorial assistance, stop expanding this product thesis. Demand for beautifully art-directed, one-off decks would justify a separate design-led experiment with different users and success criteria.
