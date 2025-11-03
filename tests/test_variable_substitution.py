"""
Tests for variable substitution module.
"""

import pytest

from gemini_imagen.cli.variable_substitution import (
    extract_variables,
    find_template_variables,
    substitute_in_string,
    substitute_variables,
    validate_variables,
)


class TestExtractVariables:
    """Test extract_variables function."""

    def test_extract_single_variable(self):
        """Test extracting a single variable."""
        result = extract_variables("Hello {name}!")
        assert result == {"name"}

    def test_extract_multiple_variables(self):
        """Test extracting multiple variables."""
        result = extract_variables("{greeting} {name}, you have {count} messages")
        assert result == {"greeting", "name", "count"}

    def test_extract_no_variables(self):
        """Test text with no variables."""
        result = extract_variables("Hello world")
        assert result == set()

    def test_extract_duplicate_variables(self):
        """Test that duplicate variables are deduplicated."""
        result = extract_variables("{name} and {name} again")
        assert result == {"name"}

    def test_extract_with_underscores(self):
        """Test variables with underscores."""
        result = extract_variables("{user_name} and {user_id}")
        assert result == {"user_name", "user_id"}


class TestFindTemplateVariables:
    """Test find_template_variables function."""

    def test_find_in_prompt(self):
        """Test finding variables in prompt field."""
        template = {"prompt": "Hello {name}"}
        result = find_template_variables(template)
        assert result == {"prompt": ["name"]}

    def test_find_in_system_prompt(self):
        """Test finding variables in system_prompt field."""
        template = {"system_prompt": "You are {role}"}
        result = find_template_variables(template)
        assert result == {"system_prompt": ["role"]}

    def test_find_in_output_images(self):
        """Test finding variables in output_images field."""
        template = {"output_images": ["output_{id}.png", "thumb_{id}.jpg"]}
        result = find_template_variables(template)
        assert result == {"output_images": ["id"]}

    def test_find_multiple_fields(self):
        """Test finding variables across multiple fields."""
        template = {
            "prompt": "Hello {name}",
            "system_prompt": "You are {role}",
            "output_images": ["output_{id}.png"],
        }
        result = find_template_variables(template)
        assert result == {
            "prompt": ["name"],
            "system_prompt": ["role"],
            "output_images": ["id"],
        }

    def test_find_no_variables(self):
        """Test template with no variables."""
        template = {
            "prompt": "Hello world",
            "output_images": ["output.png"],
        }
        result = find_template_variables(template)
        assert result == {}

    def test_ignore_non_string_fields(self):
        """Test that non-string fields are ignored."""
        template = {
            "prompt": "Hello {name}",
            "temperature": 0.8,
            "tags": ["tag1", "tag2"],
        }
        result = find_template_variables(template)
        assert result == {"prompt": ["name"]}


class TestSubstituteInString:
    """Test substitute_in_string function."""

    def test_substitute_single_variable(self):
        """Test substituting a single variable."""
        result = substitute_in_string("Hello {name}!", {"name": "Alice"})
        assert result == "Hello Alice!"

    def test_substitute_multiple_variables(self):
        """Test substituting multiple variables."""
        result = substitute_in_string("{greeting} {name}", {"greeting": "Hello", "name": "Alice"})
        assert result == "Hello Alice"

    def test_substitute_missing_variable(self):
        """Test error when variable is missing."""
        with pytest.raises(KeyError, match="Missing variable 'name'"):
            substitute_in_string("Hello {name}!", {})

    def test_substitute_with_extra_variables(self):
        """Test that extra variables don't cause errors."""
        result = substitute_in_string("Hello {name}!", {"name": "Alice", "extra": "value"})
        assert result == "Hello Alice!"

    def test_substitute_json_value(self):
        """Test substituting with JSON string value."""
        result = substitute_in_string("Context: {data}", {"data": '{"key": "value"}'})
        assert result == 'Context: {"key": "value"}'


class TestSubstituteVariables:
    """Test substitute_variables function."""

    def test_substitute_in_prompt(self):
        """Test substituting variables in prompt."""
        job = {"prompt": "Hello {name}"}
        variables = {"name": "Alice"}
        result = substitute_variables(job, variables)
        assert result == {"prompt": "Hello Alice"}

    def test_substitute_in_multiple_fields(self):
        """Test substituting variables in multiple fields."""
        job = {
            "prompt": "Hello {name}",
            "system_prompt": "You are {role}",
            "output_images": ["output_{id}.png"],
        }
        variables = {"name": "Alice", "role": "assistant", "id": "123"}
        result = substitute_variables(job, variables)
        assert result == {
            "prompt": "Hello Alice",
            "system_prompt": "You are assistant",
            "output_images": ["output_123.png"],
        }

    def test_substitute_in_list(self):
        """Test substituting variables in list field."""
        job = {"output_images": ["output_{id}_a.png", "output_{id}_b.png"]}
        variables = {"id": "123"}
        result = substitute_variables(job, variables)
        assert result == {"output_images": ["output_123_a.png", "output_123_b.png"]}

    def test_preserve_non_string_values(self):
        """Test that non-string values are preserved."""
        job = {
            "prompt": "Hello {name}",
            "temperature": 0.8,
            "tags": ["tag1", "tag2"],
        }
        variables = {"name": "Alice"}
        result = substitute_variables(job, variables)
        assert result == {
            "prompt": "Hello Alice",
            "temperature": 0.8,
            "tags": ["tag1", "tag2"],
        }

    def test_strict_mode_missing_variable(self):
        """Test strict mode raises error on missing variable."""
        job = {"prompt": "Hello {name}"}
        variables = {}
        with pytest.raises(KeyError):
            substitute_variables(job, variables, strict=True)

    def test_non_strict_mode_missing_variable(self):
        """Test non-strict mode keeps original on missing variable."""
        job = {"prompt": "Hello {name}"}
        variables = {}
        result = substitute_variables(job, variables, strict=False)
        assert result == {"prompt": "Hello {name}"}

    def test_complex_template(self):
        """Test complex real-world template."""
        job = {
            "prompt": "# Community\n{community_info}\n\n# Host\n{host_info}",
            "system_prompt": "You are an expert",
            "input_images": [
                ["community", "https://example.com/img.jpg"],
                ["host", "https://example.com/host.jpg"],
            ],
            "output_images": ["s3://bucket/thumbnails/{channel_id}/thumb.jpg"],
            "tags": ["thumbnail"],
        }
        variables = {
            "community_info": '{"name": "PowerfulJRE"}',
            "host_info": '{"name": "Gigoz"}',
            "channel_id": "drumming2-abc123",
        }
        result = substitute_variables(job, variables)
        assert (
            result["prompt"] == '# Community\n{"name": "PowerfulJRE"}\n\n# Host\n{"name": "Gigoz"}'
        )
        assert result["output_images"] == ["s3://bucket/thumbnails/drumming2-abc123/thumb.jpg"]
        assert result["input_images"] == job["input_images"]  # Unchanged


class TestValidateVariables:
    """Test validate_variables function."""

    def test_valid_all_variables_present(self):
        """Test validation passes when all variables are present."""
        template = {"prompt": "Hello {name}"}
        variables = {"name": "Alice"}
        is_valid, missing = validate_variables(template, variables)
        assert is_valid is True
        assert missing == []

    def test_invalid_missing_variable(self):
        """Test validation fails when variable is missing."""
        template = {"prompt": "Hello {name}"}
        variables = {}
        is_valid, missing = validate_variables(template, variables)
        assert is_valid is False
        assert missing == ["name"]

    def test_invalid_multiple_missing_variables(self):
        """Test validation fails with multiple missing variables."""
        template = {
            "prompt": "Hello {name}",
            "output_images": ["output_{id}.png"],
        }
        variables = {}
        is_valid, missing = validate_variables(template, variables)
        assert is_valid is False
        assert set(missing) == {"name", "id"}

    def test_valid_with_extra_variables(self):
        """Test validation passes with extra variables."""
        template = {"prompt": "Hello {name}"}
        variables = {"name": "Alice", "extra": "value"}
        is_valid, missing = validate_variables(template, variables)
        assert is_valid is True
        assert missing == []

    def test_valid_no_variables_needed(self):
        """Test validation passes when template has no variables."""
        template = {"prompt": "Hello world"}
        variables = {}
        is_valid, missing = validate_variables(template, variables)
        assert is_valid is True
        assert missing == []
