"""Pytest configuration and fixtures."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image


@pytest.fixture
def mock_gemini_model():
    """Mock Google Gemini model for testing."""
    with patch("google.generativeai.GenerativeModel") as mock:
        yield mock


@pytest.fixture
def mock_s3_client():
    """Mock boto3 S3 client for testing."""
    with patch("boto3.client") as mock:
        yield mock


@pytest.fixture
def sample_image():
    """Create a sample PIL Image for testing."""
    img = Image.new("RGB", (100, 100), color="red")
    return img


@pytest.fixture
def sample_image_path(tmp_path, sample_image):
    """Create a sample image file for testing."""
    image_path = tmp_path / "test_image.png"
    sample_image.save(image_path)
    return image_path


@pytest.fixture
def mock_env_vars():
    """Mock environment variables for testing."""
    env_vars = {
        "GOOGLE_API_KEY": "test_api_key",
        "GV_AWS_ACCESS_KEY_ID": "test_access_key",
        "GV_AWS_SECRET_ACCESS_KEY": "test_secret_key",
        "GV_AWS_STORAGE_BUCKET_NAME": "test-bucket",
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars


@pytest.fixture
def mock_langsmith():
    """Mock LangSmith tracing."""
    with patch("langsmith.traceable") as mock_traceable:
        # Make the decorator work as a pass-through
        mock_traceable.side_effect = lambda *args, **kwargs: lambda f: f
        yield mock_traceable
