CREATE DATABASE IF NOT EXISTS handwriting_db;
USE handwriting_db;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'student'
);

CREATE TABLE evaluations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    image_path VARCHAR(255) NOT NULL,
    extracted_text TEXT NOT NULL,
    letter_formation DECIMAL(5,2) NOT NULL,
    word_spacing DECIMAL(5,2) NOT NULL,
    alignment DECIMAL(5,2) NOT NULL,
    slant_consistency DECIMAL(5,2) NOT NULL,
    size_consistency DECIMAL(5,2) NOT NULL,
    legibility DECIMAL(5,2) NOT NULL,
    overall_score DECIMAL(5,2) NOT NULL,
    grade VARCHAR(2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
