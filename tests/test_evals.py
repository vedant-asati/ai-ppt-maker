"""
tests/test_evals.py — Unit and regression tests for the GenAI Evaluation Framework.

Verifies:
1. Dataset integrity (all 10 golden benchmark scenarios).
2. Deterministic metrics (DOM overflow, layout monotony, word density, block diversity, telemetry).
3. Aggregate scorecard evaluation and letter grading.
4. CLI runner offline execution.
"""

import os
import sys
import unittest

# Ensure project root is on sys.path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from ppt_maker.core.schemas import MasterPlan, Slide, Theme, StatBlock, ComparisonBlock, PullQuoteBlock
from evals.metrics import (
    calc_dom_overflow_rate,
    calc_layout_monotony,
    calc_word_density,
    calc_content_block_diversity,
    calc_system_telemetry,
    evaluate_master_plan_deterministic
)
from evals.run import load_dataset, create_synthetic_master_plan_for_scenario, run_evaluation


class TestEvalsFramework(unittest.TestCase):

    def test_01_dataset_integrity(self):
        """Verify that dataset.json exists, contains 10 scenarios with all required keys."""
        dataset = load_dataset()
        self.assertEqual(len(dataset), 10, "Golden dataset must contain exactly 10 scenarios.")
        
        required_keys = {"id", "title", "category", "topic", "target_audience", "suggested_theme", "expected_slides_range", "source_text"}
        scenario_ids = set()
        
        for item in dataset:
            self.assertTrue(required_keys.issubset(item.keys()), f"Scenario {item.get('id')} missing required keys.")
            self.assertNotIn(item["id"], scenario_ids, f"Duplicate scenario ID: {item['id']}")
            scenario_ids.add(item["id"])
            self.assertGreater(len(item["source_text"]), 100, f"Scenario {item['id']} has insufficient source_text.")

    def test_02_calc_dom_overflow_rate_clean(self):
        """Verify that zero DOM warnings produces 0.0 overflow rate and passed=True."""
        res = calc_dom_overflow_rate([], total_slides=5)
        self.assertEqual(res["overflow_rate"], 0.0)
        self.assertEqual(res["overflow_slide_count"], 0)
        self.assertEqual(res["overflow_slides"], [])
        self.assertTrue(res["passed"])

    def test_03_calc_dom_overflow_rate_detected(self):
        """Verify that DOM warnings correctly identify failing slides and compute overflow rate."""
        # Simulated warnings from Renderer / QualityChecker
        warnings = [
            {"slide_number": 2, "warnings": [{"type": "OVERFLOW", "message": "Card overflowed by 18px"}]},
            {"slide_number": 4, "warnings": [{"type": "OVERFLOW", "message": "Content overflowed by 25px"}]},
            {"slide_number": 4, "warnings": [{"type": "OVERFLOW", "message": "Secondary overflow"}]}
        ]
        res = calc_dom_overflow_rate(warnings, total_slides=5)
        self.assertEqual(res["overflow_slide_count"], 2)
        self.assertEqual(res["overflow_slides"], [2, 4])
        self.assertEqual(res["overflow_rate"], 0.4)
        self.assertEqual(res["total_overflow_instances"], 3)
        self.assertFalse(res["passed"])

    def test_04_calc_dom_overflow_string_format(self):
        """Verify string format parsing for DOM overflow warnings."""
        str_warnings = [
            "[Slide 3] Card body overflow: scrollHeight (340px) > clientHeight (310px)",
            "[Slide 3] Another issue on slide 3"
        ]
        res = calc_dom_overflow_rate(str_warnings, total_slides=6)
        self.assertEqual(res["overflow_slides"], [3])
        self.assertEqual(res["overflow_slide_count"], 1)
        self.assertAlmostEqual(res["overflow_rate"], 1/6, places=3)
        self.assertFalse(res["passed"])

    def test_05_calc_layout_monotony_varied(self):
        """Verify that varied layouts pass with low monotony score."""
        theme = Theme(structural_class="corporate_clean", palette="executive_navy")
        slides = [
            Slide(slide_number=1, layout_type="cover", title="S1"),
            Slide(slide_number=2, layout_type="split", title="S2"),
            Slide(slide_number=3, layout_type="stat", title="S3"),
            Slide(slide_number=4, layout_type="timeline", title="S4"),
            Slide(slide_number=5, layout_type="quote", title="S5")
        ]
        mp = MasterPlan(theme=theme, slides=slides)
        res = calc_layout_monotony(mp)
        self.assertEqual(res["unique_layouts"], 5)
        self.assertEqual(res["consecutive_pairs"], 0)
        self.assertEqual(res["consecutive_triplets"], 0)
        self.assertLess(res["monotony_score"], 0.1)
        self.assertTrue(res["passed"])

    def test_06_calc_layout_monotony_triplet_penalty(self):
        """Verify that 3 consecutive identical layouts trigger a monotony penalty and failed status."""
        theme = Theme(structural_class="corporate_clean", palette="executive_navy")
        slides = [
            Slide(slide_number=1, layout_type="cover", title="S1"),
            Slide(slide_number=2, layout_type="generic", title="S2"),
            Slide(slide_number=3, layout_type="generic", title="S3"),
            Slide(slide_number=4, layout_type="generic", title="S4"),
            Slide(slide_number=5, layout_type="quote", title="S5")
        ]
        mp = MasterPlan(theme=theme, slides=slides)
        res = calc_layout_monotony(mp)
        self.assertEqual(res["consecutive_triplets"], 1)
        self.assertGreaterEqual(res["monotony_score"], 0.35)
        self.assertFalse(res["passed"])

    def test_07_calc_word_density_optimal(self):
        """Verify optimal word density detection."""
        theme = Theme(structural_class="corporate_clean", palette="executive_navy")
        slides = [
            Slide(slide_number=1, layout_type="cover", title="Annual Report", subtitle="2026 Executive Summary"),
            Slide(slide_number=2, layout_type="split", title="Strategic Highlights",
                  content_bullets=["Revenue grew 48% YoY", "Gross margin reached 81%", "Operating cash flow positive"])
        ]
        mp = MasterPlan(theme=theme, slides=slides)
        res = calc_word_density(mp)
        self.assertGreater(res["total_words"], 10)
        self.assertEqual(res["wall_of_text_count"], 0)
        self.assertTrue(res["passed"])

    def test_08_calc_word_density_wall_of_text(self):
        """Verify that slides exceeding 80 words are flagged as wall-of-text."""
        theme = Theme(structural_class="corporate_clean", palette="executive_navy")
        long_paragraph = "word " * 95
        slides = [
            Slide(slide_number=1, layout_type="cover", title="Cover"),
            Slide(slide_number=2, layout_type="generic", title="Dense Slide", subtitle=long_paragraph)
        ]
        mp = MasterPlan(theme=theme, slides=slides)
        res = calc_word_density(mp)
        self.assertEqual(res["wall_of_text_count"], 1)
        self.assertEqual(res["per_slide"][1]["status"], "wall_of_text")
        self.assertFalse(res["passed"])

    def test_09_calc_content_block_diversity(self):
        """Verify content block counting and diversity scoring."""
        theme = Theme(structural_class="corporate_clean", palette="executive_navy")
        slides = [
            Slide(slide_number=1, layout_type="cover", title="Cover"),
            Slide(slide_number=2, layout_type="stat", title="Stat",
                  content_blocks=[StatBlock(value="99.99%", label="Uptime")]),
            Slide(slide_number=3, layout_type="split", title="Comparison",
                  content_blocks=[ComparisonBlock(left_label="Old", left_items=["Slow"], right_label="New", right_items=["Fast"])]),
            Slide(slide_number=4, layout_type="quote", title="Quote",
                  content_blocks=[PullQuoteBlock(quote="Simplicity is prerequisite for reliability.", attribution="— Dijkstra")])
        ]
        mp = MasterPlan(theme=theme, slides=slides)
        res = calc_content_block_diversity(mp)
        self.assertEqual(res["slides_with_blocks"], 3)
        self.assertEqual(res["typed_blocks_coverage"], 0.75)
        self.assertEqual(res["unique_block_types"], 3)
        self.assertGreaterEqual(res["diversity_score"], 7.0)
        self.assertTrue(res["passed"])

    def test_10_calc_system_telemetry(self):
        """Verify telemetry calculations for duration, token economics, and cost."""
        usage = {"input_tokens": 10000, "output_tokens": 5000}
        res = calc_system_telemetry(duration_s=2.5, token_usage=usage, model_name="gemini-3.1-flash-lite")
        self.assertEqual(res["total_tokens"], 15000)
        self.assertEqual(res["tokens_per_second"], 6000.0)
        # 10k * (0.075 / 1M) + 5k * (0.3 / 1M) = 0.00075 + 0.0015 = 0.00225 USD
        self.assertAlmostEqual(res["estimated_cost_usd"], 0.00225, places=5)

    def test_11_evaluate_master_plan_deterministic_aggregation(self):
        """Verify that evaluate_master_plan_deterministic computes composite score and grade."""
        dataset = load_dataset()
        mp = create_synthetic_master_plan_for_scenario(dataset[0])
        scorecard = evaluate_master_plan_deterministic(
            master_plan=mp,
            dom_audit_results=[],
            duration_s=1.2,
            token_usage={"input_tokens": 1200, "output_tokens": 800}
        )
        self.assertIn("composite_score", scorecard)
        self.assertIn("grade", scorecard)
        self.assertIn(scorecard["grade"], ["A", "B", "C", "D", "F"])
        self.assertGreaterEqual(scorecard["composite_score"], 70.0)
        self.assertTrue(scorecard["all_passed"])

    def test_12_run_evaluation_offline_cli(self):
        """Verify run_evaluation CLI function executes in deterministic-only mode across a subset of scenarios."""
        out = run_evaluation(deterministic_only=True, limit=2)
        self.assertEqual(len(out["results"]), 2)
        self.assertIn("summary", out)
        self.assertEqual(out["summary"]["total_scenarios"], 2)
        self.assertGreaterEqual(out["summary"]["pass_rate"], 50.0)


if __name__ == "__main__":
    unittest.main()
