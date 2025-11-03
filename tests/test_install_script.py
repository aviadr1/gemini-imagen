"""
Tests for the standalone installer script.

These tests verify the installation logic without actually creating installations.
"""

import json
import platform

# Import functions from install script
# We need to add scripts to sys.path
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# Now we can import from install.py
import install


class TestPlatformDetection:
    """Test platform and architecture detection."""

    @patch.object(platform, "system")
    @patch.object(platform, "machine")
    def test_linux_x86_64(self, mock_machine: Mock, mock_system: Mock) -> None:
        """Test detection of Linux x86_64."""
        mock_system.return_value = "Linux"
        mock_machine.return_value = "x86_64"

        os_name, arch, platform_str = install.get_platform_info()

        assert os_name == "linux"
        assert arch == "x86_64"
        assert platform_str == "linux-x86_64"

    @patch.object(platform, "system")
    @patch.object(platform, "machine")
    def test_macos_arm64(self, mock_machine: Mock, mock_system: Mock) -> None:
        """Test detection of macOS ARM64."""
        mock_system.return_value = "Darwin"
        mock_machine.return_value = "arm64"

        os_name, arch, platform_str = install.get_platform_info()

        assert os_name == "darwin"
        assert arch == "aarch64"  # Normalized
        assert platform_str == "darwin-aarch64"

    @patch.object(platform, "system")
    @patch.object(platform, "machine")
    def test_windows_amd64(self, mock_machine: Mock, mock_system: Mock) -> None:
        """Test detection of Windows AMD64."""
        mock_system.return_value = "Windows"
        mock_machine.return_value = "AMD64"

        os_name, arch, platform_str = install.get_platform_info()

        assert os_name == "windows"
        assert arch == "x86_64"  # Normalized from AMD64
        assert platform_str == "windows-x86_64"


class TestPythonVersionCheck:
    """Test Python version checking."""

    def test_current_version_passes(self) -> None:
        """Test that current Python version passes check."""
        # We're running tests, so Python version should be OK
        assert install.check_python_version() is True

    @patch.object(sys, "version_info", (3, 11, 0, "final", 0))
    def test_old_version_fails(self) -> None:
        """Test that Python 3.11 fails the check."""
        assert install.check_python_version() is False

    @patch.object(sys, "version_info", (3, 12, 0, "final", 0))
    def test_min_version_passes(self) -> None:
        """Test that Python 3.12 passes the check."""
        assert install.check_python_version() is True

    @patch.object(sys, "version_info", (3, 13, 0, "final", 0))
    def test_newer_version_passes(self) -> None:
        """Test that Python 3.13+ passes the check."""
        assert install.check_python_version() is True


class TestInstallPaths:
    """Test installation path determination."""

    def test_unix_paths(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Unix installation paths."""
        # Clear XDG environment variables to test defaults
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
        monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
        # Set HOME to tmp_path
        monkeypatch.setenv("HOME", str(tmp_path))

        venv_dir, wrapper_dir, config_dir = install.get_install_paths("linux")

        assert venv_dir == tmp_path / ".local" / "share" / "gemini-imagen"
        assert wrapper_dir == tmp_path / ".local" / "bin"
        assert config_dir == tmp_path / ".config" / "imagen"

    def test_windows_paths(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test Windows installation paths."""
        local_appdata = tmp_path / "AppData" / "Local"
        monkeypatch.setenv("LOCALAPPDATA", str(local_appdata))

        venv_dir, wrapper_dir, config_dir = install.get_install_paths("windows")

        assert venv_dir == local_appdata / "gemini-imagen"
        assert wrapper_dir == local_appdata / "Programs" / "imagen"
        assert config_dir == local_appdata / "imagen"

    def test_xdg_environment_variables(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that XDG env vars are respected."""
        custom_data = tmp_path / "custom" / "data"
        custom_config = tmp_path / "custom" / "config"

        monkeypatch.setenv("XDG_DATA_HOME", str(custom_data))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(custom_config))

        venv_dir, wrapper_dir, config_dir = install.get_install_paths("linux")

        assert venv_dir == custom_data / "gemini-imagen"
        assert config_dir == custom_config / "imagen"


class TestWrapperScript:
    """Test wrapper script generation."""

    def test_unix_wrapper_content(self, tmp_path: Path) -> None:
        """Test Unix wrapper script is a symlink to venv script."""
        venv_dir = tmp_path / "venv"
        wrapper_dir = tmp_path / "bin"
        wrapper_dir.mkdir(parents=True)

        # Create fake imagen script in venv (simulating pip install)
        venv_dir.mkdir(parents=True)
        venv_bin = venv_dir / "bin"
        venv_bin.mkdir(parents=True)
        source_script = venv_bin / "imagen"
        source_script.write_text("#!/usr/bin/env python\n# Generated by pip\n")
        source_script.chmod(0o755)

        install.create_wrapper_script(venv_dir, wrapper_dir, "linux")

        wrapper_path = wrapper_dir / "imagen"
        assert wrapper_path.exists()
        assert wrapper_path.is_symlink()
        assert wrapper_path.resolve() == source_script.resolve()

        # Check executable bit
        assert wrapper_path.stat().st_mode & 0o100  # Owner execute

    def test_windows_wrapper_content(self, tmp_path: Path) -> None:
        """Test Windows wrapper is a copy of venv script."""
        venv_dir = tmp_path / "venv"
        wrapper_dir = tmp_path / "bin"
        wrapper_dir.mkdir(parents=True)

        # Create fake imagen.exe in venv (simulating pip install)
        venv_dir.mkdir(parents=True)
        venv_scripts = venv_dir / "Scripts"
        venv_scripts.mkdir(parents=True)
        source_script = venv_scripts / "imagen.exe"
        source_script.write_bytes(b"FAKE EXE CONTENT")

        install.create_wrapper_script(venv_dir, wrapper_dir, "windows")

        wrapper_path = wrapper_dir / "imagen.exe"
        assert wrapper_path.exists()
        # On Windows, we copy instead of symlink
        assert wrapper_path.read_bytes() == b"FAKE EXE CONTENT"


class TestInstallReceipt:
    """Test install receipt creation."""

    def test_creates_receipt_file(self, tmp_path: Path) -> None:
        """Test that install receipt is created."""
        config_dir = tmp_path / "config"
        venv_dir = tmp_path / "venv"
        wrapper_dir = tmp_path / "bin"

        # Create fake python executable
        venv_dir.mkdir(parents=True)
        python_exe = venv_dir / "bin" / "python"
        python_exe.parent.mkdir(parents=True)
        python_exe.touch()
        python_exe.chmod(0o755)

        # Mock the subprocess call that gets version
        with patch.object(install.subprocess, "run") as mock_run:
            mock_result = MagicMock()
            mock_result.stdout = "0.6.0\n"
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            install.create_install_receipt(
                config_dir,
                venv_dir,
                wrapper_dir,
                "linux-x86_64",
            )

        receipt_path = config_dir / "install_receipt.json"
        assert receipt_path.exists()

        # Verify receipt contents
        receipt = json.loads(receipt_path.read_text())
        assert receipt["version"] == "0.6.0"
        assert receipt["install_method"] == "standalone"
        assert receipt["platform"] == "linux-x86_64"
        assert receipt["venv_path"] == str(venv_dir)
        assert receipt["wrapper_path"] == str(wrapper_dir)
        assert "install_date" in receipt


class TestPathUpdate:
    """Test PATH update logic."""

    def test_unix_path_update_bashrc(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test adding to .bashrc."""
        bashrc = tmp_path / ".bashrc"
        bashrc.write_text("# Existing content\n")

        wrapper_dir = Path("/home/user/.local/bin")

        # Set HOME to tmp_path
        monkeypatch.setenv("HOME", str(tmp_path))
        modified = install.update_path_unix(wrapper_dir)

        assert modified is True
        content = bashrc.read_text()
        assert str(wrapper_dir) in content
        assert "gemini-imagen installer" in content

    def test_unix_path_already_present(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that PATH is not duplicated."""
        wrapper_dir = Path("/home/user/.local/bin")

        bashrc = tmp_path / ".bashrc"
        bashrc.write_text(f'export PATH="{wrapper_dir}:$PATH"\n')

        # Set HOME to tmp_path
        monkeypatch.setenv("HOME", str(tmp_path))
        modified = install.update_path_unix(wrapper_dir)

        # Should not modify since already present
        assert modified is False

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
    def test_windows_path_update(self) -> None:
        """Test Windows PATH update (requires Windows)."""
        wrapper_dir = Path(r"C:\Users\Test\AppData\Local\Programs\imagen")

        with (
            patch("winreg.OpenKey"),
            patch("winreg.QueryValueEx") as mock_query,
            patch("winreg.SetValueEx") as mock_set,
            patch("winreg.CloseKey"),
        ):
            # Mock current PATH without our directory
            mock_query.return_value = (r"C:\Windows\System32;C:\Python312", None)

            result = install.update_path_windows(wrapper_dir)

            assert result is True
            # Verify SetValueEx was called with updated PATH
            mock_set.assert_called_once()
