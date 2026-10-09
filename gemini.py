import json
import os
import re

from google import genai
from google.genai import types


OCR_PROMPT = """You are performing OCR on an English handwriting image.

Read only the handwritten English text in the image.
Transcribe what is actually written.
Do not correct spelling, improve grammar, rewrite sentences, or summarize.
Do not add words that are not visible.
If a word cannot be read confidently, write [unclear].
Return only the transcribed text."""

EVALUATION_PROMPT = """You are evaluating English handwriting for an academic handwriting assessment.

Look at the handwriting image carefully. Evaluate ONLY these six characteristics:
1. Letter Formation
2. Word Spacing
3. Alignment
4. Slant Consistency
5. Size Consistency
6. Legibility

Give each characteristic a score from 0 to 100.
Evaluate the handwriting itself, not intelligence, sentence content, grammar, or spelling.
Do not require a particular slant direction; consistency matters more than direction.
Consider natural differences between uppercase and lowercase letters.
Base the evaluation only on visible evidence in the image.
Return JSON only with these keys: letter_formation, word_spacing, alignment,
slant_consistency, size_consistency, legibility."""

REQUIRED_SCORES = (
    "letter_formation",
    "word_spacing",
    "alignment",
    "slant_consistency",
    "size_consistency",
    "legibility",
)


def _client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing from the environment.")
    return genai.Client(api_key=api_key)


def _image_part(image_path):
    with open(image_path, "rb") as image_file:
        image_bytes = image_file.read()
    return types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")


def _generate_with_fallback(contents):
    client = _client()
    primary_model = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    fallback_models = [primary_model, "gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.8-flash"]
    seen = set()
    models_to_try = [m for m in fallback_models if not (m in seen or seen.add(m))]

    last_error = None
    for model in models_to_try:
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
            )
        except Exception as error:
            last_error = error
            continue
    raise last_error


def extract_text(image_path):
    response = _generate_with_fallback(contents=[OCR_PROMPT, _image_part(image_path)])
    return response.text.strip()


def _parse_json(response_text):
    cleaned_text = response_text.strip()
    cleaned_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned_text, flags=re.IGNORECASE)
    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned_text, re.DOTALL)
        if not match:
            raise ValueError("Gemini did not return valid evaluation JSON.")
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError as error:
            raise ValueError("Gemini did not return valid evaluation JSON.") from error


def evaluate_handwriting(image_path):
    response = _generate_with_fallback(contents=[EVALUATION_PROMPT, _image_part(image_path)])
    raw_scores = _parse_json(response.text)
    scores = {}
    for metric in REQUIRED_SCORES:
        if metric not in raw_scores:
            raise ValueError(f"Gemini response is missing the score: {metric}.")
        try:
            score = float(raw_scores[metric])
        except (TypeError, ValueError) as error:
            raise ValueError(f"Gemini returned an invalid score for {metric}.") from error
        scores[metric] = max(0, min(100, score))
    return scores
