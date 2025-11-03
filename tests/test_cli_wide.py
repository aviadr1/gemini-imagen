"""
Wide integration tests for CLI commands.

These tests actually invoke CLI commands end-to-end and test the full pipeline,
similar to what demo.sh does but in an automated, repeatable way.

Unlike the narrow unit tests that mock individual components, these tests:
1. Invoke the actual CLI entry point
2. Mock only at the API boundary (GeminiImageGenerator)
3. Test the full flow including config, arg parsing, async handling, etc.
"""

import json
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


@pytest.fixture
def mock_analysis_result():
    """Provide a mock analysis result."""
    result = Mock(spec=GenerationResult)
    result.text = "This is a test image showing various elements."
    result.images = []
    return result


class TestGenerateCommandWide:
    """Wide tests for generate command covering full end-to-end flow."""

    def test_generate_basic_flow(self, runner, mock_generation_result):
        """Test basic generate command with all the pieces working together."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            output_path = f.name

        try:
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
                mock_cfg.get_safety_settings.return_value = None
                mock_cfg.get_temperature.return_value = None
                mock_cfg.get_aspect_ratio.return_value = None
                mock_config.return_value = mock_cfg

                # Run the command
                result = runner.invoke(
                    cli,
                    ["generate", "a serene landscape", "-o", output_path],
                )

                # Should succeed
                assert result.exit_code == 0, f"Command failed: {result.output}"
                assert "Generated image saved" in result.output
                assert "'coroutine' object" not in result.output

                # Verify correct model was used
                mock_generator_class.assert_called_once_with(
                    model_name=DEFAULT_GENERATION_MODEL,
                    api_key="test-api-key",
                    log_images=False,
                )

                # Verify async generate was called with Pydantic model
                mock_generator_instance.generate.assert_called_once()
                call_args = mock_generator_instance.generate.call_args[0]
                assert (
                    len(call_args) == 1
                )  # Should be called with one positional arg (the Pydantic model)
                params = call_args[0]
                assert params.prompt == "a serene landscape"
                assert params.output_images == [output_path]

        finally:
            Path(output_path).unlink(missing_ok=True)

    def test_generate_with_all_options(self, runner, mock_generation_result):
        """Test generate with multiple options including temperature, aspect ratio, etc."""
        with (
            tempfile.NamedTemporaryFile(suffix=".png", delete=False) as output_file,
            tempfile.NamedTemporaryFile(suffix=".png", delete=False) as input_file,
        ):
            # Write minimal PNG to input
            input_file.write(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00\x00"
                b"\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            input_file.flush()

            output_path = output_file.name
            input_path = input_file.name

        try:
            mock_generator_instance = Mock()
            mock_generator_instance.generate = AsyncMock(return_value=mock_generation_result)

            with (
                patch(
                    "gemini_imagen.cli.commands.generate.GeminiImageGenerator"
                ) as mock_generator_class,
                patch("gemini_imagen.cli.commands.generate.get_config") as mock_config,
            ):
                mock_generator_class.return_value = mock_generator_instance

                mock_cfg = Mock()
                mock_cfg.get_google_api_key.return_value = "test-api-key"
                mock_cfg.get_generation_model.return_value = DEFAULT_GENERATION_MODEL
                mock_cfg.get_langsmith_tracing.return_value = False
                mock_cfg.get_safety_settings.return_value = None
                mock_cfg.get_temperature.return_value = None
                mock_cfg.get_aspect_ratio.return_value = None
                mock_config.return_value = mock_cfg

                # Run with many options
                result = runner.invoke(
                    cli,
                    [
                        "generate",
                        "test prompt",
                        "-o",
                        output_path,
                        "-i",
                        input_path,
                        "--temperature",
                        "0.8",
                        "--aspect-ratio",
                        "16:9",
                        "--tag",
                        "test",
                        "--tag",
                        "wide",
                    ],
                )

                assert result.exit_code == 0, f"Command failed: {result.output}"
                assert "'coroutine' object" not in result.output

                # Verify all options were passed correctly via Pydantic model
                call_args = mock_generator_instance.generate.call_args[0]
                params = call_args[0]
                assert params.prompt == "test prompt"
                assert params.temperature == 0.8
                assert params.aspect_ratio == "16:9"
                assert params.tags == ["test", "wide"]
                assert input_path in str(params.input_images)

        finally:
            Path(output_path).unlink(missing_ok=True)
            Path(input_path).unlink(missing_ok=True)

    def test_generate_with_json_output(self, runner, mock_generation_result):
        """Test generate with JSON output mode."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            output_path = f.name

        try:
            mock_generator_instance = Mock()
            mock_generator_instance.generate = AsyncMock(return_value=mock_generation_result)

            with (
                patch(
                    "gemini_imagen.cli.commands.generate.GeminiImageGenerator"
                ) as mock_generator_class,
                patch("gemini_imagen.cli.commands.generate.get_config") as mock_config,
            ):
                mock_generator_class.return_value = mock_generator_instance

                mock_cfg = Mock()
                mock_cfg.get_google_api_key.return_value = "test-api-key"
                mock_cfg.get_generation_model.return_value = DEFAULT_GENERATION_MODEL
                mock_cfg.get_langsmith_tracing.return_value = False
                mock_cfg.get_safety_settings.return_value = None
                mock_cfg.get_temperature.return_value = None
                mock_cfg.get_aspect_ratio.return_value = None
                mock_config.return_value = mock_cfg

                result = runner.invoke(
                    cli,
                    ["generate", "test", "-o", output_path, "--json"],
                )

                assert result.exit_code == 0, f"Command failed: {result.output}"

                # Parse JSON output
                output_data = json.loads(result.output)
                assert output_data["success"] is True
                assert output_data["image_path"] == mock_generation_result.image_location
                assert output_data["model"] == DEFAULT_GENERATION_MODEL

        finally:
            Path(output_path).unlink(missing_ok=True)


class TestAnalyzeCommandWide:
    """Wide tests for analyze command."""

    def test_analyze_basic_flow(self, runner, mock_analysis_result):
        """Test basic analyze command end-to-end."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            # Write minimal PNG
            f.write(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00\x00"
                b"\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            f.flush()
            image_path = f.name

        try:
            mock_generator_instance = Mock()
            mock_generator_instance.generate = AsyncMock(return_value=mock_analysis_result)

            with (
                patch(
                    "gemini_imagen.cli.commands.analyze.GeminiImageGenerator"
                ) as mock_generator_class,
                patch("gemini_imagen.cli.commands.analyze.get_config") as mock_config,
            ):
                mock_generator_class.return_value = mock_generator_instance

                mock_cfg = Mock()
                mock_cfg.get_google_api_key.return_value = "test-api-key"
                mock_cfg.get_analysis_model.return_value = DEFAULT_ANALYSIS_MODEL
                mock_cfg.get_langsmith_tracing.return_value = False
                mock_config.return_value = mock_cfg

                result = runner.invoke(cli, ["analyze", image_path])

                assert result.exit_code == 0, f"Command failed: {result.output}"
                assert mock_analysis_result.text in result.output
                assert "'coroutine' object" not in result.output

                # Verify correct model was used
                mock_generator_class.assert_called_once_with(
                    model_name=DEFAULT_ANALYSIS_MODEL,
                    api_key="test-api-key",
                    log_images=False,
                )

        finally:
            Path(image_path).unlink(missing_ok=True)

    def test_analyze_with_custom_prompt(self, runner, mock_analysis_result):
        """Test analyze with custom prompt."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00\x00"
                b"\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            f.flush()
            image_path = f.name

        try:
            mock_generator_instance = Mock()
            mock_generator_instance.generate = AsyncMock(return_value=mock_analysis_result)

            with (
                patch(
                    "gemini_imagen.cli.commands.analyze.GeminiImageGenerator"
                ) as mock_generator_class,
                patch("gemini_imagen.cli.commands.analyze.get_config") as mock_config,
            ):
                mock_generator_class.return_value = mock_generator_instance

                mock_cfg = Mock()
                mock_cfg.get_google_api_key.return_value = "test-api-key"
                mock_cfg.get_analysis_model.return_value = DEFAULT_ANALYSIS_MODEL
                mock_cfg.get_langsmith_tracing.return_value = False
                mock_config.return_value = mock_cfg

                result = runner.invoke(
                    cli, ["analyze", image_path, "-p", "What colors are in this image?"]
                )

                assert result.exit_code == 0, f"Command failed: {result.output}"

                # Verify custom prompt was used via Pydantic model
                call_args = mock_generator_instance.generate.call_args[0]
                params = call_args[0]
                assert params.prompt == "What colors are in this image?"
                assert params.output_text is True

        finally:
            Path(image_path).unlink(missing_ok=True)


class TestEditCommandWide:
    """Wide tests for edit command."""

    def test_edit_basic_flow(self, runner, mock_generation_result):
        """Test basic edit command end-to-end."""
        with (
            tempfile.NamedTemporaryFile(suffix=".png", delete=False) as input_file,
            tempfile.NamedTemporaryFile(suffix=".png", delete=False) as output_file,
        ):
            # Write minimal PNG
            input_file.write(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00\x00"
                b"\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            input_file.flush()

            input_path = input_file.name
            output_path = output_file.name

        try:
            mock_generator_instance = Mock()
            mock_generator_instance.generate = AsyncMock(return_value=mock_generation_result)

            with (
                patch(
                    "gemini_imagen.cli.commands.edit.GeminiImageGenerator"
                ) as mock_generator_class,
                patch("gemini_imagen.cli.commands.edit.get_config") as mock_config,
            ):
                mock_generator_class.return_value = mock_generator_instance

                mock_cfg = Mock()
                mock_cfg.get_google_api_key.return_value = "test-api-key"
                mock_cfg.get_generation_model.return_value = DEFAULT_GENERATION_MODEL
                mock_cfg.get_langsmith_tracing.return_value = False
                mock_cfg.get_safety_settings.return_value = None
                mock_cfg.get_temperature.return_value = None
                mock_cfg.get_aspect_ratio.return_value = None
                mock_config.return_value = mock_cfg

                result = runner.invoke(
                    cli,
                    ["edit", "make it sunset", "-i", input_path, "-o", output_path],
                )

                assert result.exit_code == 0, f"Command failed: {result.output}"
                assert "Edited image saved" in result.output
                assert "'coroutine' object" not in result.output

                # Verify correct model was used (edit generates images)
                mock_generator_class.assert_called_once_with(
                    model_name=DEFAULT_GENERATION_MODEL,
                    api_key="test-api-key",
                    log_images=False,
                )

        finally:
            Path(input_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)


class TestTemplateWorkflowWide:
    """Wide tests for the full template + keys workflow."""

    def test_template_save_load_generate_workflow(self, runner, mock_generation_result):
        """Test the full template workflow: save, load, generate with keys."""
        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as template_file,
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as keys_file,
            tempfile.NamedTemporaryFile(suffix=".png", delete=False) as output_file,
        ):
            # Create template JSON
            template_data = {
                "prompt": "Test {topic} for {show}",
                "output_images": ["{output_path}"],
                "temperature": 0.7,
            }
            json.dump(template_data, template_file)
            template_file.flush()

            # Create keys JSON
            keys_data = {"topic": "AI", "show": "TechTalks", "output_path": output_file.name}
            json.dump(keys_data, keys_file)
            keys_file.flush()

            template_path = template_file.name
            keys_path = keys_file.name
            output_path = output_file.name

        try:
            # Step 1: Save template
            with patch("gemini_imagen.cli.commands.template.save_template") as mock_save:
                mock_save.return_value = Path("/tmp/test_template.json")
                result = runner.invoke(
                    cli,
                    ["template", "save", "test_template", "--from-json", template_path],
                )
                assert result.exit_code == 0, f"Template save failed: {result.output}"
                assert "Template 'test_template' saved" in result.output

            # Step 2: Load template
            with patch("gemini_imagen.cli.commands.template.load_template") as mock_load:
                mock_load.return_value = template_data
                result = runner.invoke(cli, ["template", "load", "test_template"])
                assert result.exit_code == 0, f"Template load failed: {result.output}"
                assert "Test {topic}" in result.output

            # Step 3: Generate with template + keys
            mock_generator_instance = Mock()
            mock_generator_instance.generate = AsyncMock(return_value=mock_generation_result)

            with (
                patch(
                    "gemini_imagen.cli.commands.generate.GeminiImageGenerator"
                ) as mock_generator_class,
                patch("gemini_imagen.cli.commands.generate.get_config") as mock_config,
                patch("gemini_imagen.cli.commands.generate.load_template") as mock_load_template,
            ):
                mock_generator_class.return_value = mock_generator_instance

                mock_cfg = Mock()
                mock_cfg.get_google_api_key.return_value = "test-api-key"
                mock_cfg.get_generation_model.return_value = DEFAULT_GENERATION_MODEL
                mock_cfg.get_langsmith_tracing.return_value = False
                mock_cfg.get_safety_settings.return_value = None
                mock_cfg.get_temperature.return_value = None
                mock_cfg.get_aspect_ratio.return_value = None
                mock_config.return_value = mock_cfg

                mock_load_template.return_value = template_data

                result = runner.invoke(
                    cli,
                    ["generate", "--template", "test_template", "--keys", keys_path],
                )

                assert result.exit_code == 0, f"Generate with template failed: {result.output}"
                assert "'coroutine' object" not in result.output

                # Verify variable substitution worked via Pydantic model
                call_args = mock_generator_instance.generate.call_args[0]
                params = call_args[0]
                assert params.prompt == "Test AI for TechTalks"
                assert params.output_images == [output_path]
                assert params.temperature == 0.7

        finally:
            Path(template_path).unlink(missing_ok=True)
            Path(keys_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)

    def test_template_with_variable_overrides(self, runner, mock_generation_result):
        """Test template with CLI variable overrides."""
        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as keys_file,
            tempfile.NamedTemporaryFile(suffix=".png", delete=False) as output_file,
        ):
            # Create keys
            keys_data = {"topic": "AI", "show": "TechTalks", "output_path": output_file.name}
            json.dump(keys_data, keys_file)
            keys_file.flush()

            keys_path = keys_file.name
            output_path = output_file.name

        try:
            mock_generator_instance = Mock()
            mock_generator_instance.generate = AsyncMock(return_value=mock_generation_result)

            template_data = {
                "prompt": "Test {topic} for {show}",
                "output_images": ["{output_path}"],
            }

            with (
                patch(
                    "gemini_imagen.cli.commands.generate.GeminiImageGenerator"
                ) as mock_generator_class,
                patch("gemini_imagen.cli.commands.generate.get_config") as mock_config,
                patch("gemini_imagen.cli.commands.generate.load_template") as mock_load_template,
            ):
                mock_generator_class.return_value = mock_generator_instance

                mock_cfg = Mock()
                mock_cfg.get_google_api_key.return_value = "test-api-key"
                mock_cfg.get_generation_model.return_value = DEFAULT_GENERATION_MODEL
                mock_cfg.get_langsmith_tracing.return_value = False
                mock_cfg.get_safety_settings.return_value = None
                mock_cfg.get_temperature.return_value = None
                mock_cfg.get_aspect_ratio.return_value = None
                mock_config.return_value = mock_cfg

                mock_load_template.return_value = template_data

                # Generate with --var override
                result = runner.invoke(
                    cli,
                    [
                        "generate",
                        "--template",
                        "test_template",
                        "--keys",
                        keys_path,
                        "--var",
                        "topic=Machine Learning",
                    ],
                )

                assert result.exit_code == 0, f"Command failed: {result.output}"

                # Verify override worked (CLI --var should override keys) via Pydantic model
                call_args = mock_generator_instance.generate.call_args[0]
                params = call_args[0]
                assert params.prompt == "Test Machine Learning for TechTalks"

        finally:
            Path(keys_path).unlink(missing_ok=True)
            Path(output_path).unlink(missing_ok=True)


class TestConfigurationWide:
    """Wide tests for configuration management across commands."""

    def test_model_configuration_for_different_commands(
        self, runner, mock_generation_result, mock_analysis_result
    ):
        """Test that generation and analysis use correct default models."""
        with (
            tempfile.NamedTemporaryFile(suffix=".png", delete=False) as gen_output,
            tempfile.NamedTemporaryFile(suffix=".png", delete=False) as analyze_input,
        ):
            # Write minimal PNG for analysis
            analyze_input.write(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
                b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00\x00"
                b"\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
            )
            analyze_input.flush()

            gen_output_path = gen_output.name
            analyze_input_path = analyze_input.name

        try:
            # Test generate uses generation model
            mock_gen_instance = Mock()
            mock_gen_instance.generate = AsyncMock(return_value=mock_generation_result)

            with (
                patch("gemini_imagen.cli.commands.generate.GeminiImageGenerator") as mock_gen_class,
                patch("gemini_imagen.cli.commands.generate.get_config") as mock_gen_config,
            ):
                mock_gen_class.return_value = mock_gen_instance

                mock_cfg = Mock()
                mock_cfg.get_google_api_key.return_value = "test-api-key"
                mock_cfg.get_generation_model.return_value = DEFAULT_GENERATION_MODEL
                mock_cfg.get_langsmith_tracing.return_value = False
                mock_cfg.get_safety_settings.return_value = None
                mock_cfg.get_temperature.return_value = None
                mock_cfg.get_aspect_ratio.return_value = None
                mock_gen_config.return_value = mock_cfg

                result = runner.invoke(cli, ["generate", "test", "-o", gen_output_path])
                assert result.exit_code == 0

                # Verify generation model was used
                mock_gen_class.assert_called_once_with(
                    model_name=DEFAULT_GENERATION_MODEL,
                    api_key="test-api-key",
                    log_images=False,
                )

            # Test analyze uses analysis model
            mock_analyze_instance = Mock()
            mock_analyze_instance.generate = AsyncMock(return_value=mock_analysis_result)

            with (
                patch(
                    "gemini_imagen.cli.commands.analyze.GeminiImageGenerator"
                ) as mock_analyze_class,
                patch("gemini_imagen.cli.commands.analyze.get_config") as mock_analyze_config,
            ):
                mock_analyze_class.return_value = mock_analyze_instance

                mock_cfg = Mock()
                mock_cfg.get_google_api_key.return_value = "test-api-key"
                mock_cfg.get_analysis_model.return_value = DEFAULT_ANALYSIS_MODEL
                mock_cfg.get_langsmith_tracing.return_value = False
                mock_analyze_config.return_value = mock_cfg

                result = runner.invoke(cli, ["analyze", analyze_input_path])
                assert result.exit_code == 0

                # Verify analysis model was used
                mock_analyze_class.assert_called_once_with(
                    model_name=DEFAULT_ANALYSIS_MODEL,
                    api_key="test-api-key",
                    log_images=False,
                )

        finally:
            Path(gen_output_path).unlink(missing_ok=True)
            Path(analyze_input_path).unlink(missing_ok=True)
