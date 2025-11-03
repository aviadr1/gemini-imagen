"""
Version command for gemini-imagen.

Displays detailed version information.
"""

import platform
import sys
from typing import Any

import click

from ... import __version__
from .self_update import check_latest_version, load_install_receipt


@click.command(name="version")
@click.option(
    "--check-update",
    is_flag=True,
    help="Check if a newer version is available",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output in JSON format",
)
def version(check_update: bool, output_json: bool) -> None:
    """
    Display version information.

    Shows the current version of gemini-imagen, Python version,
    platform, and installation method.

    \b
    Examples:
        # Show version
        imagen version

        # Check for updates
        imagen version --check-update

        # JSON output
        imagen version --json
    """
    current_version = __version__
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    platform_info = f"{platform.system()} {platform.release()} ({platform.machine()})"

    # Get installation method
    receipt = load_install_receipt()
    install_method = "unknown"
    venv_path = None

    if receipt:
        install_method = receipt.get("install_method", "unknown")
        venv_path = receipt.get("venv_path")

    # Check for updates if requested
    latest_version = None
    update_available = False

    if check_update:
        latest_version = check_latest_version()
        if latest_version and latest_version != current_version:
            update_available = True

    if output_json:
        import json

        data: dict[str, Any] = {
            "version": current_version,
            "python_version": python_version,
            "platform": platform_info,
            "install_method": install_method,
        }

        if venv_path:
            data["venv_path"] = venv_path

        if check_update:
            data["latest_version"] = latest_version
            data["update_available"] = update_available

        click.echo(json.dumps(data, indent=2))
    else:
        # Human-readable output
        click.echo(f"imagen version {current_version}")
        click.echo(f"Python {python_version}")
        click.echo(f"Platform: {platform_info}")
        click.echo(f"Install method: {install_method}")

        if venv_path:
            click.echo(f"Virtual environment: {venv_path}")

        if check_update:
            if update_available and latest_version:
                click.echo(f"\n⚡ Update available: {current_version} → {latest_version}")
                click.echo("Run 'imagen self-update' to upgrade")
            elif latest_version:
                click.echo(f"\n✓ Up to date (latest: {latest_version})")
            else:
                click.echo("\n⚠ Could not check for updates")
