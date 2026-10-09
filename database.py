import os
import mysql.connector
from mysql.connector import Error


def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "handwriting_db"),
    )


def initialize_database():
    connection = None
    cursor = None
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3306")),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
        )
        cursor = connection.cursor()
        database_name = os.getenv("DB_NAME", "handwriting_db")
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{database_name}`")
        connection.database = database_name
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(150) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'student'
            )"""
        )
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS evaluations (
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
            )"""
        )
        connection.commit()
    except Error as error:
        raise RuntimeError(f"Database setup failed: {error}") from error
    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


def create_user(name, email, password_hash, role="student"):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
            (name, email, password_hash, role),
        )
        connection.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        connection.close()


def find_user_by_email(email):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        return cursor.fetchone()
    finally:
        cursor.close()
        connection.close()


def save_evaluation(user_id, image_path, extracted_text, scores, overall_score, grade):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """INSERT INTO evaluations (
                user_id, image_path, extracted_text, letter_formation,
                word_spacing, alignment, slant_consistency, size_consistency,
                legibility, overall_score, grade
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                user_id,
                image_path,
                extracted_text,
                scores["letter_formation"],
                scores["word_spacing"],
                scores["alignment"],
                scores["slant_consistency"],
                scores["size_consistency"],
                scores["legibility"],
                overall_score,
                grade,
            ),
        )
        connection.commit()
        return cursor.lastrowid
    finally:
        cursor.close()
        connection.close()


def get_evaluation(evaluation_id, user_id=None):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        query = """SELECT evaluations.*, users.name, users.email
                   FROM evaluations JOIN users ON evaluations.user_id = users.id
                   WHERE evaluations.id = %s"""
        parameters = [evaluation_id]
        if user_id is not None:
            query += " AND evaluations.user_id = %s"
            parameters.append(user_id)
        cursor.execute(query, parameters)
        return cursor.fetchone()
    finally:
        cursor.close()
        connection.close()


def get_user_evaluations(user_id):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT * FROM evaluations WHERE user_id = %s ORDER BY created_at DESC",
            (user_id,),
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()


def get_teacher_evaluations():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT evaluations.id, users.name, users.email, evaluations.overall_score,
                      evaluations.grade, evaluations.created_at
               FROM evaluations JOIN users ON evaluations.user_id = users.id
               WHERE users.role = 'student'
               ORDER BY evaluations.created_at DESC"""
        )
        return cursor.fetchall()
    finally:
        cursor.close()
        connection.close()
