"""Deterministic Python scoring module for EHE 2.0.

Implements the official 6-characteristic weighted scoring rubric and
letter-grade determination.
"""

from typing import Dict, Any, List

# Metric weights defined by specification (total: 100%)
METRIC_WEIGHTS: Dict[str, float] = {
    "letter_formation": 0.20,
    "word_spacing": 0.20,
    "alignment": 0.20,
    "slant_consistency": 0.15,
    "size_consistency": 0.10,
    "legibility": 0.15,
}

METRIC_LABELS: Dict[str, str] = {
    "letter_formation": "Letter Formation",
    "word_spacing": "Word Spacing",
    "alignment": "Alignment",
    "slant_consistency": "Slant Consistency",
    "size_consistency": "Size Consistency",
    "legibility": "Legibility",
}

# Configurable Grade Boundaries
GRADE_BOUNDARIES = [
    (90.0, "A+"),
    (80.0, "A"),
    (70.0, "B"),
    (60.0, "C"),
    (50.0, "D"),
]
DEFAULT_FAIL_GRADE = "F"


def validate_scores(scores: Dict[str, Any]) -> Dict[str, float]:
    """Validates that all 6 required scores exist, are finite numbers,

    and fall strictly in the range [0.0, 100.0].
    """
    if not isinstance(scores, dict):
        raise TypeError("Scores payload must be a dictionary.")

    validated: Dict[str, float] = {}
    for metric in METRIC_WEIGHTS:
        if metric not in scores:
            raise ValueError(f"Missing required score metric: '{metric}'.")

        raw_val = scores[metric]
        try:
            val = float(raw_val)
        except (TypeError, ValueError) as err:
            raise ValueError(f"Invalid non-numeric score for '{metric}': {raw_val}") from err

        # Check for NaN or Inf
        if val != val or val == float("inf") or val == float("-inf"):
            raise ValueError(f"Score for '{metric}' must be a finite number: {val}")

        if val < 0.0 or val > 100.0:
            raise ValueError(f"Score for '{metric}' must be between 0 and 100: got {val}")

        validated[metric] = round(val, 2)

    return validated


def calculate_score(scores: Dict[str, Any]) -> float:
    """Calculates deterministic weighted overall score locally in Python.

    Formula:
      letter_formation * 0.20 +
      word_spacing * 0.20 +
      alignment * 0.20 +
      slant_consistency * 0.15 +
      size_consistency * 0.10 +
      legibility * 0.15
    """
    valid = validate_scores(scores)
    total = sum(valid[m] * METRIC_WEIGHTS[m] for m in METRIC_WEIGHTS)
    return round(total, 2)


def calculate_grade(score: float) -> str:
    """Determines letter grade from the overall score using documented thresholds."""
    if not isinstance(score, (int, float)):
        raise TypeError("Overall score must be a number.")
    if score != score or score == float("inf") or score == float("-inf"):
        raise ValueError("Overall score must be a finite number.")

    for threshold, grade in GRADE_BOUNDARIES:
        if score >= threshold:
            return grade
    return DEFAULT_FAIL_GRADE


def get_score_breakdown(scores: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Returns a structured breakdown of each metric with its weight, score,

    and contribution to the final overall score.
    """
    valid = validate_scores(scores)
    breakdown = []
    for metric, weight in METRIC_WEIGHTS.items():
        score_val = valid[metric]
        contribution = round(score_val * weight, 2)
        breakdown.append({
            "key": metric,
            "label": METRIC_LABELS[metric],
            "weight": weight,
            "weight_percent": int(weight * 100),
            "score": score_val,
            "weighted_score": contribution,
        })
    return breakdown
