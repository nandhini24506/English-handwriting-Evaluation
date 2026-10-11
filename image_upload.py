"""Secure image upload validation and storage module for EHE 2.0.

Ensures real file content validation (Pillow header & integrity check),
safe unique filenames, strict extension and MIME verification,
and compute SHA-256 image hashes for evaluation caching.
"""

import hashlib
import io
import os
import uuid
import time
from typing import Tuple
from PIL import Image, ImageOps
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MIN_IMAGE_DIMENSION = 80
MAX_IMAGE_DIMENSION = 10000


def is_allowed_extension(filename: str) -> bool:
    """Checks whether the filename has an allowed extension."""
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def compute_bytes_hash(file_bytes: bytes) -> str:
    """Computes SHA-256 hash of file bytes for caching and tamper verification."""
    return hashlib.sha256(file_bytes).hexdigest()


def validate_image_content(file_bytes: bytes) -> Tuple[int, int, str]:
    """Validates real image binary content using Pillow.

    Returns (width, height, format).
    Raises ValueError on invalid, corrupted, or unsupported images.
    """
    if not file_bytes:
        raise ValueError("Uploaded file is empty (0 bytes).")

    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise ValueError(
            f"File size exceeds the maximum limit of {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB."
        )

    try:
        image_stream = io.BytesIO(file_bytes)
        with Image.open(image_stream) as img:
            # Check format
            img_format = (img.format or "").upper()
            if img_format not in {"JPEG", "JPG", "PNG"}:
                raise ValueError(
                    f"Unsupported image format: '{img_format}'. Only JPEG and PNG are permitted."
                )

            # Pillow verify checks file integrity and headers
            img.verify()

        # Reopen to read dimensions after verify() clears internal state
        image_stream.seek(0)
        with Image.open(image_stream) as img:
            width, height = img.size

        if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
            raise ValueError(
                f"Image is too small ({width}x{height}px). Minimum size is {MIN_IMAGE_DIMENSION}x{MIN_IMAGE_DIMENSION}px."
            )

        if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
            raise ValueError(
                f"Image dimensions ({width}x{height}px) exceed the maximum supported dimension of {MAX_IMAGE_DIMENSION}px."
            )

        return width, height, img_format

    except Exception as err:
        if isinstance(err, ValueError):
            raise
        raise ValueError("Corrupt or invalid image file. Please upload a standard photo or scan.") from err


def save_uploaded_file(file_storage, upload_folder: str) -> Tuple[str, str, str]:
    """Validates and safely stores an uploaded file from a Flask request.

    Returns (saved_filename, full_file_path, sha256_hash).
    """
    if not file_storage or not getattr(file_storage, "filename", None):
        raise ValueError("No file was selected for upload.")

    original_filename = file_storage.filename
    if not is_allowed_extension(original_filename):
        raise ValueError("Only JPG, JPEG, and PNG image files are allowed.")

    file_bytes = file_storage.read()
    validate_image_content(file_bytes)

    # Secure base filename
    safe_base = secure_filename(original_filename)
    if not safe_base:
        safe_base = "handwriting.jpg"

    ext = safe_base.rsplit(".", 1)[1].lower() if "." in safe_base else "jpg"
    stem = safe_base.rsplit(".", 1)[0]
    unique_id = uuid.uuid4().hex[:8]
    timestamp = int(time.time())
    unique_filename = f"{timestamp}_{unique_id}_{stem}.{ext}"

    os.makedirs(upload_folder, exist_ok=True)
    destination_path = os.path.join(upload_folder, unique_filename)

    with open(destination_path, "wb") as f:
        f.write(file_bytes)

    sha256_hash = compute_bytes_hash(file_bytes)
    return unique_filename, destination_path, sha256_hash
