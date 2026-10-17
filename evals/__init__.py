"""
evals — Systematic GenAI Evaluation Framework for AI Presentation Agency.
"""

from evals.metrics import (
    calc_dom_overflow_rate,
    calc_layout_monotony,
    calc_word_density,
    calc_content_block_diversity,
    calc_system_telemetry,
    evaluate_master_plan_deterministic,
)

__all__ = [
    "calc_dom_overflow_rate",
    "calc_layout_monotony",
    "calc_word_density",
    "calc_content_block_diversity",
    "calc_system_telemetry",
    "evaluate_master_plan_deterministic",
]
