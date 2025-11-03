"""
Tests for template storage and management.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from gemini_imagen.cli.templates import (
    delete_template,
    get_template_path,
    get_templates_dir,
    list_templates,
    load_template,
    save_template,
    template_exists,
)


@pytest.fixture
def temp_templates_dir(tmp_path):
    """Create a temporary templates directory."""
    templates_dir = tmp_path / "templates"
    templates_dir.mkdir()
    return templates_dir


@pytest.fixture
def mock_templates_dir(temp_templates_dir):
    """Mock get_templates_dir to use temporary directory."""
    with patch("gemini_imagen.cli.templates.get_templates_dir", return_value=temp_templates_dir):
        yield temp_templates_dir


class TestGetTemplatesDir:
    """Test get_templates_dir function."""

    def test_returns_path(self):
        """Test that function returns a Path."""
        result = get_templates_dir()
        assert isinstance(result, Path)
        assert result.name == "templates"


class TestSaveTemplate:
    """Test save_template function."""

    def test_save_simple_template(self, mock_templates_dir):
        """Test saving a simple template."""
        template = {"prompt": "Hello", "temperature": 0.8}
        path = save_template("test", template)

        assert path.exists()
        assert path.name == "test.json"

        # Verify contents
        with path.open() as f:
            saved = json.load(f)
        assert saved == template

    def test_save_creates_directory(self, tmp_path):
        """Test that save creates templates directory if it doesn't exist."""
        templates_dir = tmp_path / "new_templates"

        with patch("gemini_imagen.cli.templates.get_templates_dir", return_value=templates_dir):
            template = {"prompt": "Test"}
            save_template("test", template)

            assert templates_dir.exists()
            assert (templates_dir / "test.json").exists()

    def test_save_invalid_name_with_slash(self, mock_templates_dir):
        """Test that saving with slash in name raises error."""
        with pytest.raises(ValueError, match="Invalid template name"):
            save_template("invalid/name", {})

    def test_save_invalid_name_with_backslash(self, mock_templates_dir):
        """Test that saving with backslash in name raises error."""
        with pytest.raises(ValueError, match="Invalid template name"):
            save_template("invalid\\name", {})

    def test_save_empty_name(self, mock_templates_dir):
        """Test that saving with empty name raises error."""
        with pytest.raises(ValueError, match="Invalid template name"):
            save_template("", {})

    def test_save_overwrites_existing(self, mock_templates_dir):
        """Test that saving overwrites existing template."""
        save_template("test", {"version": 1})
        save_template("test", {"version": 2})

        template = load_template("test")
        assert template == {"version": 2}


class TestLoadTemplate:
    """Test load_template function."""

    def test_load_existing_template(self, mock_templates_dir):
        """Test loading an existing template."""
        template = {"prompt": "Hello", "temperature": 0.8}
        save_template("test", template)

        loaded = load_template("test")
        assert loaded == template

    def test_load_nonexistent_template(self, mock_templates_dir):
        """Test loading non-existent template raises error."""
        with pytest.raises(FileNotFoundError, match="Template 'nonexistent' not found"):
            load_template("nonexistent")

    def test_load_invalid_name(self, mock_templates_dir):
        """Test loading with invalid name raises error."""
        with pytest.raises(ValueError, match="Invalid template name"):
            load_template("invalid/name")


class TestListTemplates:
    """Test list_templates function."""

    def test_list_empty(self, mock_templates_dir):
        """Test listing when no templates exist."""
        templates = list_templates()
        assert templates == []

    def test_list_multiple_templates(self, mock_templates_dir):
        """Test listing multiple templates."""
        save_template("template1", {"a": 1})
        save_template("template2", {"b": 2})
        save_template("template3", {"c": 3})

        templates = list_templates()
        assert templates == ["template1", "template2", "template3"]

    def test_list_ignores_non_json(self, mock_templates_dir):
        """Test that list ignores non-JSON files."""
        save_template("template1", {"a": 1})

        # Create a non-JSON file
        (mock_templates_dir / "readme.txt").write_text("test")

        templates = list_templates()
        assert templates == ["template1"]

    def test_list_nonexistent_directory(self, tmp_path):
        """Test listing when templates directory doesn't exist."""
        templates_dir = tmp_path / "nonexistent"

        with patch("gemini_imagen.cli.templates.get_templates_dir", return_value=templates_dir):
            templates = list_templates()
            assert templates == []


class TestDeleteTemplate:
    """Test delete_template function."""

    def test_delete_existing_template(self, mock_templates_dir):
        """Test deleting an existing template."""
        save_template("test", {"a": 1})
        assert template_exists("test")

        result = delete_template("test")
        assert result is True
        assert not template_exists("test")

    def test_delete_nonexistent_template(self, mock_templates_dir):
        """Test deleting non-existent template returns False."""
        result = delete_template("nonexistent")
        assert result is False

    def test_delete_invalid_name(self, mock_templates_dir):
        """Test deleting with invalid name raises error."""
        with pytest.raises(ValueError, match="Invalid template name"):
            delete_template("invalid/name")


class TestTemplateExists:
    """Test template_exists function."""

    def test_exists_true(self, mock_templates_dir):
        """Test returns True for existing template."""
        save_template("test", {"a": 1})
        assert template_exists("test") is True

    def test_exists_false(self, mock_templates_dir):
        """Test returns False for non-existent template."""
        assert template_exists("nonexistent") is False

    def test_exists_invalid_name(self, mock_templates_dir):
        """Test returns False for invalid name."""
        assert template_exists("invalid/name") is False
        assert template_exists("") is False


class TestGetTemplatePath:
    """Test get_template_path function."""

    def test_returns_path(self, mock_templates_dir):
        """Test returns correct path."""
        path = get_template_path("test")
        assert path == mock_templates_dir / "test.json"

    def test_invalid_name(self, mock_templates_dir):
        """Test raises error for invalid name."""
        with pytest.raises(ValueError, match="Invalid template name"):
            get_template_path("invalid/name")


class TestIntegration:
    """Integration tests for template operations."""

    def test_full_lifecycle(self, mock_templates_dir):
        """Test full template lifecycle."""
        # Save
        template = {
            "prompt": "Hello {name}",
            "system_prompt": "You are helpful",
            "temperature": 0.8,
        }
        save_template("test-template", template)

        # List
        templates = list_templates()
        assert "test-template" in templates

        # Exists
        assert template_exists("test-template")

        # Load
        loaded = load_template("test-template")
        assert loaded == template

        # Delete
        assert delete_template("test-template")
        assert not template_exists("test-template")
        assert "test-template" not in list_templates()
