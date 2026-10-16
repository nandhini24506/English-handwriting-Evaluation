"""Automated integration tests for Flask web routes in EHE 2.0.

Tests login, dashboard, upload view, history view, result view, and PDF download.
"""

import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        yield client


def test_home_redirects_to_login(client):
    res = client.get("/")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


def test_login_page_renders(client):
    res = client.get("/login")
    assert res.status_code == 200
    assert b"Welcome to EHE 2.0" in res.data
    assert b"Sign In" in res.data


def test_register_page_renders(client):
    res = client.get("/register")
    assert res.status_code == 200
    assert b"Create an Account" in res.data
    assert b"Account Role" not in res.data
    assert b"Email Address" in res.data


def test_protected_routes_redirect_unauthenticated(client):
    protected_paths = ["/dashboard", "/upload", "/practice", "/progress", "/history", "/teacher/classes"]
    for path in protected_paths:
        res = client.get(path)
        assert res.status_code == 302
        assert "/login" in res.headers["Location"]


def test_authenticated_student_session(client):
    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["name"] = "Deepak"
        sess["role"] = "student"
        sess["csrf_token"] = "test_csrf_token"

    res = client.get("/dashboard")
    assert res.status_code == 200
    assert b"Deepak" in res.data
    assert b"Evaluate Handwriting" in res.data

    res_upload = client.get("/upload")
    assert res_upload.status_code == 200
    assert b"Evaluate Handwriting Sample" in res_upload.data

    res_practice = client.get("/practice")
    assert res_practice.status_code == 200
    assert b"Personalised Practice Centre" in res_practice.data

    res_history = client.get("/history")
    assert res_history.status_code == 200
    assert b"Evaluation History" in res_history.data

    # Test viewing evaluation #1
    res_result = client.get("/result/1")
    assert res_result.status_code == 200
    assert b"Evaluation Report #1" in res_result.data
    assert b"Download PDF Report" in res_result.data

    # Test downloading PDF for evaluation #1
    res_pdf = client.get("/result/1/download-pdf")
    assert res_pdf.status_code == 200
    assert res_pdf.headers["Content-Type"] == "application/pdf"
    assert res_pdf.data.startswith(b"%PDF-")


def test_upload_and_evaluate_pipeline_mocked(client, monkeypatch):
    """End-to-end workflow test: image upload, OpenCV CV extraction, deterministic scoring, and DB persistence."""
    from PIL import Image
    import io

    # Mock external NVIDIA API call
    mock_ai_response = {
        "transcription": "Practice makes perfection.",
        "metrics": {
            "letter_formation": {"score": 82.0, "explanation": "Neat oval closures.", "evidence": "Consistent loops."},
            "word_spacing": {"score": 78.0, "explanation": "Regular word gaps.", "evidence": "Uniform intervals."},
            "alignment": {"score": 85.0, "explanation": "Straight baseline.", "evidence": "Parallel to ruling."},
            "slant_consistency": {"score": 75.0, "explanation": "Slight forward angle.", "evidence": "Even tilt."},
            "size_consistency": {"score": 80.0, "explanation": "Uniform x-height.", "evidence": "Proportional caps."},
            "legibility": {"score": 88.0, "explanation": "Easily legible.", "evidence": "Distinct letters."},
        },
        "overall_summary": "Solid handwriting sample.",
    }
    monkeypatch.setattr("ai_client.call_ai_multimodal_api", lambda *args, **kwargs: mock_ai_response)
    monkeypatch.setattr("ai_client.call_nvidia_multimodal_api", lambda *args, **kwargs: mock_ai_response)
    monkeypatch.setattr("ai_client.call_gemini_multimodal_api", lambda *args, **kwargs: mock_ai_response)

    # Create dummy handwriting image
    buf = io.BytesIO()
    img = Image.new("RGB", (300, 300), color=(255, 255, 255))
    img.save(buf, format="JPEG")
    buf.seek(0)

    with client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["name"] = "Deepak"
        sess["role"] = "student"
        sess["csrf_token"] = "valid_csrf_token"

    res = client.post(
        "/upload",
        data={
            "image": (buf, "test_handwriting.jpg"),
            "csrf_token": "valid_csrf_token",
        },
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"Evaluation Report #" in res.data
    assert b"Overall Evaluation Score" in res.data
    assert b"Practice makes perfection." in res.data
