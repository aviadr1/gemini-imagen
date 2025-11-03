"""
Tests for the CLI module.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from gemini_imagen.cli.main import cli


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_cli_help(self, runner):
        """Test that CLI help works."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Imagen - Google Gemini Image Generation CLI" in result.output
        assert "generate" in result.output
        assert "analyze" in result.output

    def test_cli_version(self, runner):
        """Test that CLI version works."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "version" in result.output.lower() or "0." in result.output


class TestKeysCommand:
    """Test keys command."""

    def test_keys_list(self, runner, temp_config_dir):
        """Test keys list command."""
        with patch("gemini_imagen.cli.commands.keys.get_config") as mock_config:
            mock_cfg = MagicMock()
            mock_cfg.get_google_api_key.return_value = None
            mock_cfg.get_aws_access_key_id.return_value = None
            mock_cfg.get_aws_secret_access_key.return_value = None
            mock_cfg.get_aws_bucket_name.return_value = None
            mock_cfg.get_langsmith_api_key.return_value = None
            mock_config.return_value = mock_cfg

            result = runner.invoke(cli, ["keys", "list"])
            assert result.exit_code == 0
            assert "Configured keys:" in result.output

    def test_keys_set(self, runner, temp_config_dir):
        """Test keys set command."""
        with patch("gemini_imagen.cli.commands.keys.get_config") as mock_config:
            mock_cfg = MagicMock()
            mock_cfg.get_path.return_value = temp_config_dir / "config.yaml"
            mock_config.return_value = mock_cfg

            result = runner.invoke(cli, ["keys", "set", "google", "test-key-123"])
            assert result.exit_code == 0
            assert "Set google" in result.output
            mock_cfg.set.assert_called_once_with("google_api_key", "test-key-123")


class TestConfigCommand:
    """Test config command."""

    def test_config_list_empty(self, runner):
        """Test config list with no configuration."""
        with patch("gemini_imagen.cli.commands.config_cmd.get_config") as mock_config:
            mock_cfg = MagicMock()
            mock_cfg.list_all.return_value = {}
            mock_cfg.get_path.return_value = Path("/tmp/config.yaml")
            mock_config.return_value = mock_cfg

            result = runner.invoke(cli, ["config", "list"])
            assert result.exit_code == 0
            assert "No configuration values set" in result.output

    def test_config_set(self, runner):
        """Test config set command."""
        with patch("gemini_imagen.cli.commands.config_cmd.get_config") as mock_config:
            mock_cfg = MagicMock()
            mock_cfg.get_path.return_value = Path("/tmp/config.yaml")
            mock_config.return_value = mock_cfg

            result = runner.invoke(cli, ["config", "set", "test_key", "test_value"])
            assert result.exit_code == 0
            assert "Set test_key = test_value" in result.output
            mock_cfg.set.assert_called_once_with("test_key", "test_value")

    def test_config_get(self, runner):
        """Test config get command."""
        with patch("gemini_imagen.cli.commands.config_cmd.get_config") as mock_config:
            mock_cfg = MagicMock()
            mock_cfg.get.return_value = "test_value"
            mock_config.return_value = mock_cfg

            result = runner.invoke(cli, ["config", "get", "test_key"])
            assert result.exit_code == 0
            assert "test_value" in result.output


class TestModelsCommand:
    """Test models command."""

    def test_models_list(self, runner):
        """Test models list command."""
        result = runner.invoke(cli, ["models", "list"])
        assert result.exit_code == 0
        assert "Available models:" in result.output
        assert "gemini-2.0-flash-exp" in result.output

    def test_models_default_get(self, runner):
        """Test getting default model."""
        with patch("gemini_imagen.cli.commands.models.get_config") as mock_config:
            mock_cfg = MagicMock()
            mock_cfg.get_default_model.return_value = "gemini-2.5-flash-image"
            mock_config.return_value = mock_cfg

            result = runner.invoke(cli, ["models", "default"])
            assert result.exit_code == 0
            assert "gemini-2.5-flash-image" in result.output

    def test_models_default_set(self, runner):
        """Test setting default model."""
        with patch("gemini_imagen.cli.commands.models.get_config") as mock_config:
            mock_cfg = MagicMock()
            mock_cfg.get_path.return_value = Path("/tmp/config.yaml")
            mock_config.return_value = mock_cfg

            result = runner.invoke(cli, ["models", "default", "gemini-2.0-flash"])
            assert result.exit_code == 0
            assert "Set default model to: gemini-2.0-flash" in result.output


class TestGenerateCommand:
    """Test generate command."""

    def test_generate_help(self, runner):
        """Test generate help."""
        result = runner.invoke(cli, ["generate", "--help"])
        assert result.exit_code == 0
        assert "Generate images from text prompts" in result.output

    def test_generate_missing_output(self, runner):
        """Test generate without required output flag."""
        result = runner.invoke(cli, ["generate", "test prompt"])
        assert result.exit_code != 0
        assert "Error" in result.output or "Missing option" in result.output

    def test_generate_missing_api_key(self, runner):
        """Test generate without API key."""
        with patch("gemini_imagen.cli.commands.generate.get_config") as mock_config:
            mock_cfg = MagicMock()
            mock_cfg.get_google_api_key.return_value = None
            mock_config.return_value = mock_cfg

            result = runner.invoke(cli, ["generate", "test prompt", "-o", "output.png"])
            assert result.exit_code == 1
            assert "API key not configured" in result.output


class TestAnalyzeCommand:
    """Test analyze command."""

    def test_analyze_help(self, runner):
        """Test analyze help."""
        result = runner.invoke(cli, ["analyze", "--help"])
        assert result.exit_code == 0
        assert "Analyze and describe images" in result.output

    def test_analyze_missing_api_key(self, runner):
        """Test analyze without API key."""
        # Create a temporary image file
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with patch("gemini_imagen.cli.commands.analyze.get_config") as mock_config:
                mock_cfg = MagicMock()
                mock_cfg.get_google_api_key.return_value = None
                mock_config.return_value = mock_cfg

                result = runner.invoke(cli, ["analyze", tmp_path])
                assert result.exit_code == 1
                assert "API key not configured" in result.output
        finally:
            Path(tmp_path).unlink(missing_ok=True)


class TestEditCommand:
    """Test edit command."""

    def test_edit_help(self, runner):
        """Test edit help."""
        result = runner.invoke(cli, ["edit", "--help"])
        assert result.exit_code == 0
        assert "Edit images using reference images" in result.output

    def test_edit_missing_input(self, runner):
        """Test edit without required input images."""
        with patch("gemini_imagen.cli.commands.edit.get_config") as mock_config:
            mock_cfg = MagicMock()
            mock_cfg.get_google_api_key.return_value = "test-key"
            mock_config.return_value = mock_cfg

            result = runner.invoke(cli, ["edit", "test prompt", "-o", "output.png"])
            # Exit code 2 is Click's usage error code
            assert result.exit_code in (1, 2)
            # The error message might vary, so just check for an error
            assert result.exit_code != 0


class TestStorageCommands:
    """Test upload and download commands."""

    def test_upload_help(self, runner):
        """Test upload help."""
        result = runner.invoke(cli, ["upload", "--help"])
        assert result.exit_code == 0
        assert "Upload an image to S3" in result.output

    def test_download_help(self, runner):
        """Test download help."""
        result = runner.invoke(cli, ["download", "--help"])
        assert result.exit_code == 0
        assert "Download an image from S3" in result.output

    def test_upload_invalid_destination(self, runner):
        """Test upload with invalid destination."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            result = runner.invoke(cli, ["upload", tmp_path, "not-an-s3-uri"])
            assert result.exit_code == 1
            assert "must be an S3 URI" in result.output
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_download_invalid_source(self, runner):
        """Test download with invalid source."""
        result = runner.invoke(cli, ["download", "not-an-s3-uri", "output.png"])
        assert result.exit_code == 1
        assert "must be an S3 URI" in result.output
