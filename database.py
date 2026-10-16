"""Database management, migration, and query layer for EHE 2.0.

Provides centralized parameterized MySQL operations:
  - Safe migrations without resetting or dropping existing tables/data
  - User management and authentication lookups
  - Evaluation persistence (storing CV metrics, AI feedback, and overall scores)
  - OCR correction history
  - Evaluation SHA-256 caching
  - Teacher classes, student memberships, and assignments
  - Personalised practice tracking
"""

import json
import os
from typing import Dict, Any, List, Optional
import mysql.connector
from mysql.connector import Error


def get_connection():
    """Establishes and returns a connection to MySQL."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "handwriting_db"),
    )


def initialize_database():
    """Initializes database schema safely without dropping existing tables or data.

    Applies non-destructive ALTER TABLE checks to upgrade existing deployments.
    """
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

        # Users table
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(150) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'student',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )

        # Classes table
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS classes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                teacher_id INT NOT NULL,
                name VARCHAR(150) NOT NULL,
                code VARCHAR(20) NOT NULL UNIQUE,
                description TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE
            )"""
        )

        # Class members
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS class_members (
                id INT AUTO_INCREMENT PRIMARY KEY,
                class_id INT NOT NULL,
                user_id INT NOT NULL,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_class_user (class_id, user_id),
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )"""
        )

        # Assignments
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS assignments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                class_id INT NOT NULL,
                teacher_id INT NOT NULL,
                title VARCHAR(200) NOT NULL,
                description TEXT DEFAULT NULL,
                due_date DATE DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE,
                FOREIGN KEY (teacher_id) REFERENCES users(id) ON DELETE CASCADE
            )"""
        )

        # Evaluations table
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

        # Non-destructive migrations for evaluations table columns
        cursor.execute(
            """SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
               WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'evaluations'""",
            (database_name,),
        )
        existing_cols = {row[0] for row in cursor.fetchall()}

        if "image_hash" not in existing_cols:
            cursor.execute("ALTER TABLE evaluations ADD COLUMN image_hash VARCHAR(64) DEFAULT NULL")
        if "cv_features_json" not in existing_cols:
            cursor.execute("ALTER TABLE evaluations ADD COLUMN cv_features_json MEDIUMTEXT DEFAULT NULL")
        if "ai_feedback_json" not in existing_cols:
            cursor.execute("ALTER TABLE evaluations ADD COLUMN ai_feedback_json MEDIUMTEXT DEFAULT NULL")
        # Non-destructive migrations for users table columns
        cursor.execute(
            """SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
               WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users'""",
            (database_name,),
        )
        existing_user_cols = {row[0] for row in cursor.fetchall()}
        if "created_at" not in existing_user_cols:
            cursor.execute("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

        if "assignment_id" not in existing_cols:
            cursor.execute("ALTER TABLE evaluations ADD COLUMN assignment_id INT DEFAULT NULL")

        # OCR Corrections table
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS ocr_corrections (
                id INT AUTO_INCREMENT PRIMARY KEY,
                evaluation_id INT NOT NULL,
                user_id INT NOT NULL,
                original_text TEXT NOT NULL,
                corrected_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (evaluation_id) REFERENCES evaluations(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )"""
        )

        # Practice Activities table
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS practice_activities (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                evaluation_id INT DEFAULT NULL,
                metric_targeted VARCHAR(50) NOT NULL,
                exercise_title VARCHAR(200) NOT NULL,
                exercise_text TEXT NOT NULL,
                completed TINYINT(1) DEFAULT 0,
                completed_at TIMESTAMP NULL DEFAULT NULL,
                notes TEXT DEFAULT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )"""
        )

        # Evaluation Cache table
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS evaluation_cache (
                id INT AUTO_INCREMENT PRIMARY KEY,
                image_hash VARCHAR(64) NOT NULL UNIQUE,
                response_json MEDIUMTEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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


# =========================================================================
# User Management
# =========================================================================

def create_user(name: str, email: str, password_hash: str, role: str = "student") -> int:
    """Inserts a new user record."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
            (name, email, password_hash, role),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        cur.close()
        conn.close()


def find_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Retrieves a user by email."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


def find_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves a user by user ID."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, name, email, role, created_at FROM users WHERE id = %s", (user_id,))
        return cur.fetchone()
    finally:
        cur.close()
        conn.close()


def list_students() -> List[Dict[str, Any]]:
    """Lists all registered students."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id, name, email, role, created_at FROM users WHERE role = 'student' ORDER BY name ASC")
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def get_admin_dashboard_stats() -> Dict[str, Any]:
    """Retrieves high-level summary statistics for the admin dashboard."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT COUNT(*) AS total_users FROM users")
        total_users = cur.fetchone()["total_users"]

        cur.execute("SELECT COUNT(*) AS total_students FROM users WHERE role = 'student'")
        total_students = cur.fetchone()["total_students"]

        cur.execute("SELECT COUNT(*) AS total_teachers FROM users WHERE role = 'teacher'")
        total_teachers = cur.fetchone()["total_teachers"]

        cur.execute("SELECT COUNT(*) AS total_admins FROM users WHERE role = 'admin'")
        total_admins = cur.fetchone()["total_admins"]

        cur.execute("SELECT COUNT(*) AS total_evaluations FROM evaluations")
        total_evaluations = cur.fetchone()["total_evaluations"]

        cur.execute("SELECT COUNT(*) AS total_classes FROM classes")
        total_classes = cur.fetchone()["total_classes"]

        return {
            "total_users": total_users,
            "total_students": total_students,
            "total_teachers": total_teachers,
            "total_admins": total_admins,
            "total_evaluations": total_evaluations,
            "total_classes": total_classes,
        }
    finally:
        cur.close()
        conn.close()


def list_all_users_for_admin(limit: int = 100) -> List[Dict[str, Any]]:
    """Retrieves list of users with their evaluation counts for the admin overview."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """SELECT u.id, u.name, u.email, u.role, u.created_at,
                      COUNT(e.id) AS evaluation_count
               FROM users u
               LEFT JOIN evaluations e ON u.id = e.user_id
               GROUP BY u.id, u.name, u.email, u.role, u.created_at
               ORDER BY u.id DESC
               LIMIT %s""",
            (limit,),
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def list_recent_evaluations_for_admin(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieves recent evaluation records across all students for the admin dashboard."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """SELECT e.id, e.user_id, u.name AS student_name, u.email AS student_email,
                      e.overall_score, e.grade, e.created_at, e.extracted_text
               FROM evaluations e
               JOIN users u ON e.user_id = u.id
               ORDER BY e.created_at DESC
               LIMIT %s""",
            (limit,),
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


# =========================================================================
# Evaluation Persistence & Queries
# =========================================================================

def _safe_json_dumps(obj: Any) -> Optional[str]:
    """Serializes dictionaries containing numpy primitives safely to JSON string."""
    if obj is None:
        return None

    def _default(o):
        if hasattr(o, "item"):
            return o.item()
        if isinstance(o, (bool,)):
            return bool(o)
        return str(o)

    return json.dumps(obj, default=_default)


def save_evaluation(
    user_id: int,
    image_path: str,
    extracted_text: str,
    scores: Dict[str, float],
    overall_score: float,
    grade: str,
    image_hash: Optional[str] = None,
    cv_features: Optional[Dict[str, Any]] = None,
    ai_feedback: Optional[List[Dict[str, Any]]] = None,
    assignment_id: Optional[int] = None,
) -> int:
    """Saves a completed evaluation record with component scores, CV metrics, and feedback."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cv_json = _safe_json_dumps(cv_features)
        ai_json = _safe_json_dumps(ai_feedback)

        cur.execute(
            """INSERT INTO evaluations (
                user_id, image_path, image_hash, extracted_text,
                letter_formation, word_spacing, alignment,
                slant_consistency, size_consistency, legibility,
                overall_score, grade, cv_features_json, ai_feedback_json,
                assignment_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                user_id,
                image_path,
                image_hash,
                extracted_text,
                scores["letter_formation"],
                scores["word_spacing"],
                scores["alignment"],
                scores["slant_consistency"],
                scores["size_consistency"],
                scores["legibility"],
                overall_score,
                grade,
                cv_json,
                ai_json,
                assignment_id,
            ),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        cur.close()
        conn.close()


def get_evaluation(evaluation_id: int, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """Retrieves an evaluation with student details.

    If user_id is provided, enforces student ownership check.
    """
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        query = """SELECT evaluations.*, users.name, users.email
                   FROM evaluations JOIN users ON evaluations.user_id = users.id
                   WHERE evaluations.id = %s"""
        params = [evaluation_id]
        if user_id is not None:
            query += " AND evaluations.user_id = %s"
            params.append(user_id)
        cur.execute(query, params)
        record = cur.fetchone()
        if record:
            if record.get("cv_features_json"):
                try:
                    record["cv_features"] = json.loads(record["cv_features_json"])
                except Exception:
                    record["cv_features"] = None
            if record.get("ai_feedback_json"):
                try:
                    record["ai_feedback"] = json.loads(record["ai_feedback_json"])
                except Exception:
                    record["ai_feedback"] = None
        return record
    finally:
        cur.close()
        conn.close()


def get_user_evaluations(user_id: int) -> List[Dict[str, Any]]:
    """Retrieves all evaluations for a specific student, newest first."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """SELECT * FROM evaluations
               WHERE user_id = %s
               ORDER BY created_at DESC""",
            (user_id,),
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def get_teacher_evaluations() -> List[Dict[str, Any]]:
    """Retrieves all evaluations submitted by students for the teacher portal."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """SELECT evaluations.id, evaluations.user_id, users.name, users.email,
                      evaluations.overall_score, evaluations.grade, evaluations.created_at,
                      evaluations.image_path, evaluations.assignment_id
               FROM evaluations JOIN users ON evaluations.user_id = users.id
               WHERE users.role = 'student'
               ORDER BY evaluations.created_at DESC"""
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


# =========================================================================
# OCR Corrections
# =========================================================================

def save_ocr_correction(evaluation_id: int, user_id: int, original_text: str, corrected_text: str) -> int:
    """Stores a user-submitted transcription correction."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO ocr_corrections (evaluation_id, user_id, original_text, corrected_text)
               VALUES (%s, %s, %s, %s)""",
            (evaluation_id, user_id, original_text, corrected_text),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        cur.close()
        conn.close()


def get_ocr_corrections(evaluation_id: int) -> List[Dict[str, Any]]:
    """Retrieves corrections recorded for a specific evaluation."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """SELECT ocr_corrections.*, users.name as user_name
               FROM ocr_corrections JOIN users ON ocr_corrections.user_id = users.id
               WHERE evaluation_id = %s
               ORDER BY created_at DESC""",
            (evaluation_id,),
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


# =========================================================================
# Evaluation Cache
# =========================================================================

def get_cached_evaluation(image_hash: str) -> Optional[Dict[str, Any]]:
    """Retrieves completed evaluation response from cache by SHA-256 hash."""
    if not image_hash:
        return None
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT response_json FROM evaluation_cache WHERE image_hash = %s", (image_hash,))
        row = cur.fetchone()
        if row and row.get("response_json"):
            return json.loads(row["response_json"])
        return None
    except Exception:
        return None
    finally:
        cur.close()
        conn.close()


def save_cached_evaluation(image_hash: str, response_data: Dict[str, Any]) -> None:
    """Stores completed evaluation response into cache."""
    if not image_hash or not response_data:
        return
    conn = get_connection()
    cur = conn.cursor()
    try:
        payload = json.dumps(response_data)
        cur.execute(
            """INSERT INTO evaluation_cache (image_hash, response_json)
               VALUES (%s, %s)
               ON DUPLICATE KEY UPDATE response_json = VALUES(response_json)""",
            (image_hash, payload),
        )
        conn.commit()
    except Exception:
        pass
    finally:
        cur.close()
        conn.close()


# =========================================================================
# Personalised Practice Activities
# =========================================================================

def save_practice_activity(
    user_id: int,
    metric_targeted: str,
    exercise_title: str,
    exercise_text: str,
    evaluation_id: Optional[int] = None,
) -> int:
    """Records an assigned practice exercise for a student."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO practice_activities (user_id, evaluation_id, metric_targeted, exercise_title, exercise_text)
               VALUES (%s, %s, %s, %s, %s)""",
            (user_id, evaluation_id, metric_targeted, exercise_title, exercise_text),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        cur.close()
        conn.close()


def mark_practice_completed(activity_id: int, user_id: int, notes: str = "") -> bool:
    """Marks a practice activity as completed by the student."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """UPDATE practice_activities
               SET completed = 1, completed_at = CURRENT_TIMESTAMP, notes = %s
               WHERE id = %s AND user_id = %s""",
            (notes, activity_id, user_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        cur.close()
        conn.close()


def get_user_practice_activities(user_id: int) -> List[Dict[str, Any]]:
    """Retrieves all practice activities for a student."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """SELECT * FROM practice_activities
               WHERE user_id = %s
               ORDER BY created_at DESC""",
            (user_id,),
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


# =========================================================================
# Classes & Assignments
# =========================================================================

def create_class(teacher_id: int, name: str, code: str, description: str = "") -> int:
    """Creates a new class group under a teacher."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO classes (teacher_id, name, code, description)
               VALUES (%s, %s, %s, %s)""",
            (teacher_id, name, code, description),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        cur.close()
        conn.close()


def get_teacher_classes(teacher_id: int) -> List[Dict[str, Any]]:
    """Retrieves all classes created by a teacher with student counts."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """SELECT classes.*, COUNT(class_members.id) as student_count
               FROM classes LEFT JOIN class_members ON classes.id = class_members.class_id
               WHERE classes.teacher_id = %s
               GROUP BY classes.id
               ORDER BY classes.created_at DESC""",
            (teacher_id,),
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def get_student_classes(student_id: int) -> List[Dict[str, Any]]:
    """Retrieves classes joined by a student."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """SELECT classes.*, users.name as teacher_name
               FROM class_members
               JOIN classes ON class_members.class_id = classes.id
               JOIN users ON classes.teacher_id = users.id
               WHERE class_members.user_id = %s
               ORDER BY class_members.joined_at DESC""",
            (student_id,),
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def join_class(student_id: int, class_code: str) -> bool:
    """Enrolls a student in a class using the unique class code."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute("SELECT id FROM classes WHERE code = %s", (class_code.strip().upper(),))
        cls = cur.fetchone()
        if not cls:
            raise ValueError("No class found with that registration code.")
        class_id = cls["id"]

        cur.execute(
            """INSERT IGNORE INTO class_members (class_id, user_id)
               VALUES (%s, %s)""",
            (class_id, student_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        cur.close()
        conn.close()


def create_assignment(class_id: int, teacher_id: int, title: str, description: str, due_date: Optional[str] = None) -> int:
    """Creates a new assignment for a class."""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO assignments (class_id, teacher_id, title, description, due_date)
               VALUES (%s, %s, %s, %s, %s)""",
            (class_id, teacher_id, title, description, due_date if due_date else None),
        )
        conn.commit()
        return cur.lastrowid
    finally:
        cur.close()
        conn.close()


def get_assignments_for_teacher(teacher_id: int) -> List[Dict[str, Any]]:
    """Retrieves all assignments authored by a teacher."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """SELECT assignments.*, classes.name as class_name,
                      COUNT(evaluations.id) as submission_count
               FROM assignments
               JOIN classes ON assignments.class_id = classes.id
               LEFT JOIN evaluations ON assignments.id = evaluations.assignment_id
               WHERE assignments.teacher_id = %s
               GROUP BY assignments.id
               ORDER BY assignments.created_at DESC""",
            (teacher_id,),
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def get_student_assignments(student_id: int) -> List[Dict[str, Any]]:
    """Retrieves active assignments available for a enrolled student."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(
            """SELECT assignments.*, classes.name as class_name, users.name as teacher_name
               FROM assignments
               JOIN classes ON assignments.class_id = classes.id
               JOIN class_members ON classes.id = class_members.class_id
               JOIN users ON assignments.teacher_id = users.id
               WHERE class_members.user_id = %s
               ORDER BY assignments.due_date ASC, assignments.created_at DESC""",
            (student_id,),
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()
