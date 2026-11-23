"""
test_compare_pipelines.py — Unit tests for the Multi-Agent vs Single-Shot comparative benchmark harness.
"""

import pytest
from evals.compare_pipelines import PipelineBenchmark, create_scenario_config, create_synthetic_multi_agent_plan


def test_scenario_config_creation():
    scenario = {
        "id": "test_scenario",
        "title": "Quantum Computing Frontiers",
        "topic": "Overview of Quantum Advantage",
        "source_text": "Quantum computers leverage superposition and entanglement to solve specific problems exponentially faster.",
        "target_audience": "Engineers and Physicists",
        "expected_slides_range": [4, 6],
        "suggested_theme": {"structural_class": "slidesgo_dark_tech"}
    }
    config = create_scenario_config(scenario)
    assert config["source_text"] == scenario["source_text"]
    assert config["presentation_goals"]["slide_count"] == 4
    assert config["design_preferences"]["theme_style"] == "slidesgo_dark_tech"


def test_synthetic_multi_agent_plan_structure():
    scenario = {
        "id": "test_scenario",
        "title": "Executive AI Strategy",
        "topic": "Scaling Enterprise AI Workflows",
        "category": "executive",
        "expected_slides_range": [5, 6],
        "suggested_theme": {"structural_class": "slidesgo_minimalist_business"}
    }
    plan = create_synthetic_multi_agent_plan(scenario)
    assert len(plan.slides) == 5
    layout_types = [s.layout_type for s in plan.slides]
    assert "cover" in layout_types
    assert "bento" in layout_types
    assert "kpi_dashboard" in layout_types
    assert "roadmap_chain" in layout_types
    assert "editorial" in layout_types


def test_pipeline_benchmark_offline_run():
    bench = PipelineBenchmark(run_live=False)
    scenario = {
        "id": "mock_saas",
        "title": "Enterprise Cloud Migration",
        "topic": "Moving Core Infrastructure to Kubernetes",
        "source_text": "Legacy monoliths are slow to deploy and costly to maintain. Kubernetes provides horizontal pod autoscaling.",
        "category": "technical",
        "expected_slides_range": [4, 5]
    }
    result = bench.benchmark_scenario(scenario)
    assert result["id"] == "mock_saas"
    assert "single" in result
    assert "multi" in result
    assert result["single"]["composite"] > 0
    assert result["multi"]["composite"] > 0
    assert result["winner"] in ("Multi-Agent", "Single-Shot", "Tie")

