"""
test_refiner.py — Unit tests for Targeted Agentic Refinement Loop (Phase 2).

Validates:
1. Tier 1 deterministic micro-fixes (<15px overflow & filler pruning) run offline with $0 and 0 tokens.
2. Content block trimming for BulletBlock, StepBlock, CalloutBlock, ComparisonBlock.
3. Tier 2 semantic reflexions invoke mock Gemini client and return validated Slide patches.
4. Convergence limit terminates after at most 2 iterations per slide.
5. Deck-level budget caps refinements at 3 slides.
6. Algorithmic fallback line-clamps text and offloads overflow into speaker_notes.
7. End-to-end deck refinement on MasterPlan.
8. Single-slide HTML templating hook.
"""

import os
import unittest
from unittest.mock import MagicMock
from ppt_maker.core.schemas import (
    MasterPlan,
    Theme,
    Slide,
    BulletBlock,
    StepBlock,
    CalloutBlock,
    ComparisonBlock,
)
from ppt_maker.planning.refiner import (
    RefinerEngine,
    apply_deterministic_micro_fixes,
    apply_algorithmic_fallback,
    _prune_filler_text,
    _truncate_at_word,
)
from ppt_maker.planning.planner import refine_slide_patch
from ppt_maker.rendering.templater import Templater


class TestRefinerFramework(unittest.TestCase):

    def setUp(self):
        self.theme = Theme(structural_class="corporate_clean", palette="executive_navy", css_variables={})

    def test_01_prune_filler_and_truncate(self):
        """Verify filler phrase pruning and word-boundary truncation."""
        text = "In order to leverage synergy, we must moving forward optimize the platform."
        cleaned = _prune_filler_text(text)
        self.assertNotIn("In order to", cleaned)
        self.assertNotIn("leverage", cleaned)
        self.assertNotIn("synergy", cleaned)
        self.assertNotIn("moving forward", cleaned)
        self.assertIn("optimize the platform", cleaned)

        # Word boundary truncation
        long_str = "This is a very long sentence that needs to be shortened cleanly without cutting words in half"
        truncated = _truncate_at_word(long_str, 40)
        self.assertLessEqual(len(truncated), 43)  # 40 + '...'
        self.assertTrue(truncated.endswith("..."))
        self.assertNotIn("cutti...", truncated)

    def test_02_tier1_deterministic_micro_fixes_bullets(self):
        """Verify that Tier 1 micro-fixes cap flat bullets to 4 and prune filler phrases."""
        slide = Slide(
            slide_number=2,
            layout_type="generic",
            title="Operational Overview",
            subtitle="In order to summarize our progress going forward, here are the core metrics",
            content_bullets=[
                "In order to achieve growth we scaled infrastructure by 300% across all regions",
                "Best-in-class performance latency was reduced from 250ms to 45ms",
                "Utilize automated deployment pipelines to accelerate delivery cycles",
                "Leverage synergy across product and engineering teams for faster handoffs",
                "Fifth bullet that should be pruned because it exceeds the 4-bullet cap",
                "Sixth bullet that also exceeds the cap",
            ]
        )

        fixed = apply_deterministic_micro_fixes(slide, excess_px=10)

        # Asserts
        self.assertLessEqual(len(fixed.content_bullets), 4)
        self.assertNotIn("In order to", fixed.subtitle)
        self.assertNotIn("going forward", fixed.subtitle)
        self.assertNotIn("Best-in-class", fixed.content_bullets[1])
        self.assertNotIn("Leverage synergy", fixed.content_bullets[3])

    def test_03_tier1_deterministic_content_blocks(self):
        """Verify that typed content blocks (BulletBlock, StepBlock, CalloutBlock, ComparisonBlock) are compacted."""
        slide = Slide(
            slide_number=3,
            layout_type="split",
            title="Architecture Migration",
            content_blocks=[
                BulletBlock(
                    block_type="bullets",
                    items=[
                        "In order to scale, decompose the monolith into microservices",
                        "Leverage event bus for asynchronous communication",
                        "Item 3",
                        "Item 4",
                        "Item 5 to be capped",
                    ]
                ),
                StepBlock(
                    block_type="steps",
                    steps=["Step 1", "Step 2", "Step 3", "Step 4", "Step 5 to be capped"],
                    step_labels=["P1", "P2", "P3", "P4", "P5"]
                ),
                CalloutBlock(
                    block_type="callout",
                    text="In order to ensure zero downtime, all migrations utilize blue-green deployments with automated rollback.",
                    callout_type="insight"
                ),
                ComparisonBlock(
                    block_type="comparison",
                    left_label="Old",
                    left_items=["Item 1", "Item 2", "Item 3", "Item 4 excess"],
                    right_label="New",
                    right_items=["New 1", "New 2", "New 3", "New 4 excess"]
                )
            ]
        )

        fixed = apply_deterministic_micro_fixes(slide, excess_px=12)

        bullet_block = fixed.content_blocks[0]
        step_block = fixed.content_blocks[1]
        callout_block = fixed.content_blocks[2]
        comp_block = fixed.content_blocks[3]

        self.assertEqual(len(bullet_block.items), 4)
        self.assertNotIn("In order to", bullet_block.items[0])
        self.assertEqual(len(step_block.steps), 4)
        self.assertEqual(len(step_block.step_labels), 4)
        self.assertNotIn("In order to", callout_block.text)
        self.assertLessEqual(len(comp_block.left_items), 3)
        self.assertLessEqual(len(comp_block.right_items), 3)

    def test_04_tier2_semantic_overflow_calls_mock_llm(self):
        """Verify that an overflow > 15px triggers Tier 2 LLM patcher via dependency-injected mock client."""
        original_slide = Slide(
            slide_number=4,
            layout_type="generic",
            title="Massive Overflow Slide",
            content_bullets=["Very long sentence " * 10] * 5
        )

        mock_patch_json = """{
            "slide_number": 4,
            "layout_type": "generic",
            "title": "Compact Architecture",
            "subtitle": "Streamlined microservices flow",
            "content_bullets": [
                "API Gateway routes incoming client traffic",
                "Auth Service validates JWT claims in under 2ms",
                "Event Bus decouples downstream consumers"
            ]
        }"""

        mock_response = MagicMock()
        mock_response.text = mock_patch_json
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        diagnostic = "Container .generic-content overflows by 38px"
        refined = refine_slide_patch(original_slide, diagnostic, client=mock_client)

        self.assertEqual(refined.slide_number, 4)
        self.assertEqual(refined.title, "Compact Architecture")
        self.assertEqual(len(refined.content_bullets), 3)
        mock_client.models.generate_content.assert_called_once()

    def test_05_refine_slide_convergence_limit(self):
        """Verify that a stubbornly overflowing slide terminates after at most 2 iterations."""
        slide = Slide(
            slide_number=5,
            layout_type="generic",
            title="Stubborn Slide",
            content_bullets=["Point 1", "Point 2", "Point 3", "Point 4", "Point 5"]
        )

        # Audit fn that always returns an overflow
        def mock_always_overflow(s):
            return [{"type": "OVERFLOW", "excess_px": 25, "message": "Still overflowing by 25px"}]

        engine = RefinerEngine(max_iterations=2)
        refined_slide, report = engine.refine_slide(
            slide=slide,
            theme=self.theme,
            warnings=[{"type": "OVERFLOW", "excess_px": 25, "message": "Initial overflow"}],
            audit_fn=mock_always_overflow,
        )

        # Must terminate and invoke fallback
        self.assertTrue(report["resolved"])
        # History has 2 passes + 1 fallback entry
        self.assertEqual(report["passes"], 3)
        self.assertEqual(report["history"][-1]["tier"], "algorithmic_fallback")

    def test_06_deck_level_budget_capping(self):
        """Verify that deck-level budget caps refinements at 3 slides when 5 slides fail."""
        slides = [
            Slide(slide_number=i, layout_type="generic", title=f"Slide {i}", content_bullets=["B1", "B2"])
            for i in range(1, 7)
        ]
        mp = MasterPlan(theme=self.theme, slides=slides)

        # 5 slides have overflows
        dom_audit = [
            {"slide_number": 2, "warnings": [{"type": "OVERFLOW", "excess_px": 10, "message": "Over 10px"}]},
            {"slide_number": 3, "warnings": [{"type": "OVERFLOW", "excess_px": 45, "message": "Over 45px"}]},
            {"slide_number": 4, "warnings": [{"type": "OVERFLOW", "excess_px": 30, "message": "Over 30px"}]},
            {"slide_number": 5, "warnings": [{"type": "OVERFLOW", "excess_px": 12, "message": "Over 12px"}]},
            {"slide_number": 6, "warnings": [{"type": "OVERFLOW", "excess_px": 60, "message": "Over 60px"}]},
        ]

        # Audit fn resolves immediately after 1 pass
        def mock_audit_resolve(s):
            return []

        engine = RefinerEngine(max_iterations=2, max_refined_slides=3)
        updated_mp, summary = engine.refine_deck(mp, dom_audit, audit_fn=mock_audit_resolve)

        self.assertEqual(summary["total_overflows_detected"], 5)
        self.assertEqual(summary["refined_count"], 3)
        self.assertEqual(summary["budget_capped_count"], 2)
        # Should have targeted the top 3 worst overflows (slides 6, 3, 4)
        refined_slide_nums = [rec["slide_number"] for rec in summary["slides"]]
        self.assertEqual(refined_slide_nums, [6, 3, 4])
        self.assertEqual(set(summary["skipped_slides"]), {2, 5})

    def test_07_algorithmic_fallback_moves_text_to_speaker_notes(self):
        """Verify that algorithmic fallback preserves truncated text in speaker notes."""
        slide = Slide(
            slide_number=7,
            layout_type="generic",
            title="Dense Presentation Slide",
            content_bullets=[
                "Primary takeaway about revenue growth",
                "Secondary takeaway about margin expansion",
                "Tertiary takeaway about churn reduction",
                "Fourth bullet that cannot fit on screen",
                "Fifth bullet that cannot fit on screen",
            ],
            speaker_notes="Presenter introduction."
        )

        fallback_slide = apply_algorithmic_fallback(slide)

        self.assertEqual(len(fallback_slide.content_bullets), 3)
        self.assertIn("[Overflow note (preserved for presenter)]:", fallback_slide.speaker_notes)
        self.assertIn("Fourth bullet that cannot fit on screen", fallback_slide.speaker_notes)
        self.assertIn("Fifth bullet that cannot fit on screen", fallback_slide.speaker_notes)
        self.assertTrue(fallback_slide.speaker_notes.startswith("Presenter introduction."))

    def test_08_templater_generate_single_slide_html(self):
        """Verify that Templater.generate_single_slide_html produces valid HTML file on disk."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            templater = Templater(build_dir=tmpdir)
            slide = Slide(
                slide_number=1,
                layout_type="cover",
                title="Single Slide Test",
                subtitle="Verifying targeted template generation"
            )
            out_file = templater.generate_single_slide_html(
                slide=slide,
                theme=self.theme,
                total_slides=1
            )
            self.assertTrue(os.path.isfile(out_file))
            with open(out_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("Single Slide Test", content)
            self.assertIn("Verifying targeted template generation", content)


if __name__ == "__main__":
    unittest.main()
