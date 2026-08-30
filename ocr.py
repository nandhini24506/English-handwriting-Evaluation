import os
import easyocr

# Singleton reader instance
_reader_instance = None

def get_ocr_reader():
    global _reader_instance
    if _reader_instance is None:
        print("Initializing EasyOCR English Reader (quiet CPU mode)...")
        _reader_instance = easyocr.Reader(['en'], gpu=False, verbose=False)
    return _reader_instance

def extract_text_from_image(image_path):
    """
    Extracts text and recognition confidence from handwritten image using EasyOCR.
    
    Returns:
    - extracted_text (str): Main text to present to user (or warning if low confidence)
    - ocr_confidence (float): Overall confidence between 0.0 and 1.0
    - ocr_status (str): 'Good', 'Moderate', or 'Low'
    - raw_text (str): Raw OCR output string for debug / raw view
    """
    if not os.path.exists(image_path):
        return "Low OCR confidence: Image file not found.", 0.0, 'Low', ""

    try:
        reader = get_ocr_reader()
        results = reader.readtext(image_path)

        if not results:
            return "Low OCR confidence: No handwritten text detected. Please upload a clearer, well-lit image.", 0.0, 'Low', ""

        lines = []
        confidences = []
        for bbox, text, prob in results:
            clean_text = text.strip() if text else ""
            if clean_text:
                lines.append(clean_text)
                confidences.append(float(prob))

        if not lines:
            return "Low OCR confidence: No readable text recognized.", 0.0, 'Low', ""

        raw_text = " ".join(lines)
        avg_confidence = round(float(sum(confidences) / len(confidences)), 4) if confidences else 0.0

        # Classify OCR Status based on confidence
        if avg_confidence >= 0.70 and len(raw_text) > 3:
            ocr_status = 'Good'
            extracted_text = raw_text
        elif avg_confidence >= 0.40:
            ocr_status = 'Moderate'
            extracted_text = raw_text
        else:
            ocr_status = 'Low'
            extracted_text = "Low OCR confidence: The handwritten text could not be recognized reliably. Please upload a clearer, well-lit image."

        return extracted_text, avg_confidence, ocr_status, raw_text

    except Exception as e:
        print(f"EasyOCR Error: {e}")
        return f"OCR Error: Unable to process image text ({str(e)})", 0.0, 'Low', ""
