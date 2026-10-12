"""Handwriting evaluation orchestration module for EHE 2.0.

Integrates multimodal AI qualitative assessment with computer-vision
measurements, enforcing the structured output contract for the six
handwriting characteristics:
  1. Letter formation
  2. Word spacing
  3. Alignment
  4. Slant consistency
  5. Size consistency
  6. Legibility

Maintains strict separation between:
  - Computer vision measured features
  - AI visual assessments
  - Python-computed deterministic rubric score
"""

from typing import Dict, Any, Optional
from scoring import validate_scores, calculate_score, calculate_grade, get_score_breakdown
from image_processing import extract_cv_features
from ai_client import evaluate_with_cache, call_nvidia_multimodal_api

REQUIRED_CHARACTERISTICS = [
    "letter_formation",
    "word_spacing",
    "alignment",
    "slant_consistency",
    "size_consistency",
    "legibility",
]


def evaluate_handwriting_bundle(
    image_path: str,
    image_hash: str,
    db_lookup_fn=None,
    db_store_fn=None,
) -> Dict[str, Any]:
    """Coordinates computer-vision analysis and AI qualitative assessment.

    Returns the unified evaluation bundle with deterministic scoring and grades.
    """
    # 1. Real Computer Vision Analysis (independent of AI)
    cv_features = extract_cv_features(image_path)

    # 2. Multimodal AI Analysis (with SHA-256 caching)
    ai_result = evaluate_with_cache(
        image_path=image_path,
        image_hash=image_hash,
        db_lookup_fn=db_lookup_fn,
        db_store_fn=db_store_fn,
    )

    # 3. Extract and validate component scores
    raw_scores = {metric: ai_result["metrics"][metric]["score"] for metric in REQUIRED_CHARACTERISTICS}
    validated_scores = validate_scores(raw_scores)

    # 4. Deterministic Python Scoring
    overall_score = calculate_score(validated_scores)
    grade = calculate_grade(overall_score)
    score_breakdown = get_score_breakdown(validated_scores)

    # Build metric details combining AI qualitative feedback and confidence
    metric_details = {}
    for metric in REQUIRED_CHARACTERISTICS:
        ai_metric = ai_result["metrics"][metric]
        metric_details[metric] = {
            "score": validated_scores[metric],
            "explanation": ai_metric["explanation"],
            "evidence": ai_metric["evidence"],
        }

    return {
        "transcription": ai_result.get("transcription", ""),
        "scores": validated_scores,
        "overall_score": overall_score,
        "grade": grade,
        "score_breakdown": score_breakdown,
        "metric_details": metric_details,
        "cv_features": cv_features,
        "overall_summary": ai_result.get("overall_summary", ""),
    }
