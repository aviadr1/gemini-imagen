"""Tests for langsmith_client module."""

import os
from unittest.mock import Mock, patch

import httpx
import pytest

from gemini_imagen.cli.langsmith_client import (
    extract_imagen_params,
    fetch_trace,
    fetch_trace_from_url,
    get_langsmith_api_key,
    parse_trace_url,
)


class TestGetLangsmithApiKey:
    """Tests for get_langsmith_api_key."""

    def test_returns_api_key_from_env(self):
        """Should return API key from environment."""
        with patch.dict(os.environ, {"LANGSMITH_API_KEY": "test-key"}):
            result = get_langsmith_api_key()
            assert result == "test-key"

    def test_returns_none_when_not_set(self):
        """Should return None when API key not set."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_langsmith_api_key()
            assert result is None


class TestParseTraceUrl:
    """Tests for parse_trace_url."""

    def test_parses_public_url(self):
        """Should parse public LangSmith URL."""
        url = "https://smith.langchain.com/public/abc123/r/def456"
        result = parse_trace_url(url)
        assert result == ("abc123", "def456")

    def test_parses_project_url(self):
        """Should parse project LangSmith URL."""
        url = "https://smith.langchain.com/o/org/projects/p/proj123/r/run456"
        result = parse_trace_url(url)
        assert result == ("proj123", "run456")

    def test_treats_plain_string_as_run_id(self):
        """Should treat plain string as run ID."""
        result = parse_trace_url("run123")
        assert result == (None, "run123")

    def test_returns_none_for_invalid_url(self):
        """Should return None for invalid URL format."""
        url = "https://example.com/invalid/path"
        result = parse_trace_url(url)
        assert result is None


class TestFetchTrace:
    """Tests for fetch_trace."""

    def test_fetches_trace_successfully(self):
        """Should fetch trace from LangSmith API."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "run123",
            "inputs": {"prompt": "test prompt"},
        }

        with (
            patch("httpx.Client") as mock_client_class,
            patch.dict(os.environ, {"LANGSMITH_API_KEY": "test-key"}),
        ):
            mock_client = Mock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=None)
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = fetch_trace("run123")

            assert result == {"id": "run123", "inputs": {"prompt": "test prompt"}}
            mock_client.get.assert_called_once_with(
                "https://api.smith.langchain.com/runs/run123",
                headers={"x-api-key": "test-key", "Content-Type": "application/json"},
                timeout=30.0,
            )

    def test_uses_provided_api_key(self):
        """Should use provided API key over environment."""
        mock_response = Mock()
        mock_response.json.return_value = {"id": "run123"}

        with patch("httpx.Client") as mock_client_class:
            mock_client = Mock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=None)
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = fetch_trace("run123", api_key="custom-key")

            assert result == {"id": "run123"}
            mock_client.get.assert_called_once()
            call_kwargs = mock_client.get.call_args[1]
            assert call_kwargs["headers"]["x-api-key"] == "custom-key"

    def test_raises_error_when_no_api_key(self):
        """Should raise ValueError when no API key provided."""
        with (
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(ValueError, match="LangSmith API key not provided"),
        ):
            fetch_trace("run123")

    def test_raises_error_on_http_error(self):
        """Should raise HTTPError on API failure."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "404 Not Found", request=Mock(), response=Mock()
        )

        with (
            patch("httpx.Client") as mock_client_class,
            patch.dict(os.environ, {"LANGSMITH_API_KEY": "test-key"}),
        ):
            mock_client = Mock()
            mock_client.__enter__ = Mock(return_value=mock_client)
            mock_client.__exit__ = Mock(return_value=None)
            mock_client.get.return_value = mock_response
            mock_client_class.return_value = mock_client

            with pytest.raises(httpx.HTTPStatusError):
                fetch_trace("run123")


class TestFetchTraceFromUrl:
    """Tests for fetch_trace_from_url."""

    def test_fetches_from_public_url(self):
        """Should extract run ID and fetch trace."""
        with patch("gemini_imagen.cli.langsmith_client.fetch_trace") as mock_fetch:
            mock_fetch.return_value = {"id": "def456"}

            result = fetch_trace_from_url("https://smith.langchain.com/public/abc123/r/def456")

            assert result == {"id": "def456"}
            mock_fetch.assert_called_once_with("def456", None)

    def test_fetches_from_project_url(self):
        """Should extract run ID from project URL."""
        with patch("gemini_imagen.cli.langsmith_client.fetch_trace") as mock_fetch:
            mock_fetch.return_value = {"id": "run456"}

            result = fetch_trace_from_url(
                "https://smith.langchain.com/o/org/projects/p/proj/r/run456"
            )

            assert result == {"id": "run456"}
            mock_fetch.assert_called_once_with("run456", None)

    def test_raises_error_for_invalid_url(self):
        """Should raise ValueError for invalid URL."""
        with pytest.raises(ValueError, match="Invalid LangSmith trace URL"):
            fetch_trace_from_url("https://example.com/invalid")


class TestExtractImagenParams:
    """Tests for extract_imagen_params."""

    def test_extracts_from_inputs(self):
        """Should extract parameters from inputs."""
        trace_data = {
            "inputs": {
                "prompt": "test prompt",
                "system_prompt": "test system",
                "input_images": ["image1.jpg"],
            }
        }

        result = extract_imagen_params(trace_data)

        assert result["prompt"] == "test prompt"
        assert result["system_prompt"] == "test system"
        assert result["input_images"] == ["image1.jpg"]

    def test_extracts_from_outputs(self):
        """Should extract output_images from outputs."""
        trace_data = {"outputs": {"output_images": ["output.jpg"]}}

        result = extract_imagen_params(trace_data)

        assert result["output_images"] == ["output.jpg"]

    def test_extracts_from_metadata(self):
        """Should extract metadata fields."""
        trace_data = {
            "extra": {
                "metadata": {
                    "temperature": 0.8,
                    "aspect_ratio": "16:9",
                    "model": "gemini-2.0",
                    "output_text": True,
                }
            }
        }

        result = extract_imagen_params(trace_data)

        assert result["temperature"] == 0.8
        assert result["aspect_ratio"] == "16:9"
        assert result["model"] == "gemini-2.0"
        assert result["output_text"] is True

    def test_extracts_tags(self):
        """Should extract tags from trace."""
        trace_data = {"tags": ["test", "thumbnail"]}

        result = extract_imagen_params(trace_data)

        assert result["tags"] == ["test", "thumbnail"]

    def test_handles_empty_trace(self):
        """Should handle trace with no relevant data."""
        trace_data = {"id": "run123", "name": "test"}

        result = extract_imagen_params(trace_data)

        assert result == {}

    def test_ignores_non_dict_inputs(self):
        """Should ignore non-dict inputs/outputs."""
        trace_data = {"inputs": "not a dict", "outputs": ["not", "a", "dict"]}

        result = extract_imagen_params(trace_data)

        assert result == {}
