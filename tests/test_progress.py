"""Automated unit tests for progress.py in EHE 2.0.

Tests progress calculation, improvement/decline delta tracking,
empty state handling, and metric averaging across historical records.
"""

from progress import calculate_progress_analytics


def test_calculate_progress_empty_records():
    analytics = calculate_progress_analytics([])
    assert analytics["has_data"] is False
    assert analytics["total_evaluations"] == 0
    assert analytics["latest_score"] is None


def test_calculate_progress_single_evaluation():
    single_eval = [
        {
            "id": 1,
            "overall_score": 75.0,
            "grade": "B",
            "letter_formation": 70,
            "word_spacing": 80,
            "alignment": 75,
            "slant_consistency": 70,
            "size_consistency": 80,
            "legibility": 75,
            "created_at": "2026-10-01 10:00:00",
        }
    ]
    analytics = calculate_progress_analytics(single_eval)
    assert analytics["has_data"] is True
    assert analytics["total_evaluations"] == 1
    assert analytics["latest_score"] == 75.0
    assert analytics["average_score"] == 75.0
    assert analytics["trend_direction"] == "first_assessment"


def test_calculate_progress_improving_trajectory():
    evals = [
        {
            "id": 1,
            "overall_score": 68.0,
            "grade": "C",
            "letter_formation": 65,
            "word_spacing": 70,
            "alignment": 68,
            "slant_consistency": 65,
            "size_consistency": 70,
            "legibility": 70,
            "created_at": "2026-10-01 10:00:00",
        },
        {
            "id": 2,
            "overall_score": 78.5,
            "grade": "B",
            "letter_formation": 75,
            "word_spacing": 80,
            "alignment": 80,
            "slant_consistency": 75,
            "size_consistency": 80,
            "legibility": 81,
            "created_at": "2026-10-05 10:00:00",
        },
    ]
    analytics = calculate_progress_analytics(evals)
    assert analytics["has_data"] is True
    assert analytics["total_evaluations"] == 2
    assert analytics["latest_score"] == 78.5
    assert analytics["delta"] == 10.5
    assert analytics["trend_direction"] == "improving"
    assert "+" in analytics["score_trend"]
