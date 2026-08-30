# English Handwriting Evaluation System

A complete, functional, end-to-end web application built using **Python, Flask, MySQL, OpenCV, and Gemini Vision AI** for evaluating handwritten English text and performing exact handwriting transcription.

---

## 1. Architecture & Pipeline

```text
                    HANDWRITING IMAGE
                           ↓
                    OpenCV Processing
                           ↓
                ┌──────────┴──────────┐
                ↓                     ↓
          AI HANDWRITING         AI OCR
            EVALUATION          TRANSCRIPTION
                ↓                     ↓
          6 handwriting          Text + confidence
             metrics                   ↓
                ↓                  MySQL
          Overall score
                ↓
              Grade
                ↓
           Feedback
                ↓
             MySQL
```

---

## 2. API Quota & Rate Limit Notice

> **API Quota & Availability**: The handwriting evaluation and transcription services use a cloud vision AI API. Usage is subject to the provider's current API quotas, rate limits, pricing, and availability.

---

## 3. Primary AI Vision OCR Engine

Gemini Vision serves as the **Primary OCR Engine** (`services/ai_ocr.py`).

Key Features:
- **Strict Transcription**: Transcribes exact visible text without summarizing, paraphrasing, grammar correction, or spelling alterations.
- **Uncertainty Marking**: Words that cannot be confidently recognized are tagged as `[unclear]`.
- **Notebook Line Ignorance**: Horizontal ruling lines and vertical margin lines are explicitly ignored (no stray `_`, `-`, or `~` artifacts).
- **Structure Preservation**: Line structure and double newline (`\n\n`) paragraph formatting are preserved.
- **Decoupled Scoring**: OCR transcription confidence is completely decoupled from visual handwriting quality scoring. Low OCR confidence never lowers the handwriting score.

EasyOCR remains only as an optional secondary fallback engine (`engine = 'easyocr_fallback'`).

---

## 4. Technology Stack

- **Backend Framework**: Python 3.x, Flask
- **Vision AI Engine**: Gemini Vision API (`gemini-3.6-flash` or configured model)
- **Primary OCR Engine**: Gemini Vision AI (`services/ai_ocr.py`)
- **Fallback OCR Engine**: EasyOCR (`services/ocr.py`)
- **Database**: MySQL (`mysql-connector-python`)
- **Computer Vision**: OpenCV (`cv2`) for non-destructive notebook line removal & deskew
- **Security**: Werkzeug password hashing, Flask sessions, environment variable API keys (`.env`)
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5, FontAwesome, Chart.js

---

## 5. Environment Configuration

Create a `.env` file in the root directory (based on `.env.example`):

```text
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=handwriting_evaluation

SECRET_KEY=super-secret-key-change-in-production
FLASK_DEBUG=True

GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-3.6-flash

OCR_ENGINE=gemini
OCR_FALLBACK=easyocr
```

---

## 6. Evaluation Metrics & Scoring Rubric

The AI Vision model evaluates 6 core handwriting metrics on a 0–100 scale:

1. **Letter Formation**: Shape clarity, stroke consistency, connected letter readability (cursive connections are not penalized).
2. **Word Spacing**: Uniformity of spacing between adjacent words (connected cursive strokes are ignored).
3. **Baseline Alignment**: Horizontal baseline stability (measured independently of notebook ruling lines).
4. **Slant Consistency**: Uniformity of character slant angle (left or right slant style is acceptable; consistency is measured).
5. **Size Consistency**: Relative height and scale consistency across words.
6. **Legibility**: Direct visual readability.

### Weighted Overall Score Calculation

The Flask backend calculates the final score from the 6 metrics:

$$\text{Overall Score} = 0.20 \times \text{Letter Formation} + 0.20 \times \text{Word Spacing} + 0.20 \times \text{Alignment} + 0.15 \times \text{Slant Consistency} + 0.10 \times \text{Size Consistency} + 0.15 \times \text{Legibility}$$

### Grade Mapping

- **90.00 – 100.00**: A+
- **80.00 – 89.99**: A
- **70.00 – 79.99**: B
- **60.00 – 69.99**: C
- **50.00 – 59.99**: D
- **0.00 – 49.99**: F

---

## 7. Setup & Running Instructions

1. **Initialize Database & Seed Accounts**:
   ```bash
   python database/seed.py
   ```

2. **Run Flask Application**:
   ```bash
   python app.py
   ```

3. **Access in Browser**: `http://127.0.0.1:5000`

### Demo Login Credentials

| Role | Email | Password | Details |
| :--- | :--- | :--- | :--- |
| **Student** | `student@college.edu` | `student123` | Roll: `CS2026-042`, Dept: CSE, Year: 4 |
| **Teacher** | `teacher@college.edu` | `teacher123` | Prof. Robert Smith |
