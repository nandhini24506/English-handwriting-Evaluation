"""Computer vision preprocessing and feature extraction module for EHE 2.0.

Provides real computer-vision analysis:
  1. Image quality & illumination (sharpness via Laplacian variance, brightness, contrast)
  2. Baseline alignment & line tilt via linear regression on line contours
  3. Word and character spacing consistency via morphological segmentation
  4. Character height & size consistency via connected component analysis
  5. Dominant handwriting slant via vertical projection shear analysis
  6. Stroke density and estimated stroke thickness via distance transform

Each metric returns clear measured values, confidence indicators, and
explicit failure/limitation explanations when lines or words cannot be segmented.
"""

import math
import os
from typing import Dict, Any, List, Tuple
import cv2
import numpy as np
from PIL import Image, ImageOps


def process_image(image_path: str) -> str:
    """Corrects EXIF orientation, validates dimensions, and creates a preprocessed

    analysis-ready copy without destroying fine handwriting strokes.
    """
    if not os.path.exists(image_path):
        raise ValueError(f"Image file does not exist: {image_path}")

    # 1. Correct EXIF orientation using Pillow
    with Image.open(image_path) as pil_img:
        pil_img = ImageOps.exif_transpose(pil_img)
        # Convert to RGB if palette or alpha
        if pil_img.mode != "RGB":
            pil_img = pil_img.convert("RGB")
        img_np = np.array(pil_img)

    # Convert RGB to BGR for OpenCV
    image = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)

    height, width = image.shape[:2]
    largest_side = max(height, width)

    # Resize oversized images proportionally to 1800px on the longest side
    if largest_side > 1800:
        scale = 1800.0 / largest_side
        new_w = int(round(width * scale))
        new_h = int(round(height * scale))
        image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # Create processed copy: subtle illumination leveling via CLAHE on L channel
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced_l = clahe.apply(l_channel)
    merged_lab = cv2.merge((enhanced_l, a_channel, b_channel))
    processed_bgr = cv2.cvtColor(merged_lab, cv2.COLOR_LAB2BGR)

    processed_path = os.path.splitext(image_path)[0] + "_processed.jpg"
    if not cv2.imwrite(processed_path, processed_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 92]):
        raise ValueError("Failed to save the preprocessed image.")

    return processed_path


def analyze_image_quality(gray: np.ndarray) -> Dict[str, Any]:
    """Measures image sharpness (Laplacian variance), illumination, and contrast."""
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    mean_brightness = float(np.mean(gray))
    std_contrast = float(np.std(gray))

    # Sharpness assessment
    if laplacian_var < 75.0:
        sharpness_rating = "Blurry"
        sharpness_flag = "Low sharpness; fine stroke edges may appear fuzzy."
    elif laplacian_var < 200.0:
        sharpness_rating = "Moderate"
        sharpness_flag = "Acceptable sharpness for handwriting inspection."
    else:
        sharpness_rating = "Sharp"
        sharpness_flag = "Crisp, distinct stroke boundaries."

    # Illumination assessment
    if mean_brightness < 50.0:
        lighting_rating = "Under-exposed"
    elif mean_brightness > 250.0:
        lighting_rating = "Over-exposed"
    else:
        lighting_rating = "Well-lit"

    # Contrast assessment
    if std_contrast < 20.0:
        contrast_rating = "Low"
    else:
        contrast_rating = "Good"

    is_readable = bool(laplacian_var >= 30.0 and 25.0 <= mean_brightness <= 253.0)

    return {
        "sharpness_score": round(laplacian_var, 1),
        "sharpness_rating": sharpness_rating,
        "sharpness_note": sharpness_flag,
        "mean_brightness": round(mean_brightness, 1),
        "lighting_rating": lighting_rating,
        "contrast_std": round(std_contrast, 1),
        "contrast_rating": contrast_rating,
        "is_readable": is_readable,
    }


def binarize_for_analysis(gray: np.ndarray) -> np.ndarray:
    """Produces clean inverted binary image where foreground strokes = 255

    and background paper = 0.
    """
    # Gaussian blur to suppress fine paper texture
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    # Otsu thresholding with inversion
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return binary


def analyze_baseline_alignment(binary: np.ndarray) -> Dict[str, Any]:
    """Measures writing baseline alignment using horizontal projection and linear regression.

    Returns baseline angle (degrees), deviation, and confidence.
    """
    h, w = binary.shape[:2]
    # Find contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    letter_boxes = []

    for c in contours:
        x, y, bw, bh = cv2.boundingRect(c)
        area = cv2.contourArea(c)
        # Filter tiny specks and huge page-spanning contours
        if 20 < area < (w * h * 0.15) and 8 < bh < (h * 0.4):
            letter_boxes.append((x, y, bw, bh, y + bh))  # store baseline y (y + bh)

    if len(letter_boxes) < 6:
        return {
            "status": "limited",
            "measured_slope_deg": 0.0,
            "baseline_stability_score": None,
            "explanation": "Insufficient isolated letter components detected to calculate reliable baseline regression.",
            "confidence": "Low",
        }

    # Group components into rough line bands based on y-coordinates
    letter_boxes.sort(key=lambda b: b[1])
    lines: List[List[Tuple[int, int, int, int, int]]] = []
    current_line = [letter_boxes[0]]

    for box in letter_boxes[1:]:
        prev_box = current_line[-1]
        # Overlap in y-range?
        if abs(box[1] - prev_box[1]) < (prev_box[3] * 0.75):
            current_line.append(box)
        else:
            if len(current_line) >= 4:
                lines.append(current_line)
            current_line = [box]

    if len(current_line) >= 4:
        lines.append(current_line)

    if not lines:
        return {
            "status": "limited",
            "measured_slope_deg": 0.0,
            "baseline_stability_score": None,
            "explanation": "Text could not be segmented into distinct lines. Writing may be single-line or irregularly dispersed.",
            "confidence": "Low",
        }

    # Calculate slope for each detected line using linear regression on bottom points
    line_slopes = []
    for line in lines:
        # Sort left to right
        line.sort(key=lambda b: b[0])
        xs = [b[0] + b[2] / 2.0 for b in line]
        ys = [b[4] for b in line]

        if len(xs) >= 3 and (max(xs) - min(xs)) > 50:
            slope, _ = np.polyfit(xs, ys, 1)
            angle_deg = math.degrees(math.atan(slope))
            line_slopes.append(angle_deg)

    if not line_slopes:
        return {
            "status": "limited",
            "measured_slope_deg": 0.0,
            "baseline_stability_score": None,
            "explanation": "Line span was insufficient to compute a stable slope angle.",
            "confidence": "Low",
        }

    avg_slope = float(np.mean(line_slopes))
    slope_std = float(np.std(line_slopes)) if len(line_slopes) > 1 else 0.0

    # Baseline stability score: 100 is perfectly horizontal (0 slope, 0 std)
    penalty = min(60.0, abs(avg_slope) * 6.0 + slope_std * 5.0)
    stability_score = round(max(30.0, 100.0 - penalty), 1)

    return {
        "status": "ok",
        "measured_slope_deg": round(avg_slope, 2),
        "slope_variation_deg": round(slope_std, 2),
        "lines_detected": len(lines),
        "baseline_stability_score": stability_score,
        "explanation": f"Detected {len(lines)} writing lines with an average baseline angle of {round(avg_slope, 1)}°.",
        "confidence": "High" if len(lines) >= 2 else "Medium",
    }


def analyze_spacing_consistency(binary: np.ndarray) -> Dict[str, Any]:
    """Estimates horizontal spacing uniformity between words using morphological dilation."""
    h, w = binary.shape[:2]
    # Horizontal dilation bridges letters inside a word while leaving word gaps
    kernel_w = max(5, int(w * 0.015))
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_w, 1))
    dilated = cv2.dilate(binary, kernel, iterations=2)

    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    word_boxes = []

    for c in contours:
        x, y, bw, bh = cv2.boundingRect(c)
        if bw > 15 and bh > 10:
            word_boxes.append((x, y, bw, bh))

    if len(word_boxes) < 4:
        return {
            "status": "limited",
            "word_count_estimate": len(word_boxes),
            "spacing_uniformity_score": None,
            "explanation": "Too few word blocks detected to compute statistical spacing distribution.",
            "confidence": "Low",
        }

    # Sort vertically then horizontally
    word_boxes.sort(key=lambda b: (b[1] // 40, b[0]))
    gaps: List[int] = []

    for i in range(len(word_boxes) - 1):
        b1 = word_boxes[i]
        b2 = word_boxes[i + 1]
        # Same approximate line
        if abs(b1[1] - b2[1]) < max(b1[3], b2[3]) * 0.6:
            gap = b2[0] - (b1[0] + b1[2])
            if 5 < gap < (w * 0.3):
                gaps.append(gap)

    if len(gaps) < 3:
        return {
            "status": "limited",
            "word_count_estimate": len(word_boxes),
            "spacing_uniformity_score": None,
            "explanation": "Insufficient adjacent word pairs on identical lines for spacing metrics.",
            "confidence": "Low",
        }

    mean_gap = float(np.mean(gaps))
    std_gap = float(np.std(gaps))
    cv_gap = std_gap / (mean_gap + 1e-5)  # coefficient of variation

    # Consistency score: CV < 0.25 is very uniform (90+), CV > 0.75 is irregular (<60)
    consistency_score = round(max(35.0, min(100.0, 100.0 - (cv_gap * 70.0))), 1)

    return {
        "status": "ok",
        "word_count_estimate": len(word_boxes),
        "mean_word_gap_px": round(mean_gap, 1),
        "gap_variation_px": round(std_gap, 1),
        "spacing_uniformity_score": consistency_score,
        "explanation": f"Analyzed {len(gaps)} inter-word gaps with a mean distance of {round(mean_gap, 1)}px.",
        "confidence": "High" if len(gaps) >= 6 else "Medium",
    }


def analyze_character_size_consistency(binary: np.ndarray) -> Dict[str, Any]:
    """Measures the variation of character component bounding box heights."""
    h, w = binary.shape[:2]
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    heights = []

    for c in contours:
        _, _, bw, bh = cv2.boundingRect(c)
        area = cv2.contourArea(c)
        if 25 < area < (w * h * 0.05) and 10 < bh < (h * 0.35) and 4 < bw < (w * 0.2):
            heights.append(bh)

    if len(heights) < 8:
        return {
            "status": "limited",
            "median_height_px": None,
            "size_consistency_score": None,
            "explanation": "Insufficient character components detected for size consistency analysis.",
            "confidence": "Low",
        }

    median_h = float(np.median(heights))
    std_h = float(np.std(heights))
    cv_h = std_h / (median_h + 1e-5)

    # Upper/lowercase mixes naturally produce CV around 0.3 - 0.45
    # High variance CV > 0.6 indicates irregular letter scaling
    score = round(max(35.0, min(100.0, 100.0 - (max(0.0, cv_h - 0.20) * 85.0))), 1)

    return {
        "status": "ok",
        "component_count": len(heights),
        "median_height_px": round(median_h, 1),
        "height_variation_px": round(std_h, 1),
        "size_consistency_score": score,
        "explanation": f"Measured {len(heights)} glyph components with median height {round(median_h, 1)}px.",
        "confidence": "High" if len(heights) >= 15 else "Medium",
    }


def analyze_slant_consistency(binary: np.ndarray) -> Dict[str, Any]:
    """Estimates dominant handwriting slant angle using shear vertical projection variance."""
    h, w = binary.shape[:2]
    if h < 50 or w < 50:
        return {
            "status": "limited",
            "slant_angle_deg": 0.0,
            "explanation": "Image too small for vertical projection shear analysis.",
            "confidence": "Low",
        }

    # Subsample for fast, stable projection analysis
    scale = 300.0 / max(h, w)
    if scale < 1.0:
        thumb = cv2.resize(binary, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_NEAREST)
    else:
        thumb = binary

    th_h, th_w = thumb.shape[:2]
    angles = list(range(-30, 32, 2))  # test angles -30 to +30 degrees
    variances = []

    for angle in angles:
        rad = math.radians(angle)
        # Shear matrix along x
        shear_m = np.float32([[1, -math.tan(rad), 0], [0, 1, 0]])
        sheared = cv2.warpAffine(thumb, shear_m, (th_w, th_h), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        # Vertical projection (column sums)
        vert_proj = np.sum(sheared, axis=0)
        variances.append(float(np.var(vert_proj)))

    best_idx = int(np.argmax(variances))
    dominant_angle = angles[best_idx]

    # Description of slant
    if abs(dominant_angle) <= 4:
        slant_type = "Upright (Near vertical)"
    elif dominant_angle > 4:
        slant_type = f"Forward slant (+{dominant_angle}°)"
    else:
        slant_type = f"Backward slant ({dominant_angle}°)"

    return {
        "status": "ok",
        "slant_angle_deg": dominant_angle,
        "slant_type": slant_type,
        "explanation": f"Dominant stroke slant measured at {dominant_angle}° ({slant_type}).",
        "confidence": "Medium",
    }


def analyze_stroke_density(binary: np.ndarray) -> Dict[str, Any]:
    """Calculates ink stroke density and estimated stroke thickness."""
    total_pixels = binary.size
    ink_pixels = int(np.count_nonzero(binary))
    density_ratio = float(ink_pixels) / float(total_pixels + 1e-5)

    # Distance transform on ink pixels to measure stroke half-width
    dist_map = cv2.distanceTransform(binary, cv2.DIST_L2, 3)
    non_zero_dist = dist_map[binary > 0]

    if len(non_zero_dist) > 0:
        est_thickness = float(np.median(non_zero_dist) * 2.0)
    else:
        est_thickness = 0.0

    return {
        "ink_density_percent": round(density_ratio * 100.0, 2),
        "estimated_stroke_width_px": round(est_thickness, 1),
    }


def extract_cv_features(image_path: str) -> Dict[str, Any]:
    """Runs full automated computer-vision analysis on the handwriting sample.

    Extracts real image quality, baseline alignment, spacing, sizing, slant,
    and stroke characteristics.
    """
    if not os.path.exists(image_path):
        raise ValueError(f"Image not found for CV analysis: {image_path}")

    # Read image in grayscale
    gray = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if gray is None:
        raise ValueError("Could not decode image for CV analysis.")

    quality = analyze_image_quality(gray)
    binary = binarize_for_analysis(gray)

    baseline = analyze_baseline_alignment(binary)
    spacing = analyze_spacing_consistency(binary)
    size_consistency = analyze_character_size_consistency(binary)
    slant = analyze_slant_consistency(binary)
    strokes = analyze_stroke_density(binary)

    return {
        "image_quality": quality,
        "baseline_alignment": baseline,
        "word_spacing": spacing,
        "size_consistency": size_consistency,
        "slant_consistency": slant,
        "stroke_density": strokes,
    }
