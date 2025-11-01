"""Integration tests for LangSmith tracing with S3 logging."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PIL import Image

from gemini_imagen import GeminiImageGenerator


class TestLangSmithIntegration:
    """Test LangSmith integration with actual tracing."""

    @pytest.mark.asyncio
    @patch("gemini_imagen.gemini_image_wrapper.get_current_run_tree")
    @patch("gemini_imagen.gemini_image_wrapper.genai.Client")
    async def test_s3_input_logging_to_langsmith(
        self, mock_client_class, mock_get_run_tree, mock_env_vars
    ):
        """Test that S3 input images are properly logged to LangSmith."""
        # Setup mock run tree
        mock_run_tree = MagicMock()
        mock_run_tree.inputs = {}
        mock_get_run_tree.return_value = mock_run_tree

        # Setup mock Gemini response
        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [MagicMock(text="Test response")]

        # Setup mock client instance
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Create generator with logging enabled
        generator = GeminiImageGenerator(log_images=True)

        # Mock load_image to avoid actual S3 calls
        with patch("gemini_imagen.gemini_image_wrapper.load_image") as mock_load:
            mock_img = Image.new("RGB", (100, 100), color="red")
            mock_load.return_value = mock_img
            mock_load.side_effect = AsyncMock(return_value=mock_img)

            # Generate with S3 input
            await generator.generate(
                prompt="Test prompt",
                input_images=[("Test Image:", "s3://test-bucket/input.png")],
                output_text=True,
            )

        # Verify S3 URLs were logged to LangSmith
        assert "input_image_0_label" in mock_run_tree.inputs
        assert mock_run_tree.inputs["input_image_0_label"] == "Test Image:"
        assert "input_image_0_s3_uri" in mock_run_tree.inputs
        assert mock_run_tree.inputs["input_image_0_s3_uri"] == "s3://test-bucket/input.png"
        assert "input_image_0_http_url" in mock_run_tree.inputs
        # HTTP URL should be generated
        assert "https://" in mock_run_tree.inputs["input_image_0_http_url"]

    @pytest.mark.asyncio
    @patch("gemini_imagen.gemini_image_wrapper.get_current_run_tree")
    @patch("gemini_imagen.gemini_image_wrapper.genai.Client")
    @patch("gemini_imagen.gemini_image_wrapper.save_image")
    async def test_s3_output_logging_to_langsmith(
        self, mock_save, mock_client_class, mock_get_run_tree, mock_env_vars
    ):
        """Test that S3 output images are properly logged to LangSmith."""
        # Setup mock run tree
        mock_run_tree = MagicMock()
        mock_run_tree.inputs = {}
        mock_run_tree.outputs = {}
        mock_get_run_tree.return_value = mock_run_tree

        # Setup mock Gemini response with image
        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_part = MagicMock()
        mock_part.inline_data.mime_type = "image/png"
        mock_part.inline_data.data = b"fake_image_data"
        # Set text to None to avoid Pydantic serialization warnings
        mock_part.text = None
        mock_response.candidates[0].content.parts = [mock_part]

        with patch("PIL.Image.open") as mock_image_open:
            mock_img = Image.new("RGB", (100, 100), color="blue")
            mock_image_open.return_value = mock_img

            # Setup mock client instance
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_client_class.return_value = mock_client

            # Mock save_image to return S3 URIs
            mock_save.return_value = (
                "s3://test-bucket/output.png",
                "s3://test-bucket/output.png",
                "https://test-bucket.s3.us-east-1.amazonaws.com/output.png",
            )
            mock_save.side_effect = AsyncMock(
                return_value=(
                    "s3://test-bucket/output.png",
                    "s3://test-bucket/output.png",
                    "https://test-bucket.s3.us-east-1.amazonaws.com/output.png",
                )
            )

            # Create generator with logging enabled
            generator = GeminiImageGenerator(log_images=True)

            # Generate with S3 output
            await generator.generate(
                prompt="Test prompt", output_images=[("Generated:", "s3://test-bucket/output.png")]
            )

        # Verify S3 URLs were logged to LangSmith outputs
        assert "output_image_0_label" in mock_run_tree.outputs
        assert mock_run_tree.outputs["output_image_0_label"] == "Generated:"
        assert "output_image_0_s3_uri" in mock_run_tree.outputs
        assert mock_run_tree.outputs["output_image_0_s3_uri"] == "s3://test-bucket/output.png"
        assert "output_image_0_http_url" in mock_run_tree.outputs
        assert (
            mock_run_tree.outputs["output_image_0_http_url"]
            == "https://test-bucket.s3.us-east-1.amazonaws.com/output.png"
        )

    @pytest.mark.asyncio
    @patch("gemini_imagen.gemini_image_wrapper.get_current_run_tree")
    @patch("gemini_imagen.gemini_image_wrapper.genai.Client")
    async def test_local_input_logging_to_langsmith(
        self, mock_client_class, mock_get_run_tree, mock_env_vars, sample_image_path
    ):
        """Test that local input images are properly logged to LangSmith."""
        # Setup mock run tree
        mock_run_tree = MagicMock()
        mock_run_tree.inputs = {}
        mock_get_run_tree.return_value = mock_run_tree

        # Setup mock Gemini response
        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [MagicMock(text="Test response")]

        # Setup mock client instance
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Create generator with logging enabled
        generator = GeminiImageGenerator(log_images=True)

        # Generate with local input
        await generator.generate(
            prompt="Test prompt", input_images=[str(sample_image_path)], output_text=True
        )

        # Verify local path was logged to LangSmith
        assert "input_image_0_local_path" in mock_run_tree.inputs
        assert mock_run_tree.inputs["input_image_0_local_path"] == str(sample_image_path)
        # S3 fields should NOT be present for local files
        assert "input_image_0_s3_uri" not in mock_run_tree.inputs
        assert "input_image_0_http_url" not in mock_run_tree.inputs

    @pytest.mark.asyncio
    @patch("gemini_imagen.gemini_image_wrapper.get_current_run_tree")
    @patch("gemini_imagen.gemini_image_wrapper.genai.Client")
    async def test_no_logging_when_disabled(
        self, mock_client_class, mock_get_run_tree, mock_env_vars
    ):
        """Test that nothing is logged when log_images=False."""
        # Setup mock run tree
        mock_run_tree = MagicMock()
        mock_run_tree.inputs = {}
        mock_run_tree.outputs = {}
        mock_get_run_tree.return_value = mock_run_tree

        # Setup mock Gemini response
        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [MagicMock(text="Test response")]

        # Setup mock client instance
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Create generator with logging DISABLED
        generator = GeminiImageGenerator(log_images=False)

        # Mock load_image to avoid actual S3 calls
        with patch("gemini_imagen.gemini_image_wrapper.load_image") as mock_load:
            mock_img = Image.new("RGB", (100, 100), color="red")
            mock_load.return_value = mock_img
            mock_load.side_effect = AsyncMock(return_value=mock_img)

            # Generate with S3 input
            await generator.generate(
                prompt="Test prompt", input_images=["s3://test-bucket/input.png"], output_text=True
            )

        # Verify nothing was logged
        assert len(mock_run_tree.inputs) == 0
        assert len(mock_run_tree.outputs) == 0

    @pytest.mark.asyncio
    @patch("gemini_imagen.gemini_image_wrapper.get_current_run_tree")
    @patch("gemini_imagen.gemini_image_wrapper.genai.Client")
    async def test_multiple_s3_inputs_logged(
        self, mock_client_class, mock_get_run_tree, mock_env_vars
    ):
        """Test that multiple S3 input images are all logged correctly."""
        # Setup mock run tree
        mock_run_tree = MagicMock()
        mock_run_tree.inputs = {}
        mock_get_run_tree.return_value = mock_run_tree

        # Setup mock Gemini response
        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [MagicMock(text="Test response")]

        # Setup mock client instance
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Create generator with logging enabled
        generator = GeminiImageGenerator(log_images=True)

        # Mock load_image to avoid actual S3 calls
        with patch("gemini_imagen.gemini_image_wrapper.load_image") as mock_load:
            mock_img = Image.new("RGB", (100, 100), color="red")
            mock_load.return_value = mock_img
            mock_load.side_effect = AsyncMock(return_value=mock_img)

            # Generate with multiple S3 inputs
            await generator.generate(
                prompt="Test prompt",
                input_images=[
                    ("Image A:", "s3://bucket/image1.png"),
                    ("Image B:", "s3://bucket/image2.png"),
                    ("Image C:", "s3://bucket/image3.png"),
                ],
                output_text=True,
            )

        # Verify all three images were logged
        for idx in range(3):
            prefix = f"input_image_{idx}"
            assert f"{prefix}_label" in mock_run_tree.inputs
            assert f"{prefix}_s3_uri" in mock_run_tree.inputs
            assert f"{prefix}_http_url" in mock_run_tree.inputs

        assert mock_run_tree.inputs["input_image_0_label"] == "Image A:"
        assert mock_run_tree.inputs["input_image_1_label"] == "Image B:"
        assert mock_run_tree.inputs["input_image_2_label"] == "Image C:"
