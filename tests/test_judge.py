"""
test_judge.py — Unit tests for Calibrated LLM-as-a-Judge (Phase 3).

Validates:
1. SlideEvaluation schema contract and normalized scoring calculation.
2. Calibration dataset integrity (10 pre-labeled slides).
3. Calibration runner agreement with ground truth (>= 90% accuracy).
4. Position bias mitigation: symmetric agreement vs detected bias reconciliation.
5. Deck-level judge score aggregation.
"""

import os
import json
import unittest
from unittest.mock import MagicMock
from ppt_maker.core.schemas import MasterPlan, Theme, Slide
from evals.judge import (
    SlideEvaluation,
    ComparisonVerdict,
    evaluate_slide,
    evaluate_deck_judge,
    compare_slides,
    calibrate_judge,
)


class TestJudgeFramework(unittest.TestCase):

    def setUp(self):
        self.theme = Theme(structural_class="corporate_clean", palette="executive_navy", css_variables={})

    def test_01_slide_evaluation_schema_and_score(self):
        """Verify SlideEvaluation schema fields and normalized score property."""
        ev_perfect = SlideEvaluation(
            slide_number=1,
            is_grounded_in_source=True,
            has_single_takeaway=True,
            free_of_filler_phrases=True,
            concise_and_punchy=True,
        )
        self.assertEqual(ev_perfect.score, 1.0)

        ev_partial = SlideEvaluation(
            slide_number=2,
            is_grounded_in_source=True,
            has_single_takeaway=True,
            free_of_filler_phrases=False,
            concise_and_punchy=True,
            criticism="Contains buzzwords: leverage synergy",
        )
        self.assertEqual(ev_partial.score, 0.75)

        ev_poor = SlideEvaluation(
            slide_number=3,
            is_grounded_in_source=False,
            has_single_takeaway=False,
            free_of_filler_phrases=False,
            concise_and_punchy=False,
        )
        self.assertEqual(ev_poor.score, 0.0)

    def test_02_calibration_dataset_integrity(self):
        """Verify calibration_slides.json has 10 pre-labeled cases with balanced coverage."""
        calib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evals", "calibration_slides.json")
        self.assertTrue(os.path.isfile(calib_path), "evals/calibration_slides.json must exist")
        with open(calib_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(len(data), 10)
        high_qual = [d for d in data if d["expected"]["is_grounded_in_source"] and d["expected"]["free_of_filler_phrases"] and d["expected"]["concise_and_punchy"]]
        hallucinated = [d for d in data if not d["expected"]["is_grounded_in_source"]]
        jargon = [d for d in data if not d["expected"]["free_of_filler_phrases"]]

        self.assertEqual(len(high_qual), 5)
        self.assertEqual(len(hallucinated), 3)
        self.assertEqual(len(jargon), 2)

    def test_03_calibrate_judge_with_mock_client(self):
        """Verify calibrate_judge executes against calibration dataset and checks >=90% accuracy."""
        calib_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evals", "calibration_slides.json")
        with open(calib_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Mock client returning exact expected labels per slide
        def side_effect(*args, **kwargs):
            prompt = kwargs.get("contents", [""])[0]
            # Match item by title or content in prompt
            matched_item = data[0]
            for item in data:
                if item["slide"]["title"] in prompt:
                    matched_item = item
                    break
            resp = MagicMock()
            resp.text = json.dumps({
                "slide_number": matched_item["slide"]["slide_number"],
                **matched_item["expected"],
                "criticism": None
            })
            return resp

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = side_effect

        calib_res = calibrate_judge(data, client=mock_client)
        self.assertEqual(calib_res["accuracy"], 1.0)
        self.assertTrue(calib_res["passed"])
        self.assertEqual(calib_res["correct_checks"], calib_res["total_checks"])

    def test_04_position_bias_mitigation_symmetric_agreement(self):
        """Verify that when forward and reverse evaluations agree, winner is declared with position_bias_detected=False."""
        slide_a = Slide(slide_number=1, layout_type="stat", title="Clear Metric")
        slide_b = Slide(slide_number=1, layout_type="generic", title="Unclear Fluff")

        call_count = [0]
        def mock_generate(*args, **kwargs):
            call_count[0] += 1
            resp = MagicMock()
            # Call 1 (Forward A vs B): Candidate 1 (A) is preferred
            if call_count[0] == 1:
                resp.text = json.dumps({"preferred": "candidate_1", "reasoning": "Candidate 1 is more grounded."})
            # Call 2 (Reverse B vs A): Candidate 2 (A) is preferred
            elif call_count[0] == 2:
                resp.text = json.dumps({"preferred": "candidate_2", "reasoning": "Candidate 2 is more grounded."})
            # Individual evaluations for score_a and score_b
            elif call_count[0] == 3:
                resp.text = json.dumps({"is_grounded_in_source": True, "has_single_takeaway": True, "free_of_filler_phrases": True, "concise_and_punchy": True})
            else:
                resp.text = json.dumps({"is_grounded_in_source": False, "has_single_takeaway": True, "free_of_filler_phrases": True, "concise_and_punchy": False})
            return resp

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = mock_generate

        verdict = compare_slides(slide_a, slide_b, source_text="Source data", client=mock_client)

        self.assertEqual(verdict.preferred_model, "model_a")
        self.assertFalse(verdict.position_bias_detected)
        self.assertEqual(verdict.score_a, 1.0)
        self.assertEqual(verdict.score_b, 0.5)

    def test_05_position_bias_mitigation_bias_detected_and_reconciled(self):
        """Verify that when forward and reverse passes suffer from primacy bias (always picking 1st), position_bias is flagged and reconciled."""
        slide_a = Slide(slide_number=1, layout_type="generic", title="Slide A")
        slide_b = Slide(slide_number=1, layout_type="generic", title="Slide B")

        call_count = [0]
        def mock_generate(*args, **kwargs):
            call_count[0] += 1
            resp = MagicMock()
            # Primacy bias: always picks candidate_1
            if call_count[0] == 1:
                resp.text = json.dumps({"preferred": "candidate_1", "reasoning": "First looked better."})
            elif call_count[0] == 2:
                resp.text = json.dumps({"preferred": "candidate_1", "reasoning": "First looked better."})
            # Independent evaluation: Model A scores 1.0, Model B scores 0.5
            elif call_count[0] in (3, 5):
                resp.text = json.dumps({"is_grounded_in_source": True, "has_single_takeaway": True, "free_of_filler_phrases": True, "concise_and_punchy": True})
            else:
                resp.text = json.dumps({"is_grounded_in_source": False, "has_single_takeaway": True, "free_of_filler_phrases": True, "concise_and_punchy": False})
            return resp

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = mock_generate

        verdict = compare_slides(slide_a, slide_b, source_text="Source data", client=mock_client)

        self.assertTrue(verdict.position_bias_detected)
        # Reconciled by checklist scores
        self.assertEqual(verdict.preferred_model, "model_a")
        self.assertIn("Positional bias detected", verdict.reasoning)

    def test_06_evaluate_deck_judge_aggregation(self):
        """Verify deck-level evaluation aggregates groundedness, punchiness, and overall judge score."""
        slides = [
            Slide(slide_number=1, layout_type="cover", title="Cover"),
            Slide(slide_number=2, layout_type="stat", title="Stat"),
            Slide(slide_number=3, layout_type="split", title="Split"),
        ]
        mp = MasterPlan(theme=self.theme, slides=slides)

        call_count = [0]
        def mock_generate(*args, **kwargs):
            call_count[0] += 1
            resp = MagicMock()
            if call_count[0] == 1:
                resp.text = json.dumps({"is_grounded_in_source": True, "has_single_takeaway": True, "free_of_filler_phrases": True, "concise_and_punchy": True})
            elif call_count[0] == 2:
                resp.text = json.dumps({"is_grounded_in_source": True, "has_single_takeaway": True, "free_of_filler_phrases": True, "concise_and_punchy": True})
            else:
                resp.text = json.dumps({"is_grounded_in_source": False, "has_single_takeaway": True, "free_of_filler_phrases": False, "concise_and_punchy": True})
            return resp

        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = mock_generate

        deck_eval = evaluate_deck_judge(mp, source_text="Source text", client=mock_client)

        self.assertEqual(deck_eval["slide_count"], 3)
        self.assertAlmostEqual(deck_eval["grounded_rate"], 2/3, places=2)
        self.assertAlmostEqual(deck_eval["filler_free_rate"], 2/3, places=2)
        self.assertEqual(deck_eval["single_takeaway_rate"], 1.0)
        self.assertEqual(deck_eval["punchy_rate"], 1.0)
        self.assertGreater(deck_eval["overall_judge_score"], 80.0)


if __name__ == "__main__":
    unittest.main()
