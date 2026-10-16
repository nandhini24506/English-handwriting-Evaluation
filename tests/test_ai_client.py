"""Automated unit tests for ai_client.py in EHE 2.0.

Tests response JSON parsing, markdown code block stripping,
missing metric detection, and hash-based caching without making paid API calls.
"""

import json
import pytest
from ai_client import (
    parse_and_validate_ai_response,
    evaluate_with_cache,
)


def test_parse_valid_json_response():
    sample_json = {
        "transcription": "The quick brown fox jumps over the lazy dog.",
        "metrics": {
            "letter_formation": {"score": 85, "explanation": "Consistent letter shapes.", "evidence": "Well formed loops."},
            "word_spacing": {"score": 80, "explanation": "Uniform gaps.", "evidence": "Standard spacing observed."},
            "alignment": {"score": 75, "explanation": "Good baseline.", "evidence": "Adheres to horizontal line."},
            "slant_consistency": {"score": 70, "explanation": "Slight forward slant.", "evidence": "Parallel strokes."},
            "size_consistency": {"score": 85, "explanation": "Uniform x-height.", "evidence": "Proportional capitals."},
            "legibility": {"score": 90, "explanation": "Clear readability.", "evidence": "Every letter is distinct."},
        },
        "overall_summary": "High quality handwriting sample.",
    }

    raw_text = json.dumps(sample_json)
    parsed = parse_and_validate_ai_response(raw_text)

    assert parsed["transcription"] == "The quick brown fox jumps over the lazy dog."
    assert parsed["metrics"]["letter_formation"]["score"] == 85.0
    assert parsed["metrics"]["legibility"]["score"] == 90.0


def test_parse_markdown_fenced_json():
    sample_json = {
        "transcription": "Practice makes progress.",
        "metrics": {
            "letter_formation": {"score": 75, "explanation": "OK", "evidence": "OK"},
            "word_spacing": {"score": 75, "explanation": "OK", "evidence": "OK"},
            "alignment": {"score": 75, "explanation": "OK", "evidence": "OK"},
            "slant_consistency": {"score": 75, "explanation": "OK", "evidence": "OK"},
            "size_consistency": {"score": 75, "explanation": "OK", "evidence": "OK"},
            "legibility": {"score": 75, "explanation": "OK", "evidence": "OK"},
        },
    }
    fenced_text = f"```json\n{json.dumps(sample_json)}\n```"
    parsed = parse_and_validate_ai_response(fenced_text)
    assert parsed["transcription"] == "Practice makes progress."
    assert parsed["metrics"]["letter_formation"]["score"] == 75.0


def test_missing_metric_in_ai_response_raises_error():
    incomplete_json = {
        "transcription": "Incomplete sample.",
        "metrics": {
            "letter_formation": {"score": 75, "explanation": "OK", "evidence": "OK"},
            "word_spacing": {"score": 75, "explanation": "OK", "evidence": "OK"},
        },
    }
    with pytest.raises(ValueError, match="missing evaluation metric"):
        parse_and_validate_ai_response(json.dumps(incomplete_json))


def test_empty_response_raises_error():
    with pytest.raises(ValueError, match="empty response"):
        parse_and_validate_ai_response("")


def test_caching_lookup_bypasses_api_call():
    """Verifies that when a hash is cached in the DB, it is immediately returned

    without making an external network request.
    """
    cached_data = {
        "transcription": "Cached text",
        "metrics": {
            "letter_formation": {"score": 90, "explanation": "Cached", "evidence": "Cached"},
            "word_spacing": {"score": 90, "explanation": "Cached", "evidence": "Cached"},
            "alignment": {"score": 90, "explanation": "Cached", "evidence": "Cached"},
            "slant_consistency": {"score": 90, "explanation": "Cached", "evidence": "Cached"},
            "size_consistency": {"score": 90, "explanation": "Cached", "evidence": "Cached"},
            "legibility": {"score": 90, "explanation": "Cached", "evidence": "Cached"},
        },
    }

    mock_lookup = lambda h: cached_data if h == "dummy_hash_123" else None
    mock_store = lambda h, data: None

    result = evaluate_with_cache(
        image_path="non_existent.jpg",
        image_hash="dummy_hash_123",
        db_lookup_fn=mock_lookup,
        db_store_fn=mock_store,
    )
    assert result["transcription"] == "Cached text"
