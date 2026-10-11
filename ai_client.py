"""AI client module for EHE 2.0 supporting Gemini and NVIDIA multimodal APIs.

Configured Active AI Provider:
  - Google Gemini API (gemini-flash-latest via https://generativelanguage.googleapis.com/v1beta)
  - Key: GEMINI_API_KEY (supports X-goog-api-key header)
  - Automatic fallback to gemini-3.8-flash if primary model experiences high-demand 503 spikes.

Also preserves NVIDIA OpenAI-compatible format support (moonshotai/kimi-k3 via NVIDIA_API_KEY).

Performs a single unified multimodal request per unique image to extract:
  1. Handwritten English OCR transcription (preserving [unclear] markers for illegible words)
  2. Six handwriting evaluation metrics with qualitative explanations and observable evidence:
     - Letter formation
     - Word spacing
     - Alignment
     - Slant consistency
     - Size consistency
     - Legibility

Features SHA-256 image byte caching to prevent duplicate API requests.
"""

import base64
import json
import os
import re
from typing import Dict, Any, Optional
import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_GEMINI_MODEL = "gemini-flash-latest"

DEFAULT_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_NVIDIA_MODEL = "moonshotai/kimi-k3"

UNIFIED_EVALUATION_PROMPT = """You are an expert specialist in English handwriting evaluation and OCR transcription.
Analyze the provided English handwriting image carefully.

You must perform TWO tasks simultaneously:
Task 1: OCR Transcription
- Transcribe the handwritten English text exactly as written.
- Do not autocorrect spelling errors or alter grammar.
- If a word is unreadable or illegible, represent it strictly as [unclear].

Task 2: Handwriting Evaluation
Evaluate ONLY these six characteristics:
1. letter_formation: Letter shapes, stroke completeness, loops, ascenders/descenders.
2. word_spacing: Uniformity and appropriateness of gaps between words.
3. alignment: Consistency of the writing baseline along horizontal or ruled lines.
4. slant_consistency: Consistency of letter slant (upright, forward, or backward). Consistency matters more than the slant angle.
5. size_consistency: Proportion and height uniformity of uppercase and lowercase letters.
6. legibility: Overall ease of reading words without ambiguity.

For each of the six characteristics, provide:
- "score": A number between 0 and 100 based strictly on visible handwriting evidence.
- "explanation": A concise, constructive explanation of the handwriting quality.
- "evidence": Specific observable visual characteristics or limitations seen in the image.

Do NOT evaluate student personality, intelligence, or writing topic.

Return ONLY a valid JSON object matching this schema:
{
  "transcription": "Transcribed handwritten text...",
  "metrics": {
    "letter_formation": {"score": 85, "explanation": "...", "evidence": "..."},
    "word_spacing": {"score": 75, "explanation": "...", "evidence": "..."},
    "alignment": {"score": 80, "explanation": "...", "evidence": "..."},
    "slant_consistency": {"score": 70, "explanation": "...", "evidence": "..."},
    "size_consistency": {"score": 80, "explanation": "...", "evidence": "..."},
    "legibility": {"score": 85, "explanation": "...", "evidence": "..."}
  },
  "overall_summary": "Concise summary of handwriting characteristics..."
}"""

REQUIRED_METRICS = [
    "letter_formation",
    "word_spacing",
    "alignment",
    "slant_consistency",
    "size_consistency",
    "legibility",
]


def get_api_credentials() -> Dict[str, str]:
    """Retrieves configured AI API credentials from environment variables."""
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip()

    nvidia_key = os.getenv("NVIDIA_API_KEY", "").strip()
    nvidia_base_url = os.getenv("NVIDIA_BASE_URL", DEFAULT_NVIDIA_BASE_URL).rstrip("/")
    nvidia_model = os.getenv("NVIDIA_MODEL", DEFAULT_NVIDIA_MODEL).strip()

    return {
        "gemini_api_key": gemini_key,
        "gemini_model": gemini_model,
        "api_key": nvidia_key or gemini_key,
        "base_url": nvidia_base_url,
        "model": nvidia_model,
    }


def encode_image_base64(image_path: str) -> tuple[str, str]:
    """Returns (base64_encoded_str, mime_type) for the given image file."""
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at path: {image_path}")

    ext = os.path.splitext(image_path)[1].lower()
    mime_type = "image/png" if ext == ".png" else "image/jpeg"

    with open(image_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")

    return encoded, mime_type


def encode_image_to_data_url(image_path: str) -> str:
    """Encodes image file to base64 Data URL for OpenAI-compatible multimodal input."""
    encoded, mime_type = encode_image_base64(image_path)
    return f"data:{mime_type};base64,{encoded}"


def parse_and_validate_ai_response(response_text: str) -> Dict[str, Any]:
    """Extracts, parses, and validates JSON evaluation from model response text."""
    if not response_text or not response_text.strip():
        raise ValueError("AI provider returned an empty response.")

    cleaned = response_text.strip()
    # Strip markdown code blocks if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Search for first outermost JSON object
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise ValueError("AI response did not contain a valid JSON object.")
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError as err:
            raise ValueError("Failed to parse JSON from AI response.") from err

    # Validate transcription
    transcription = data.get("transcription", "")
    if not isinstance(transcription, str):
        transcription = str(transcription)
    transcription = transcription.strip()

    # Validate metrics
    raw_metrics = data.get("metrics")
    if not isinstance(raw_metrics, dict):
        raw_metrics = {k: data[k] for k in REQUIRED_METRICS if k in data}

    validated_metrics: Dict[str, Dict[str, Any]] = {}
    for metric_name in REQUIRED_METRICS:
        if metric_name not in raw_metrics:
            raise ValueError(f"AI response is missing evaluation metric: '{metric_name}'.")

        metric_data = raw_metrics[metric_name]
        if isinstance(metric_data, (int, float)):
            score = float(metric_data)
            explanation = "Evaluated characteristic."
            evidence = "Observable visual sample."
        elif isinstance(metric_data, dict):
            raw_score = metric_data.get("score")
            try:
                score = float(raw_score)
            except (TypeError, ValueError) as err:
                raise ValueError(f"Metric '{metric_name}' score must be a number: got {raw_score}") from err
            explanation = str(metric_data.get("explanation", "Evaluation completed.")).strip()
            evidence = str(metric_data.get("evidence", "Observed from visual analysis.")).strip()
        else:
            raise ValueError(f"Invalid format for metric '{metric_name}'.")

        if score != score or score == float("inf") or score == float("-inf"):
            raise ValueError(f"Score for '{metric_name}' must be finite.")

        score = max(0.0, min(100.0, score))

        validated_metrics[metric_name] = {
            "score": round(score, 2),
            "explanation": explanation,
            "evidence": evidence,
        }

    overall_summary = str(data.get("overall_summary", "")).strip()

    return {
        "transcription": transcription,
        "metrics": validated_metrics,
        "overall_summary": overall_summary,
    }


def call_gemini_multimodal_api(
    image_path: str,
    override_api_key: Optional[str] = None,
    timeout_seconds: int = 45,
) -> Dict[str, Any]:
    """Executes multimodal request using Google Gemini Generative Language API.

    Header: X-goog-api-key: <KEY>
    Model: gemini-flash-latest (with fallback to gemini-3.8-flash on 503 high demand)
    """
    api_key = override_api_key or os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured in .env.")

    base_url = os.getenv("GEMINI_BASE_URL", DEFAULT_GEMINI_BASE_URL).rstrip("/")
    primary_model = os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip()
    models_to_try = [primary_model, "gemini-3.8-flash", "gemini-flash-lite-latest"]

    b64_data, mime_type = encode_image_base64(image_path)

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": UNIFIED_EVALUATION_PROMPT},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64_data,
                        }
                    },
                ]
            }
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": api_key,
    }

    last_error = None
    for model_name in models_to_try:
        endpoint = f"{base_url}/models/{model_name}:generateContent"
        try:
            response = requests.post(endpoint, json=payload, headers=headers, timeout=timeout_seconds)
            if response.status_code == 200:
                res_json = response.json()
                content = res_json["candidates"][0]["content"]["parts"][0]["text"]
                return parse_and_validate_ai_response(content)
            elif response.status_code == 503:
                # Temporary high demand on this model; try next fallback model
                last_error = RuntimeError(f"Model {model_name} currently experiencing high demand (503).")
                continue
            elif response.status_code in (401, 403):
                raise RuntimeError("Authentication failed with Gemini API. Check your GEMINI_API_KEY.")
            elif response.status_code == 429:
                raise RuntimeError("Gemini API rate limit exceeded. Please wait a moment and try again.")
            else:
                last_error = RuntimeError(f"Gemini API returned HTTP {response.status_code}: {response.text[:200]}")
        except requests.exceptions.Timeout as err:
            last_error = RuntimeError("AI evaluation request timed out.")
        except requests.exceptions.RequestException as err:
            last_error = RuntimeError(f"Network error communicating with AI provider: {type(err).__name__}")

    raise last_error or RuntimeError("Gemini API could not process the evaluation request.")


def call_nvidia_multimodal_api(
    image_path: str,
    override_api_key: Optional[str] = None,
    timeout_seconds: int = 45,
) -> Dict[str, Any]:
    """Executes multimodal request to the NVIDIA OpenAI-compatible chat completion endpoint."""
    creds = get_api_credentials()
    api_key = override_api_key or os.getenv("NVIDIA_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError("NVIDIA_API_KEY is not configured in the environment.")

    endpoint = f"{creds['base_url']}/chat/completions"
    data_url = encode_image_to_data_url(image_path)

    payload = {
        "model": creds["model"],
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": UNIFIED_EVALUATION_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "temperature": 0.2,
        "max_tokens": 1200,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=timeout_seconds)
    except requests.exceptions.Timeout as err:
        raise RuntimeError("AI evaluation request timed out after 45 seconds.") from err
    except requests.exceptions.ConnectionError as err:
        raise RuntimeError("Network connection to AI provider failed.") from err
    except requests.exceptions.RequestException as err:
        raise RuntimeError(f"Failed to communicate with AI provider: {type(err).__name__}") from err

    if response.status_code in (401, 403):
        raise RuntimeError("Authentication failed with NVIDIA API. Please check your NVIDIA_API_KEY.")
    elif response.status_code == 429:
        raise RuntimeError("NVIDIA API rate limit exceeded.")
    elif not response.ok:
        raise RuntimeError(f"NVIDIA API returned HTTP error {response.status_code}.")

    try:
        res_json = response.json()
        content = res_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as err:
        raise ValueError("Invalid response format received from AI provider.") from err

    return parse_and_validate_ai_response(content)


def call_ai_multimodal_api(image_path: str) -> Dict[str, Any]:
    """Routes to the active configured AI provider (Google Gemini or NVIDIA)."""
    if os.getenv("GEMINI_API_KEY"):
        return call_gemini_multimodal_api(image_path)
    elif os.getenv("NVIDIA_API_KEY"):
        return call_nvidia_multimodal_api(image_path)
    else:
        raise RuntimeError(
            "No AI API key is configured. Please provide GEMINI_API_KEY in .env."
        )


def evaluate_with_cache(
    image_path: str,
    image_hash: str,
    db_lookup_fn=None,
    db_store_fn=None,
) -> Dict[str, Any]:
    """Evaluates an image using SHA-256 byte caching to avoid duplicate provider API calls."""
    if db_lookup_fn:
        cached_result = db_lookup_fn(image_hash)
        if cached_result:
            return cached_result

    # Make API call through active provider
    result = call_ai_multimodal_api(image_path)

    # Store in cache only on full success
    if db_store_fn:
        try:
            db_store_fn(image_hash, result)
        except Exception:
            pass

    return result
