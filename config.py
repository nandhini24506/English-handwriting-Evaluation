import os
from dotenv import load_dotenv

# Load environment variables from .env file if available
load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    BASE_DIR = BASE_DIR
    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'handwriting_eval_secret_key_college_project_2026')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() in ['true', '1', 't']
    
    # Database settings (MySQL)
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'handwriting_evaluation')
    
    # File upload settings
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB Max limit
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

    # Gemini Vision API Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-3.6-flash')

    # OCR Engine Configuration
    OCR_ENGINE = os.getenv('OCR_ENGINE', 'gemini')
    OCR_FALLBACK = os.getenv('OCR_FALLBACK', 'easyocr')


    
    # Feature Evaluation Weights
    FEATURE_WEIGHTS = {
        'letter_formation': 0.20,
        'word_spacing': 0.20,
        'alignment': 0.20,
        'slant_consistency': 0.15,
        'size_consistency': 0.10,
        'legibility': 0.15
    }

    # Grading thresholds
    GRADE_THRESHOLDS = [
        (90.0, 'A+'),
        (80.0, 'A'),
        (70.0, 'B'),
        (60.0, 'C'),
        (50.0, 'D'),
        (0.0,  'F')
    ]

    @staticmethod
    def get_grade(score):
        """Convert score (0-100) into a letter grade."""
        for threshold, grade in Config.GRADE_THRESHOLDS:
            if score >= threshold:
                return grade
        return 'F'
