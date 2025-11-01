"""Tests for the GeminiImageGenerator class."""

from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from gemini_imagen import GeminiImageGenerator, GenerationResult


class TestGeminiImageGenerator:
    """Test suite for GeminiImageGenerator."""

    def test_initialization(self, mock_env_vars):
        """Test basic initialization."""
        generator = GeminiImageGenerator()
        assert generator.model_name == "gemini-2.5-flash-image"
        # log_images defaults to True when LANGSMITH_TRACING is set
        assert isinstance(generator.log_images, bool)

    def test_initialization_with_custom_params(self, mock_env_vars):
        """Test initialization with custom parameters."""
        generator = GeminiImageGenerator(
            model_name="custom-model", api_key="custom_key", log_images=True
        )
        assert generator.model_name == "custom-model"
        assert generator.log_images is True

    @pytest.mark.asyncio
    @patch("gemini_imagen.gemini_image_wrapper.genai.Client")
    async def test_generate_text_only(self, mock_client_class, mock_env_vars, mock_langsmith):
        """Test generating text-only output."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.candidates = [MagicMock()]
        mock_response.candidates[0].content.parts = [MagicMock(text="Test response")]

        # Setup mock client instance
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        generator = GeminiImageGenerator()
        result = await generator.generate(prompt="Test prompt", output_text=True)

        assert isinstance(result, GenerationResult)
        assert result.text == "Test response"
        assert len(result.images) == 0

    @pytest.mark.asyncio
    @patch("gemini_imagen.gemini_image_wrapper.genai.Client")
    async def test_generate_with_image_output(
        self, mock_client_class, mock_env_vars, tmp_path, mock_langsmith
    ):
        """Test generating image output."""
        # Setup mock response with image data
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

            generator = GeminiImageGenerator()
            output_path = tmp_path / "output.png"
            result = await generator.generate(
                prompt="Generate an image", output_images=[str(output_path)]
            )

            assert isinstance(result, GenerationResult)
            assert len(result.images) == 1
            assert isinstance(result.images[0], Image.Image)

    @pytest.mark.asyncio
    @patch("gemini_imagen.gemini_image_wrapper.genai.Client")
    async def test_generate_with_single_string_output(
        self, mock_client_class, mock_env_vars, tmp_path, mock_langsmith
    ):
        """Test generating image output with a single string (not a list)."""
        # Setup mock response with image data
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

            generator = GeminiImageGenerator()
            output_path = tmp_path / "thumbnail.jpg"
            # Pass a single string instead of a list
            result = await generator.generate(
                prompt="Generate an image", output_images=str(output_path)
            )

            assert isinstance(result, GenerationResult)
            assert len(result.images) == 1
            assert isinstance(result.images[0], Image.Image)
            assert result.image_location == str(output_path)

    @pytest.mark.asyncio
    async def test_labeled_input_images(self, mock_env_vars, sample_image_path):
        """Test using labeled input images."""
        generator = GeminiImageGenerator()

        labeled_images = [
            ("Label 1:", str(sample_image_path)),
            ("Label 2:", str(sample_image_path)),
        ]

        # Test that the method accepts labeled images without error
        content, image_infos = await generator._build_content_with_labels(
            prompt="Test prompt", input_images=labeled_images
        )

        # Check that labels are in the content
        assert "Label 1:" in content
        assert "Label 2:" in content
        assert len(image_infos) == 2


class TestGenerationResult:
    """Test suite for GenerationResult."""

    def test_empty_result(self):
        """Test empty result initialization."""
        result = GenerationResult()
        assert result.text is None
        assert result.images == []
        assert result.image is None
        assert result.image_location is None

    def test_result_with_single_image(self, sample_image):
        """Test result with a single image."""
        result = GenerationResult(images=[sample_image], image_locations=["test.png"])
        assert result.image == sample_image
        assert result.image_location == "test.png"

    def test_result_with_multiple_images(self, sample_image):
        """Test result with multiple images."""
        img1 = sample_image
        img2 = Image.new("RGB", (100, 100), color="blue")

        result = GenerationResult(
            images=[img1, img2],
            image_locations=["img1.png", "img2.png"],
            image_labels=["Image 1", "Image 2"],
        )

        assert len(result.images) == 2
        assert result.image == img1  # First image
        assert result.image_location == "img1.png"  # First location
        assert result.image_labels == ["Image 1", "Image 2"]

    def test_result_with_text(self):
        """Test result with text output."""
        result = GenerationResult(text="Test text response")
        assert result.text == "Test text response"

    def test_result_with_s3_uris(self):
        """Test result with S3 URIs."""
        result = GenerationResult(
            image_s3_uris=["s3://bucket/image1.png", "s3://bucket/image2.png"],
            image_http_urls=["https://bucket.s3.region.amazonaws.com/image1.png"],
        )

        assert len(result.image_s3_uris) == 2
        assert result.image_s3_uri == "s3://bucket/image1.png"
        assert result.image_http_url == "https://bucket.s3.region.amazonaws.com/image1.png"


class TestResponseModalities:
    """Test response modalities handling."""

    def test_determine_modalities_text_only(self, mock_env_vars):
        """Test determining modalities for text-only output."""
        generator = GeminiImageGenerator()
        modalities = generator._determine_response_modalities(output_images=None, output_text=True)
        assert modalities == ["TEXT"]

    def test_determine_modalities_image_only(self, mock_env_vars):
        """Test determining modalities for image-only output."""
        generator = GeminiImageGenerator()
        modalities = generator._determine_response_modalities(
            output_images=["test.png"], output_text=False
        )
        assert modalities == ["IMAGE"]

    def test_determine_modalities_both(self, mock_env_vars):
        """Test determining modalities for both image and text."""
        generator = GeminiImageGenerator()
        modalities = generator._determine_response_modalities(
            output_images=["test.png"], output_text=True
        )
        assert set(modalities) == {"IMAGE", "TEXT"}
