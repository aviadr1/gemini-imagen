"""
Self-update command for gemini-imagen.

Allows users who installed via the standalone installer to update to the latest version.
"""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import click
import httpx

from ... import __version__


def get_install_receipt_path() -> Path:
    """Get path to install receipt file."""
    import os
    import platform

    os_name = platform.system().lower()

    if os_name == "windows":
        # Respect LOCALAPPDATA env var (important for testing)
        local_appdata = os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
        config_dir = Path(local_appdata) / "imagen"
    else:
        # Unix (Linux/macOS)
        # Respect XDG_CONFIG_HOME and HOME env vars (important for testing)
        home = os.environ.get("HOME", str(Path.home()))
        config_home = os.environ.get("XDG_CONFIG_HOME", str(Path(home) / ".config"))
        config_dir = Path(config_home) / "imagen"

    return config_dir / "install_receipt.json"


def load_install_receipt() -> dict | None:
    """Load install receipt if it exists."""
    receipt_path = get_install_receipt_path()

    if not receipt_path.exists():
        return None

    try:
        with receipt_path.open() as f:
            return json.load(f)
    except Exception:
        return None


def save_install_receipt(receipt: dict) -> None:
    """Save install receipt."""
    receipt_path = get_install_receipt_path()
    receipt_path.parent.mkdir(parents=True, exist_ok=True)

    with receipt_path.open("w") as f:
        json.dump(receipt, indent=2, fp=f)


def check_latest_version(timeout: float = 5.0) -> str | None:
    """
    Check latest version from GitHub API.

    Returns:
        Latest version string, or None if check failed
    """
    api_url = "https://api.github.com/repos/aviadr1/gemini-imagen/releases/latest"

    try:
        response = httpx.get(api_url, timeout=timeout, follow_redirects=True)
        response.raise_for_status()

        data = response.json()
        tag_name = data.get("tag_name", "")

        # Strip 'v' prefix if present
        version = tag_name.lstrip("v")
        return version

    except Exception:
        return None


def get_python_executable() -> Path:
    """Get path to Python executable in current environment."""
    return Path(sys.executable)


def update_package(venv_python: Path, version: str | None = None) -> bool:
    """
    Update gemini-imagen package using pip.

    Args:
        venv_python: Path to Python executable in venv
        version: Specific version to install, or None for latest

    Returns:
        True if successful, False otherwise
    """
    try:
        # Build pip install command
        package_spec = f"gemini-imagen[s3]=={version}" if version else "gemini-imagen[s3]"

        # Run pip install --upgrade
        result = subprocess.run(
            [str(venv_python), "-m", "pip", "install", "--upgrade", package_spec],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            click.echo(f"Error: {result.stderr}", err=True)
            return False

        return True

    except Exception as e:
        click.echo(f"Error updating package: {e}", err=True)
        return False


@click.command(name="self-update")
@click.option(
    "--check",
    is_flag=True,
    help="Only check for updates without installing",
)
@click.option(
    "--version",
    "target_version",
    help="Update to specific version (e.g., 0.6.0)",
)
def self_update(check: bool, target_version: str | None) -> None:
    """
    Update gemini-imagen to the latest version.

    This command only works if gemini-imagen was installed using the
    standalone installer. If installed via pip, use 'pip install --upgrade gemini-imagen'.

    \b
    Examples:
        # Check for updates
        imagen self-update --check

        # Update to latest version
        imagen self-update

        # Update to specific version
        imagen self-update --version 0.6.0
    """
    # Check if installed via standalone installer
    receipt = load_install_receipt()

    if receipt is None or receipt.get("install_method") != "standalone":
        click.echo(
            "Error: self-update only works for standalone installations.\n\n"
            "If you installed via pip, use:\n"
            "  pip install --upgrade gemini-imagen\n\n"
            "If you installed via a package manager (brew, etc.), use that to update.",
            err=True,
        )
        sys.exit(1)

    current_version = __version__
    click.echo(f"Current version: {current_version}")

    # Check latest version
    latest_version: str
    if target_version:
        latest_version = target_version
        click.echo(f"Target version:  {latest_version}")
    else:
        click.echo("Checking for updates...", nl=False)
        latest_version_or_none = check_latest_version()

        if latest_version_or_none is None:
            click.echo(" failed")
            click.echo(
                "\nError: Could not check for updates. Please try again later.",
                err=True,
            )
            sys.exit(1)

        latest_version = latest_version_or_none
        click.echo(" done")
        click.echo(f"Latest version:  {latest_version}")

    # Compare versions
    if latest_version == current_version and not target_version:
        click.echo("\n[OK] Already on latest version!")
        return

    if latest_version < current_version and not target_version:
        click.echo(
            f"\n[WARN] You're running a newer version ({current_version}) than the latest release ({latest_version})"
        )
        if not click.confirm("Continue with downgrade?"):
            return

    # Check only mode
    if check:
        if latest_version != current_version:
            click.echo(f"\n[INFO] Update available: {current_version} -> {latest_version}")
            click.echo("Run 'imagen self-update' to install")
        return

    # Confirm update
    click.echo(f"\nUpdate: {current_version} -> {latest_version}")
    if not click.confirm("Continue?", default=True):
        click.echo("Update cancelled")
        return

    # Get Python executable from venv
    venv_path = receipt.get("venv_path")
    if not venv_path:
        click.echo("Error: Could not find venv path in install receipt", err=True)
        sys.exit(1)

    import platform

    os_name = platform.system().lower()

    if os_name == "windows":
        venv_python = Path(venv_path) / "Scripts" / "python.exe"
    else:
        venv_python = Path(venv_path) / "bin" / "python"

    if not venv_python.exists():
        click.echo(f"Error: Python executable not found at {venv_python}", err=True)
        sys.exit(1)

    # Perform update
    click.echo("\nUpdating...")

    if not update_package(venv_python, target_version or latest_version):
        click.echo("\n[ERROR] Update failed", err=True)
        sys.exit(1)

    # Update install receipt
    receipt["version"] = target_version or latest_version
    receipt["last_update"] = datetime.utcnow().isoformat() + "Z"
    save_install_receipt(receipt)

    click.echo(f"\n[OK] Successfully updated to version {target_version or latest_version}!")
    click.echo("\nRestart your terminal to use the new version.")


def check_for_updates_background() -> None:
    """
    Check for updates in background (non-blocking).

    This runs on CLI startup for standalone installations.
    Only checks once per day to avoid rate limiting.
    """
    try:
        # Only for standalone installations
        receipt = load_install_receipt()
        if receipt is None or receipt.get("install_method") != "standalone":
            return

        # Check if we've checked recently
        last_check_str = receipt.get("last_update_check")
        if last_check_str:
            try:
                last_check = datetime.fromisoformat(last_check_str.rstrip("Z"))
                if datetime.utcnow() - last_check < timedelta(days=1):
                    # Checked within last 24 hours, skip
                    return
            except Exception:
                pass

        # Quick check (short timeout)
        latest_version = check_latest_version(timeout=2.0)

        if latest_version and latest_version != __version__:
            # New version available!
            click.echo(
                f"\n[INFO] New version available: {latest_version} (current: {__version__})\n"
                f"       Run 'imagen self-update' to upgrade\n",
                err=True,
            )

        # Update last check time
        receipt["last_update_check"] = datetime.utcnow().isoformat() + "Z"
        save_install_receipt(receipt)

    except Exception:
        # Fail silently - don't interrupt user's workflow
        pass
