"""Automated unit tests for feedback.py and practice.py in EHE 2.0.

Tests metric weakness prioritization, actionable guidance generation,
and curriculum exercise mapping.
"""

from feedback import generate_feedback, identify_weakest_metric
from practice import get_recommended_exercises, get_all_practice_categories


def test_identify_weakest_metric():
    scores = {
        "letter_formation": 85.0,
        "word_spacing": 55.0,  # lowest
        "alignment": 70.0,
        "slant_consistency": 80.0,
        "size_consistency": 75.0,
        "legibility": 90.0,
    }
    weakest = identify_weakest_metric(scores)
    assert weakest["metric"] == "word_spacing"
    assert weakest["score"] == 55.0


def test_generate_feedback_prioritizes_weakest():
    scores = {
        "letter_formation": 50.0,  # critical focus (<60)
        "word_spacing": 70.0,       # needs improvement (<75)
        "alignment": 90.0,          # strong
        "slant_consistency": 90.0,
        "size_consistency": 90.0,
        "legibility": 90.0,
    }
    fb_items = generate_feedback(scores)
    assert len(fb_items) >= 2
    # First item should be the lowest (letter_formation)
    assert fb_items[0]["metric"] == "letter_formation"
    assert fb_items[0]["priority"] == "High"
    assert "Letter Formation Drills" in fb_items[0]["actionable_tip"] or len(fb_items[0]["actionable_tip"]) > 0


def test_get_recommended_exercises_mapping():
    ex_spacing = get_recommended_exercises("word_spacing")
    assert len(ex_spacing) >= 2
    assert "Spacing" in ex_spacing[0]["title"] or "Spacing" in ex_spacing[1]["title"]
    assert "target_text" in ex_spacing[0]
    assert "instructions" in ex_spacing[0]


def test_all_practice_categories_populated():
    cats = get_all_practice_categories()
    expected_metrics = [
        "letter_formation",
        "word_spacing",
        "alignment",
        "slant_consistency",
        "size_consistency",
        "legibility",
    ]
    for m in expected_metrics:
        assert m in cats
        assert len(cats[m]) >= 1
