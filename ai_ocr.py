import os
import re
import cv2
import json
import time
import base64
import requests
import numpy as np
from config import Config

AI_OCR_PROMPT = """You are an expert handwriting transcription specialist.

Transcribe EXACTLY what is visibly written in the provided image.

Strict Rules:
1. Do NOT summarize the content.
2. Do NOT paraphrase.
3. Do NOT improve grammar or rewrite sentences into proper English.
4. Do NOT correct spelling errors (transcribe misspelled words exactly as written).
5. Do NOT invent missing words or use outside context to guess intended text.
6. Preserve original wording, punctuation, capitalization, line structure, and paragraph structure whenever visually identifiable.
7. If a word cannot be read confidently, mark it as [unclear] instead of guessing or inventing a word.
8. The handwriting is handwritten English and may be in cursive. Connected cursive letters are normal; do not interpret cursive join strokes as dashes, hyphens, underscores, or separate characters.
9. IGNORE ALL BACKGROUND NOTEBOOK RULING LINES and vertical margin lines. Do NOT interpret notebook lines as underscores ('_'), hyphens ('-'), tildes ('~'), or punctuation marks. Only transcribe ink belonging to handwritten letters.

Identify each handwritten line and detect blank spaces between lines to separate paragraphs.

Return ONLY a valid JSON object matching this exact structure, with NO markdown formatting, NO code blocks, and NO text outside JSON:

{
  "text": "Full transcribed text with double newlines (\\\\n\\\\n) between paragraphs",
  "lines": [
    {
      "line_number": 1,
      "text": "The Importance of Education"
    },
    {
      "line_number": 2,
      "text": "Education is the most powerful tool which you can use to change the world."
    }
  ],
  "confidence": 92,
  "status": "good",
  "uncertain_words": []
}
"""

RETRY_STRICT_OCR_PROMPT = AI_OCR_PROMPT + "\n\nCRITICAL: Your previous response was invalid. Return ONLY the raw JSON object starting with '{' and ending with '}'. Do NOT wrap in markdown code blocks."


def prepare_image_for_ocr(image_path, output_dir=None):
    """
    OCR-specific image preprocessing pipeline:
    1. Read original image.
    2. Mild border crop (5px) if large enough to remove scanner/shadow artifacts.
    3. Mild CLAHE contrast enhancement preserving thin cursive strokes.
    4. 2x resolution upscaling preserving smooth letter curves.
    5. Save and return path to OCR-ready image.
    """
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at {image_path}")

    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Unable to decode image at {image_path}")

    h, w = img.shape[:2]

    # 1. Mild crop if image is large enough
    if h > 100 and w > 100:
        crop_margin_h = int(h * 0.01)
        crop_margin_w = int(w * 0.01)
        img = img[crop_margin_h:h - crop_margin_h, crop_margin_w:w - crop_margin_w]

    # 2. Grayscale & CLAHE contrast enhancement
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=1.8, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)

    # 3. Preserve smooth cursive curves: 2x upscaling
    upscaled = cv2.resize(enhanced, (enhanced.shape[1] * 2, enhanced.shape[0] * 2), interpolation=cv2.INTER_CUBIC)
    
    # 3-channel output for Gemini Vision
    ocr_bgr = cv2.cvtColor(upscaled, cv2.COLOR_GRAY2BGR)

    if output_dir is None:
        output_dir = os.path.dirname(image_path)

    os.makedirs(output_dir, exist_ok=True)
    orig_name = os.path.basename(image_path)
    prep_name = f"ocr_prep_{orig_name}"
    prep_path = os.path.join(output_dir, prep_name)

    cv2.imwrite(prep_path, ocr_bgr)
    return prep_path


def _call_gemini_ocr_api(image_path, prompt, api_key, model_name):
    """Sends image payload to Gemini Vision API for transcription."""
def _get_optimized_ocr_bytes(image_path):
    """Encodes image to JPEG bytes, resizing down if max dim > 1600px for fast API transfer."""
    img = cv2.imread(image_path)
    if img is not None:
        h, w = img.shape[:2]
        if max(h, w) > 1600:
            scale = 1600.0 / float(max(h, w))
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        success, encoded_img = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
        if success:
            return encoded_img.tobytes(), "image/jpeg"
            
    with open(image_path, "rb") as f:
        return f.read(), "image/jpeg"

def _call_gemini_ocr_api(image_path, prompt, api_key, model_name):
    """Sends image payload to Gemini Vision API for transcription."""
    img_bytes, mime_type = _get_optimized_ocr_bytes(image_path)

    # Try Google GenAI SDK first if available
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=[
                types.Part.from_bytes(data=img_bytes, mime_type=mime_type),
                prompt
            ]
        )
        if response and hasattr(response, 'text') and response.text:
            return response.text
    except Exception:
        pass

    # Direct REST API Fallback
    b64_img = base64.b64encode(img_bytes).decode('utf-8')
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": api_key
    }
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64_img
                        }
                    },
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini OCR API returned status {resp.status_code}: {resp.text}")


    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as err:
        raise RuntimeError(f"Unexpected response structure from Gemini OCR API: {data}") from err


def _parse_and_validate_ocr_json(raw_text):
    """Parses raw text into validated structured OCR response dict."""
    text_clean = raw_text.strip()
    match = re.search(r'\{.*\}', text_clean, re.DOTALL)
    if match:
        json_str = match.group(0)
        parsed = json.loads(json_str)
    else:
        parsed = json.loads(text_clean)

    # Validate fields
    lines_list = parsed.get("lines", [])
    if not isinstance(lines_list, list):
        lines_list = []

    lines = []
    reconstructed_text_lines = []
    for idx, l in enumerate(lines_list):
        line_str = ""
        if isinstance(l, dict):
            line_str = str(l.get("text", "")).strip()
        elif isinstance(l, str):
            line_str = l.strip()

        if line_str:
            lines.append({"line_number": idx + 1, "text": line_str})
            reconstructed_text_lines.append(line_str)

    # Main text
    full_text = str(parsed.get("text", "")).strip()
    if not full_text and reconstructed_text_lines:
        full_text = "\n".join(reconstructed_text_lines)

    # Clean stray line artifacts like sole underscores or dashes
    cleaned_lines = []
    for line in full_text.splitlines():
        line_s = line.strip()
        if line_s in ["_", "-", "~", "—", "--", "__"]:
            continue
        cleaned_lines.append(line)
    full_text = "\n".join(cleaned_lines).strip()

    # Confidence calculation & status assignment
    raw_conf = parsed.get("confidence", 85)
    if not isinstance(raw_conf, (int, float)) or np.isnan(raw_conf) or np.isinf(raw_conf):
        raw_conf = 85.0
    else:
        raw_conf = float(raw_conf)
        if 0.0 < raw_conf <= 1.0:
            raw_conf = raw_conf * 100.0

    confidence = round(max(0.0, min(100.0, raw_conf)), 1)

    status = str(parsed.get("status", "")).lower().strip()
    if status not in ["good", "moderate", "low"] or confidence < 70.0:
        if confidence >= 90.0 and status != "low":
            status = "good"
        elif confidence >= 70.0 and status != "low":
            status = "moderate"
        else:
            status = "low"


    uncertain_words = parsed.get("uncertain_words", [])
    if not isinstance(uncertain_words, list):
        uncertain_words = []
    uncertain_words = [str(w).strip() for w in uncertain_words if str(w).strip()]

    # Check for [unclear] tags in text
    unclear_count = full_text.count("[unclear]")
    if unclear_count > 0 and confidence > 75.0:
        # Adjust confidence down slightly for each unclear word
        confidence = max(50.0, confidence - (unclear_count * 5.0))
        if confidence < 70.0:
            status = "low"
        elif confidence < 90.0:
            status = "moderate"

    return {
        "text": full_text if full_text else "No handwritten text recognized.",
        "lines": lines,
        "confidence": confidence,
        "status": status,
        "uncertain_words": uncertain_words,
        "engine": "gemini_vision"
    }


def extract_handwritten_text(original_image_path, processed_image_path=None):
    """
    Primary Handwriting OCR Engine powered by Gemini Vision AI.
    
    Returns dictionary:
    - text (str): Transcribed handwritten text (preserving line breaks and paragraphs)
    - lines (list): Array of line objects [{"line_number": 1, "text": "..."}]
    - confidence (float): 0.0 to 100.0
    - status (str): 'good', 'moderate', or 'low'
    - uncertain_words (list): List of unconfident words
    - engine (str): 'gemini_vision' (or 'easyocr_fallback' if fallback triggered)
    """
    start_time = time.time()
    api_key = Config.GEMINI_API_KEY or os.getenv('GEMINI_API_KEY', '')
    model_name = Config.GEMINI_MODEL or os.getenv('GEMINI_MODEL', 'gemini-3.6-flash')

    # Always use the untouched ORIGINAL handwriting image as primary AI input
    ocr_ready_path = original_image_path

    if not api_key:
        print("Gemini API key missing. Invoking EasyOCR fallback...")
        return _fallback_easyocr(ocr_ready_path)


    # 1. First Attempt: Gemini Vision AI OCR
    try:
        raw_response = _call_gemini_ocr_api(ocr_ready_path, AI_OCR_PROMPT, api_key, model_name)
        res = _parse_and_validate_ocr_json(raw_response)
    except Exception as err1:
        print(f"Gemini OCR Attempt 1 failed ({err1}). Retrying with strict JSON prompt...")
        # 2. Retry Attempt
        try:
            raw_response = _call_gemini_ocr_api(ocr_ready_path, RETRY_STRICT_OCR_PROMPT, api_key, model_name)
            res = _parse_and_validate_ocr_json(raw_response)
        except Exception as err2:
            print(f"Gemini OCR Retry failed ({err2}). Falling back to EasyOCR...")
            return _fallback_easyocr(ocr_ready_path)

    elapsed = round(time.time() - start_time, 2)
    
    # Dev mode logging (no API keys logged)
    img_dim = "N/A"
    try:
        img_temp = cv2.imread(ocr_ready_path)
        if img_temp is not None:
            img_dim = f"{img_temp.shape[1]}x{img_temp.shape[0]}"
    except Exception:
        pass

    unclear_word_count = res['text'].count("[unclear]")
    print(f"[OCR LOG] Engine: {res['engine']} | Time: {elapsed}s | Dim: {img_dim} | Conf: {res['confidence']}% | Status: {res['status']} | Lines: {len(res['lines'])} | Uncertain Words: {unclear_word_count}")

    return res


def _fallback_easyocr(image_path):
    """Fallback EasyOCR execution when Gemini API is unavailable."""
    from services.ocr import extract_text_from_image
    txt, conf, status, raw = extract_text_from_image(image_path)
    
    # Format line objects
    lines = []
    for idx, line in enumerate(txt.splitlines()):
        if line.strip():
            lines.append({"line_number": idx + 1, "text": line.strip()})

    return {
        "text": txt,
        "lines": lines,
        "confidence": round(conf * 100.0, 1),
        "status": "low" if status == "Low" else "moderate",
        "uncertain_words": [],
        "engine": "easyocr_fallback"
    }
