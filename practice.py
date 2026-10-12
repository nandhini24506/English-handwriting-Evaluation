"""Personalised practice module for EHE 2.0.

Generates deterministic practice exercises based on evaluated weaknesses:
  - Letter formation drills (curves, stems, ascenders/descenders)
  - Word spacing exercises (uniform gaps, copy-work)
  - Ruled-line alignment exercises (baseline adherence, tracking)
  - Consistent letter-size practice (x-height uniformity, 4-line guides)
  - Legibility exercises (clarity pangrams, distinct stroke terminals)
"""

from typing import Dict, Any, List

PRACTICE_CURRICULUM: Dict[str, List[Dict[str, Any]]] = {
    "letter_formation": [
        {
            "id": "lf_01",
            "title": "Oval Closures & Ascender Extensions",
            "level": "Foundational",
            "instructions": "Write out the following words slowly on ruled paper. Pay close attention to fully closing ovals in 'a', 'o', 'd' and making ascenders in 'b', 'd', 'h', 'l' crisp and straight.",
            "target_text": "badger dolphin balloon holiday daylight shadow",
            "focus_cue": "Close each round letter fully before releasing the stroke.",
        },
        {
            "id": "lf_02",
            "title": "Descender Loops & Crossbars",
            "level": "Intermediate",
            "instructions": "Copy this sentence ensuring descenders ('g', 'j', 'p', 'q', 'y') drop uniformly beneath the baseline with smooth tail loops.",
            "target_text": "Quick jumping frogs playfully dodge heavy muddy puddles.",
            "focus_cue": "Descenders should extend exactly equal depth below the baseline.",
        },
    ],
    "word_spacing": [
        {
            "id": "ws_01",
            "title": "Index-Finger Spacing Intervals",
            "level": "Foundational",
            "instructions": "Copy this sentence leaving a strict, uniform one-character gap between every word. Do not let words cluster together or drift excessively apart.",
            "target_text": "Clear thinking produces clear writing with calm, steady pacing.",
            "focus_cue": "Visualise an extra letter 'o' fitting neatly in the gap between each word.",
        },
        {
            "id": "ws_02",
            "title": "Rhythmic Sentence Pacing",
            "level": "Intermediate",
            "instructions": "Transcribe the following text, keeping both word-to-word intervals and punctuation spacing uniform across three consecutive lines.",
            "target_text": "Small continuous improvements over time create substantial, lasting excellence in handwriting.",
            "focus_cue": "Pause your pen slightly at each word boundary to confirm gap spacing.",
        },
    ],
    "alignment": [
        {
            "id": "al_01",
            "title": "Horizontal Baseline Grounding",
            "level": "Foundational",
            "instructions": "Using ruled paper, write the target words ensuring every non-descender letter sits directly on the printed line without floating or sagging.",
            "target_text": "sunset mountain horizon baseline foundation riverbank",
            "focus_cue": "Anchor the bottom of every oval and stem right onto the guideline.",
        },
        {
            "id": "al_02",
            "title": "Unruled Straight-Line Challenge",
            "level": "Advanced",
            "instructions": "Write the following sentence on blank (unlined) paper. Keep the imaginary baseline strictly level from the left margin to the right margin.",
            "target_text": "Straight lines require steady focus and a relaxed, balanced hand position.",
            "focus_cue": "Keep your wrist aligned and glide your forearm smoothly across the page.",
        },
    ],
    "slant_consistency": [
        {
            "id": "sc_01",
            "title": "Parallel Downstroke Rhythm",
            "level": "Foundational",
            "instructions": "Before writing words, practice 10 parallel hatch marks (///). Then copy the text matching every downstroke to that exact angle.",
            "target_text": "willow miller brilliant parallel rolling yellow hills",
            "focus_cue": "Downstrokes in 'l', 'i', 't', 'b' must remain strictly parallel.",
        },
        {
            "id": "sc_02",
            "title": "Full Sentence Tilt Calibration",
            "level": "Intermediate",
            "instructions": "Transcribe this passage maintaining your natural slant angle consistently from the first word to the final word.",
            "target_text": "Consistent slant brings harmonious visual rhythm and elegance to written script.",
            "focus_cue": "Check that the paper angle on your desk remains steady throughout.",
        },
    ],
    "size_consistency": [
        {
            "id": "sz_01",
            "title": "X-Height Mid-Zone Uniformity",
            "level": "Foundational",
            "instructions": "Write these words ensuring all lowercase mid-zone letters (a, c, e, m, n, o, r, s, u, v, w, x, z) are identical in height.",
            "target_text": "summer season remove runner common senses weaves",
            "focus_cue": "Caps should be twice the height of mid-zone letters; mid-zone letters must never fluctuate.",
        },
        {
            "id": "sz_02",
            "title": "Proportional Ratio Practice",
            "level": "Intermediate",
            "instructions": "Transcribe the pangram keeping uppercase capital letters exactly 100% height, ascenders at 100%, and lowercase bodies at 50%.",
            "target_text": "The Five Boxing Wizards Jump Quickly Across New Frontiers.",
            "focus_cue": "Maintain a strict 2:1 height ratio between capitals and lowercase vowels.",
        },
    ],
    "legibility": [
        {
            "id": "lg_01",
            "title": "Ambiguous Letter Pair Disambiguation",
            "level": "Foundational",
            "instructions": "Write these contrasting pairs clearly, ensuring strokes do not blur together: u/v, n/r, cl/d, a/o.",
            "target_text": "under vapor, near real, clean deer, auto order, unity value",
            "focus_cue": "Sharp point at the bottom of 'v', smooth curve at bottom of 'u'.",
        },
        {
            "id": "lg_02",
            "title": "Comprehensive Clarity Pangram",
            "level": "Intermediate",
            "instructions": "Transcribe this complete 26-letter English pangram at a controlled, deliberate tempo for maximum legibility.",
            "target_text": "Pack my box with five dozen liquor jugs. The quick brown fox jumps over the lazy dog.",
            "focus_cue": "Every single letter must be instantly recognizable on its own out of context.",
        },
    ],
}


def get_recommended_exercises(weakest_metric: str) -> List[Dict[str, Any]]:
    """Returns curated deterministic practice exercises tailored to the target metric."""
    metric_key = weakest_metric.lower().strip()
    exercises = PRACTICE_CURRICULUM.get(metric_key)

    if not exercises:
        # Fallback to letter formation
        exercises = PRACTICE_CURRICULUM["letter_formation"]

    return exercises


def get_all_practice_categories() -> Dict[str, List[Dict[str, Any]]]:
    """Returns all practice categories and exercises across all six metrics."""
    return PRACTICE_CURRICULUM
