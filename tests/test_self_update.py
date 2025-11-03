"""
Tests for the self-update command.

These tests verify the update checking and installation logic.
"""

import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest
from click.testing import CliRunner

from gemini_imagen.cli.commands import self_update


class TestInstallReceipt:
    """Test install receipt loading and saving."""

    def test_load_nonexistent_receipt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test loading receipt when it doesn't exist."""
        config_dir = tmp_path / "config"
        monkeypatch.setattr(
            self_update, "get_install_receipt_path", lambda: config_dir / "install_receipt.json"
        )

        receipt = self_update.load_install_receipt()
        assert receipt is None

    def test_load_existing_receipt(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading existing receipt."""
        config_dir = tmp_path / "config"
        config_dir.mkdir(parents=True)

        receipt_data = {
            "version": "0.6.0",
            "install_method": "standalone",
            "platform": "linux-x86_64",
        }

        receipt_path = config_dir / "install_receipt.json"
        receipt_path.write_text(json.dumps(receipt_data))

        monkeypatch.setattr(self_update, "get_install_receipt_path", lambda: receipt_path)

        receipt = self_update.load_install_receipt()
        assert receipt is not None
        assert receipt["version"] == "0.6.0"
        assert receipt["install_method"] == "standalone"

    def test_save_receipt(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test saving receipt."""
        config_dir = tmp_path / "config"
        receipt_path = config_dir / "install_receipt.json"

        monkeypatch.setattr(self_update, "get_install_receipt_path", lambda: receipt_path)

        receipt_data = {
            "version": "0.7.0",
            "install_method": "standalone",
            "last_update": "2025-11-03T12:00:00Z",
        }

        self_update.save_install_receipt(receipt_data)

        assert receipt_path.exists()
        saved = json.loads(receipt_path.read_text())
        assert saved["version"] == "0.7.0"


class TestVersionChecking:
    """Test version checking against GitHub API."""

    def test_check_latest_version_success(self) -> None:
        """Test successful version check."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"tag_name": "v0.7.0"}

        with patch.object(httpx, "get", return_value=mock_response):
            version = self_update.check_latest_version()

        assert version == "0.7.0"

    def test_check_latest_version_strips_v_prefix(self) -> None:
        """Test that 'v' prefix is stripped from version."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"tag_name": "v1.0.0"}

        with patch.object(httpx, "get", return_value=mock_response):
            version = self_update.check_latest_version()

        assert version == "1.0.0"

    def test_check_latest_version_no_prefix(self) -> None:
        """Test version without 'v' prefix."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"tag_name": "2.0.0"}

        with patch.object(httpx, "get", return_value=mock_response):
            version = self_update.check_latest_version()

        assert version == "2.0.0"

    def test_check_latest_version_network_error(self) -> None:
        """Test handling of network errors."""
        with patch.object(httpx, "get", side_effect=httpx.RequestError("Network error")):
            version = self_update.check_latest_version()

        assert version is None

    def test_check_latest_version_http_error(self) -> None:
        """Test handling of HTTP errors."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not found", request=Mock(), response=mock_response
        )

        with patch.object(httpx, "get", return_value=mock_response):
            version = self_update.check_latest_version()

        assert version is None


class TestPackageUpdate:
    """Test package update logic."""

    def test_update_package_success(self, tmp_path: Path) -> None:
        """Test successful package update."""
        python_exe = tmp_path / "venv" / "bin" / "python"
        python_exe.parent.mkdir(parents=True)
        python_exe.touch()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stderr = ""

        with patch.object(subprocess, "run", return_value=mock_result):
            success = self_update.update_package(python_exe)

        assert success is True

    def test_update_package_specific_version(self, tmp_path: Path) -> None:
        """Test updating to specific version."""
        python_exe = tmp_path / "venv" / "bin" / "python"
        python_exe.parent.mkdir(parents=True)
        python_exe.touch()

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch.object(subprocess, "run", return_value=mock_result) as mock_run:
            success = self_update.update_package(python_exe, version="0.8.0")

        assert success is True
        # Verify correct package spec was used
        call_args = mock_run.call_args[0][0]
        assert "gemini-imagen[s3]==0.8.0" in call_args

    def test_update_package_failure(self, tmp_path: Path) -> None:
        """Test handling of update failure."""
        python_exe = tmp_path / "venv" / "bin" / "python"
        python_exe.parent.mkdir(parents=True)
        python_exe.touch()

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Error installing package"

        with patch.object(subprocess, "run", return_value=mock_result):
            success = self_update.update_package(python_exe)

        assert success is False


class TestSelfUpdateCommand:
    """Test the self-update CLI command."""

    def test_fails_for_pip_installation(self) -> None:
        """Test that self-update fails for pip installations."""
        runner = CliRunner()

        with patch.object(self_update, "load_install_receipt", return_value=None):
            result = runner.invoke(self_update.self_update)

        assert result.exit_code == 1
        assert "only works for standalone installations" in result.output

    def test_check_only_mode(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test --check flag."""
        runner = CliRunner()

        receipt = {
            "version": "0.6.0",
            "install_method": "standalone",
            "venv_path": str(tmp_path / "venv"),
        }

        with (
            patch.object(self_update, "load_install_receipt", return_value=receipt),
            patch.object(self_update, "check_latest_version", return_value="0.7.0"),
            patch.object(self_update, "__version__", "0.6.0"),
        ):
            result = runner.invoke(self_update.self_update, ["--check"])

        assert result.exit_code == 0
        assert "0.6.0" in result.output
        assert "0.7.0" in result.output
        assert "Update available" in result.output

    def test_already_latest_version(self, tmp_path: Path) -> None:
        """Test when already on latest version."""
        runner = CliRunner()

        receipt = {
            "version": "0.6.0",
            "install_method": "standalone",
            "venv_path": str(tmp_path / "venv"),
        }

        with (
            patch.object(self_update, "load_install_receipt", return_value=receipt),
            patch.object(self_update, "check_latest_version", return_value="0.6.0"),
            patch.object(self_update, "__version__", "0.6.0"),
        ):
            result = runner.invoke(self_update.self_update)

        assert result.exit_code == 0
        assert "Already on latest version" in result.output

    def test_update_cancelled(self, tmp_path: Path) -> None:
        """Test cancelling update."""
        runner = CliRunner()

        receipt = {
            "version": "0.6.0",
            "install_method": "standalone",
            "venv_path": str(tmp_path / "venv"),
        }

        with (
            patch.object(self_update, "load_install_receipt", return_value=receipt),
            patch.object(self_update, "check_latest_version", return_value="0.7.0"),
            patch.object(self_update, "__version__", "0.6.0"),
        ):
            # Simulate user saying "no" to confirmation
            result = runner.invoke(self_update.self_update, input="n\n")

        assert result.exit_code == 0
        assert "cancelled" in result.output.lower()


class TestBackgroundUpdateCheck:
    """Test background update checking."""

    def test_skips_for_pip_installation(self) -> None:
        """Test that background check skips pip installations."""
        with patch.object(self_update, "load_install_receipt", return_value=None):
            # Should not raise any errors
            self_update.check_for_updates_background()

    def test_skips_if_checked_recently(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that check is skipped if done recently."""
        receipt = {
            "version": "0.6.0",
            "install_method": "standalone",
            "last_update_check": datetime.utcnow().isoformat() + "Z",
        }

        with (
            patch.object(self_update, "load_install_receipt", return_value=receipt),
            patch.object(self_update, "check_latest_version") as mock_check,
            patch.object(self_update, "save_install_receipt"),
        ):
            self_update.check_for_updates_background()

        # Should not have checked for updates
        mock_check.assert_not_called()

    def test_checks_if_not_checked_recently(self, tmp_path: Path) -> None:
        """Test that check happens if not done recently."""
        yesterday = datetime.utcnow() - timedelta(days=2)
        receipt = {
            "version": "0.6.0",
            "install_method": "standalone",
            "last_update_check": yesterday.isoformat() + "Z",
        }

        with (
            patch.object(self_update, "load_install_receipt", return_value=receipt),
            patch.object(self_update, "check_latest_version", return_value="0.7.0"),
            patch.object(self_update, "__version__", "0.6.0"),
            patch.object(self_update, "save_install_receipt") as mock_save,
        ):
            self_update.check_for_updates_background()

        # Should have saved updated receipt
        mock_save.assert_called_once()

    def test_silent_failure_on_error(self) -> None:
        """Test that background check fails silently on errors."""
        with patch.object(
            self_update, "load_install_receipt", side_effect=Exception("Network error")
        ):
            # Should not raise
            self_update.check_for_updates_background()

    def test_notifies_of_new_version(self, capsys: pytest.CaptureFixture) -> None:
        """Test notification when new version available."""
        receipt = {
            "version": "0.6.0",
            "install_method": "standalone",
        }

        with (
            patch.object(self_update, "load_install_receipt", return_value=receipt),
            patch.object(self_update, "check_latest_version", return_value="0.7.0"),
            patch.object(self_update, "__version__", "0.6.0"),
            patch.object(self_update, "save_install_receipt"),
        ):
            self_update.check_for_updates_background()

        captured = capsys.readouterr()
        assert "New version available" in captured.err
        assert "0.7.0" in captured.err
        assert "imagen self-update" in captured.err
