"""
Tests for the version command.
"""

import json
import platform
import sys
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from gemini_imagen import __version__
from gemini_imagen.cli.commands import version


class TestVersionCommand:
    """Test the version command."""

    def test_version_basic_output(self) -> None:
        """Test basic version output."""
        runner = CliRunner()
        result = runner.invoke(version.version)

        assert result.exit_code == 0
        assert f"imagen version {__version__}" in result.output
        assert "Python" in result.output
        assert "Platform:" in result.output
        assert "Install method:" in result.output

    def test_version_json_output(self) -> None:
        """Test JSON output format."""
        runner = CliRunner()
        result = runner.invoke(version.version, ["--json"])

        assert result.exit_code == 0

        data = json.loads(result.output)
        assert data["version"] == __version__
        assert "python_version" in data
        assert "platform" in data
        assert "install_method" in data

    def test_version_with_install_receipt(self, tmp_path: pytest.TempPathFactory) -> None:
        """Test version with standalone installation."""
        receipt = {
            "version": "0.6.0",
            "install_method": "standalone",
            "venv_path": "/home/user/.local/share/gemini-imagen",
        }

        with patch.object(version, "load_install_receipt", return_value=receipt):
            runner = CliRunner()
            result = runner.invoke(version.version)

            assert result.exit_code == 0
            assert "Install method: standalone" in result.output
            assert "/home/user/.local/share/gemini-imagen" in result.output

    def test_version_with_install_receipt_json(self) -> None:
        """Test JSON output with install receipt."""
        receipt = {
            "version": "0.6.0",
            "install_method": "standalone",
            "venv_path": "/home/user/.local/share/gemini-imagen",
        }

        with patch.object(version, "load_install_receipt", return_value=receipt):
            runner = CliRunner()
            result = runner.invoke(version.version, ["--json"])

            assert result.exit_code == 0

            data = json.loads(result.output)
            assert data["install_method"] == "standalone"
            assert data["venv_path"] == "/home/user/.local/share/gemini-imagen"

    def test_version_check_update_available(self) -> None:
        """Test checking for updates when update is available."""
        with patch.object(version, "check_latest_version", return_value="0.7.0"):
            runner = CliRunner()
            result = runner.invoke(version.version, ["--check-update"])

            assert result.exit_code == 0
            assert "⚡ Update available" in result.output
            assert "0.7.0" in result.output
            assert "imagen self-update" in result.output

    def test_version_check_update_up_to_date(self) -> None:
        """Test checking for updates when already up to date."""
        with patch.object(version, "check_latest_version", return_value=__version__):
            runner = CliRunner()
            result = runner.invoke(version.version, ["--check-update"])

            assert result.exit_code == 0
            assert "✓ Up to date" in result.output

    def test_version_check_update_failed(self) -> None:
        """Test checking for updates when network fails."""
        with patch.object(version, "check_latest_version", return_value=None):
            runner = CliRunner()
            result = runner.invoke(version.version, ["--check-update"])

            assert result.exit_code == 0
            assert "⚠ Could not check for updates" in result.output

    def test_version_check_update_json(self) -> None:
        """Test JSON output with update check."""
        with patch.object(version, "check_latest_version", return_value="0.7.0"):
            runner = CliRunner()
            result = runner.invoke(version.version, ["--check-update", "--json"])

            assert result.exit_code == 0

            data = json.loads(result.output)
            assert data["latest_version"] == "0.7.0"
            assert data["update_available"] is True

    def test_version_check_update_json_up_to_date(self) -> None:
        """Test JSON output when up to date."""
        with patch.object(version, "check_latest_version", return_value=__version__):
            runner = CliRunner()
            result = runner.invoke(version.version, ["--check-update", "--json"])

            assert result.exit_code == 0

            data = json.loads(result.output)
            assert data["latest_version"] == __version__
            assert data["update_available"] is False

    def test_version_python_version_format(self) -> None:
        """Test that Python version is correctly formatted."""
        runner = CliRunner()
        result = runner.invoke(version.version)

        assert result.exit_code == 0
        expected_py_version = (
            f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )
        assert expected_py_version in result.output

    def test_version_platform_info(self) -> None:
        """Test that platform info is included."""
        runner = CliRunner()
        result = runner.invoke(version.version, ["--json"])

        assert result.exit_code == 0

        data = json.loads(result.output)
        assert platform.system() in data["platform"]
        assert platform.machine() in data["platform"]

    def test_version_no_install_receipt(self) -> None:
        """Test version when no install receipt exists (pip install)."""
        with patch.object(version, "load_install_receipt", return_value=None):
            runner = CliRunner()
            result = runner.invoke(version.version)

            assert result.exit_code == 0
            assert "Install method: unknown" in result.output

    def test_version_combined_flags(self) -> None:
        """Test using both --check-update and --json together."""
        receipt = {
            "version": "0.6.0",
            "install_method": "standalone",
            "venv_path": "/home/user/.local/share/gemini-imagen",
        }

        with (
            patch.object(version, "load_install_receipt", return_value=receipt),
            patch.object(version, "check_latest_version", return_value="0.7.0"),
        ):
            runner = CliRunner()
            result = runner.invoke(version.version, ["--check-update", "--json"])

            assert result.exit_code == 0

            data = json.loads(result.output)
            assert data["version"] == __version__
            assert data["install_method"] == "standalone"
            assert data["venv_path"] == "/home/user/.local/share/gemini-imagen"
            assert data["latest_version"] == "0.7.0"
            assert data["update_available"] is True
