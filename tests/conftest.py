"""Pytest configuration and fixtures."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from dotenv import load_dotenv
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:  # pragma: no cover - initialization
    sys.path.insert(0, str(SRC_PATH))

# Load environment variables for tests
load_dotenv()


@pytest.fixture
def mock_gemini_client():
    """Mock Google Gemini client for testing."""
    with patch("google.genai.Client") as mock:
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


# Helper functions for skipping tests that require secrets
def requires_google_api_key():
    """Skip test if GOOGLE_API_KEY is not set."""
    return pytest.mark.skipif(
        not os.getenv("GOOGLE_API_KEY"),
        reason="GOOGLE_API_KEY environment variable not set. Set it to run this test.",
    )


def requires_aws_credentials():
    """Skip test if AWS credentials are not set."""
    has_creds = (os.getenv("GV_AWS_ACCESS_KEY_ID") or os.getenv("AWS_ACCESS_KEY_ID")) and (
        os.getenv("GV_AWS_SECRET_ACCESS_KEY") or os.getenv("AWS_SECRET_ACCESS_KEY")
    )
    return pytest.mark.skipif(
        not has_creds,
        reason="AWS credentials not set. Set GV_AWS_ACCESS_KEY_ID and GV_AWS_SECRET_ACCESS_KEY to run this test.",
    )


def requires_langsmith():
    """Skip test if LangSmith API key is not set."""
    return pytest.mark.skipif(
        not os.getenv("LANGSMITH_API_KEY"),
        reason="LANGSMITH_API_KEY environment variable not set. Set it to run this test.",
    )
