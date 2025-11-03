"""
Tests for job merge utility.
"""

from gemini_imagen.cli.job_merge import (
    deep_merge,
    merge_template_keys_overrides,
    split_job_and_variables,
)


class TestDeepMerge:
    """Test deep_merge function."""

    def test_merge_non_overlapping(self):
        """Test merging dictionaries with no overlapping keys."""
        base = {"a": 1}
        overlay = {"b": 2}
        result = deep_merge(base, overlay)
        assert result == {"a": 1, "b": 2}

    def test_merge_overlapping_simple(self):
        """Test merging dictionaries with overlapping simple values."""
        base = {"a": 1}
        overlay = {"a": 2}
        result = deep_merge(base, overlay)
        assert result == {"a": 2}

    def test_merge_nested_dicts(self):
        """Test deep merging of nested dictionaries."""
        base = {"a": {"b": 1, "c": 2}}
        overlay = {"a": {"c": 3, "d": 4}}
        result = deep_merge(base, overlay)
        assert result == {"a": {"b": 1, "c": 3, "d": 4}}

    def test_merge_multiple_overlays(self):
        """Test merging multiple overlay dictionaries."""
        base = {"a": 1}
        overlay1 = {"b": 2}
        overlay2 = {"c": 3}
        result = deep_merge(base, overlay1, overlay2)
        assert result == {"a": 1, "b": 2, "c": 3}

    def test_merge_multiple_overlapping(self):
        """Test multiple overlays with same key - last wins."""
        base = {"a": 1}
        overlay1 = {"a": 2}
        overlay2 = {"a": 3}
        result = deep_merge(base, overlay1, overlay2)
        assert result == {"a": 3}

    def test_merge_preserves_base(self):
        """Test that original base dict is not mutated."""
        base = {"a": 1}
        overlay = {"a": 2}
        result = deep_merge(base, overlay)
        assert base == {"a": 1}  # Unchanged
        assert result == {"a": 2}

    def test_merge_lists_overwrite(self):
        """Test that lists are overwritten, not merged."""
        base = {"tags": ["a", "b"]}
        overlay = {"tags": ["c", "d"]}
        result = deep_merge(base, overlay)
        assert result == {"tags": ["c", "d"]}

    def test_merge_dict_with_list(self):
        """Test merging dict value with list value - overlay wins."""
        base = {"field": {"nested": "value"}}
        overlay = {"field": ["list", "values"]}
        result = deep_merge(base, overlay)
        assert result == {"field": ["list", "values"]}

    def test_merge_deeply_nested(self):
        """Test merging deeply nested dictionaries."""
        base = {"a": {"b": {"c": 1}}}
        overlay = {"a": {"b": {"d": 2}}}
        result = deep_merge(base, overlay)
        assert result == {"a": {"b": {"c": 1, "d": 2}}}


class TestSplitJobAndVariables:
    """Test split_job_and_variables function."""

    def test_split_only_library_params(self):
        """Test splitting with only library parameters."""
        merged = {"prompt": "Hello", "temperature": 0.8}
        lib_params, variables = split_job_and_variables(merged)
        assert lib_params == {"prompt": "Hello", "temperature": 0.8}
        assert variables == {}

    def test_split_only_variables(self):
        """Test splitting with only variables."""
        merged = {"name": "Alice", "age": 30}
        lib_params, variables = split_job_and_variables(merged)
        assert lib_params == {}
        assert variables == {"name": "Alice", "age": 30}

    def test_split_mixed(self):
        """Test splitting with both library params and variables."""
        merged = {
            "prompt": "Hello {name}",
            "temperature": 0.8,
            "name": "Alice",
            "context": "Some context",
        }
        lib_params, variables = split_job_and_variables(merged)
        assert lib_params == {"prompt": "Hello {name}", "temperature": 0.8}
        assert variables == {"name": "Alice", "context": "Some context"}

    def test_split_all_library_params(self):
        """Test that all library params are recognized."""
        merged = {
            "prompt": "test",
            "system_prompt": "test",
            "input_images": [],
            "output_images": [],
            "temperature": 0.5,
            "aspect_ratio": "16:9",
            "safety_settings": [],
            "output_text": True,
            "run_name": "test",
            "metadata": {},
            "tags": [],
        }
        lib_params, variables = split_job_and_variables(merged)
        assert lib_params == merged
        assert variables == {}

    def test_split_empty(self):
        """Test splitting empty dictionary."""
        lib_params, variables = split_job_and_variables({})
        assert lib_params == {}
        assert variables == {}


class TestMergeTemplateKeysOverrides:
    """Test merge_template_keys_overrides function."""

    def test_template_only(self):
        """Test with only template."""
        template = {"prompt": "Hello", "temperature": 0.5}
        result = merge_template_keys_overrides(template=template)
        assert result == {"prompt": "Hello", "temperature": 0.5}

    def test_template_and_single_keys(self):
        """Test with template and single keys file."""
        template = {"prompt": "Hello", "temperature": 0.5}
        keys = [{"prompt": "Hi there", "tags": ["test"]}]
        result = merge_template_keys_overrides(template=template, keys=keys)
        assert result == {"prompt": "Hi there", "temperature": 0.5, "tags": ["test"]}

    def test_template_and_multiple_keys(self):
        """Test with template and multiple keys files."""
        template = {"prompt": "Hello", "temperature": 0.5}
        keys = [
            {"prompt": "Hi there", "tags": ["test"]},
            {"prompt": "Greetings", "aspect_ratio": "16:9"},
        ]
        result = merge_template_keys_overrides(template=template, keys=keys)
        # Later keys file wins
        assert result == {
            "prompt": "Greetings",
            "temperature": 0.5,
            "tags": ["test"],
            "aspect_ratio": "16:9",
        }

    def test_template_keys_and_cli_overrides(self):
        """Test with template, keys, and CLI overrides."""
        template = {"prompt": "Hello", "temperature": 0.5}
        keys = [{"prompt": "Hi there", "tags": ["test"]}]
        cli_overrides = {"temperature": 0.9, "aspect_ratio": "1:1"}
        result = merge_template_keys_overrides(
            template=template, keys=keys, cli_overrides=cli_overrides
        )
        # CLI overrides have highest precedence
        assert result == {
            "prompt": "Hi there",
            "temperature": 0.9,
            "tags": ["test"],
            "aspect_ratio": "1:1",
        }

    def test_cli_overrides_only(self):
        """Test with only CLI overrides."""
        cli_overrides = {"prompt": "Hello", "temperature": 0.8}
        result = merge_template_keys_overrides(cli_overrides=cli_overrides)
        assert result == {"prompt": "Hello", "temperature": 0.8}

    def test_no_inputs(self):
        """Test with no inputs - returns empty dict."""
        result = merge_template_keys_overrides()
        assert result == {}

    def test_keys_order_matters(self):
        """Test that keys are applied in order."""
        keys = [
            {"prompt": "First"},
            {"prompt": "Second"},
            {"prompt": "Third"},
        ]
        result = merge_template_keys_overrides(keys=keys)
        assert result == {"prompt": "Third"}

    def test_deep_merge_in_template_keys(self):
        """Test deep merging works across template and keys."""
        template = {
            "metadata": {"author": "Alice", "version": 1},
        }
        keys = [
            {"metadata": {"version": 2, "tags": ["test"]}},
        ]
        result = merge_template_keys_overrides(template=template, keys=keys)
        assert result == {"metadata": {"author": "Alice", "version": 2, "tags": ["test"]}}

    def test_real_world_scenario(self):
        """Test a real-world scenario with template, keys, and overrides."""
        # Template with system prompt and placeholders
        template = {
            "system_prompt": "You are an expert",
            "prompt": "# Community\n{community_info}\n\n# Host\n{host_info}",
            "output_images": ["s3://bucket/{channel_id}/thumb.jpg"],
            "tags": ["thumbnail"],
        }

        # Keys with episode-specific data
        keys = [
            {
                "community_info": '{"name": "PowerfulJRE"}',
                "host_info": '{"name": "Gigoz"}',
                "channel_id": "drumming2-abc123",
                "input_images": [["community", "https://example.com/img.jpg"]],
            }
        ]

        # CLI override for temperature
        cli_overrides = {"temperature": 0.8}

        result = merge_template_keys_overrides(
            template=template, keys=keys, cli_overrides=cli_overrides
        )

        # Check result
        assert result["system_prompt"] == "You are an expert"
        assert result["prompt"] == "# Community\n{community_info}\n\n# Host\n{host_info}"
        assert result["community_info"] == '{"name": "PowerfulJRE"}'
        assert result["host_info"] == '{"name": "Gigoz"}'
        assert result["channel_id"] == "drumming2-abc123"
        assert result["temperature"] == 0.8
        assert result["tags"] == ["thumbnail"]
        assert result["input_images"] == [["community", "https://example.com/img.jpg"]]

    def test_preserves_originals(self):
        """Test that original dicts are not mutated."""
        template = {"a": 1}
        keys = [{"b": 2}]
        cli_overrides = {"c": 3}

        result = merge_template_keys_overrides(
            template=template, keys=keys, cli_overrides=cli_overrides
        )

        # Check originals unchanged
        assert template == {"a": 1}
        assert keys == [{"b": 2}]
        assert cli_overrides == {"c": 3}

        # Check result is correct
        assert result == {"a": 1, "b": 2, "c": 3}
