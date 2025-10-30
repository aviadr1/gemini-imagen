"""
End-to-end integration tests that require real API keys.

These tests are skipped if the required environment variables are not set.
Run with: pytest tests/test_e2e_integration.py -v -s
"""

import os

import pytest

from tests.conftest import requires_aws_credentials, requires_google_api_key, requires_langsmith


# Mark entire module to run only when requested
pytestmark = pytest.mark.integration


@requires_google_api_key()
class TestRealGeminiAPI:
    """Tests that hit the real Gemini API."""

    def test_basic_image_generation(self):
        """Test basic text-to-image generation with real API."""
        from gemini_imagen import GeminiImageGenerator

        generator = GeminiImageGenerator(log_images=False)
        result = generator.generate(
            prompt="A simple red circle",
            output_images=["test_e2e_circle.png"]
        )

        assert result.image is not None
        assert result.image.size == (1024, 1024)
        assert os.path.exists("test_e2e_circle.png")

        # Cleanup
        os.remove("test_e2e_circle.png")


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

        generator = GeminiImageGenerator(log_images=False)
        result = generator.generate(
            prompt="A simple blue square",
            output_images=[s3_path]
        )

        assert result.image_s3_uri == s3_path
        assert result.image_http_url is not None
        assert "https://" in result.image_http_url


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
            tags=["pytest", "e2e", "langsmith-logging-test"]
        )

        assert result.image_s3_uri == s3_path
        assert result.image_http_url is not None

        print(f"\n✅ Image generated and logged to LangSmith")
        print(f"   S3 URI: {result.image_s3_uri}")
        print(f"   HTTP URL: {result.image_http_url}")
        print(f"\n📊 Check LangSmith for a run with tags: pytest, e2e, langsmith-logging-test")
        print(f"   The run should have 'output_image_0_s3_uri' and 'output_image_0_http_url' in outputs")
        print(f"   URL: https://smith.langchain.com/")
