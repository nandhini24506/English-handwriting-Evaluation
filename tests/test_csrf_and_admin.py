"""Automated test suite for CSRF security protection, public registration constraints, and admin subsystem in EHE 2.0.
"""

import re
import pytest
from app import app
import auth
import database


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def get_token_from_html(html_str: str) -> str:
    """Helper to extract CSRF token from rendered HTML form."""
    match = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', html_str)
    assert match, "CSRF token hidden input not found in rendered HTML"
    return match.group(1)


def test_csrf_token_injected_on_get_routes(client):
    """GET /login and GET /register must automatically provide a valid CSRF token."""
    # Test Login
    res_login = client.get("/login")
    assert res_login.status_code == 200
    token_login = get_token_from_html(res_login.data.decode("utf-8"))
    assert len(token_login) >= 24

    # Test Register
    res_reg = client.get("/register")
    assert res_reg.status_code == 200
    token_reg = get_token_from_html(res_reg.data.decode("utf-8"))
    assert len(token_reg) >= 24


def test_post_missing_csrf_token_rejected(client):
    """POST request without CSRF token must be rejected."""
    res = client.post(
        "/register",
        data={"name": "Alice Tester", "email": "alice@example.com", "password": "password123"},
        follow_redirects=True,
    )
    # Rejection should show session security notice or flash error
    assert b"security token was invalid or has expired" in res.data or b"Security Token Expired" in res.data


def test_post_invalid_csrf_token_rejected(client):
    """POST request with tampered/invalid CSRF token must be rejected."""
    # First visit page to initialize session
    client.get("/register")
    res = client.post(
        "/register",
        data={
            "csrf_token": "tampered_fake_token_12345",
            "name": "Bob Tester",
            "email": "bob@example.com",
            "password": "password123",
        },
        follow_redirects=True,
    )
    assert b"security token was invalid or has expired" in res.data or b"Security Token Expired" in res.data


def test_public_registration_contains_no_role_selector(client):
    """Public registration form must not have any Account Role dropdown or role field."""
    res = client.get("/register")
    assert res.status_code == 200
    assert b"Account Role" not in res.data
    assert b"<select id=\"role\"" not in res.data
    assert b"Full Name" in res.data
    assert b"Email Address" in res.data
    assert b"Password" in res.data


def test_public_registration_role_escalation_rejected(client):
    """Attempting to submit role=admin or role=teacher via public registration must be rejected."""
    res_get = client.get("/register")
    token = get_token_from_html(res_get.data.decode("utf-8"))

    # Attempt to submit role=admin
    res = client.post(
        "/register",
        data={
            "csrf_token": token,
            "name": "Attacker Admin",
            "email": "escalate_admin@test.com",
            "password": "password123",
            "role": "admin",
        },
        follow_redirects=True,
    )
    assert res.status_code == 400
    assert b"Privileged account roles cannot be created via public registration" in res.data

    # Attempt to submit role=teacher
    res2 = client.post(
        "/register",
        data={
            "csrf_token": token,
            "name": "Attacker Teacher",
            "email": "escalate_teacher@test.com",
            "password": "password123",
            "role": "teacher",
        },
        follow_redirects=True,
    )
    assert res2.status_code == 400
    assert b"Privileged account roles cannot be created via public registration" in res2.data


def test_valid_public_registration_creates_student(client):
    """Valid public registration must succeed and create a student account."""
    res_get = client.get("/register")
    token = get_token_from_html(res_get.data.decode("utf-8"))
    unique_email = f"student_new_{auth.secrets.token_hex(4)}@test.com"

    res = client.post(
        "/register",
        data={
            "csrf_token": token,
            "name": "New Student",
            "email": unique_email,
            "password": "password123",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"Account successfully created" in res.data

    # Verify user in database is strictly student
    user = database.find_user_by_email(unique_email)
    assert user is not None
    assert user["role"] == "student"


def test_admin_login_page_renders_cleanly(client):
    """GET /admin/login renders with Admin Sign In and no role selector."""
    res = client.get("/admin/login")
    assert res.status_code == 200
    assert b"Admin Sign In" in res.data
    assert b"Sign in to manage EHE 2.0" in res.data
    assert b"Account Role" not in res.data
    assert b"csrf_token" in res.data


def test_admin_login_with_valid_credentials(client):
    """Valid admin credentials log in successfully and redirect to /admin."""
    # Ensure admin user exists
    admin_email = f"admin_{auth.secrets.token_hex(4)}@test.com"
    pw_hash = auth.hash_password("SuperSecretAdminPass123!")
    database.create_user("Test Admin", admin_email, pw_hash, role="admin")

    res_get = client.get("/admin/login")
    token = get_token_from_html(res_get.data.decode("utf-8"))

    res = client.post(
        "/admin/login",
        data={
            "csrf_token": token,
            "email": admin_email,
            "password": "SuperSecretAdminPass123!",
        },
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"EHE 2.0 Administration" in res.data
    assert b"Sign Out (Admin)" in res.data


def test_admin_login_with_invalid_credentials_rejected(client):
    """Admin login with wrong password fails with 401."""
    res_get = client.get("/admin/login")
    token = get_token_from_html(res_get.data.decode("utf-8"))

    res = client.post(
        "/admin/login",
        data={
            "csrf_token": token,
            "email": "admin@ehe.local",
            "password": "WrongPassword123!",
        },
    )
    assert res.status_code == 401
    assert b"Invalid administrator email address or password" in res.data


def test_admin_login_denies_student_accounts(client):
    """Student account attempting to log in at /admin/login is denied with 403."""
    student_email = f"student_{auth.secrets.token_hex(4)}@test.com"
    pw_hash = auth.hash_password("StudentPass123!")
    database.create_user("Normal Student", student_email, pw_hash, role="student")

    res_get = client.get("/admin/login")
    token = get_token_from_html(res_get.data.decode("utf-8"))

    res = client.post(
        "/admin/login",
        data={
            "csrf_token": token,
            "email": student_email,
            "password": "StudentPass123!",
        },
    )
    assert res.status_code == 403
    assert b"does not possess administrator privileges" in res.data


def test_anonymous_access_to_admin_dashboard_redirects(client):
    """Anonymous user accessing /admin must be redirected to /admin/login."""
    res = client.get("/admin")
    assert res.status_code == 302
    assert "/admin/login" in res.headers["Location"]


def test_student_and_teacher_denied_from_admin_dashboard(client):
    """Student and teacher sessions accessing /admin receive HTTP 403 Forbidden."""
    # Student
    with client.session_transaction() as sess:
        sess["user_id"] = 101
        sess["name"] = "Student Sam"
        sess["role"] = "student"
        sess["csrf_token"] = "valid_token"

    res_student = client.get("/admin")
    assert res_student.status_code == 403

    # Teacher
    with client.session_transaction() as sess:
        sess["user_id"] = 102
        sess["name"] = "Teacher Tina"
        sess["role"] = "teacher"
        sess["csrf_token"] = "valid_token"

    res_teacher = client.get("/admin")
    assert res_teacher.status_code == 403


def test_admin_dashboard_displays_real_metrics(client):
    """Admin dashboard renders real user counts, evaluations, and accounts list."""
    with client.session_transaction() as sess:
        sess["user_id"] = 999
        sess["name"] = "Chief Admin"
        sess["role"] = "admin"
        sess["csrf_token"] = "valid_token"

    res = client.get("/admin")
    assert res.status_code == 200
    assert b"EHE 2.0 Administration" in res.data
    assert b"Total Registered Users" in res.data
    assert b"Total Evaluations" in res.data
    assert b"User Accounts Management" in res.data


def test_admin_logout_invalidates_session(client):
    """POST /admin/logout clears session and redirects to /admin/login."""
    with client.session_transaction() as sess:
        sess["user_id"] = 999
        sess["name"] = "Chief Admin"
        sess["role"] = "admin"
        sess["csrf_token"] = "admin_valid_csrf"

    res = client.post(
        "/admin/logout",
        data={"csrf_token": "admin_valid_csrf"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"Admin Sign In" in res.data

    # Confirm admin dashboard is now inaccessible
    res_after = client.get("/admin")
    assert res_after.status_code == 302
    assert "/admin/login" in res_after.headers["Location"]
