"""OCR module for EHE 2.0.

Provides a dedicated text-recognition interface:
  - Invokes the shared AI client for transcription
  - Preserves exact raw transcriptions including [unclear] tags
  - Calculates confidence and word counts
  - Manages student/teacher OCR correction submissions separately from raw AI transcription
"""

import re
from typing import Dict, Any, Optional


def process_ocr_result(raw_text: str) -> Dict[str, Any]:
    """Processes raw OCR transcription and extracts readable metrics."""
    cleaned = (raw_text or "").strip()
    words = re.findall(r"\b\w+\b", cleaned)
    unclear_count = len(re.findall(r"\[unclear\]", cleaned, re.IGNORECASE))
    total_token_count = len(words) + unclear_count

    # Confidence calculation based on ratio of recognized words vs unclear markers
    if total_token_count > 0:
        recognized_ratio = len(words) / float(total_token_count)
        if recognized_ratio >= 0.90:
            confidence = "High"
        elif recognized_ratio >= 0.65:
            confidence = "Moderate"
        else:
            confidence = "Low"
    else:
        confidence = "Low"

    return {
        "raw_text": cleaned,
        "word_count": len(words),
        "unclear_count": unclear_count,
        "confidence": confidence,
        "is_empty": len(cleaned) == 0,
    }


def record_ocr_correction(
    evaluation_id: int,
    user_id: int,
    original_text: str,
    corrected_text: str,
    save_fn=None,
) -> Dict[str, Any]:
    """Records a user-submitted OCR correction without overwriting the original AI transcription.

    Distinguishes OCR transcription errors from handwriting quality scores.
    """
    if not corrected_text or not corrected_text.strip():
        raise ValueError("Corrected text cannot be blank.")

    cleaned_correction = corrected_text.strip()
    if cleaned_correction == original_text.strip():
        raise ValueError("Corrected text is identical to the original transcription.")

    record = {
        "evaluation_id": evaluation_id,
        "user_id": user_id,
        "original_text": original_text,
        "corrected_text": cleaned_correction,
    }

    if save_fn:
        correction_id = save_fn(
            evaluation_id=evaluation_id,
            user_id=user_id,
            original_text=original_text,
            corrected_text=cleaned_correction,
        )
        record["id"] = correction_id

    return record
