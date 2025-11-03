"""
Tests for path expansion and validation in CLI utilities.

Tests various path scenarios including tilde expansion, relative paths,
absolute paths, symlinks, S3 URIs, and HTTP URLs.
"""

from pathlib import Path

import pytest

from gemini_imagen.cli.utils import validate_input_path, validate_output_path


class TestInputPathValidation:
    """Test validate_input_path with various path formats."""

    def test_absolute_path(self, tmp_path: Path) -> None:
        """Test validation with absolute path."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        result = validate_input_path(str(test_file))
        assert result == str(test_file)

    def test_relative_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test validation with relative path - should resolve to absolute."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        # Change to tmp_path directory
        monkeypatch.chdir(tmp_path)

        result = validate_input_path("test.txt")
        assert result == str(test_file)
        assert Path(result).is_absolute()

    def test_tilde_expansion(self, tmp_path: Path) -> None:
        """Test validation with ~ (home directory) expansion."""
        # Create a test file in actual home directory
        home = Path.home()
        test_file = home / ".test_imagen_tilde_input.txt"
        test_file.write_text("test")

        try:
            result = validate_input_path("~/.test_imagen_tilde_input.txt")
            assert result == str(test_file)
            assert Path(result).is_absolute()
        finally:
            # Cleanup
            test_file.unlink(missing_ok=True)

    def test_dot_relative_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test validation with ./file notation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        monkeypatch.chdir(tmp_path)

        result = validate_input_path("./test.txt")
        assert result == str(test_file)
        assert Path(result).is_absolute()

    def test_parent_directory_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test validation with ../file notation."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        monkeypatch.chdir(subdir)

        result = validate_input_path("../test.txt")
        assert result == str(test_file)

    def test_symlink_resolution(self, tmp_path: Path) -> None:
        """Test that symlinks are resolved to actual file."""
        test_file = tmp_path / "original.txt"
        test_file.write_text("test")

        symlink = tmp_path / "link.txt"
        symlink.symlink_to(test_file)

        result = validate_input_path(str(symlink))
        # Should resolve to the actual file
        assert result == str(test_file)

    def test_s3_uri_passthrough(self) -> None:
        """Test that S3 URIs are passed through without validation."""
        s3_uri = "s3://bucket/path/to/file.png"
        result = validate_input_path(s3_uri)
        assert result == s3_uri

    def test_http_url_passthrough(self) -> None:
        """Test that HTTP URLs are passed through without validation."""
        http_url = "https://example.com/image.png"
        result = validate_input_path(http_url)
        assert result == http_url

    def test_https_url_passthrough(self) -> None:
        """Test that HTTPS URLs are passed through without validation."""
        https_url = "https://example.com/image.png"
        result = validate_input_path(https_url)
        assert result == https_url

    def test_nonexistent_file_error(self, tmp_path: Path) -> None:
        """Test that nonexistent files raise error."""
        nonexistent = tmp_path / "nonexistent.txt"

        with pytest.raises(Exception) as exc_info:
            validate_input_path(str(nonexistent))

        assert "does not exist" in str(exc_info.value)

    def test_directory_not_file_error(self, tmp_path: Path) -> None:
        """Test that directories are rejected (must be files)."""
        with pytest.raises(Exception) as exc_info:
            validate_input_path(str(tmp_path))

        assert "not a file" in str(exc_info.value)

    def test_tilde_with_nonexistent_file(self) -> None:
        """Test that ~ expansion works even when file doesn't exist."""
        with pytest.raises(Exception) as exc_info:
            validate_input_path("~/.test_imagen_nonexistent_file_12345.txt")

        assert "does not exist" in str(exc_info.value)


class TestOutputPathValidation:
    """Test validate_output_path with various path formats."""

    def test_absolute_path(self, tmp_path: Path) -> None:
        """Test validation with absolute path."""
        output_file = tmp_path / "output.png"

        result = validate_output_path(str(output_file))
        assert result == str(output_file)

    def test_relative_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test validation with relative path - should resolve to absolute."""
        monkeypatch.chdir(tmp_path)

        result = validate_output_path("output.png")
        assert result == str(tmp_path / "output.png")
        assert Path(result).is_absolute()

    def test_tilde_expansion(self) -> None:
        """Test validation with ~ (home directory) expansion."""
        home = Path.home()
        result = validate_output_path("~/.test_imagen_output.png")
        assert result == str(home / ".test_imagen_output.png")
        assert Path(result).is_absolute()

    def test_s3_uri_passthrough(self) -> None:
        """Test that S3 URIs are passed through without validation."""
        s3_uri = "s3://bucket/path/to/output.png"
        result = validate_output_path(s3_uri)
        assert result == s3_uri

    def test_s3_uri_rejected_when_not_allowed(self) -> None:
        """Test that S3 URIs are rejected when allow_s3=False."""
        s3_uri = "s3://bucket/path/to/output.png"

        with pytest.raises(Exception) as exc_info:
            validate_output_path(s3_uri, allow_s3=False)

        assert "not supported" in str(exc_info.value).lower()

    def test_parent_directory_not_exists(self, tmp_path: Path) -> None:
        """Test that error is raised if parent directory doesn't exist."""
        output_file = tmp_path / "nonexistent" / "subdir" / "output.png"

        with pytest.raises(Exception) as exc_info:
            validate_output_path(str(output_file))

        assert "does not exist" in str(exc_info.value)

    def test_nested_path_with_existing_parents(self, tmp_path: Path) -> None:
        """Test that nested paths work when parent directories exist."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        output_file = subdir / "output.png"

        result = validate_output_path(str(output_file))
        assert result == str(output_file)

    def test_current_directory_output(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test output to current directory."""
        monkeypatch.chdir(tmp_path)

        result = validate_output_path("./output.png")
        assert result == str(tmp_path / "output.png")

    def test_tilde_with_subdirectory(self, tmp_path: Path) -> None:
        """Test ~ expansion with subdirectory path."""
        # Create a subdirectory in actual home
        home = Path.home()
        subdir = home / ".test_imagen_subdir"
        subdir.mkdir(exist_ok=True)

        try:
            result = validate_output_path("~/.test_imagen_subdir/output.png")
            assert result == str(home / ".test_imagen_subdir" / "output.png")
            assert Path(result).is_absolute()
        finally:
            # Cleanup
            subdir.rmdir()


class TestPathNormalization:
    """Test that paths are properly normalized."""

    def test_removes_redundant_separators(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that multiple slashes are normalized."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        monkeypatch.chdir(tmp_path)

        # Path with redundant separators
        result = validate_input_path("./test.txt")
        assert "//" not in result

    def test_normalizes_dot_segments(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that . and .. are properly resolved."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        monkeypatch.chdir(tmp_path)

        result = validate_input_path("./subdir/../test.txt")
        assert result == str(test_file)
        assert "." not in Path(result).parts

    def test_consistent_path_format(self, tmp_path: Path) -> None:
        """Test that same file always returns same normalized path."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test")

        # Different ways to reference the same file
        result1 = validate_input_path(str(test_file))
        result2 = validate_input_path(str(test_file.absolute()))

        assert result1 == result2
