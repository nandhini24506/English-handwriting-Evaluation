"""Automated unit tests for scoring.py in EHE 2.0.

Tests weighted calculation, grade boundaries, non-finite handling, and validation.
"""

import math
import pytest
from scoring import (
    calculate_score,
    calculate_grade,
    validate_scores,
    get_score_breakdown,
    METRIC_WEIGHTS,
)


def test_metric_weights_sum_to_one():
    """Validates that all rubric weights total exactly 1.0 (100%)."""
    total = sum(METRIC_WEIGHTS.values())
    assert math.isclose(total, 1.0, rel_tol=1e-5), f"Weights sum to {total}, expected 1.0"


def test_calculate_score_perfect():
    """All 100s should yield a perfect 100.0 overall score."""
    scores = {
        "letter_formation": 100,
        "word_spacing": 100,
        "alignment": 100,
        "slant_consistency": 100,
        "size_consistency": 100,
        "legibility": 100,
    }
    assert calculate_score(scores) == 100.0
    assert calculate_grade(100.0) == "A+"


def test_calculate_score_weighted_known():
    """Tests known weighted formula result."""
    # 80*0.2 + 90*0.2 + 70*0.2 + 60*0.15 + 85*0.10 + 75*0.15
    # = 16 + 18 + 14 + 9 + 8.5 + 11.25 = 76.75
    scores = {
        "letter_formation": 80,
        "word_spacing": 90,
        "alignment": 70,
        "slant_consistency": 60,
        "size_consistency": 85,
        "legibility": 75,
    }
    result = calculate_score(scores)
    assert result == 76.75
    assert calculate_grade(result) == "B"


def test_grade_boundaries():
    """Tests all documented grade thresholds."""
    assert calculate_grade(95.0) == "A+"
    assert calculate_grade(90.0) == "A+"
    assert calculate_grade(89.99) == "A"
    assert calculate_grade(80.0) == "A"
    assert calculate_grade(79.99) == "B"
    assert calculate_grade(70.0) == "B"
    assert calculate_grade(69.99) == "C"
    assert calculate_grade(60.0) == "C"
    assert calculate_grade(59.99) == "D"
    assert calculate_grade(50.0) == "D"
    assert calculate_grade(49.99) == "F"
    assert calculate_grade(0.0) == "F"


def test_missing_metric_raises_value_error():
    """Missing any required metric must explicitly raise ValueError."""
    incomplete = {
        "letter_formation": 80,
        "word_spacing": 90,
        "alignment": 70,
    }
    with pytest.raises(ValueError, match="Missing required score metric"):
        calculate_score(incomplete)


def test_non_finite_scores_raise_value_error():
    """NaN or Inf scores must be rejected explicitly."""
    nan_scores = {
        "letter_formation": float("nan"),
        "word_spacing": 90,
        "alignment": 70,
        "slant_consistency": 60,
        "size_consistency": 85,
        "legibility": 75,
    }
    with pytest.raises(ValueError, match="finite number"):
        validate_scores(nan_scores)


def test_out_of_range_scores_raise_value_error():
    """Scores < 0 or > 100 must be rejected."""
    high_scores = {
        "letter_formation": 120,
        "word_spacing": 90,
        "alignment": 70,
        "slant_consistency": 60,
        "size_consistency": 85,
        "legibility": 75,
    }
    with pytest.raises(ValueError, match="between 0 and 100"):
        validate_scores(high_scores)


def test_get_score_breakdown():
    """Validates structured breakdown elements."""
    scores = {
        "letter_formation": 80,
        "word_spacing": 90,
        "alignment": 70,
        "slant_consistency": 60,
        "size_consistency": 85,
        "legibility": 75,
    }
    breakdown = get_score_breakdown(scores)
    assert len(breakdown) == 6
    assert breakdown[0]["key"] == "letter_formation"
    assert breakdown[0]["weight_percent"] == 20
    assert breakdown[0]["weighted_score"] == 16.0
