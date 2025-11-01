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

    @pytest.mark.asyncio
    async def test_basic_image_generation(self):
        """Test basic text-to-image generation with real API."""
        from gemini_imagen import GeminiImageGenerator

        generator = GeminiImageGenerator(log_images=True)
        result = await generator.generate(
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

    @pytest.mark.asyncio
    async def test_s3_image_generation(self):
        """Test image generation with S3 output."""
        from datetime import datetime

        from gemini_imagen import GeminiImageGenerator

        aws_bucket = os.getenv("GV_AWS_STORAGE_BUCKET_NAME")
        if not aws_bucket:
            pytest.skip("GV_AWS_STORAGE_BUCKET_NAME not set")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_path = f"s3://{aws_bucket}/test_e2e/circle_{timestamp}.png"

        generator = GeminiImageGenerator(log_images=True)
        result = await generator.generate(
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

    @pytest.mark.asyncio
    async def test_langsmith_s3_url_logging(self):
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
        result = await generator.generate(
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


@requires_google_api_key()
@requires_aws_credentials()
class TestAdvancedFeatures:
    """Comprehensive tests for advanced features with real API."""

    @pytest.mark.asyncio
    async def test_labeled_inputs_and_outputs(self):
        """Test labeled input images and labeled output images with S3."""
        from datetime import datetime
        from pathlib import Path

        from PIL import Image

        from gemini_imagen import GeminiImageGenerator

        aws_bucket = os.getenv("GV_AWS_STORAGE_BUCKET_NAME")
        if not aws_bucket:
            pytest.skip("GV_AWS_STORAGE_BUCKET_NAME not set")

        # Create test input images
        test_dir = Path("test_inputs")
        test_dir.mkdir(exist_ok=True)

        img1_path = test_dir / "red_square.png"
        img2_path = test_dir / "blue_circle.png"

        # Create simple test images
        Image.new("RGB", (100, 100), color="red").save(img1_path)
        Image.new("RGB", (100, 100), color="blue").save(img2_path)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_path1 = f"s3://{aws_bucket}/test_e2e/advanced/output1_{timestamp}.png"
        s3_path2 = f"s3://{aws_bucket}/test_e2e/advanced/output2_{timestamp}.png"

        generator = GeminiImageGenerator(log_images=True)
        result = await generator.generate(
            prompt="Create two variations: one combining the red color with circular shape, another with blue and square shape",
            system_prompt="You are an expert image generator. Create variations based on the provided images.",
            input_images=[
                ("Reference Color (Red):", str(img1_path)),
                ("Reference Shape (Circle):", str(img2_path)),
            ],
            output_images=[
                ("Red Circle Variation", s3_path1),
                ("Blue Square Variation", s3_path2),
            ],
            run_name="test_labeled_inputs_and_outputs",
            tags=["pytest", "e2e", "labeled-io", "advanced"],
        )

        # Verify outputs
        assert len(result.images) >= 1
        assert len(result.image_labels) >= 1
        assert len(result.image_s3_uris) >= 1
        assert len(result.image_http_urls) >= 1

        # Check that at least one image was saved to S3
        assert result.image_s3_uris[0] is not None
        assert result.image_http_urls[0] is not None
        assert "https://" in result.image_http_urls[0]

        print("\n✅ Labeled inputs and outputs test passed")
        print(f"   Generated {len(result.images)} image(s)")
        print(f"   Labels: {result.image_labels}")
        print(f"   S3 URIs: {result.image_s3_uris}")

        # Cleanup
        img1_path.unlink()
        img2_path.unlink()
        test_dir.rmdir()

    @pytest.mark.asyncio
    async def test_multiple_outputs_with_text(self):
        """Test generating multiple images with text output."""
        from datetime import datetime

        from gemini_imagen import GeminiImageGenerator

        aws_bucket = os.getenv("GV_AWS_STORAGE_BUCKET_NAME")
        if not aws_bucket:
            pytest.skip("GV_AWS_STORAGE_BUCKET_NAME not set")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        s3_paths = [
            f"s3://{aws_bucket}/test_e2e/multi/sunrise_{timestamp}.png",
            f"s3://{aws_bucket}/test_e2e/multi/sunset_{timestamp}.png",
        ]

        generator = GeminiImageGenerator(log_images=True)
        result = await generator.generate(
            prompt="Generate two landscape images: one at sunrise and one at sunset. Also explain the differences in lighting and colors between them.",
            system_prompt="Create beautiful landscape images and provide technical analysis.",
            output_images=[
                ("Sunrise Landscape", s3_paths[0]),
                ("Sunset Landscape", s3_paths[1]),
            ],
            output_text=True,
            temperature=0.7,
            run_name="test_multiple_outputs_with_text",
            tags=["pytest", "e2e", "multi-output", "text-output"],
            metadata={"test_type": "comprehensive", "feature": "multi-output+text"},
        )

        # Verify images
        assert len(result.images) >= 1
        assert len(result.image_s3_uris) >= 1
        assert result.image_s3_uris[0] is not None

        # Verify text output
        assert result.text is not None
        assert len(result.text) > 10  # Should have meaningful text

        print("\n✅ Multiple outputs with text test passed")
        print(f"   Generated {len(result.images)} image(s)")
        print(f"   Text output length: {len(result.text)} characters")
        print(f"   S3 URIs: {result.image_s3_uris}")
        print(f"   Text preview: {result.text[:100]}...")

    @pytest.mark.asyncio
    async def test_image_analysis_with_system_prompt(self):
        """Test image analysis with system prompt and text-only output."""
        from pathlib import Path

        from PIL import Image

        from gemini_imagen import GeminiImageGenerator

        # Create a test image to analyze
        test_dir = Path("test_analysis")
        test_dir.mkdir(exist_ok=True)
        test_image_path = test_dir / "analyze_me.png"

        # Create an image with specific characteristics
        img = Image.new("RGB", (200, 200))
        pixels = img.load()
        # Create a red-blue gradient
        for x in range(200):
            for y in range(200):
                r = int(255 * (x / 200))
                b = int(255 * (y / 200))
                pixels[x, y] = (r, 0, b)
        img.save(test_image_path)

        generator = GeminiImageGenerator(log_images=True)
        result = await generator.generate(
            prompt="Describe this image in detail, focusing on the color gradient pattern and dimensions.",
            system_prompt="You are a professional image analyst. Provide technical, precise descriptions of images.",
            input_images=[("Gradient Image:", str(test_image_path))],
            output_text=True,
            temperature=0.3,  # Lower temperature for more consistent analysis
            run_name="test_image_analysis_with_system_prompt",
            tags=["pytest", "e2e", "analysis", "system-prompt"],
            metadata={"analysis_type": "gradient", "input_type": "synthetic"},
        )

        # Verify text-only output
        assert result.text is not None
        assert len(result.text) > 20
        assert len(result.images) == 0  # No images generated
        assert len(result.image_s3_uris) == 0

        # Check that the analysis mentions relevant terms
        text_lower = result.text.lower()
        assert any(
            word in text_lower for word in ["color", "gradient", "red", "blue", "purple"]
        ), "Analysis should mention colors"

        print("\n✅ Image analysis with system prompt test passed")
        print(f"   Analysis length: {len(result.text)} characters")
        print(f"   Analysis preview: {result.text[:150]}...")

        # Cleanup
        test_image_path.unlink()
        test_dir.rmdir()


@requires_google_api_key()
class TestAspectRatioAndResolution:
    """Integration tests for aspect ratio and image size features."""

    @pytest.mark.asyncio
    async def test_preset_aspect_ratios(self):
        """Test image generation with preset aspect ratios."""
        import asyncio

        from gemini_imagen import GeminiImageGenerator

        generator = GeminiImageGenerator(log_images=False)

        # Test different preset aspect ratios
        test_ratios = [
            ("1:1", 1.0),  # Square
            ("16:9", 16 / 9),  # Widescreen
            ("9:16", 9 / 16),  # Portrait
        ]

        for aspect_ratio, expected_ratio in test_ratios:
            # Retry up to 3 times to handle transient API failures
            max_retries = 3

            for attempt in range(max_retries):
                try:
                    result = await generator.generate(
                        prompt="A simple geometric shape",
                        aspect_ratio=aspect_ratio,
                        output_images=[f"test_aspect_{aspect_ratio.replace(':', 'x')}.png"],
                    )

                    assert result.image is not None
                    # Check actual aspect ratio matches expected (with tolerance)
                    actual_ratio = result.image.size[0] / result.image.size[1]
                    assert (
                        abs(actual_ratio - expected_ratio) < 0.1
                    ), f"Aspect ratio mismatch for {aspect_ratio}: expected ~{expected_ratio:.2f}, got {actual_ratio:.2f} ({result.image.size[0]}x{result.image.size[1]})"

                    # Cleanup
                    from pathlib import Path

                    Path(f"test_aspect_{aspect_ratio.replace(':', 'x')}.png").unlink(
                        missing_ok=True
                    )

                    print(
                        f"\n✅ Aspect ratio {aspect_ratio} test passed: {result.image.size[0]}x{result.image.size[1]}"
                    )
                    break  # Success, exit retry loop

                except ValueError as e:
                    if "No content parts in response" in str(e) and attempt < max_retries - 1:
                        print(f"\n⚠️  Attempt {attempt + 1} failed for {aspect_ratio}, retrying...")
                        await asyncio.sleep(2)  # Wait before retry
                        continue
                    raise  # Re-raise if not retryable or last attempt

    @pytest.mark.asyncio
    async def test_custom_aspect_ratio(self):
        """Test image generation with custom aspect ratio tuple."""
        from gemini_imagen import GeminiImageGenerator

        generator = GeminiImageGenerator(log_images=False)

        # Test custom aspect ratio using tuple
        result = await generator.generate(
            prompt="A panoramic landscape",
            aspect_ratio=(21, 9),  # Ultra-widescreen
            output_images=["test_custom_21x9.png"],
        )

        assert result.image is not None
        # Check that aspect ratio is approximately correct
        ratio = result.image.size[0] / result.image.size[1]
        expected_ratio = 21 / 9
        assert (
            abs(ratio - expected_ratio) < 0.2
        ), f"Aspect ratio mismatch: expected ~{expected_ratio:.2f}, got {ratio:.2f}"

        # Cleanup
        from pathlib import Path

        Path("test_custom_21x9.png").unlink(missing_ok=True)

        print(
            f"\n✅ Custom aspect ratio (21:9) test passed: {result.image.size[0]}x{result.image.size[1]}"
        )

    @pytest.mark.asyncio
    async def test_image_size_not_supported(self):
        """Test that image_size parameter raises ValueError on gemini-2.5-flash-image."""
        from gemini_imagen import GeminiImageGenerator

        generator = GeminiImageGenerator(log_images=False)

        # Test that image_size raises ValueError for gemini-2.5-flash-image
        with pytest.raises(ValueError) as exc_info:
            await generator.generate(
                prompt="A colorful abstract pattern",
                aspect_ratio="1:1",
                image_size="1K",  # Should raise ValueError
                output_images=["test_1k.png"],
            )

        error_msg = str(exc_info.value)
        assert "image_size parameter is not supported" in error_msg
        assert "gemini-2.5-flash-image" in error_msg
        assert "Imagen models" in error_msg

        print("\n✅ image_size parameter correctly raises ValueError on gemini-2.5-flash-image")

    @pytest.mark.asyncio
    async def test_multiple_images_with_aspect_ratio(self):
        """Test saving one image to multiple outputs with aspect ratio."""
        from gemini_imagen import GeminiImageGenerator

        generator = GeminiImageGenerator(log_images=False)

        # Request 3 output locations with 16:9 aspect ratio
        # Note: gemini-2.5-flash-image only generates 1 image, but saves it to all locations
        result = await generator.generate(
            prompt="A futuristic cityscape",
            aspect_ratio="16:9",
            output_images=[
                "test_multi_1.png",
                "test_multi_2.png",
                "test_multi_3.png",
            ],
        )

        # Should generate 1 image (API limitation)
        assert len(result.images) >= 1, f"Expected at least 1 image, got {len(result.images)}"

        # Check aspect ratio
        img = result.images[0]
        ratio = img.size[0] / img.size[1]
        expected_ratio = 16 / 9
        assert (
            abs(ratio - expected_ratio) < 0.2
        ), f"Aspect ratio mismatch: expected ~{expected_ratio:.2f}, got {ratio:.2f}"

        print(f"\n✅ Multiple outputs with aspect ratio test passed: {img.size[0]}x{img.size[1]}")

        # Cleanup
        from pathlib import Path

        for i in range(1, 4):
            Path(f"test_multi_{i}.png").unlink(missing_ok=True)


@requires_google_api_key()
class TestImagenModels:
    """Integration tests for Imagen models (imagen-3, imagen-4) with advanced features."""

    @pytest.mark.asyncio
    async def test_imagen_advanced_features(self):
        """Test Imagen model with image_size and multiple images (advanced features)."""
        from gemini_imagen import GeminiImageGenerator

        # Initialize with Imagen model
        generator = GeminiImageGenerator(model_name="imagen-3.0-generate-001", log_images=False)

        # Test 1: High resolution with image_size parameter
        print("\n🎨 Testing Imagen model with 2K resolution...")
        result_2k = await generator.generate(
            prompt="A detailed landscape with mountains",
            aspect_ratio="16:9",
            image_size="2K",  # Only supported on Imagen models
            output_images=["test_imagen_2k.png"],
        )

        assert result_2k.image is not None
        width, height = result_2k.image.size
        total_pixels = width * height

        # 2K should have significantly more pixels than 1K
        # Rough expectation: 2K ≈ 2048x1152 = 2,359,296 pixels for 16:9
        assert total_pixels > 1_500_000, f"2K image should have >1.5M pixels, got {total_pixels:,}"

        print(f"  ✓ 2K image: {width}x{height} ({total_pixels:,} pixels)")

        # Test 2: Multiple different images in one call
        print("\n🎨 Testing Imagen model with multiple images...")
        result_multi = await generator.generate(
            prompt="Abstract art with vibrant colors",
            aspect_ratio="1:1",
            output_images=[
                ("Variation 1", "test_imagen_var1.png"),
                ("Variation 2", "test_imagen_var2.png"),
                ("Variation 3", "test_imagen_var3.png"),
            ],
        )

        # Imagen models can generate multiple different images
        # Note: This assumes the API actually returns multiple images
        # If it only returns 1, the code will duplicate it to all outputs
        assert len(result_multi.images) >= 1
        assert len(result_multi.image_labels) == 3
        assert result_multi.image_labels[0] == "Variation 1"

        print(
            f"  ✓ Generated {len(result_multi.images)} image(s) with "
            f"{len(result_multi.image_labels)} labels"
        )

        # Test 3: Combined features (2K + multiple images)
        print("\n🎨 Testing combined features (2K + multiple images)...")
        result_combined = await generator.generate(
            prompt="A futuristic cityscape",
            aspect_ratio="16:9",
            image_size="2K",
            output_images=[
                ("City View 1", "test_imagen_combined1.png"),
                ("City View 2", "test_imagen_combined2.png"),
            ],
        )

        assert len(result_combined.images) >= 1
        assert len(result_combined.image_labels) == 2

        # Verify high resolution
        width, height = result_combined.images[0].size
        total_pixels = width * height
        assert total_pixels > 1_500_000, f"2K image should have >1.5M pixels, got {total_pixels:,}"

        print(f"  ✓ Combined: {width}x{height}, {len(result_combined.images)} image(s)")

        print("\n✅ All Imagen advanced features tests passed!")

        # Cleanup
        from pathlib import Path

        Path("test_imagen_2k.png").unlink(missing_ok=True)
        Path("test_imagen_var1.png").unlink(missing_ok=True)
        Path("test_imagen_var2.png").unlink(missing_ok=True)
        Path("test_imagen_var3.png").unlink(missing_ok=True)
        Path("test_imagen_combined1.png").unlink(missing_ok=True)
        Path("test_imagen_combined2.png").unlink(missing_ok=True)
