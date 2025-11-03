"""
Wide integration test for async/await bugs in CLI commands.

This test actually invokes CLI commands and ensures they properly handle async operations.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from gemini_imagen.cli.main import cli
from gemini_imagen.constants import DEFAULT_ANALYSIS_MODEL, DEFAULT_GENERATION_MODEL
from gemini_imagen.gemini_image_wrapper import GenerationResult


@pytest.fixture
def runner():
    """Provide Click CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_generation_result():
    """Provide a mock generation result."""
    result = Mock(spec=GenerationResult)
    result.image_location = "/tmp/test_output.png"
    result.image_s3_uri = None
    result.image_http_url = None
    result.text = None
    result.images = []
    return result


class TestGenerateCommandAsync:
    """Test that generate command properly awaits async operations."""

    def test_generate_command_awaits_async_generate(self, runner, mock_generation_result):
        """
        BUG: Generate command calls async generate() without await.

        This is a WIDE test that actually invokes the CLI command
        and mocks the generator to ensure it's being called correctly.
        """
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            output_path = f.name

        try:
            # Mock the generator class and its async generate method
            mock_generator_instance = Mock()
            mock_generator_instance.generate = AsyncMock(return_value=mock_generation_result)

            with (
                patch(
                    "gemini_imagen.cli.commands.generate.GeminiImageGenerator"
                ) as mock_generator_class,
                patch("gemini_imagen.cli.commands.generate.get_config") as mock_config,
            ):
                # Setup mocks
                mock_generator_class.return_value = mock_generator_instance

                mock_cfg = Mock()
                mock_cfg.get_google_api_key.return_value = "test-api-key"
                mock_cfg.get_generation_model.return_value = DEFAULT_GENERATION_MODEL
                mock_cfg.get_langsmith_tracing.return_value = False
                mock_cfg.get_safety_settings.return_value = None
                mock_cfg.get_temperature.return_value = None
                mock_cfg.get_aspect_ratio.return_value = None
                mock_config.return_value = mock_cfg

                # Run the command
                result = runner.invoke(
                    cli,
                    ["generate", "test prompt", "-o", output_path],
                )

                # The command should succeed, not crash with AttributeError
                assert result.exit_code == 0, f"Command failed: {result.output}"
                assert "Error" not in result.output
                assert "'coroutine' object" not in result.output

                # Verify async generate was called
                mock_generator_instance.generate.assert_called_once()

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_generate_with_template_awaits_async(self, runner, mock_generation_result):
        """Test that template-based generation also properly awaits."""
        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as template_file,
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as keys_file,
            tempfile.NamedTemporaryFile(suffix=".png", delete=False) as output_file,
        ):
            # Create template
            template_file.write('{"prompt": "Test {var}", "output_images": ["/tmp/out.png"]}')
            template_file.flush()

            # Create keys
            keys_file.write('{"var": "value"}')
            keys_file.flush()

            template_path = template_file.name
            keys_path = keys_file.name
            output_path = output_file.name

        try:
            # Save template first
            with patch("gemini_imagen.cli.commands.template.save_template"):
                result = runner.invoke(
                    cli,
                    ["template", "save", "test_template", "--from-json", template_path],
                )
                assert result.exit_code == 0

            # Mock the generator
            mock_generator_instance = Mock()
            mock_generator_instance.generate = AsyncMock(return_value=mock_generation_result)

            with (
                patch(
                    "gemini_imagen.cli.commands.generate.GeminiImageGenerator"
                ) as mock_generator_class,
                patch("gemini_imagen.cli.commands.generate.get_config") as mock_config,
                patch("gemini_imagen.cli.commands.generate.load_template") as mock_load,
            ):
                # Setup mocks
                mock_generator_class.return_value = mock_generator_instance

                mock_cfg = Mock()
                mock_cfg.get_google_api_key.return_value = "test-api-key"
                mock_cfg.get_generation_model.return_value = DEFAULT_GENERATION_MODEL
                mock_cfg.get_langsmith_tracing.return_value = False
                mock_cfg.get_safety_settings.return_value = None
                mock_cfg.get_temperature.return_value = None
                mock_cfg.get_aspect_ratio.return_value = None
                mock_config.return_value = mock_cfg

                mock_load.return_value = {
                    "prompt": "Test {var}",
                    "output_images": [output_path],
                }

                # Run generate with template
                result = runner.invoke(
                    cli,
                    [
                        "generate",
                        "--template",
                        "test_template",
                        "--keys",
                        keys_path,
                    ],
                )

                # Should succeed
                assert result.exit_code == 0, f"Command failed: {result.output}"
                assert "'coroutine' object" not in result.output

                # Verify async generate was called
                mock_generator_instance.generate.assert_called_once()

        finally:
            Path(template_path).unlink(missing_ok=True)
            Path(keys_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)


class TestAnalyzeCommandAsync:
    """Test that analyze command properly awaits async operations."""

    def test_analyze_command_awaits_async_analyze(self, runner):
        """Test that analyze command properly awaits async operations."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            image_path = f.name
            # Write a minimal PNG
            f.write(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00\x00"
                b"\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            )

        try:
            mock_generator = Mock()
            # Analyze command uses generate() method with output_text=True
            mock_result = Mock()
            mock_result.text = "Test analysis result"
            mock_generator.generate = AsyncMock(return_value=mock_result)

            with (
                patch("gemini_imagen.cli.commands.analyze.GeminiImageGenerator") as mock_class,
                patch("gemini_imagen.cli.commands.analyze.get_config") as mock_config,
            ):
                mock_class.return_value = mock_generator

                mock_cfg = Mock()
                mock_cfg.get_google_api_key.return_value = "test-api-key"
                mock_cfg.get_analysis_model.return_value = DEFAULT_ANALYSIS_MODEL
                mock_cfg.get_langsmith_tracing.return_value = False
                mock_config.return_value = mock_cfg

                result = runner.invoke(cli, ["analyze", image_path])

                # Should not crash with coroutine error
                assert "'coroutine' object" not in result.output
                assert result.exit_code == 0 or "Error" not in result.output

        finally:
            Path(image_path).unlink(missing_ok=True)


class TestEditCommandAsync:
    """Test that edit command properly awaits async operations."""

    def test_edit_command_awaits_async_generate(self, runner, mock_generation_result):
        """Test that edit command properly awaits async operations."""
        with (
            tempfile.NamedTemporaryFile(suffix=".png", delete=False) as input_file,
            tempfile.NamedTemporaryFile(suffix=".png", delete=False) as output_file,
        ):
            # Write minimal PNG to input
            input_file.write(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00\x00"
                b"\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            input_file.flush()

            input_path = input_file.name
            output_path = output_file.name

        try:
            mock_generator = Mock()
            mock_generator.generate = AsyncMock(return_value=mock_generation_result)

            with (
                patch("gemini_imagen.cli.commands.edit.GeminiImageGenerator") as mock_class,
                patch("gemini_imagen.cli.commands.edit.get_config") as mock_config,
            ):
                mock_class.return_value = mock_generator

                mock_cfg = Mock()
                mock_cfg.get_google_api_key.return_value = "test-api-key"
                mock_cfg.get_generation_model.return_value = DEFAULT_GENERATION_MODEL
                mock_config.return_value = mock_cfg

                result = runner.invoke(
                    cli,
                    ["edit", "test prompt", "-i", input_path, "-o", output_path],
                )

                # Should not crash with coroutine error
                assert "'coroutine' object" not in result.output
                assert result.exit_code == 0 or "Error" not in result.output

        finally:
            Path(input_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)
