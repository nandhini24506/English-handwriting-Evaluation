"""Actionable feedback generation module for EHE 2.0.

Produces deterministic rule-based recommendations tailored to the student's
weakest evaluated characteristics, distinguishing fixed rule-based advice
from AI qualitative observations.
"""

from typing import Dict, Any, List

RULE_BASED_GUIDANCE: Dict[str, Dict[str, str]] = {
    "letter_formation": {
        "title": "Letter Formation Drills",
        "action": "Focus on complete closures of ovals (a, o, d, g) and uniform height for ascenders (b, d, h, k, l) and descenders (g, j, p, q, y).",
        "exercise": "Practice slow tracing drills using 3-line ruling, ensuring ascender loops reach the top guideline.",
    },
    "word_spacing": {
        "title": "Word Spacing Consistency",
        "action": "Maintain an approximate index-finger width gap (or standard 1-character width) consistently between consecutive words.",
        "exercise": "Perform sentence copy-work using dot guides between words to train uniform horizontal separation.",
    },
    "alignment": {
        "title": "Baseline Alignment Practice",
        "action": "Keep the bottom of all non-descender letters grounded firmly on the baseline without drifting above or sinking below.",
        "exercise": "Use ruled paper with a dark guide sheet beneath to train continuous horizontal baseline tracking.",
    },
    "slant_consistency": {
        "title": "Slant Rhythm & Direction",
        "action": "Keep all downstrokes parallel at your natural slant angle. Whether upright or slightly forward, maintain consistent tilt across the line.",
        "exercise": "Practice rhythmic parallel hatch marks (///) before writing full sentences to calibrate downstroke slant.",
    },
    "size_consistency": {
        "title": "X-Height & Proportional Scaling",
        "action": "Ensure all lowercase mid-zone letters (a, c, e, m, n, o, r, s, u, v, w, x, z) share an identical uniform height.",
        "exercise": "Write on 4-line handwriting practice paper, keeping mid-zone letters strictly between the middle two lines.",
    },
    "legibility": {
        "title": "Legibility & Stroke Clarity",
        "action": "Decelerate writing speed slightly on complex strokes. Ensure ambiguous letter pairs (such as 'u' vs 'v', 'cl' vs 'd', 'n' vs 'r') have clear distinctions.",
        "exercise": "Transcribe pangrams at half-speed, focusing purely on unambiguous recognition for each individual letter.",
    },
}


def generate_feedback(scores: Dict[str, float], cv_features: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Generates structured, actionable rule-based feedback based on component scores

    and measured computer vision indicators.
    """
    feedback_items: List[Dict[str, Any]] = []

    # Sort metrics by score ascending to prioritize the weakest areas
    sorted_metrics = sorted(scores.items(), key=lambda item: item[1])

    for metric, score in sorted_metrics:
        rule = RULE_BASED_GUIDANCE.get(metric)
        if not rule:
            continue

        if score < 60.0:
            status = "needs_critical_focus"
            priority = "High"
            message = f"Score: {score}/100. Significant inconsistency identified in {metric.replace('_', ' ')}."
        elif score < 75.0:
            status = "needs_improvement"
            priority = "Medium"
            message = f"Score: {score}/100. Moderate variance observed; targeted practice will strengthen consistency."
        else:
            status = "strong"
            priority = "Low"
            message = f"Score: {score}/100. Demonstrates consistent execution in {metric.replace('_', ' ')}."

        # Include items needing improvement, or include the lowest if all are strong
        if score < 80.0 or len(feedback_items) == 0:
            feedback_items.append({
                "metric": metric,
                "metric_label": metric.replace("_", " ").title(),
                "score": score,
                "status": status,
                "priority": priority,
                "feedback_text": message,
                "actionable_tip": rule["action"],
                "recommended_exercise": rule["exercise"],
                "source": "deterministic_rule_engine",
            })

    # Add computer vision specific technical alerts if detected
    if cv_features:
        quality = cv_features.get("image_quality", {})
        if quality.get("sharpness_score", 100.0) < 70.0:
            feedback_items.append({
                "metric": "capture_quality",
                "metric_label": "Capture Quality Notice",
                "score": quality.get("sharpness_score"),
                "status": "warning",
                "priority": "Informational",
                "feedback_text": "The uploaded photo is somewhat blurry. For highest accuracy, capture photos under bright, direct light with the camera held steady and parallel to the paper.",
                "actionable_tip": "Place paper on a flat surface, avoid shadows, and ensure the lens is focused.",
                "recommended_exercise": "Retake sample in high-contrast natural daylight.",
                "source": "computer_vision_analysis",
            })

    return feedback_items


def identify_weakest_metric(scores: Dict[str, float]) -> Dict[str, Any]:
    """Identifies the single weakest characteristic for focused practice."""
    if not scores:
        return {"metric": "letter_formation", "label": "Letter Formation", "score": 0.0}

    weakest_key = min(scores.keys(), key=lambda k: scores[k])
    return {
        "metric": weakest_key,
        "label": weakest_key.replace("_", " ").title(),
        "score": scores[weakest_key],
    }
