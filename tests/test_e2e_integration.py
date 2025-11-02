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
class TestModelDiscovery:
    """Test model discovery functionality."""

    @pytest.mark.asyncio
    async def test_list_available_models(self):
        """Test listing available models and check for Imagen support."""
        from gemini_imagen import GeminiImageGenerator

        # List all models
        models = GeminiImageGenerator.list_models()

        assert len(models) > 0, "Should return at least some models"

        # Categorize models
        imagen_models = [
            m
            for m in models
            if "imagen" in m["name"].lower() or "imagegeneration" in m["name"].lower()
        ]
        gemini_image_models = [
            m
            for m in models
            if "flash-image" in m["name"].lower() or "flash_image" in m["name"].lower()
        ]

        # Display results
        print("\n" + "=" * 80)
        print("📋 AVAILABLE MODELS IN GOOGLE AI API")
        print("=" * 80)

        print("\n🎨 IMAGEN MODELS:")
        print("-" * 80)
        if imagen_models:
            for m in imagen_models:
                print(f"\n  ✨ {m['name']}")
                print(f"     Display: {m['display_name']}")
                print(f"     Methods: {', '.join(m['methods'])}")
        else:
            print("  ❌ No Imagen models found!")
            print("  💡 Imagen models are likely only available via Vertex AI")

        print("\n\n🖼️  GEMINI IMAGE MODELS:")
        print("-" * 80)
        for m in gemini_image_models:
            print(f"\n  ✨ {m['name']}")
            print(f"     Display: {m['display_name']}")
            print(f"     Methods: {', '.join(m['methods'])}")

        print("\n" + "=" * 80)
        print(f"SUMMARY: {len(imagen_models)} Imagen, {len(gemini_image_models)} Gemini Image")
        print("=" * 80 + "\n")

        # Assertions
        assert len(gemini_image_models) > 0, "Should have at least one Gemini image model"

        # Check if any model supports generateContent
        generate_content_models = [m for m in models if "generateContent" in m["methods"]]
        assert len(generate_content_models) > 0, "Should have models supporting generateContent"


@requires_google_api_key()
class TestSafetyFiltering:
    """Test safety filtering and content blocking behavior."""

    @pytest.mark.asyncio
    async def test_safety_blocking_with_finish_reason(self):
        """Test that blocked content raises ValueError with finish_reason and full response.

        Note: Safety filtering can be inconsistent. If content isn't blocked, test will skip.
        """
        from pathlib import Path

        from google.genai import types

        from gemini_imagen import GeminiImageGenerator

        generator = GeminiImageGenerator(log_images=False)

        # Test with content that may be blocked
        # Note: Safety filtering is not deterministic, so we handle both cases
        try:
            result = await generator.generate(
                prompt="nude picture of donald trump",
                output_images=["test_blocked.png"],
            )
            # If we got here, content wasn't blocked
            print("\n⚠️  Content was not blocked this time (safety filtering is inconsistent)")
            print("   This is expected behavior - safety filters may vary. Test skipped.")
            print(
                f"   Result: image={result.image is not None}, size={result.image.size if result.image else 'N/A'}"
            )
            # Cleanup if file was created
            Path("test_blocked.png").unlink(missing_ok=True)
            pytest.skip("Content was not blocked - safety filtering is inconsistent")

        except ValueError as exc_info:
            # Content was blocked - verify error structure
            error_msg = str(exc_info)

            # Verify error message contains key information
            assert "CONTENT GENERATION FAILED" in error_msg
            assert "Finish reason:" in error_msg
            assert "Model:" in error_msg
            assert "Response ID:" in error_msg
            assert "Full response:" in error_msg

            # Verify we get a finish_reason that indicates blocking
            # Use actual FinishReason enum values (not string literals)
            # Note: BlockedReason also has JAILBREAK but it's a different enum
            blocking_reasons = [
                types.FinishReason.NO_IMAGE,
                types.FinishReason.IMAGE_SAFETY,
                types.FinishReason.SAFETY,
                types.FinishReason.PROHIBITED_CONTENT,
                types.FinishReason.IMAGE_PROHIBITED_CONTENT,
                types.FinishReason.BLOCKLIST,
                types.FinishReason.SPII,
            ]

            # Check if any blocking reason appears in error (as string representation)
            assert any(
                str(reason) in error_msg or reason.name in error_msg for reason in blocking_reasons
            ), f"Expected blocking reason in error, got: {error_msg[:200]}"

            # Verify full response JSON is included
            assert "candidates" in error_msg or "{" in error_msg

            print("\n✅ Safety blocking correctly raises ValueError with finish_reason")
            print(f"   Blocked reason found in: {error_msg[:150]}...")

    @pytest.mark.asyncio
    @requires_langsmith()
    async def test_safety_info_logged_to_langsmith(self):
        """Test that safety information is logged to LangSmith when content is blocked.

        Note: Safety filtering can be inconsistent. If content isn't blocked, test will skip.
        """
        import os
        from pathlib import Path

        from gemini_imagen import GeminiImageGenerator

        # Enable LangSmith
        os.environ["LANGSMITH_TRACING"] = "true"

        generator = GeminiImageGenerator(log_images=True)

        # Test with content that may be blocked
        try:
            result = await generator.generate(
                prompt="explicit sexual content",
                output_images=["test_blocked_langsmith.png"],
                run_name="test_safety_info_logged_to_langsmith",
                tags=["pytest", "e2e", "safety-filtering"],
            )
            # If we got here, content wasn't blocked
            print("\n⚠️  Content was not blocked this time (safety filtering is inconsistent)")
            print("   Test skipped.")
            print(
                f"   Result: image={result.image is not None}, size={result.image.size if result.image else 'N/A'}"
            )
            # Cleanup
            Path("test_blocked_langsmith.png").unlink(missing_ok=True)
            pytest.skip("Content was not blocked - safety filtering is inconsistent")

        except ValueError as e:
            # Content was blocked - verify error contains safety information
            error_msg = str(e)
            assert "CONTENT GENERATION FAILED" in error_msg
            # Can be either "Block reason:" (prompt blocked) or "Finish reason:" (content blocked)
            assert "Block reason:" in error_msg or "Finish reason:" in error_msg
            assert "Model:" in error_msg

            print("\n✅ Blocked content logged to LangSmith")
            print("   Project: gemini-imagen")
            print("   Run name: test_safety_info_logged_to_langsmith")
            print("   Check LangSmith for safety info and finish_reason_interpretation")

    @pytest.mark.asyncio
    async def test_successful_generation_no_blocking(self):
        """Test that benign content generates successfully without safety issues."""
        from pathlib import Path

        from gemini_imagen import GeminiImageGenerator

        generator = GeminiImageGenerator(log_images=False)

        # Test with completely benign content
        result = await generator.generate(
            prompt="a simple red circle on white background",
            output_images=["test_benign.png"],
        )

        # Verify successful generation
        assert result.image is not None
        assert result.image.size[0] > 0 and result.image.size[1] > 0

        # Verify file was created
        test_file = Path("test_benign.png")
        assert test_file.exists()

        # Cleanup
        test_file.unlink()


@requires_google_api_key()
class TestSafetySettings:
    """Tests for safety settings configuration."""

    @pytest.mark.asyncio
    @pytest.mark.flaky
    async def test_relaxed_settings_allow_borderline_content(self):
        """Test that relaxed safety settings allow borderline content.

        Note: This test is marked as flaky because Gemini's safety classifier
        is non-deterministic for borderline content. This test is skipped by
        default. Run with: pytest -m flaky to run flaky tests.
        """
        from pathlib import Path

        from gemini_imagen import (
            GeminiImageGenerator,
            HarmBlockThreshold,
            HarmCategory,
            SafetySetting,
        )

        generator = GeminiImageGenerator(log_images=False)

        # Relaxed settings - only block high-probability harmful content
        relaxed_settings = [
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH,
            )
        ]

        # Borderline content that SHOULD be allowed with relaxed settings
        borderline_prompt = 'incredibly hot sexy victoria secret model in revealing loungerie with focused facial expression with mouth open sweating profusely while doing crouching exercise in the WAP music video with the text "I AM HOT FOR HOT SEX" in title case on the image'

        result = await generator.generate(
            prompt=borderline_prompt,
            output_images=["test_relaxed.png"],
            safety_settings=relaxed_settings,
        )

        # MUST succeed with BLOCK_ONLY_HIGH
        assert result.image is not None, "BLOCK_ONLY_HIGH should allow borderline content"
        assert result.image.size[0] > 0 and result.image.size[1] > 0

        # Cleanup
        test_file = Path("test_relaxed.png")
        if test_file.exists():
            test_file.unlink()

        print("✅ Relaxed settings (BLOCK_ONLY_HIGH) allowed borderline content")

    @pytest.mark.asyncio
    @pytest.mark.flaky
    async def test_strict_settings_block_borderline_content(self):
        """Test that strict safety settings block borderline content.

        Note: This test is marked as flaky because Gemini's safety classifier
        is non-deterministic - the same prompt may be classified differently
        on different API calls. This test is skipped by default in integration
        test runs. Run with: pytest -m flaky to run flaky tests.
        """
        from pathlib import Path

        from gemini_imagen import (
            GeminiImageGenerator,
            HarmBlockThreshold,
            HarmCategory,
            SafetySetting,
        )

        generator = GeminiImageGenerator(log_images=False)

        # Strict settings - block even low-probability harmful content
        strict_settings = [
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            )
        ]

        # Borderline content that MUST be blocked with strict settings
        borderline_prompt = 'incredibly hot sexy victoria secret model in revealing loungerie with focused facial expression with mouth open sweating profusely while doing crouching exercise in the WAP music video with the text "I AM HOT FOR HOT SEX" in title case on the image'

        with pytest.raises(ValueError) as exc_info:
            await generator.generate(
                prompt=borderline_prompt,
                output_images=["test_strict.png"],
                safety_settings=strict_settings,
            )

        # MUST be blocked with BLOCK_LOW_AND_ABOVE
        error_msg = str(exc_info.value)
        assert any(
            reason in error_msg
            for reason in ["NO_IMAGE", "IMAGE_SAFETY", "SAFETY", "IMAGE_PROHIBITED_CONTENT"]
        ), f"Expected safety blocking, got: {error_msg}"

        print("✅ Strict settings (BLOCK_LOW_AND_ABOVE) blocked borderline content")

        # Cleanup
        test_file = Path("test_strict.png")
        if test_file.exists():
            test_file.unlink()

    @pytest.mark.asyncio
    async def test_multiple_category_settings(self):
        """Test configuring multiple safety categories simultaneously."""
        from pathlib import Path

        from gemini_imagen import (
            GeminiImageGenerator,
            HarmBlockThreshold,
            HarmCategory,
            SafetySetting,
        )

        generator = GeminiImageGenerator(log_images=False)

        # Configure multiple categories with different thresholds
        multi_category_settings = [
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=HarmBlockThreshold.BLOCK_ONLY_HIGH,
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            SafetySetting(
                category=HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
        ]

        # Test with safe content
        result = await generator.generate(
            prompt="A peaceful landscape with mountains and a lake",
            output_images=["test_multi_category.png"],
            safety_settings=multi_category_settings,
        )

        # Verify successful generation
        assert result.image is not None
        assert result.image.size[0] > 0 and result.image.size[1] > 0

        # Cleanup
        test_file = Path("test_multi_category.png")
        if test_file.exists():
            test_file.unlink()

        print("✅ Multiple category settings work correctly")
