"""
Tests for the bump_version script.
"""

import sys
from pathlib import Path

import pytest

# Import the script functions
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import bump_version


class TestGetCurrentVersion:
    """Test get_current_version function."""

    def test_extracts_version(self, tmp_path: Path) -> None:
        """Test extracting version from pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "1.2.3"\n')

        version = bump_version.get_current_version(pyproject)
        assert version == "1.2.3"

    def test_version_not_found(self, tmp_path: Path) -> None:
        """Test error when version not found."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "test"\n')

        with pytest.raises(ValueError, match="Could not find version"):
            bump_version.get_current_version(pyproject)


class TestBumpVersion:
    """Test bump_version function."""

    def test_bump_patch(self) -> None:
        """Test bumping patch version."""
        assert bump_version.bump_version("1.2.3", "patch") == "1.2.4"
        assert bump_version.bump_version("0.5.0", "patch") == "0.5.1"

    def test_bump_minor(self) -> None:
        """Test bumping minor version."""
        assert bump_version.bump_version("1.2.3", "minor") == "1.3.0"
        assert bump_version.bump_version("0.5.9", "minor") == "0.6.0"

    def test_bump_major(self) -> None:
        """Test bumping major version."""
        assert bump_version.bump_version("1.2.3", "major") == "2.0.0"
        assert bump_version.bump_version("0.5.9", "major") == "1.0.0"

    def test_set_specific_version(self) -> None:
        """Test setting a specific version."""
        assert bump_version.bump_version("1.2.3", "2.0.0") == "2.0.0"
        assert bump_version.bump_version("0.5.0", "1.0.0") == "1.0.0"

    def test_invalid_current_version(self) -> None:
        """Test error with invalid current version format."""
        with pytest.raises(ValueError, match="Invalid version format"):
            bump_version.bump_version("1.2", "patch")

    def test_invalid_bump_type(self) -> None:
        """Test error with invalid bump type."""
        with pytest.raises(ValueError, match="Invalid version or bump type"):
            bump_version.bump_version("1.2.3", "invalid")

        with pytest.raises(ValueError, match="Invalid version or bump type"):
            bump_version.bump_version("1.2.3", "1.2")  # Not enough parts


class TestUpdateVersionInPyproject:
    """Test update_version_in_pyproject function."""

    def test_updates_version(self, tmp_path: Path) -> None:
        """Test updating version in pyproject.toml."""
        pyproject = tmp_path / "pyproject.toml"
        content = '[project]\nname = "test"\nversion = "1.2.3"\n'
        pyproject.write_text(content)

        bump_version.update_version_in_pyproject(pyproject, "2.0.0")

        updated = pyproject.read_text()
        assert 'version = "2.0.0"' in updated
        assert 'version = "1.2.3"' not in updated

    def test_only_updates_first_occurrence(self, tmp_path: Path) -> None:
        """Test that only the first version is updated."""
        pyproject = tmp_path / "pyproject.toml"
        content = "[project]\n" 'version = "1.2.3"\n' "[tool.something]\n" 'min_version = "1.0.0"\n'
        pyproject.write_text(content)

        bump_version.update_version_in_pyproject(pyproject, "2.0.0")

        updated = pyproject.read_text()
        assert 'version = "2.0.0"' in updated
        assert 'min_version = "1.0.0"' in updated  # Should not change


class TestUpdateVersionInInit:
    """Test update_version_in_init function."""

    def test_updates_init_version(self, tmp_path: Path) -> None:
        """Test updating version in __init__.py."""
        project_root = tmp_path
        init_dir = project_root / "src" / "gemini_imagen"
        init_dir.mkdir(parents=True)
        init_file = init_dir / "__init__.py"
        init_file.write_text('__version__ = "1.2.3"\n')

        bump_version.update_version_in_init(project_root, "2.0.0")

        updated = init_file.read_text()
        assert '__version__ = "2.0.0"' in updated
        assert '__version__ = "1.2.3"' not in updated

    def test_handles_missing_init_file(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        """Test graceful handling when __init__.py doesn't exist."""
        project_root = tmp_path

        # Should not raise an error
        bump_version.update_version_in_init(project_root, "2.0.0")

        captured = capsys.readouterr()
        assert "Warning" in captured.out

    def test_only_updates_first_occurrence(self, tmp_path: Path) -> None:
        """Test that only the first __version__ is updated."""
        project_root = tmp_path
        init_dir = project_root / "src" / "gemini_imagen"
        init_dir.mkdir(parents=True)
        init_file = init_dir / "__init__.py"
        content = (
            '__version__ = "1.2.3"\n'
            '# Some comment about __version__ = "something"\n'
            'MIN_VERSION = "1.0.0"\n'
        )
        init_file.write_text(content)

        bump_version.update_version_in_init(project_root, "2.0.0")

        updated = init_file.read_text()
        assert '__version__ = "2.0.0"' in updated
        assert 'MIN_VERSION = "1.0.0"' in updated


class TestBumpVersionIntegration:
    """Integration tests for the complete bump_version workflow."""

    def test_full_version_bump_workflow(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test complete workflow of bumping version in both files."""
        # Set up project structure
        project_root = tmp_path
        pyproject = project_root / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "0.5.0"\n')

        init_dir = project_root / "src" / "gemini_imagen"
        init_dir.mkdir(parents=True)
        init_file = init_dir / "__init__.py"
        init_file.write_text('__version__ = "0.5.0"\n')

        # Mock sys.argv and paths
        monkeypatch.setattr(sys, "argv", ["bump_version.py", "minor"])
        monkeypatch.setattr(
            bump_version, "__file__", str(project_root / "scripts" / "bump_version.py")
        )

        # Create scripts dir so __file__ works
        (project_root / "scripts").mkdir()

        # Run the main function (it doesn't raise SystemExit on success)
        bump_version.main()

        # Verify both files were updated
        assert 'version = "0.6.0"' in pyproject.read_text()
        assert '__version__ = "0.6.0"' in init_file.read_text()

    def test_version_sync_patch_bump(self, tmp_path: Path) -> None:
        """Test that patch bump syncs both files correctly."""
        project_root = tmp_path
        pyproject = project_root / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "1.0.0"\n')

        init_dir = project_root / "src" / "gemini_imagen"
        init_dir.mkdir(parents=True)
        init_file = init_dir / "__init__.py"
        init_file.write_text('__version__ = "1.0.0"\n')

        # Bump patch
        new_version = bump_version.bump_version("1.0.0", "patch")
        bump_version.update_version_in_pyproject(pyproject, new_version)
        bump_version.update_version_in_init(project_root, new_version)

        assert 'version = "1.0.1"' in pyproject.read_text()
        assert '__version__ = "1.0.1"' in init_file.read_text()

    def test_version_sync_specific_version(self, tmp_path: Path) -> None:
        """Test that setting specific version syncs both files."""
        project_root = tmp_path
        pyproject = project_root / "pyproject.toml"
        pyproject.write_text('[project]\nversion = "1.0.0"\n')

        init_dir = project_root / "src" / "gemini_imagen"
        init_dir.mkdir(parents=True)
        init_file = init_dir / "__init__.py"
        init_file.write_text('__version__ = "1.0.0"\n')

        # Set specific version
        new_version = "2.5.0"
        bump_version.update_version_in_pyproject(pyproject, new_version)
        bump_version.update_version_in_init(project_root, new_version)

        assert 'version = "2.5.0"' in pyproject.read_text()
        assert '__version__ = "2.5.0"' in init_file.read_text()
