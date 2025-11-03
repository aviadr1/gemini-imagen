"""
Tests for handling various Gemini API finish reasons.

Ensures the library properly handles all possible finish reasons including
new ones like IMAGE_OTHER that may not be in the SDK enum yet.
"""

from unittest.mock import MagicMock, patch

import pytest
from google.genai import types

from gemini_imagen import GeminiImageGenerator
from gemini_imagen.models import GenerateParams


class TestFinishReasonHandling:
    """Test handling of various finish reasons from Gemini API."""

    @pytest.fixture
    def generator(self):
        """Create a generator instance for testing."""
        return GeminiImageGenerator(
            model_name="gemini-2.5-flash-image",
            api_key="test-key",
            log_images=False,
        )

    def _create_mock_response(self, finish_reason_str: str, has_content: bool = True):
        """
        Create a mock Gemini response with specified finish reason.

        Args:
            finish_reason_str: Finish reason as string
            has_content: Whether to include content parts in the response
        """
        mock_response = MagicMock(spec=types.GenerateContentResponse)
        mock_response.model_version = "gemini-2.5-flash-image"
        mock_response.response_id = "test-response-id"
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.total_token_count = 100
        mock_response.prompt_feedback = None
        mock_response.model_dump = MagicMock(
            return_value={
                "model_version": "gemini-2.5-flash-image",
                "response_id": "test-response-id",
                "candidates": [{"finish_reason": finish_reason_str}],
            }
        )

        # Create candidate
        mock_candidate = MagicMock()
        mock_candidate.finish_reason = finish_reason_str
        mock_candidate.finish_message = None
        mock_candidate.safety_ratings = None

        if has_content:
            # Create mock content with parts
            mock_part = MagicMock()
            mock_part.text = None
            mock_part.inline_data = MagicMock()
            mock_part.inline_data.mime_type = "image/png"
            mock_part.inline_data.data = b"fake-image-data"

            mock_content = MagicMock()
            mock_content.parts = [mock_part]
            mock_candidate.content = mock_content
        else:
            # No content (empty response)
            mock_candidate.content = None

        mock_response.candidates = [mock_candidate]

        return mock_response

    @pytest.mark.asyncio
    async def test_stop_finish_reason_success(self, generator):
        """Test that STOP finish reason is handled as success."""
        mock_response = self._create_mock_response("STOP", has_content=True)

        with patch.object(generator, "_call_gemini", return_value=mock_response):
            params = GenerateParams(prompt="test prompt", output_images=["output.png"])
            result = await generator.generate(params)

            # Should succeed without raising
            assert result is not None

    @pytest.mark.asyncio
    async def test_image_other_finish_reason(self, generator):
        """Test that IMAGE_OTHER finish reason with no content raises informative error."""
        # IMAGE_OTHER with no content should raise error with helpful message
        mock_response = self._create_mock_response("IMAGE_OTHER", has_content=False)

        with patch.object(generator, "_call_gemini", return_value=mock_response):
            params = GenerateParams(prompt="test prompt", output_images=["output.png"])
            # Should raise with informative message about IMAGE_OTHER
            with pytest.raises(ValueError) as exc_info:
                await generator.generate(params)

            error_msg = str(exc_info.value)
            assert "CONTENT GENERATION FAILED" in error_msg
            assert "IMAGE_OTHER" in error_msg
            # Should include our interpretation
            assert "alternative format" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_safety_finish_reason_raises(self, generator):
        """Test that SAFETY finish reason raises appropriate error."""
        mock_response = self._create_mock_response("SAFETY", has_content=False)

        with patch.object(generator, "_call_gemini", return_value=mock_response):
            params = GenerateParams(prompt="test prompt", output_images=["output.png"])
            with pytest.raises(ValueError, match="CONTENT GENERATION FAILED"):
                await generator.generate(params)

    @pytest.mark.asyncio
    async def test_no_image_finish_reason_raises(self, generator):
        """Test that NO_IMAGE finish reason raises appropriate error."""
        mock_response = self._create_mock_response("NO_IMAGE", has_content=False)

        with patch.object(generator, "_call_gemini", return_value=mock_response):
            params = GenerateParams(prompt="test prompt", output_images=["output.png"])
            with pytest.raises(ValueError, match="CONTENT GENERATION FAILED"):
                await generator.generate(params)

    @pytest.mark.asyncio
    async def test_image_safety_finish_reason_raises(self, generator):
        """Test that IMAGE_SAFETY finish reason raises appropriate error."""
        mock_response = self._create_mock_response("IMAGE_SAFETY", has_content=False)

        with patch.object(generator, "_call_gemini", return_value=mock_response):
            params = GenerateParams(prompt="test prompt", output_images=["output.png"])
            with pytest.raises(ValueError, match="CONTENT GENERATION FAILED"):
                await generator.generate(params)

    @pytest.mark.asyncio
    async def test_prohibited_content_finish_reason_raises(self, generator):
        """Test that PROHIBITED_CONTENT finish reason raises appropriate error."""
        mock_response = self._create_mock_response("PROHIBITED_CONTENT", has_content=False)

        with patch.object(generator, "_call_gemini", return_value=mock_response):
            params = GenerateParams(prompt="test prompt", output_images=["output.png"])
            with pytest.raises(ValueError, match="CONTENT GENERATION FAILED"):
                await generator.generate(params)

    @pytest.mark.asyncio
    async def test_max_tokens_finish_reason_raises(self, generator):
        """Test that MAX_TOKENS finish reason raises appropriate error."""
        mock_response = self._create_mock_response("MAX_TOKENS", has_content=False)

        with patch.object(generator, "_call_gemini", return_value=mock_response):
            params = GenerateParams(prompt="test prompt", output_images=["output.png"])
            with pytest.raises(ValueError, match="CONTENT GENERATION FAILED"):
                await generator.generate(params)

    @pytest.mark.asyncio
    async def test_unknown_finish_reason_interpretation(self, generator):
        """Test that unknown finish reasons are handled with generic message."""
        mock_response = self._create_mock_response("NEW_UNKNOWN_REASON", has_content=False)

        with patch.object(generator, "_call_gemini", return_value=mock_response):
            params = GenerateParams(prompt="test prompt", output_images=["output.png"])
            with pytest.raises(ValueError, match="Unknown finish reason"):
                await generator.generate(params)

    def test_interpret_finish_reason_image_other(self, generator):
        """Test that _interpret_finish_reason handles IMAGE_OTHER correctly."""
        # Create a mock finish reason that includes IMAGE_OTHER in string representation
        mock_finish_reason = MagicMock()
        mock_finish_reason.__str__ = lambda self: "FinishReason.IMAGE_OTHER"

        interpretation = generator._interpret_finish_reason(mock_finish_reason)
        assert "Image generation completed" in interpretation
        assert "alternative" in interpretation.lower()

    def test_interpret_finish_reason_stop(self, generator):
        """Test that _interpret_finish_reason handles STOP correctly."""
        interpretation = generator._interpret_finish_reason(types.FinishReason.STOP)
        assert "completed successfully" in interpretation.lower()

    def test_interpret_finish_reason_safety(self, generator):
        """Test that _interpret_finish_reason handles SAFETY correctly."""
        interpretation = generator._interpret_finish_reason(types.FinishReason.SAFETY)
        assert "blocked" in interpretation.lower()
        assert "safety" in interpretation.lower()


class TestEmptyResponseHandling:
    """Test handling of empty or incomplete responses."""

    @pytest.fixture
    def generator(self):
        """Create a generator instance for testing."""
        return GeminiImageGenerator(
            model_name="gemini-2.5-flash-image",
            api_key="test-key",
            log_images=False,
        )

    @pytest.mark.asyncio
    async def test_no_candidates_raises(self, generator):
        """Test that response with no candidates raises appropriate error."""
        mock_response = MagicMock(spec=types.GenerateContentResponse)
        mock_response.candidates = []
        mock_response.model_version = "gemini-2.5-flash-image"
        mock_response.response_id = "test-id"
        mock_response.prompt_feedback = None
        mock_response.model_dump = MagicMock(return_value={})

        with patch.object(generator, "_call_gemini", return_value=mock_response):
            params = GenerateParams(prompt="test prompt", output_images=["output.png"])
            with pytest.raises(ValueError, match="No candidates in response"):
                await generator.generate(params)

    @pytest.mark.asyncio
    async def test_candidate_with_no_content_and_bad_finish_reason(self, generator):
        """Test that candidate with no content and error finish reason raises."""
        mock_response = MagicMock(spec=types.GenerateContentResponse)
        mock_response.model_version = "gemini-2.5-flash-image"
        mock_response.response_id = "test-id"
        mock_response.usage_metadata = None
        mock_response.prompt_feedback = None
        mock_response.model_dump = MagicMock(return_value={})

        mock_candidate = MagicMock()
        mock_candidate.finish_reason = types.FinishReason.SAFETY
        mock_candidate.finish_message = None
        mock_candidate.safety_ratings = None
        mock_candidate.content = None

        mock_response.candidates = [mock_candidate]

        with patch.object(generator, "_call_gemini", return_value=mock_response):
            params = GenerateParams(prompt="test prompt", output_images=["output.png"])
            with pytest.raises(ValueError, match="CONTENT GENERATION FAILED"):
                await generator.generate(params)
