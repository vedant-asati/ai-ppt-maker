"""
evidence.py — Evidentiary data structures and deterministic period comparison engine.

Implements typed ClaimRecord and mathematical variance calculation for recurring
monthly operating reviews, enforcing zero-hallucination policies and strict
distinction between percentage points and percent change.
"""

from typing import List, Dict, Any, Optional, Tuple, Literal
from pydantic import BaseModel, Field


class ClaimRecord(BaseModel):
    """
    A typed, auditable factual claim bound to a specific entity, period, and source locator.
    """
    claim_id: str = Field(description="Unique persistent slug, e.g. clm_q3_ndr_01")
    entity: str = Field(description="Normalized business entity, e.g. Net Dollar Retention")
    period: str = Field(description="Reporting period, e.g. Q3 2026")
    raw_value: str = Field(description="Literal string representation, e.g. 121%")
    numeric_value: float = Field(description="Clean numeric value for mathematical verification, e.g. 121.0")
    unit: str = Field(description="Canonical unit: USD, percentage, percentage_points, count, ratio")
    denominator: Optional[str] = Field(default=None, description="Base population or timeframe")
    direction: Literal['up', 'down', 'flat', 'unspecified'] = 'unspecified'
    is_forecast: bool = Field(default=False, description="False = actual; True = forward projection")
    definition_version: str = Field(default="1.0", description="Schema/accounting definition version")
    source_locator: str = Field(default="", description="Document citation locator, e.g. table_arr_01")
    source_span: str = Field(default="", description="Verbatim snippet supporting this claim")
    approval_status: Literal['approved', 'provisional', 'contradicted', 'unresolved'] = 'provisional'


def calculate_rate_variance(prior_val: float, current_val: float, unit: str) -> Tuple[float, str]:
    """
    Computes mathematical variance between prior and current values.
    
    CRITICAL RULE (Review #04):
    When comparing percentage rates (e.g. 134% -> 121%), the difference is in
    PERCENTAGE POINTS (e.g. -13.0 percentage points), NEVER percent (-9.7%)!
    """
    diff = round(current_val - prior_val, 4)
    sign = "+" if diff > 0 else ""

    if unit.lower() in {'percentage', '%', 'pct', 'rate', 'percentage_points'}:
        formatted_delta = f"{sign}{diff:.1f} percentage points"
        return diff, formatted_delta
    else:
        if prior_val != 0:
            pct_change = round((diff / abs(prior_val)) * 100.0, 1)
            formatted_delta = f"{sign}{pct_change:.1f}%"
        else:
            formatted_delta = f"{sign}{diff:.1f}"
        return diff, formatted_delta


def calculate_relative_luminance_contrast(fg_hex: str, bg_hex: str) -> float:
    """
    Computes WCAG 2.1 relative luminance contrast ratio between two hex colors.
    Returns contrast ratio in range [1.0, 21.0].
    """
    def _hex_to_rgb(hex_str: str) -> Tuple[float, float, float]:
        hex_str = hex_str.lstrip("#")
        if len(hex_str) == 3:
            hex_str = "".join([c * 2 for c in hex_str])
        r = int(hex_str[0:2], 16) / 255.0
        g = int(hex_str[2:4], 16) / 255.0
        b = int(hex_str[4:6], 16) / 255.0
        return r, g, b

    def _channel_luminance(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r1, g1, b1 = _hex_to_rgb(fg_hex)
    r2, g2, b2 = _hex_to_rgb(bg_hex)

    l1 = 0.2126 * _channel_luminance(r1) + 0.7152 * _channel_luminance(g1) + 0.0722 * _channel_luminance(b1)
    l2 = 0.2126 * _channel_luminance(r2) + 0.7152 * _channel_luminance(g2) + 0.0722 * _channel_luminance(b2)

    brightest = max(l1, l2)
    darkest = min(l1, l2)
    return round((brightest + 0.05) / (darkest + 0.05), 2)


def compare_periods(
    prior_records: List[ClaimRecord],
    current_records: List[ClaimRecord]
) -> List[Dict[str, Any]]:
    """
    Performs deterministic period-over-period comparison across matched metric IDs.
    
    Enforces:
    1. Precision retention math (percentage points).
    2. Comparability break flags when definition_version changes.
    3. Explicit zero vs missing distinction.
    4. Sourced delta calculation without model guesswork.
    """
    prior_map = {r.claim_id: r for r in prior_records}
    current_map = {r.claim_id: r for r in current_records}
    all_keys = list(dict.fromkeys(list(prior_map.keys()) + list(current_map.keys())))

    comparisons = []
    for key in all_keys:
        prior = prior_map.get(key)
        current = current_map.get(key)

        if prior and current:
            # Check unit compatibility
            if prior.unit.lower() != current.unit.lower():
                comparisons.append({
                    "claim_id": key,
                    "entity": current.entity,
                    "error": f"Incompatible units: prior={prior.unit}, current={current.unit}",
                    "comparable": False,
                    "status": "incompatible_units"
                })
                continue

            # Check definition version comparability
            definition_shifted = prior.definition_version != current.definition_version

            diff_val, delta_str = calculate_rate_variance(
                prior.numeric_value,
                current.numeric_value,
                current.unit
            )

            # Determine direction
            if diff_val > 0:
                direction = "up"
            elif diff_val < 0:
                direction = "down"
            else:
                direction = "flat"

            comparisons.append({
                "claim_id": key,
                "entity": current.entity,
                "prior_period": prior.period,
                "prior_value": prior.numeric_value,
                "prior_raw": prior.raw_value,
                "current_period": current.period,
                "current_value": current.numeric_value,
                "current_raw": current.raw_value,
                "unit": current.unit,
                "numeric_delta": diff_val,
                "delta_formatted": delta_str,
                "direction": direction,
                "definition_shifted": definition_shifted,
                "comparability_warning": (
                    f"Comparability Break: definition changed from {prior.definition_version} to {current.definition_version}"
                    if definition_shifted else None
                ),
                "is_zero": (current.numeric_value == 0.0),
                "status": "compared"
            })
        elif prior and not current:
            comparisons.append({
                "claim_id": key,
                "entity": prior.entity,
                "prior_period": prior.period,
                "prior_value": prior.numeric_value,
                "prior_raw": prior.raw_value,
                "current_period": None,
                "current_value": None,
                "current_raw": "—",
                "unit": prior.unit,
                "delta_formatted": "UNAVAILABLE",
                "status": "missing_current"
            })
        elif current and not prior:
            comparisons.append({
                "claim_id": key,
                "entity": current.entity,
                "prior_period": None,
                "prior_value": None,
                "prior_raw": "—",
                "current_period": current.period,
                "current_value": current.numeric_value,
                "current_raw": current.raw_value,
                "unit": current.unit,
                "delta_formatted": "NEW_METRIC",
                "status": "new_metric"
            })

    return comparisons
