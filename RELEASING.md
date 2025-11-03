# Release Process

This project uses **dynamic versioning** with `hatch-vcs`. Versions are automatically derived from git tags, eliminating the need for manual version bumps in code.

## Quick Release

To create a new release, use the release script:

```bash
./scripts/release.sh [patch|minor|major|VERSION]
```

Examples:
```bash
./scripts/release.sh          # Bump patch version (0.6.5 -> 0.6.6)
./scripts/release.sh minor    # Bump minor version (0.6.5 -> 0.7.0)
./scripts/release.sh major    # Bump major version (0.6.5 -> 1.0.0)
./scripts/release.sh 1.2.3    # Create specific version v1.2.3
```

## What Happens

The release script:

1. **Validates** your working directory is clean
2. **Checks** you're on the main branch
3. **Pulls** latest changes
4. **Installs** dependencies with `uv sync --extra dev --extra s3`
5. **Runs linters** (ruff check, ruff format, mypy)
6. **Runs tests** (pytest, excluding integration tests)
7. **Calculates** the new version based on your input
8. **Prompts** for confirmation
9. **Creates and pushes** a git tag (e.g., `v0.6.6`)

## CI/CD Automation

Once you push the tag, GitHub Actions automatically:

1. **Builds** the package with the correct version from the tag
2. **Publishes** to PyPI using stored credentials
3. **Creates** a GitHub release with changelog

Monitor the release workflow at: https://github.com/aviadr1/gemini-imagen/actions

## How Dynamic Versioning Works

### Configuration

In `pyproject.toml`:
```toml
[project]
dynamic = ["version"]

[build-system]
requires = ["hatchling", "hatch-vcs"]

[tool.hatch.version]
source = "vcs"

[tool.hatch.build.hooks.vcs]
version-file = "src/gemini_imagen/_version.py"
```

### Version Detection

- **On a tag** (e.g., `v0.6.5`): Version is `0.6.5`
- **After a tag**: Version is `0.6.6.dev0+g<commit>.d<date>`
- **No tags**: Version is `0.0.0.dev0`

The version is:
1. Auto-generated in `src/gemini_imagen/_version.py` during build
2. Imported by `src/gemini_imagen/__init__.py`
3. Available via `gemini_imagen.__version__`

### Benefits

- ✅ No manual version bumps in code
- ✅ Version always matches git tags
- ✅ Development versions include commit hash
- ✅ Eliminates version drift
- ✅ Cleaner git history (no version bump commits)

## Manual Release (Advanced)

If you need to release manually without the script:

```bash
# 1. Ensure working directory is clean
git status

# 2. Create and push tag
git tag v0.6.6
git push origin v0.6.6

# 3. Wait for CI/CD to complete
# Monitor at: https://github.com/aviadr1/gemini-imagen/actions
```

## Troubleshooting

### Wrong version detected

If the version is incorrect, check your git tags:
```bash
git describe --tags --abbrev=0  # Shows latest tag
git tag --list                  # Shows all tags
```

### CI/CD fails to publish

- Verify `PYPI_API_TOKEN` secret is set in GitHub repository settings
- Check the workflow logs for specific errors
- Ensure the tag follows semantic versioning (v0.6.6, not 0.6.6)

### Development version persists after tag

Make sure you're building from the tag:
```bash
git checkout v0.6.6
python -m build
```

Or ensure your checkout is clean:
```bash
git pull
git describe --tags  # Should show the exact tag
```

## Legacy Scripts

- `scripts/bump_version.py` - **DEPRECATED** (now shows helpful message)

These are no longer needed with dynamic versioning.
