"""
Integration tests for template + keys system.

These tests verify the full workflow from template creation to generation.
"""

import json
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from gemini_imagen.cli.main import cli
from gemini_imagen.cli.templates import delete_template, save_template, template_exists


@pytest.fixture
def runner():
    """Provide Click CLI runner."""
    return CliRunner()


@pytest.fixture
def temp_template_name():
    """Provide temporary template name and cleanup after test."""
    name = "test_integration_template"
    yield name
    # Cleanup
    if template_exists(name):
        delete_template(name)


@pytest.fixture
def sample_template():
    """Provide sample template data."""
    return {
        "prompt": "Create a YouTube thumbnail for {show_name}. Guest: {guest_name}",
        "system_prompt": "You are an expert thumbnail designer.",
        "temperature": 0.7,
        "aspect_ratio": "16:9",
        "output_images": ["/tmp/output.png"],
        "tags": ["test", "integration"],
    }


@pytest.fixture
def sample_keys():
    """Provide sample keys data."""
    return {
        "show_name": "The Joe Rogan Experience",
        "guest_name": "Daryl Davis",
    }


class TestTemplateWorkflow:
    """Integration tests for full template workflow."""

    def test_save_and_load_template(self, temp_template_name, sample_template):
        """Test saving and loading a template."""
        # Save template
        save_template(temp_template_name, sample_template)

        # Verify it exists
        assert template_exists(temp_template_name)

        # Load it back
        from gemini_imagen.cli.templates import load_template

        loaded = load_template(temp_template_name)

        # Verify content matches
        assert loaded == sample_template

    def test_template_cli_save_and_show(self, runner, temp_template_name, sample_template):
        """Test template save and show via CLI."""
        # Create temp file with template
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sample_template, f)
            template_file = f.name

        try:
            # Save via CLI
            result = runner.invoke(
                cli,
                ["template", "save", temp_template_name, "--from-json", template_file],
            )
            assert result.exit_code == 0
            assert f"Template '{temp_template_name}' saved" in result.output

            # Show via CLI
            result = runner.invoke(cli, ["template", "show", temp_template_name])
            assert result.exit_code == 0
            assert "guest_name" in result.output
            assert "show_name" in result.output
            assert temp_template_name in result.output

        finally:
            Path(template_file).unlink()

    def test_template_cli_list(self, runner, temp_template_name, sample_template):
        """Test listing templates via CLI."""
        # Save a template first
        save_template(temp_template_name, sample_template)

        # List templates
        result = runner.invoke(cli, ["template", "list"])
        assert result.exit_code == 0
        assert temp_template_name in result.output

    def test_template_cli_delete(self, runner, temp_template_name, sample_template):
        """Test deleting template via CLI."""
        # Save a template first
        save_template(temp_template_name, sample_template)
        assert template_exists(temp_template_name)

        # Delete via CLI
        result = runner.invoke(cli, ["template", "delete", temp_template_name], input="y\n")
        assert result.exit_code == 0

        # Verify it's gone
        assert not template_exists(temp_template_name)


class TestVariableSubstitutionIntegration:
    """Integration tests for variable substitution with templates."""

    def test_substitute_variables_in_prompt(self, temp_template_name, sample_template, sample_keys):
        """Test variable substitution works end-to-end."""
        from gemini_imagen.cli.job_merge import (
            merge_template_keys_overrides,
            split_job_and_variables,
        )
        from gemini_imagen.cli.variable_substitution import substitute_variables

        # Save template
        save_template(temp_template_name, sample_template)

        # Merge template + keys
        merged = merge_template_keys_overrides(
            template=sample_template,
            keys=[sample_keys],
            cli_overrides=None,
        )

        # Split and substitute
        lib_params, var_values = split_job_and_variables(merged)
        final_job = substitute_variables(lib_params, var_values)

        # Verify substitution
        assert "The Joe Rogan Experience" in final_job["prompt"]
        assert "Daryl Davis" in final_job["prompt"]
        assert "{show_name}" not in final_job["prompt"]
        assert "{guest_name}" not in final_job["prompt"]

    def test_cli_override_variables(self, temp_template_name, sample_template, sample_keys):
        """Test that CLI overrides work correctly."""
        from gemini_imagen.cli.job_merge import (
            merge_template_keys_overrides,
            split_job_and_variables,
        )
        from gemini_imagen.cli.variable_substitution import substitute_variables

        # CLI override
        cli_overrides = {"guest_name": "Elon Musk"}

        # Merge all three layers
        merged = merge_template_keys_overrides(
            template=sample_template,
            keys=[sample_keys],
            cli_overrides=cli_overrides,
        )

        # Split and substitute
        lib_params, var_values = split_job_and_variables(merged)
        final_job = substitute_variables(lib_params, var_values)

        # Verify CLI override took precedence
        assert "Elon Musk" in final_job["prompt"]
        assert "Daryl Davis" not in final_job["prompt"]
        assert "The Joe Rogan Experience" in final_job["prompt"]  # From keys

    def test_multiple_keys_files_precedence(self, sample_template):
        """Test that later keys files override earlier ones."""
        from gemini_imagen.cli.job_merge import (
            merge_template_keys_overrides,
            split_job_and_variables,
        )
        from gemini_imagen.cli.variable_substitution import substitute_variables

        keys1 = {"show_name": "Show 1", "guest_name": "Guest 1"}
        keys2 = {"guest_name": "Guest 2"}  # Override guest_name only

        merged = merge_template_keys_overrides(
            template=sample_template,
            keys=[keys1, keys2],
            cli_overrides=None,
        )

        lib_params, var_values = split_job_and_variables(merged)
        final_job = substitute_variables(lib_params, var_values)

        # keys2 should override guest_name, but not show_name
        assert "Show 1" in final_job["prompt"]
        assert "Guest 2" in final_job["prompt"]
        assert "Guest 1" not in final_job["prompt"]


class TestGenerateCommandIntegration:
    """Integration tests for generate command with templates."""

    def test_generate_dump_job_with_template(
        self, runner, temp_template_name, sample_template, sample_keys
    ):
        """Test generate --dump-job with template and keys."""
        # Save template
        save_template(temp_template_name, sample_template)

        # Create keys file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sample_keys, f)
            keys_file = f.name

        try:
            # Run generate with --dump-job
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--template",
                    temp_template_name,
                    "--keys",
                    keys_file,
                    "--dump-job",
                ],
            )

            assert result.exit_code == 0

            # Parse output as JSON
            output = json.loads(result.output)

            # Verify variables were substituted
            assert "The Joe Rogan Experience" in output["prompt"]
            assert "Daryl Davis" in output["prompt"]
            assert output["temperature"] == 0.7
            assert output["aspect_ratio"] == "16:9"

        finally:
            Path(keys_file).unlink()

    def test_generate_dry_run_with_var_override(
        self, runner, temp_template_name, sample_template, sample_keys
    ):
        """Test generate --dry-run with --var override."""
        # Save template
        save_template(temp_template_name, sample_template)

        # Create keys file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sample_keys, f)
            keys_file = f.name

        try:
            # Run with --dry-run and --var
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--template",
                    temp_template_name,
                    "--keys",
                    keys_file,
                    "--var",
                    "guest_name=Neil deGrasse Tyson",
                    "--dry-run",
                ],
            )

            assert result.exit_code == 0
            assert "Would execute the following job:" in result.output
            assert "Neil deGrasse Tyson" in result.output
            assert "Daryl Davis" not in result.output

        finally:
            Path(keys_file).unlink()

    def test_generate_missing_variable_error(self, runner, temp_template_name, sample_template):
        """Test that missing variables produce clear error."""
        # Save template
        save_template(temp_template_name, sample_template)

        # Create incomplete keys (missing guest_name)
        incomplete_keys = {"show_name": "The Joe Rogan Experience"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(incomplete_keys, f)
            keys_file = f.name

        try:
            # Run generate - should fail
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--template",
                    temp_template_name,
                    "--keys",
                    keys_file,
                    "--dump-job",
                ],
            )

            assert result.exit_code != 0
            assert "Missing required variables" in result.output
            assert "guest_name" in result.output

        finally:
            Path(keys_file).unlink()

    def test_generate_with_system_prompt_from_file(
        self, runner, temp_template_name, sample_template, sample_keys
    ):
        """Test generate with system prompt loaded from file."""
        # Save template
        save_template(temp_template_name, sample_template)

        # Create keys file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(sample_keys, f)
            keys_file = f.name

        # Create system prompt file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Custom system prompt from file")
            system_prompt_file = f.name

        try:
            # Run with @file.txt syntax
            result = runner.invoke(
                cli,
                [
                    "generate",
                    "--template",
                    temp_template_name,
                    "--keys",
                    keys_file,
                    "-s",
                    f"@{system_prompt_file}",
                    "--dump-job",
                ],
            )

            assert result.exit_code == 0
            output = json.loads(result.output)
            assert output["system_prompt"] == "Custom system prompt from file"

        finally:
            Path(keys_file).unlink()
            Path(system_prompt_file).unlink()


class TestComplexVariablePatterns:
    """Integration tests for complex variable patterns."""

    def test_nested_json_in_variables(self, temp_template_name):
        """Test handling complex JSON data in variables."""
        template = {
            "prompt": "Use this data: {data}",
            "output_images": ["/tmp/out.png"],
        }

        keys = {
            "data": json.dumps({"name": "Test", "nested": {"value": 123}}),
        }

        save_template(temp_template_name, template)

        from gemini_imagen.cli.job_merge import (
            merge_template_keys_overrides,
            split_job_and_variables,
        )
        from gemini_imagen.cli.variable_substitution import substitute_variables

        merged = merge_template_keys_overrides(template, [keys], None)
        lib_params, var_values = split_job_and_variables(merged)
        final_job = substitute_variables(lib_params, var_values)

        # Verify JSON was substituted
        assert '"name": "Test"' in final_job["prompt"]
        assert '"nested"' in final_job["prompt"]

    def test_multiple_variables_in_output_path(self):
        """Test multiple variables in output path pattern."""
        template = {
            "prompt": "test",
            "output_images": ["s3://bucket/{show_id}/{episode_id}/thumbnail.jpg"],
        }

        keys = {
            "show_id": "show123",
            "episode_id": "ep456",
        }

        from gemini_imagen.cli.job_merge import (
            merge_template_keys_overrides,
            split_job_and_variables,
        )
        from gemini_imagen.cli.variable_substitution import substitute_variables

        merged = merge_template_keys_overrides(template, [keys], None)
        lib_params, var_values = split_job_and_variables(merged)
        final_job = substitute_variables(lib_params, var_values)

        # Verify path was constructed correctly
        expected_path = "s3://bucket/show123/ep456/thumbnail.jpg"
        assert final_job["output_images"][0] == expected_path
