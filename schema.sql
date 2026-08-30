-- English Handwriting Evaluation System Schema (Gemini Vision AI Version)
-- Database Name: handwriting_evaluation

CREATE DATABASE IF NOT EXISTS handwriting_evaluation;
USE handwriting_evaluation;

SET FOREIGN_KEY_CHECKS = 0;

-- Drop tables if they exist to allow clean re-run
DROP TABLE IF EXISTS FEEDBACK;
DROP TABLE IF EXISTS EVALUATION;
DROP TABLE IF EXISTS HANDWRITING_FEATURES;
DROP TABLE IF EXISTS OCR_TEXT;
DROP TABLE IF EXISTS HANDWRITTEN_IMAGE;
DROP TABLE IF EXISTS STUDENT;
DROP TABLE IF EXISTS USER;

SET FOREIGN_KEY_CHECKS = 1;


-- 1. USER Table
CREATE TABLE USER (
    user_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('student', 'teacher')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. STUDENT Table
CREATE TABLE STUDENT (
    student_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT UNIQUE NOT NULL,
    roll_number VARCHAR(50) NOT NULL,
    department VARCHAR(100) NOT NULL,
    year INT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES USER(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. HANDWRITTEN_IMAGE Table
CREATE TABLE HANDWRITTEN_IMAGE (
    image_id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    image_path VARCHAR(255) NOT NULL,
    processed_image_path VARCHAR(255),
    debug_lines_path VARCHAR(255),
    image_quality_score FLOAT DEFAULT 80.0,
    image_quality_status VARCHAR(20) DEFAULT 'Good',
    upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES STUDENT(student_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. OCR_TEXT Table (Gemini Vision AI Primary OCR Engine)
CREATE TABLE OCR_TEXT (
    ocr_id INT PRIMARY KEY AUTO_INCREMENT,
    image_id INT NOT NULL,
    extracted_text TEXT,
    ocr_confidence FLOAT DEFAULT 85.0,
    ocr_status VARCHAR(20) DEFAULT 'good',
    engine VARCHAR(50) DEFAULT 'gemini_vision',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (image_id) REFERENCES HANDWRITTEN_IMAGE(image_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- 5. HANDWRITING_FEATURES Table (Gemini Vision AI 6 Core Metrics)
CREATE TABLE HANDWRITING_FEATURES (
    feature_id INT PRIMARY KEY AUTO_INCREMENT,
    image_id INT NOT NULL,
    letter_formation FLOAT NOT NULL,
    word_spacing FLOAT NOT NULL,
    alignment FLOAT NOT NULL,
    slant FLOAT NOT NULL,
    size_consistency FLOAT NOT NULL,
    legibility FLOAT NOT NULL,
    FOREIGN KEY (image_id) REFERENCES HANDWRITTEN_IMAGE(image_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. EVALUATION Table
CREATE TABLE EVALUATION (
    evaluation_id INT PRIMARY KEY AUTO_INCREMENT,
    feature_id INT NOT NULL,
    score FLOAT NOT NULL,
    grade VARCHAR(5) NOT NULL,
    evaluation_reliability VARCHAR(20) DEFAULT 'High',
    evaluated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (feature_id) REFERENCES HANDWRITING_FEATURES(feature_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. FEEDBACK Table
CREATE TABLE FEEDBACK (
    feedback_id INT PRIMARY KEY AUTO_INCREMENT,
    evaluation_id INT NOT NULL,
    feedback_text TEXT NOT NULL,
    suggestion TEXT NOT NULL,
    strengths TEXT,
    improvements TEXT,
    FOREIGN KEY (evaluation_id) REFERENCES EVALUATION(evaluation_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Indexes for performance
CREATE INDEX idx_user_email ON USER(email);
CREATE INDEX idx_student_user ON STUDENT(user_id);
CREATE INDEX idx_image_student ON HANDWRITTEN_IMAGE(student_id);
CREATE INDEX idx_features_image ON HANDWRITING_FEATURES(image_id);
CREATE INDEX idx_eval_features ON EVALUATION(feature_id);

