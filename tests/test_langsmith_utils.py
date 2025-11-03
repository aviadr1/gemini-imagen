"""Tests for langsmith_utils module."""

from gemini_imagen.cli.langsmith_utils import (
    convert_backtick_data_to_variables,
    detect_variable_in_context,
    extract_backtick_sections,
    split_template_from_trace,
)


class TestExtractBacktickSections:
    """Tests for extract_backtick_sections."""

    def test_extracts_single_variable(self):
        """Should extract single variable placeholder."""
        text = "# Context\n```\n{community_info}\n```"
        result = extract_backtick_sections(text)
        assert result == {"community_info": "{community_info}"}

    def test_extracts_multiple_variables(self):
        """Should extract multiple variable placeholders."""
        text = """
# Community
```
{community_info}
```

# Host
```
{host_info}
```
"""
        result = extract_backtick_sections(text)
        assert result == {
            "community_info": "{community_info}",
            "host_info": "{host_info}",
        }

    def test_ignores_actual_data(self):
        """Should not extract structured data as variables."""
        text = '```\n{"name": "PowerfulJRE"}\n```'
        result = extract_backtick_sections(text)
        assert result == {}

    def test_handles_whitespace(self):
        """Should handle whitespace around backticks."""
        text = "```  \n{variable_name}\n  ```"
        result = extract_backtick_sections(text)
        assert result == {"variable_name": "{variable_name}"}

    def test_returns_empty_dict_when_no_backticks(self):
        """Should return empty dict when no backtick sections."""
        text = "Just plain text without backticks"
        result = extract_backtick_sections(text)
        assert result == {}


class TestDetectVariableInContext:
    """Tests for detect_variable_in_context."""

    def test_detects_from_context_header(self):
        """Should detect variable name from context header."""
        text = "# Context: The community\n```\n{...}\n```"
        result = detect_variable_in_context(text, "{...}")
        assert result == "community_info"

    def test_handles_lowercase_context(self):
        """Should handle lowercase 'the' in context."""
        text = "# Context: the host\n```\ndata\n```"
        result = detect_variable_in_context(text, "data")
        assert result == "host_info"

    def test_returns_none_when_no_context(self):
        """Should return None when no context header found."""
        text = "```\ndata\n```"
        result = detect_variable_in_context(text, "data")
        assert result is None

    def test_handles_complex_context(self):
        """Should extract word from complex context."""
        text = "# Context: The show information\n```\ndata\n```"
        result = detect_variable_in_context(text, "data")
        assert result == "show_info"


class TestSplitTemplateFromTrace:
    """Tests for split_template_from_trace."""

    def test_splits_basic_trace(self):
        """Should split trace into template and keys."""
        trace_data = {
            "prompt": "Generate thumbnail for {show_name}",
            "system_prompt": "You are an expert",
            "temperature": 0.7,
            "aspect_ratio": "16:9",
        }

        template, _keys = split_template_from_trace(trace_data)

        assert template["prompt"] == "Generate thumbnail for {show_name}"
        assert template["system_prompt"] == "You are an expert"
        assert template["temperature"] == 0.7
        assert template["aspect_ratio"] == "16:9"

    def test_extracts_input_images_to_keys(self):
        """Should put input_images in keys."""
        trace_data = {
            "prompt": "test",
            "input_images": ["image1.jpg", "image2.jpg"],
        }

        template, keys = split_template_from_trace(trace_data)

        assert "input_images" not in template
        assert keys["input_images"] == ["image1.jpg", "image2.jpg"]

    def test_extracts_variable_fields_to_keys(self):
        """Should extract fields with _info, _data suffixes to keys."""
        trace_data = {
            "prompt": "test",
            "community_info": '{"name": "PowerfulJRE"}',
            "host_data": "Joe Rogan",
            "show_context": "Podcast",
        }

        _template, keys = split_template_from_trace(trace_data)

        assert keys["community_info"] == '{"name": "PowerfulJRE"}'
        assert keys["host_data"] == "Joe Rogan"
        assert keys["show_context"] == "Podcast"

    def test_handles_backtick_variables_in_prompt(self):
        """Should detect backtick variables in prompt."""
        trace_data = {
            "prompt": "# Community\n```\n{community_info}\n```",
            "community_info": '{"name": "PowerfulJRE"}',
        }

        _template, keys = split_template_from_trace(trace_data)

        assert "community_info" in keys
        assert keys["community_info"] == '{"name": "PowerfulJRE"}'

    def test_puts_structural_fields_in_template(self):
        """Should put structural fields in template."""
        trace_data = {
            "prompt": "test",
            "temperature": 0.8,
            "aspect_ratio": "16:9",
            "tags": ["test"],
            "output_text": True,
        }

        template, _keys = split_template_from_trace(trace_data)

        assert template["temperature"] == 0.8
        assert template["aspect_ratio"] == "16:9"
        assert template["tags"] == ["test"]
        assert template["output_text"] is True

    def test_puts_long_strings_in_keys(self):
        """Should put long string values in keys."""
        trace_data = {
            "prompt": "test",
            "short_field": "short",
            "long_field": "x" * 100,  # Long string
        }

        _template, keys = split_template_from_trace(trace_data)

        # Short field could go either way, but long field should be in keys
        assert "long_field" in keys
        assert keys["long_field"] == "x" * 100

    def test_handles_output_images(self):
        """Should include output_images in template."""
        trace_data = {
            "prompt": "test",
            "output_images": ["s3://bucket/output.jpg"],
        }

        template, _keys = split_template_from_trace(trace_data)

        assert template["output_images"] == ["s3://bucket/output.jpg"]

    def test_handles_empty_trace(self):
        """Should handle empty trace data."""
        trace_data = {}

        template, keys = split_template_from_trace(trace_data)

        assert template == {}
        assert keys == {}


class TestConvertBacktickDataToVariables:
    """Tests for convert_backtick_data_to_variables."""

    def test_converts_single_backtick_section(self):
        """Should convert single backtick section to variable."""
        prompt = '# Community\n```\n{"name":"PowerfulJRE"}\n```'
        data_dict = {"community_info": '{"name":"PowerfulJRE"}'}

        template_prompt, variables = convert_backtick_data_to_variables(prompt, data_dict)

        assert "{community_info}" in template_prompt
        assert variables["community_info"] == '{"name":"PowerfulJRE"}'

    def test_converts_multiple_backtick_sections(self):
        """Should convert multiple backtick sections."""
        prompt = """# Community
```
{"name":"PowerfulJRE"}
```

# Host
```
{"name":"Joe Rogan"}
```
"""
        data_dict = {
            "community_info": '{"name":"PowerfulJRE"}',
            "host_info": '{"name":"Joe Rogan"}',
        }

        template_prompt, variables = convert_backtick_data_to_variables(prompt, data_dict)

        assert "{community_info}" in template_prompt
        assert "{host_info}" in template_prompt
        assert variables["community_info"] == '{"name":"PowerfulJRE"}'
        assert variables["host_info"] == '{"name":"Joe Rogan"}'

    def test_handles_whitespace_differences(self):
        """Should handle whitespace differences in comparison."""
        prompt = '```\n{"name": "PowerfulJRE"}\n```'
        data_dict = {"community_info": '{"name":"PowerfulJRE"}'}  # No spaces

        template_prompt, variables = convert_backtick_data_to_variables(prompt, data_dict)

        assert "{community_info}" in template_prompt
        assert variables["community_info"] == '{"name": "PowerfulJRE"}'

    def test_infers_variable_name_from_context(self):
        """Should infer variable name when not in data_dict."""
        prompt = "# Context: The community\n```\ndata\n```"
        data_dict = {}

        template_prompt, variables = convert_backtick_data_to_variables(prompt, data_dict)

        assert "{community_info}" in template_prompt
        assert variables["community_info"] == "data"

    def test_preserves_non_matching_backticks(self):
        """Should preserve backtick sections that don't match."""
        prompt = "```\ncode block\n```"
        data_dict = {"community_info": "different data"}

        template_prompt, variables = convert_backtick_data_to_variables(prompt, data_dict)

        # Should not convert since no match found
        assert "```" in template_prompt
        assert "{" not in template_prompt or variables == {}

    def test_handles_empty_prompt(self):
        """Should handle empty prompt."""
        prompt = ""
        data_dict = {"test": "value"}

        template_prompt, variables = convert_backtick_data_to_variables(prompt, data_dict)

        assert template_prompt == ""
        assert variables == {}

    def test_handles_prompt_without_backticks(self):
        """Should handle prompt without backtick sections."""
        prompt = "Just plain text"
        data_dict = {"test": "value"}

        template_prompt, variables = convert_backtick_data_to_variables(prompt, data_dict)

        assert template_prompt == "Just plain text"
        assert variables == {}
