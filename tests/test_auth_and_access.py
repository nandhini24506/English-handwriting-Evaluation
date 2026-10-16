"""Automated unit tests for auth.py and teacher.py in EHE 2.0.

Tests password hashing, verification, form validation, role constraints,
and ownership isolation.
"""

from auth import (
    validate_registration_form,
    hash_password,
    verify_password,
    ALLOWED_ROLES,
)
from teacher import (
    verify_evaluation_access,
    calculate_cohort_stats,
)


def test_password_hashing_and_verification():
    raw_pw = "SecurePass123!"
    pw_hash = hash_password(raw_pw)

    assert pw_hash != raw_pw
    assert verify_password(raw_pw, pw_hash) is True
    assert verify_password("WrongPassword", pw_hash) is False
    assert verify_password("", pw_hash) is False


def test_validate_registration_form():
    # Valid student
    valid, err = validate_registration_form("Deepak", "deepak@example.edu", "pass123", "student")
    assert valid is True
    assert err is None

    # Invalid email
    valid, err = validate_registration_form("Deepak", "notanemail", "pass123", "student")
    assert valid is False
    assert "email" in err.lower()

    # Short password (<6 chars)
    valid, err = validate_registration_form("Deepak", "deepak@example.edu", "123", "student")
    assert valid is False
    assert "at least 6 characters" in err

    # Invalid role
    valid, err = validate_registration_form("Deepak", "deepak@example.edu", "pass123", "admin")
    assert valid is False
    assert "role" in err.lower()


def test_evaluation_access_isolation():
    evaluation = {"id": 10, "user_id": 42}

    # Student 42 owns the evaluation
    assert verify_evaluation_access(evaluation, current_user_id=42, current_user_role="student") is True

    # Peer student 99 does NOT own the evaluation -> Access Denied!
    assert verify_evaluation_access(evaluation, current_user_id=99, current_user_role="student") is False

    # Teacher has supervisory access to view all evaluations
    assert verify_evaluation_access(evaluation, current_user_id=1, current_user_role="teacher") is True


def test_cohort_stats_calculation():
    students = [{"id": 1}, {"id": 2}]
    evaluations = [
        {"overall_score": 80.0, "grade": "A"},
        {"overall_score": 60.0, "grade": "C"},
    ]
    stats = calculate_cohort_stats(evaluations, students)
    assert stats["total_students"] == 2
    assert stats["total_evaluations"] == 2
    assert stats["class_average"] == 70.0
    assert stats["grade_distribution"]["A"] == 1
    assert stats["grade_distribution"]["C"] == 1
