"""
test_operating_review_pilot.py — Verification of the 2-period Operating Review pilot fixtures.

Tests:
1. Deterministic comparison engine across prior & current reporting periods.
2. Exact retention math (-13 percentage points vs -9.7%).
3. True zero vs missing value preservation.
4. Definition version shift detection.
5. Damaged slide failure conditions.
"""

import os
import csv
import json
import pytest
from pathlib import Path
from ppt_maker.core.evidence import ClaimRecord, compare_periods, calculate_rate_variance


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "operating_review"


def load_csv_claims(csv_path: Path) -> list:
    claims = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            claims.append(ClaimRecord(
                claim_id=row["metric_id"],
                entity=row["metric_id"].replace("_", " ").title(),
                period=row["period"],
                raw_value=row["value"],
                numeric_value=float(row["numeric_value"]),
                unit=row["unit"],
                definition_version=row["definition_version"],
                source_locator=row["source_ref"]
            ))
    return claims


def test_operating_review_two_period_comparison():
    """Verify that compare_periods accurately computes deltas from the canonical fixture CSVs."""
    prior = load_csv_claims(FIXTURE_DIR / "prior_period_metrics.csv")
    current = load_csv_claims(FIXTURE_DIR / "current_period_metrics.csv")

    with open(FIXTURE_DIR / "answer_key.json", "r", encoding="utf-8") as f:
        answer_key = json.load(f)["expected_deltas"]

    results = compare_periods(prior, current)
    result_map = {r["claim_id"]: r for r in results}

    # 1. Verify Net Dollar Retention (NDR) math:
    ndr = result_map["ndr"]
    assert ndr["numeric_delta"] == -13.0
    # Must be "percentage points", NEVER percent:
    assert ndr["delta_formatted"] == "-13.0 percentage points"
    assert "-9.7%" not in ndr["delta_formatted"]
    assert ndr["direction"] == "down"

    # 2. Verify Incident Count (True zero):
    incidents = result_map["incidents"]
    assert incidents["current_value"] == 0.0
    assert incidents["is_zero"] is True
    assert incidents["numeric_delta"] == -2.0
    assert incidents["direction"] == "down"

    # 3. Verify Definition Shift (APAC expansion):
    apac = result_map["apac_expansion"]
    assert apac["definition_shifted"] is True
    assert "Comparability Break" in apac["comparability_warning"]

    # 4. Verify ARR Percentage Growth:
    arr = result_map["arr"]
    assert round(arr["numeric_delta"], 1) == 2.2
    assert arr["delta_formatted"] == "+18.3%"
    assert arr["direction"] == "up"

    # 5. Verify New Metric Handling:
    new_m = result_map["new_initiative_pilot"]
    assert new_m["status"] == "new_metric"
    assert new_m["delta_formatted"] == "NEW_METRIC"


def test_rate_variance_percentage_points_rule():
    """Explicitly verify that calculate_rate_variance enforces percentage points for rate units."""
    # Percentage rate comparison: 134% -> 121%
    diff, delta_str = calculate_rate_variance(134.0, 121.0, "percentage")
    assert diff == -13.0
    assert delta_str == "-13.0 percentage points"

    # Percentage rate comparison: 76% -> 78.5%
    diff, delta_str = calculate_rate_variance(76.0, 78.5, "%")
    assert diff == 2.5
    assert delta_str == "+2.5 percentage points"

    # Currency comparison: $12M -> $14.2M
    diff, delta_str = calculate_rate_variance(12.0, 14.2, "USD_M")
    assert round(diff, 1) == 2.2
    assert delta_str == "+18.3%"


def test_damaged_slide_white_on_white_fails_contrast_rule():
    """Verify that white text on white background yields contrast ratio 1.0 (violating 4.5/7.0)."""
    from ppt_maker.core.evidence import calculate_relative_luminance_contrast

    # White on white: #FFFFFF on #FFFFFF
    ratio = calculate_relative_luminance_contrast("#FFFFFF", "#FFFFFF")
    assert ratio == 1.0
    # Must fail both body (7.0) and headline (4.5) thresholds
    assert ratio < 4.5, "White on white passed contrast threshold!"
    assert ratio < 7.0, "White on white passed body contrast threshold!"


def test_damaged_slide_empty_kpi_card_fails_validation(capsys):
    """Verify that an empty KPI card with blank/whitespace value triggers a validator warning."""
    from ppt_maker.planning.validator import ContentValidator
    from ppt_maker.core.schemas import MasterPlan, Slide, Theme, KPIBlock, KPICard

    empty_kpi = KPIBlock(cards=[
        KPICard(badge="REVENUE", value="", label="ARR Target", delta=""),
    ])
    slide = Slide(
        slide_number=1,
        layout_type="kpi_dashboard",
        title="Empty Card Test",
        content_blocks=[empty_kpi]
    )
    plan = MasterPlan(
        deck_title="Test Plan",
        slides=[slide],
        theme=Theme(structural_class="corporate_clean")
    )

    ContentValidator.validate_and_prune(plan)
    captured = capsys.readouterr().out
    assert "empty value" in captured.lower() or "empty" in captured.lower(), \
        f"Empty KPI card did not trigger warning in validator output: {captured}"
