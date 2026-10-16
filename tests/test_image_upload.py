"""Automated unit tests for image_upload.py in EHE 2.0.

Tests real file content inspection, extension filters, size boundaries,
and corrupted file rejection.
"""

import io
import pytest
from PIL import Image
from image_upload import (
    is_allowed_extension,
    validate_image_content,
    compute_bytes_hash,
)


def create_test_image_bytes(format="JPEG", size=(200, 200), color=(255, 255, 255)) -> bytes:
    """Helper creating in-memory valid image bytes."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color)
    img.save(buf, format=format)
    return buf.getvalue()


def test_allowed_extensions():
    assert is_allowed_extension("sample.jpg") is True
    assert is_allowed_extension("sample.jpeg") is True
    assert is_allowed_extension("sample.png") is True
    assert is_allowed_extension("sample.JPG") is True
    assert is_allowed_extension("document.pdf") is False
    assert is_allowed_extension("script.py") is False
    assert is_allowed_extension("image.gif") is False
    assert is_allowed_extension("") is False


def test_validate_valid_jpeg():
    valid_bytes = create_test_image_bytes(format="JPEG", size=(300, 300))
    w, h, fmt = validate_image_content(valid_bytes)
    assert w == 300
    assert h == 300
    assert fmt == "JPEG"


def test_validate_valid_png():
    valid_bytes = create_test_image_bytes(format="PNG", size=(250, 150))
    w, h, fmt = validate_image_content(valid_bytes)
    assert w == 250
    assert h == 150
    assert fmt == "PNG"


def test_empty_bytes_rejected():
    with pytest.raises(ValueError, match="empty"):
        validate_image_content(b"")


def test_corrupted_bytes_rejected():
    corrupted = b"NOT_A_REAL_IMAGE_BINARY_DATA_XYZ"
    with pytest.raises(ValueError, match="Corrupt or invalid"):
        validate_image_content(corrupted)


def test_too_small_dimensions_rejected():
    tiny = create_test_image_bytes(format="JPEG", size=(30, 30))
    with pytest.raises(ValueError, match="too small"):
        validate_image_content(tiny)


def test_compute_bytes_hash():
    data = b"Handwriting test bytes"
    h1 = compute_bytes_hash(data)
    h2 = compute_bytes_hash(data)
    assert h1 == h2
    assert len(h1) == 64
