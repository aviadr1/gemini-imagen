"""
Tests for safety settings CLI functionality.

Tests the --safety-setting flag and config defaults for safety settings.
"""

from unittest.mock import patch

import pytest
from click.testing import CliRunner
from google.genai import types

from gemini_imagen.cli.commands import config_cmd
from gemini_imagen.cli.commands.config_cmd import config
from gemini_imagen.cli.commands.generate import parse_safety_setting
from gemini_imagen.constants import (
    CONFIG_KEY_SAFETY_SETTINGS,
    HarmBlockThreshold,
    HarmCategory,
)


class TestParseSafetySetting:
    """Test the parse_safety_setting helper function."""

    def test_parse_preset_relaxed(self):
        """Test parsing preset:relaxed returns all categories with BLOCK_ONLY_HIGH."""
        result = parse_safety_setting("preset:relaxed")

        assert len(result) == 4
        assert all(isinstance(s, types.SafetySetting) for s in result)
        assert all(s.threshold == HarmBlockThreshold.BLOCK_ONLY_HIGH for s in result)

        categories = {s.category for s in result}
        expected_categories = {
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            HarmCategory.HARM_CATEGORY_HARASSMENT,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        }
        assert categories == expected_categories

    def test_parse_preset_strict(self):
        """Test parsing preset:strict returns all categories with BLOCK_LOW_AND_ABOVE."""
        result = parse_safety_setting("preset:strict")

        assert len(result) == 4
        assert all(s.threshold == HarmBlockThreshold.BLOCK_LOW_AND_ABOVE for s in result)

    def test_parse_preset_default(self):
        """Test parsing preset:default returns BLOCK_MEDIUM_AND_ABOVE."""
        result = parse_safety_setting("preset:default")

        assert len(result) == 4
        assert all(s.threshold == HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE for s in result)

    def test_parse_preset_none(self):
        """Test parsing preset:none returns BLOCK_NONE."""
        result = parse_safety_setting("preset:none")

        assert len(result) == 4
        assert all(s.threshold == HarmBlockThreshold.BLOCK_NONE for s in result)

    def test_parse_specific_category_with_prefix(self):
        """Test parsing HARM_CATEGORY_SEXUALLY_EXPLICIT:BLOCK_ONLY_HIGH."""
        result = parse_safety_setting("HARM_CATEGORY_SEXUALLY_EXPLICIT:BLOCK_ONLY_HIGH")

        assert len(result) == 1
        assert result[0].category == HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT
        assert result[0].threshold == HarmBlockThreshold.BLOCK_ONLY_HIGH

    def test_parse_specific_category_without_prefix(self):
        """Test parsing SEXUALLY_EXPLICIT:BLOCK_ONLY_HIGH (without HARM_CATEGORY_ prefix)."""
        result = parse_safety_setting("SEXUALLY_EXPLICIT:BLOCK_ONLY_HIGH")

        assert len(result) == 1
        assert result[0].category == HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT
        assert result[0].threshold == HarmBlockThreshold.BLOCK_ONLY_HIGH

    def test_parse_threshold_without_block_prefix(self):
        """Test parsing with threshold name without BLOCK_ prefix."""
        result = parse_safety_setting("SEXUALLY_EXPLICIT:ONLY_HIGH")

        assert len(result) == 1
        assert result[0].threshold == HarmBlockThreshold.BLOCK_ONLY_HIGH

    def test_parse_invalid_format_no_colon(self):
        """Test that missing colon raises ValueError."""
        with pytest.raises(ValueError, match="Invalid safety setting format"):
            parse_safety_setting("relaxed")

    def test_parse_invalid_threshold(self):
        """Test that invalid threshold raises ValueError."""
        with pytest.raises(ValueError, match="Invalid threshold"):
            parse_safety_setting("preset:invalid_threshold")

    def test_parse_invalid_category(self):
        """Test that invalid category raises ValueError."""
        with pytest.raises(ValueError, match="Invalid category"):
            parse_safety_setting("INVALID_CATEGORY:BLOCK_ONLY_HIGH")


class TestConfigSetSafetySettings:
    """Test 'imagen config set safety_settings' command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create temporary config directory."""
        config_dir = tmp_path / ".config" / "imagen"
        config_dir.mkdir(parents=True)
        return config_dir

    def test_set_safety_settings_relaxed(self, runner, temp_config_dir):
        """Test setting safety_settings to relaxed preset."""
        with patch.object(config_cmd, "get_config") as mock_get_config:
            # Import Config here to use the temp directory
            from gemini_imagen.cli.config import Config

            cfg = Config(config_dir=temp_config_dir)
            mock_get_config.return_value = cfg

            result = runner.invoke(config, ["set", CONFIG_KEY_SAFETY_SETTINGS, "relaxed"])

            assert result.exit_code == 0
            assert "Set safety_settings = relaxed" in result.output

            # Verify saved config
            saved_value = cfg.get(CONFIG_KEY_SAFETY_SETTINGS)
            assert saved_value is not None
            assert isinstance(saved_value, list)
            assert len(saved_value) == 4

            # Check that all values are strings (YAML-serializable)
            for item in saved_value:
                assert isinstance(item["category"], str)
                assert isinstance(item["threshold"], str)
                assert "HARM_CATEGORY_" in item["category"]
                assert "BLOCK_ONLY_HIGH" in item["threshold"]

    def test_set_safety_settings_strict(self, runner, temp_config_dir):
        """Test setting safety_settings to strict preset."""
        with patch.object(config_cmd, "get_config") as mock_get_config:
            from gemini_imagen.cli.config import Config

            cfg = Config(config_dir=temp_config_dir)
            mock_get_config.return_value = cfg

            result = runner.invoke(config, ["set", CONFIG_KEY_SAFETY_SETTINGS, "strict"])

            assert result.exit_code == 0

            saved_value = cfg.get(CONFIG_KEY_SAFETY_SETTINGS)
            for item in saved_value:
                assert "BLOCK_LOW_AND_ABOVE" in item["threshold"]

    def test_set_safety_settings_invalid_preset(self, runner, temp_config_dir):
        """Test that invalid preset fails with helpful error."""
        with patch.object(config_cmd, "get_config") as mock_get_config:
            from gemini_imagen.cli.config import Config

            cfg = Config(config_dir=temp_config_dir)
            mock_get_config.return_value = cfg

            result = runner.invoke(config, ["set", CONFIG_KEY_SAFETY_SETTINGS, "invalid"])

            assert result.exit_code == 1
            assert "Invalid safety preset" in result.output
            assert "strict" in result.output  # Should show valid values


class TestConfigSetTemperature:
    """Test 'imagen config set temperature' command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create temporary config directory."""
        config_dir = tmp_path / ".config" / "imagen"
        config_dir.mkdir(parents=True)
        return config_dir

    def test_set_temperature_valid(self, runner, temp_config_dir):
        """Test setting valid temperature value."""
        with patch.object(config_cmd, "get_config") as mock_get_config:
            from gemini_imagen.cli.config import Config

            cfg = Config(config_dir=temp_config_dir)
            mock_get_config.return_value = cfg

            result = runner.invoke(config, ["set", "temperature", "0.8"])

            assert result.exit_code == 0
            assert "Set temperature = 0.8" in result.output

            # Verify saved as float
            saved_value = cfg.get("temperature")
            assert saved_value == 0.8
            assert isinstance(saved_value, float)

    def test_set_temperature_boundary_values(self, runner, temp_config_dir):
        """Test temperature boundary values (0.0 and 1.0)."""
        with patch.object(config_cmd, "get_config") as mock_get_config:
            from gemini_imagen.cli.config import Config

            cfg = Config(config_dir=temp_config_dir)
            mock_get_config.return_value = cfg

            # Test 0.0
            result = runner.invoke(config, ["set", "temperature", "0.0"])
            assert result.exit_code == 0
            assert cfg.get("temperature") == 0.0

            # Test 1.0
            result = runner.invoke(config, ["set", "temperature", "1.0"])
            assert result.exit_code == 0
            assert cfg.get("temperature") == 1.0

    def test_set_temperature_out_of_range_low(self, runner, temp_config_dir):
        """Test that temperature < 0.0 fails."""
        with patch.object(config_cmd, "get_config") as mock_get_config:
            from gemini_imagen.cli.config import Config

            cfg = Config(config_dir=temp_config_dir)
            mock_get_config.return_value = cfg

            # Use -- to separate args so negative numbers aren't interpreted as flags
            result = runner.invoke(config, ["set", "temperature", "--", "-0.1"])

            assert result.exit_code != 0  # Should fail, either 1 or 2
            assert "must be between 0.0 and 1.0" in result.output

    def test_set_temperature_out_of_range_high(self, runner, temp_config_dir):
        """Test that temperature > 1.0 fails."""
        with patch.object(config_cmd, "get_config") as mock_get_config:
            from gemini_imagen.cli.config import Config

            cfg = Config(config_dir=temp_config_dir)
            mock_get_config.return_value = cfg

            result = runner.invoke(config, ["set", "temperature", "1.5"])

            assert result.exit_code == 1
            assert "must be between 0.0 and 1.0" in result.output

    def test_set_temperature_invalid_format(self, runner, temp_config_dir):
        """Test that non-numeric temperature fails."""
        with patch.object(config_cmd, "get_config") as mock_get_config:
            from gemini_imagen.cli.config import Config

            cfg = Config(config_dir=temp_config_dir)
            mock_get_config.return_value = cfg

            result = runner.invoke(config, ["set", "temperature", "not_a_number"])

            assert result.exit_code == 1
            assert "Invalid temperature value" in result.output


class TestConfigSetAspectRatio:
    """Test 'imagen config set aspect_ratio' command."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create temporary config directory."""
        config_dir = tmp_path / ".config" / "imagen"
        config_dir.mkdir(parents=True)
        return config_dir

    def test_set_aspect_ratio(self, runner, temp_config_dir):
        """Test setting aspect_ratio."""
        with patch.object(config_cmd, "get_config") as mock_get_config:
            from gemini_imagen.cli.config import Config

            cfg = Config(config_dir=temp_config_dir)
            mock_get_config.return_value = cfg

            result = runner.invoke(config, ["set", "aspect_ratio", "16:9"])

            assert result.exit_code == 0
            assert "Set aspect_ratio = 16:9" in result.output

            # Verify saved as string
            saved_value = cfg.get("aspect_ratio")
            assert saved_value == "16:9"
            assert isinstance(saved_value, str)


class TestConfigGetMethods:
    """Test Config class getter methods for new parameters."""

    def test_get_temperature(self, tmp_path):
        """Test get_temperature() method."""
        from gemini_imagen.cli.config import Config

        config_dir = tmp_path / ".config" / "imagen"
        config_dir.mkdir(parents=True)
        cfg = Config(config_dir=config_dir)

        # Initially None
        assert cfg.get_temperature() is None

        # After setting
        cfg.set("temperature", 0.7)
        assert cfg.get_temperature() == 0.7

    def test_get_aspect_ratio(self, tmp_path):
        """Test get_aspect_ratio() method."""
        from gemini_imagen.cli.config import Config

        config_dir = tmp_path / ".config" / "imagen"
        config_dir.mkdir(parents=True)
        cfg = Config(config_dir=config_dir)

        # Initially None
        assert cfg.get_aspect_ratio() is None

        # After setting
        cfg.set("aspect_ratio", "16:9")
        assert cfg.get_aspect_ratio() == "16:9"

    def test_get_safety_settings(self, tmp_path):
        """Test get_safety_settings() method."""
        from gemini_imagen.cli.config import Config

        config_dir = tmp_path / ".config" / "imagen"
        config_dir.mkdir(parents=True)
        cfg = Config(config_dir=config_dir)

        # Initially None
        assert cfg.get_safety_settings() is None

        # After setting
        safety_data = [
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"}
        ]
        cfg.set("safety_settings", safety_data)
        assert cfg.get_safety_settings() == safety_data


class TestSafetySettingsIntegration:
    """Test safety settings integration in generate command."""

    def test_config_safety_settings_applied_to_generate(self, tmp_path):
        """Test that config safety_settings are correctly applied when generating."""
        from gemini_imagen.cli.config import Config

        # This tests the bug where str(HarmCategory.X) creates "HarmCategory.X"
        # and we need to strip the prefix when reading back
        config_dir = tmp_path / ".config" / "imagen"
        config_dir.mkdir(parents=True)
        cfg = Config(config_dir=config_dir)

        # Set safety settings like the CLI command does (with full enum string representation)
        safety_data = [
            {
                "category": "HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "HarmBlockThreshold.BLOCK_ONLY_HIGH",
            }
        ]
        cfg.set("safety_settings", safety_data)

        # Verify we can read it back and strip the prefix correctly
        config_safety = cfg.get_safety_settings()
        assert config_safety is not None

        # Simulate what generate command does
        from gemini_imagen.constants import HarmBlockThreshold, HarmCategory, SafetySetting

        settings = [
            SafetySetting(
                category=getattr(
                    HarmCategory,
                    s["category"].replace("HarmCategory.", ""),
                ),
                threshold=getattr(
                    HarmBlockThreshold,
                    s["threshold"].replace("HarmBlockThreshold.", ""),
                ),
            )
            for s in config_safety
        ]

        # Should create valid SafetySetting objects
        assert len(settings) == 1
        assert settings[0].category == HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT
        assert settings[0].threshold == HarmBlockThreshold.BLOCK_ONLY_HIGH
