#!/usr/bin/env python3
"""
DEPRECATED: This script is no longer needed with dynamic versioning.

The project now uses hatch-vcs for dynamic versioning from git tags.
Version is automatically derived from git tags.

Use scripts/release.sh instead to create releases.
"""

import re
import sys
from pathlib import Path


def get_current_version(pyproject_path: Path) -> str:
    """Extract current version from pyproject.toml."""
    content = pyproject_path.read_text()
    match = re.search(r'version = "([^"]+)"', content)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    return match.group(1)


def bump_version(current: str, bump_type: str) -> str:
    """Bump version according to semantic versioning."""
    parts = [int(x) for x in current.split(".")]
    if len(parts) != 3:
        raise ValueError(f"Invalid version format: {current}")

    major, minor, patch = parts

    if bump_type == "major":
        return f"{major + 1}.0.0"
    elif bump_type == "minor":
        return f"{major}.{minor + 1}.0"
    elif bump_type == "patch":
        return f"{major}.{minor}.{patch + 1}"
    else:
        # Validate it's a proper version string
        if not re.match(r"^\d+\.\d+\.\d+$", bump_type):
            raise ValueError(f"Invalid version or bump type: {bump_type}")
        return bump_type


def update_version_in_pyproject(pyproject_path: Path, new_version: str) -> None:
    """Update version in pyproject.toml."""
    content = pyproject_path.read_text()
    updated = re.sub(
        r'version = "[^"]+"',
        f'version = "{new_version}"',
        content,
        count=1,
    )
    pyproject_path.write_text(updated)


def update_version_in_init(project_root: Path, new_version: str) -> None:
    """Update version in src/gemini_imagen/__init__.py."""
    init_path = project_root / "src" / "gemini_imagen" / "__init__.py"

    if not init_path.exists():
        print(f"Warning: Could not find {init_path}")
        return

    content = init_path.read_text()
    updated = re.sub(
        r'__version__ = "[^"]+"',
        f'__version__ = "{new_version}"',
        content,
        count=1,
    )
    init_path.write_text(updated)
    print(f"Updated version in {init_path}")


def main() -> None:
    print(__doc__)
    print("\nThis project now uses dynamic versioning with hatch-vcs.")
    print("Versions are automatically derived from git tags.")
    print("\nTo create a new release:")
    print("  ./scripts/release.sh [patch|minor|major|VERSION]")
    print("\nExamples:")
    print("  ./scripts/release.sh          # Bump patch version")
    print("  ./scripts/release.sh minor    # Bump minor version")
    print("  ./scripts/release.sh 1.2.3    # Create v1.2.3 release")
    sys.exit(1)


if __name__ == "__main__":
    main()
