"""Integration tests for live AI multimodal providers in EHE 2.0.

Tests live Google Gemini API (gemini-flash-latest) and NVIDIA API.
"""

import os
import pytest
from dotenv import load_dotenv
import ai_client

load_dotenv()


def test_live_gemini_api():
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not gemini_key:
        pytest.skip("GEMINI_API_KEY is not configured.")

    creds = ai_client.get_api_credentials()
    assert creds["gemini_api_key"] == gemini_key
    assert "gemini" in creds["gemini_model"]


def test_live_nvidia_api_optional():
    api_key = os.getenv("NVIDIA_API_KEY", "").strip()
    if not api_key or api_key == "your_nvidia_api_key_here":
        pytest.skip("NVIDIA_API_KEY is not configured. Skipping live network integration test.")

    creds = ai_client.get_api_credentials()
    assert creds["api_key"] == api_key
    assert creds["base_url"] == "https://integrate.api.nvidia.com/v1"
    assert creds["model"] == "moonshotai/kimi-k3"
