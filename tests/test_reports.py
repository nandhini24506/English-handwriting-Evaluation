"""Automated unit tests for reports.py in EHE 2.0.

Tests ReportLab PDF document compilation and header verification.
"""

from reports import generate_pdf_report


def test_generate_pdf_report_valid_bytes():
    eval_dict = {
        "id": 101,
        "overall_score": 84.5,
        "grade": "A",
        "extracted_text": "Sample handwriting evaluation text.",
        "letter_formation": 85.0,
        "word_spacing": 80.0,
        "alignment": 90.0,
        "slant_consistency": 82.0,
        "size_consistency": 85.0,
        "legibility": 85.0,
        "created_at": "2026-10-10 14:30:00",
    }
    feedback_items = [
        {
            "metric_label": "Slant Consistency",
            "actionable_tip": "Keep parallel tilt.",
            "recommended_exercise": "Practice hatch marks.",
        }
    ]

    pdf_bytes = generate_pdf_report(
        evaluation=eval_dict,
        student_name="Deepak Kumar",
        feedback_items=feedback_items,
        image_full_path=None,
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    # PDF files must start with the %PDF- header magic bytes
    assert pdf_bytes.startswith(b"%PDF-")
