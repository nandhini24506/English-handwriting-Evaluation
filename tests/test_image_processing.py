"""Automated unit tests for image_processing.py in EHE 2.0.

Tests OpenCV computer vision feature extraction:
sharpness, baseline regression, word spacing, slant, and stroke density.
"""

import os
import tempfile
import cv2
import numpy as np
import pytest
from image_processing import (
    analyze_image_quality,
    binarize_for_analysis,
    analyze_baseline_alignment,
    analyze_spacing_consistency,
    analyze_character_size_consistency,
    analyze_slant_consistency,
    analyze_stroke_density,
    extract_cv_features,
    process_image,
)


@pytest.fixture
def sample_handwriting_image():
    """Generates a synthetic handwriting-like image with ruled lines and text strokes."""
    # 600x400 white canvas
    img = np.ones((400, 600, 3), dtype=np.uint8) * 255

    # Draw lines of text-like strokes (black ink)
    for y_base in [120, 200, 280]:
        for x_word in range(60, 500, 80):
            # Draw pseudo letters
            cv2.putText(
                img,
                "text",
                (x_word, y_base),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (20, 20, 20),
                2,
                cv2.LINE_AA,
            )

    fd, path = tempfile.mkstemp(suffix=".jpg")
    os.close(fd)
    cv2.imwrite(path, img)
    yield path

    if os.path.exists(path):
        os.remove(path)
    processed = os.path.splitext(path)[0] + "_processed.jpg"
    if os.path.exists(processed):
        os.remove(processed)


def test_image_quality_sharpness(sample_handwriting_image):
    gray = cv2.imread(sample_handwriting_image, cv2.IMREAD_GRAYSCALE)
    quality = analyze_image_quality(gray)
    assert "sharpness_score" in quality
    assert quality["is_readable"] is True
    assert quality["sharpness_rating"] in ["Moderate", "Sharp"]


def test_binarization(sample_handwriting_image):
    gray = cv2.imread(sample_handwriting_image, cv2.IMREAD_GRAYSCALE)
    binary = binarize_for_analysis(gray)
    # Check that ink exists as foreground (non-zero)
    assert np.count_nonzero(binary) > 0


def test_baseline_alignment(sample_handwriting_image):
    gray = cv2.imread(sample_handwriting_image, cv2.IMREAD_GRAYSCALE)
    binary = binarize_for_analysis(gray)
    baseline = analyze_baseline_alignment(binary)
    assert "status" in baseline
    assert baseline["status"] in ["ok", "limited"]
    if baseline["status"] == "ok":
        assert "measured_slope_deg" in baseline
        assert abs(baseline["measured_slope_deg"]) < 15.0  # roughly horizontal


def test_process_image_creates_processed_file(sample_handwriting_image):
    processed_path = process_image(sample_handwriting_image)
    assert os.path.exists(processed_path)
    assert processed_path.endswith("_processed.jpg")


def test_extract_cv_features_comprehensive(sample_handwriting_image):
    features = extract_cv_features(sample_handwriting_image)
    assert "image_quality" in features
    assert "baseline_alignment" in features
    assert "word_spacing" in features
    assert "size_consistency" in features
    assert "slant_consistency" in features
    assert "stroke_density" in features
