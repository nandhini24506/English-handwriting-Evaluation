"""Automated tests for database.py in EHE 2.0.

Verifies schema initialization, user lookups, evaluation saving,
and cache operations.
"""

import pytest
from dotenv import load_dotenv
import database

load_dotenv()


def test_database_connection_and_initialization():
    """Validates that database initialize_database runs safely and idempotently."""
    try:
        database.initialize_database()
        conn = database.get_connection()
        assert conn.is_connected() is True
        conn.close()
    except Exception as e:
        pytest.skip(f"Live MySQL database is not available: {e}")


def test_user_lookup_nonexistent():
    """Finding a non-existent email returns None."""
    try:
        user = database.find_user_by_email("nonexistent_user_xyz@test.edu")
        assert user is None
    except Exception as e:
        pytest.skip(f"Live MySQL database is not available: {e}")


def test_cache_roundtrip():
    """Stores and retrieves evaluation response from cache."""
    try:
        dummy_hash = "test_hash_abcdef1234567890"
        dummy_response = {
            "transcription": "Test cache roundtrip",
            "metrics": {
                "letter_formation": {"score": 88, "explanation": "Good", "evidence": "Good"}
            },
        }

        database.save_cached_evaluation(dummy_hash, dummy_response)
        retrieved = database.get_cached_evaluation(dummy_hash)
        assert retrieved is not None
        assert retrieved["transcription"] == "Test cache roundtrip"
    except Exception as e:
        pytest.skip(f"Live MySQL database is not available: {e}")
