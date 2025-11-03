#!/usr/bin/env python3
"""
Standalone installer for gemini-imagen CLI.

This script installs gemini-imagen in an isolated environment without requiring
the user to manually install Python or manage dependencies.

Inspired by: uv, poetry, and ruff installation patterns.

Usage:
    python3 install.py
    curl -sSL https://raw.githubusercontent.com/aviadr1/gemini-imagen/main/scripts/install.py | python3 -
"""

import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Optional

# Configuration
PACKAGE_NAME = "gemini-imagen"
GITHUB_REPO = "aviadr1/gemini-imagen"
MIN_PYTHON_VERSION = (3, 12)

# Colors for terminal output
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"


def log_info(msg: str) -> None:
    """Print info message."""
    print(f"{GREEN}[OK]{RESET} {msg}")


def log_warning(msg: str) -> None:
    """Print warning message."""
    print(f"{YELLOW}[WARN]{RESET} {msg}", file=sys.stderr)


def log_error(msg: str) -> None:
    """Print error message."""
    print(f"{RED}[ERROR]{RESET} {msg}", file=sys.stderr)


def get_platform_info() -> tuple[str, str, str]:
    """
    Detect platform and architecture.

    Returns:
        Tuple of (os_name, arch, platform_str)
        - os_name: 'linux', 'darwin', 'windows'
        - arch: 'x86_64', 'aarch64', 'arm64', etc.
        - platform_str: Combined string like 'linux-x86_64'
    """
    os_name = platform.system().lower()
    arch = platform.machine().lower()

    # Normalize architecture names
    arch_map = {
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "arm64": "aarch64",
        "aarch64": "aarch64",
    }
    arch = arch_map.get(arch, arch)

    platform_str = f"{os_name}-{arch}"
    return os_name, arch, platform_str


def check_python_version() -> bool:
    """Check if current Python version meets minimum requirement."""
    current = sys.version_info[:2]
    if current < MIN_PYTHON_VERSION:
        log_error(
            f"Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}+ required "
            f"(found {current[0]}.{current[1]})"
        )
        return False
    return True


def get_install_paths(os_name: str) -> tuple[Path, Path, Path]:
    """
    Get installation paths for the current platform.

    Returns:
        Tuple of (venv_dir, wrapper_dir, config_dir)
    """
    if os_name == "windows":
        # Windows paths
        local_appdata = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        venv_dir = local_appdata / "gemini-imagen"
        wrapper_dir = local_appdata / "Programs" / "imagen"
        config_dir = local_appdata / "imagen"
    else:
        # Unix paths (Linux/macOS)
        # Follow XDG Base Directory specification
        data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

        venv_dir = data_home / "gemini-imagen"
        wrapper_dir = Path.home() / ".local" / "bin"
        config_dir = config_home / "imagen"

    return venv_dir, wrapper_dir, config_dir


def create_venv(venv_dir: Path) -> bool:
    """Create virtual environment."""
    log_info(f"Creating virtual environment at {venv_dir}")

    try:
        # Remove existing venv if present
        if venv_dir.exists():
            log_warning(f"Removing existing installation at {venv_dir}")
            shutil.rmtree(venv_dir)

        venv_dir.parent.mkdir(parents=True, exist_ok=True)

        # Create venv
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            check=True,
            capture_output=True,
        )

        log_info("Virtual environment created")
        return True

    except subprocess.CalledProcessError as e:
        log_error(f"Failed to create virtual environment: {e}")
        if e.stderr:
            log_error(e.stderr.decode())
        return False


def get_pip_executable(venv_dir: Path, os_name: str) -> Path:
    """Get path to pip executable in venv."""
    if os_name == "windows":
        return venv_dir / "Scripts" / "pip.exe"
    else:
        return venv_dir / "bin" / "pip"


def get_python_executable(venv_dir: Path, os_name: str) -> Path:
    """Get path to python executable in venv."""
    if os_name == "windows":
        return venv_dir / "Scripts" / "python.exe"
    else:
        return venv_dir / "bin" / "python"


def install_package(venv_dir: Path, os_name: str) -> bool:
    """Install gemini-imagen package into venv."""
    log_info(f"Installing {PACKAGE_NAME} from PyPI...")

    pip_exe = get_pip_executable(venv_dir, os_name)

    try:
        # Upgrade pip first
        subprocess.run(
            [str(pip_exe), "install", "--upgrade", "pip"],
            check=True,
            capture_output=True,
        )

        # Install gemini-imagen with S3 support
        subprocess.run(
            [str(pip_exe), "install", f"{PACKAGE_NAME}[s3]"],
            check=True,
            capture_output=True,
        )

        log_info(f"{PACKAGE_NAME} installed successfully")
        return True

    except subprocess.CalledProcessError as e:
        log_error(f"Failed to install {PACKAGE_NAME}: {e}")
        if e.stderr:
            log_error(e.stderr.decode())
        return False


def create_wrapper_script(venv_dir: Path, wrapper_dir: Path, os_name: str) -> bool:
    """Create wrapper script that launches imagen from venv."""
    wrapper_dir.mkdir(parents=True, exist_ok=True)

    # Pip already creates an 'imagen' script in venv/bin or venv/Scripts
    # We just need to symlink or copy it to the wrapper directory
    if os_name == "windows":
        source_script = venv_dir / "Scripts" / "imagen.exe"
        wrapper_path = wrapper_dir / "imagen.exe"
    else:
        source_script = venv_dir / "bin" / "imagen"
        wrapper_path = wrapper_dir / "imagen"

    try:
        if not source_script.exists():
            log_error(f"Source script not found at {source_script}")
            return False

        # On Unix, create symlink; on Windows, copy the executable
        if os_name == "windows":
            shutil.copy2(source_script, wrapper_path)
        else:
            # Remove existing symlink if present
            if wrapper_path.exists() or wrapper_path.is_symlink():
                wrapper_path.unlink()
            wrapper_path.symlink_to(source_script)

        log_info(f"Created wrapper script at {wrapper_path}")
        return True

    except Exception as e:
        log_error(f"Failed to create wrapper script: {e}")
        return False


def create_install_receipt(
    config_dir: Path,
    venv_dir: Path,
    wrapper_dir: Path,
    platform_str: str,
) -> bool:
    """Create install receipt for tracking installation."""
    config_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = config_dir / "install_receipt.json"

    # Get installed version
    python_exe = get_python_executable(venv_dir, platform.system().lower())
    try:
        result = subprocess.run(
            [str(python_exe), "-c", "import gemini_imagen; print(gemini_imagen.__version__)"],
            check=True,
            capture_output=True,
            text=True,
        )
        version = result.stdout.strip()
    except Exception:
        version = "unknown"

    receipt = {
        "version": version,
        "install_date": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "install_method": "standalone",
        "venv_path": str(venv_dir),
        "wrapper_path": str(wrapper_dir),
        "platform": platform_str,
    }

    try:
        receipt_path.write_text(json.dumps(receipt, indent=2))
        log_info(f"Install receipt created at {receipt_path}")
        return True
    except Exception as e:
        log_error(f"Failed to create install receipt: {e}")
        return False


def update_path_unix(wrapper_dir: Path, shell_name: Optional[str] = None) -> bool:
    """Update PATH in Unix shell profile files."""
    home = Path.home()

    # Determine which shell profiles to update
    if shell_name:
        profiles = [home / f".{shell_name}rc"]
    else:
        # Try to detect shell
        shell = os.environ.get("SHELL", "")
        if "zsh" in shell:
            profiles = [home / ".zshrc"]
        elif "bash" in shell:
            profiles = [home / ".bashrc", home / ".bash_profile"]
        else:
            # Default to common profiles
            profiles = [home / ".profile", home / ".bashrc"]

    path_line = f'\nexport PATH="{wrapper_dir}:$PATH"\n'

    modified = False
    for profile in profiles:
        if not profile.exists():
            continue

        try:
            content = profile.read_text()
            if str(wrapper_dir) in content:
                # Already in PATH
                continue

            # Append to file
            with profile.open("a") as f:
                f.write("\n# Added by gemini-imagen installer\n")
                f.write(path_line)

            log_info(f"Added {wrapper_dir} to PATH in {profile}")
            modified = True
        except Exception as e:
            log_warning(f"Could not update {profile}: {e}")

    return modified


def update_path_windows(wrapper_dir: Path) -> bool:
    """Update PATH in Windows registry."""
    try:
        import winreg

        # Open user environment variables key
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            "Environment",
            0,
            winreg.KEY_READ | winreg.KEY_WRITE,
        )

        try:
            # Get current PATH
            path_value, _ = winreg.QueryValueEx(key, "Path")

            # Check if already in PATH
            if str(wrapper_dir) in path_value:
                return False

            # Add to PATH
            new_path = f"{path_value};{wrapper_dir}"
            winreg.SetValueEx(key, "Path", 0, winreg.REG_EXPAND_SZ, new_path)

            log_info(f"Added {wrapper_dir} to PATH")
            return True

        finally:
            winreg.CloseKey(key)

    except Exception as e:
        log_error(f"Failed to update PATH: {e}")
        return False


def prompt_path_update(wrapper_dir: Path, os_name: str) -> None:
    """Prompt user to update PATH if needed."""
    # Check if already in PATH
    path_env = os.environ.get("PATH", "")
    if str(wrapper_dir) in path_env:
        log_info("Wrapper directory already in PATH")
        return

    print(f"\n{BOLD}Update PATH?{RESET}")
    print(f"The installer can add {wrapper_dir} to your PATH automatically.")
    print("This allows you to run 'imagen' from anywhere.")

    response = input("Add to PATH? [Y/n]: ").strip().lower()

    if response in ("", "y", "yes"):
        if os_name == "windows":
            if update_path_windows(wrapper_dir):
                print(
                    f"\n{YELLOW}Note:{RESET} You may need to restart your terminal for PATH changes to take effect."
                )
        else:
            if update_path_unix(wrapper_dir):
                print(
                    f"\n{YELLOW}Note:{RESET} Run 'source ~/.bashrc' (or equivalent) to reload your shell profile."
                )
    else:
        print(f"\n{YELLOW}Skipped PATH update.{RESET}")
        print("To use 'imagen', add this to your PATH manually:")
        print(f"  {wrapper_dir}")


def main() -> int:
    """Main installation function."""
    print(f"\n{BOLD}gemini-imagen Standalone Installer{RESET}\n")

    # Check Python version
    if not check_python_version():
        return 1

    # Get platform info
    os_name, arch, platform_str = get_platform_info()
    log_info(f"Detected platform: {platform_str}")

    # Get installation paths
    venv_dir, wrapper_dir, config_dir = get_install_paths(os_name)

    print(f"\n{BOLD}Installation Plan:{RESET}")
    print(f"  Virtual environment: {venv_dir}")
    print(f"  Wrapper script:      {wrapper_dir}")
    print(f"  Configuration:       {config_dir}")
    print()

    # Confirm installation
    response = input("Continue with installation? [Y/n]: ").strip().lower()
    if response not in ("", "y", "yes"):
        print("Installation cancelled.")
        return 0

    print()

    # Create virtual environment
    if not create_venv(venv_dir):
        return 1

    # Install package
    if not install_package(venv_dir, os_name):
        return 1

    # Create wrapper script
    if not create_wrapper_script(venv_dir, wrapper_dir, os_name):
        return 1

    # Create install receipt
    if not create_install_receipt(config_dir, venv_dir, wrapper_dir, platform_str):
        log_warning("Could not create install receipt (self-update may not work)")

    # Update PATH
    prompt_path_update(wrapper_dir, os_name)

    # Success message
    print(f"\n{BOLD}{GREEN}[OK] Installation complete!{RESET}\n")
    print(f"Run '{BOLD}imagen --help{RESET}' to get started.")
    print(f"Run '{BOLD}imagen self-update{RESET}' to update to the latest version.")
    print()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user.")
        sys.exit(130)
    except Exception as e:
        log_error(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
