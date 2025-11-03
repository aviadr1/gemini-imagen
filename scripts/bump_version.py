#!/usr/bin/env python3
"""
Bump version in pyproject.toml following semantic versioning.

Usage:
    uv run python scripts/bump_version.py patch   # 0.1.0 -> 0.1.1
    uv run python scripts/bump_version.py minor   # 0.1.0 -> 0.2.0
    uv run python scripts/bump_version.py major   # 0.1.0 -> 1.0.0
    uv run python scripts/bump_version.py 1.2.3   # Set specific version
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
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    bump_type = sys.argv[1].lower()
    if bump_type in ["-h", "--help", "help"]:
        print(__doc__)
        sys.exit(0)

    # Validate bump type early
    if bump_type not in ["patch", "minor", "major"] and not re.match(r"^\d+\.\d+\.\d+$", bump_type):
        print(f"Error: Invalid version or bump type: {bump_type}")
        print(__doc__)
        sys.exit(1)

    # Find pyproject.toml
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    pyproject_path = project_root / "pyproject.toml"

    if not pyproject_path.exists():
        print(f"Error: Could not find {pyproject_path}")
        sys.exit(1)

    # Get current version
    current_version = get_current_version(pyproject_path)
    print(f"Current version: {current_version}")

    # Calculate new version
    try:
        new_version = bump_version(current_version, bump_type)
    except ValueError as e:
        print(f"Error: {e}")
        print(__doc__)
        sys.exit(1)

    # Update version in both files
    update_version_in_pyproject(pyproject_path, new_version)
    print(f"Updated version in pyproject.toml: {new_version}")

    update_version_in_init(project_root, new_version)

    print(f"\n✓ Version successfully updated to {new_version}")
    print("Note: This is typically called by release.sh, not directly.")


if __name__ == "__main__":
    main()
