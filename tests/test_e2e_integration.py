"""
End-to-end integration tests that require real API keys.

These tests are skipped if the required environment variables are not set.
Run with: pytest tests/test_e2e_integration.py -v -s
"""

import os
from pathlib import Path

import pytest

from tests.conftest import requires_aws_credentials, requires_google_api_key, requires_langsmith

# Mark entire module to run only when requested
pytestmark = pytest.mark.integration


# Set LangSmith project for all tests in this module
@pytest.fixture(autouse=True)
def set_langsmith_project():
    """Set LangSmith project name for all tests."""
    os.environ["LANGSMITH_PROJECT"] = "gemini-imagen"
    yield
    # Cleanup not needed as env vars are per-process


@requires_google_api_key()
class TestRealGeminiAPI:
    """Tests that hit the real Gemini API."""

    def test_basic_image_generation(self):
        """Test basic text-to-image generation with real API."""
        from gemini_imagen import GeminiImageGenerator

        generator = GeminiImageGenerator(log_images=True)
        result = generator.generate(
            prompt="A simple red circle",
            output_images=["test_e2e_circle.png"],
            run_name="test_basic_image_generation",
            tags=["pytest", "e2e", "basic-generation"],
        )

        assert result.image is not None
        assert result.image.size == (1024, 1024)

        test_file = Path("test_e2e_circle.png")
        assert test_file.exists()

        # Cleanup
        test_file.unlink()


@requires_google_api_key()
@requires_aws_credentials()
class TestRealS3Integration:
    """Tests that require both Gemini API and AWS S3."""

    def test_s3_image_generation(self):
        """Test image generation with S3 output."""
        from datetime import datetime

        from gemini_imagen import GeminiImageGenerator

        aws_bucket = os.getenv("GV_AWS_STORAGE_BUCKET_NAME")
        if not aws_bucket:
            pytest.skip("GV_AWS_STORAGE_BUCKET_NAME not set")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_path = f"s3://{aws_bucket}/test_e2e/circle_{timestamp}.png"

        generator = GeminiImageGenerator(log_images=True)
        result = generator.generate(
            prompt="A simple blue square",
            output_images=[s3_path],
            run_name="test_s3_image_generation",
            tags=["pytest", "e2e", "s3-integration"],
        )

        assert result.image_s3_uri == s3_path
        assert result.image_http_url is not None
        assert "https://" in result.image_http_url

        print("\n✅ S3 image generated and logged to LangSmith")
        print(f"   S3 URI: {result.image_s3_uri}")
        print(f"   HTTP URL: {result.image_http_url}")
        print("   Check LangSmith project 'gemini-imagen' for run 'test_s3_image_generation'")


@requires_google_api_key()
@requires_langsmith()
class TestRealLangSmithLogging:
    """Tests that verify LangSmith logging actually works."""

    def test_langsmith_s3_url_logging(self):
        """Test that S3 URLs are actually logged to LangSmith."""
        import os
        from datetime import datetime

        from gemini_imagen import GeminiImageGenerator

        # Enable LangSmith
        os.environ["LANGSMITH_TRACING"] = "true"

        aws_bucket = os.getenv("GV_AWS_STORAGE_BUCKET_NAME")
        if not aws_bucket:
            pytest.skip("GV_AWS_STORAGE_BUCKET_NAME not set")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_path = f"s3://{aws_bucket}/test_langsmith/test_{timestamp}.png"

        generator = GeminiImageGenerator(log_images=True)
        result = generator.generate(
            prompt="A simple test image for LangSmith logging",
            output_images=[("Test Image", s3_path)],
            run_name="test_langsmith_s3_url_logging",
            tags=["pytest", "e2e", "langsmith-logging-test"],
        )

        assert result.image_s3_uri == s3_path
        assert result.image_http_url is not None

        print("\n✅ Image generated and logged to LangSmith")
        print("   Project: gemini-imagen")
        print("   Run name: test_langsmith_s3_url_logging")
        print(f"   S3 URI: {result.image_s3_uri}")
        print(f"   HTTP URL: {result.image_http_url}")
        print(
            "\n📊 Check LangSmith project 'gemini-imagen' for run 'test_langsmith_s3_url_logging'"
        )
        print("   Tags: pytest, e2e, langsmith-logging-test")
        print(
            "   The run should have 'output_image_0_s3_uri' and 'output_image_0_http_url' in outputs"
        )
        print("   URL: https://smith.langchain.com/o/YOURORG/projects/p/gemini-imagen")
