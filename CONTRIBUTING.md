# Contributing to gemini-imagen

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Running Tests](#running-tests)
- [Code Quality](#code-quality)
- [Building and Publishing](#building-and-publishing)
- [CI/CD](#cicd)
- [Pull Request Process](#pull-request-process)
- [Code Style](#code-style)
- [Reporting Bugs](#reporting-bugs)
- [License](#license)

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/gemini-imagen.git
   cd gemini-imagen
   ```

3. Install development dependencies (see [Development Setup](#development-setup) below)

## Development Setup

We use modern Python tooling with **uv** as the primary package manager:
- **uv** for fast dependency management (recommended)
- **pytest** for testing
- **ruff** for linting and formatting
- **mypy** for type checking
- **pre-commit** for git hooks

### Requirements

- Python >= 3.12 (supports Python 3.12 and 3.13)

### Using uv (recommended)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/aviadr1/gemini-imagen.git
cd gemini-imagen

# Lock dependencies and sync (installs everything)
uv lock
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install
```

### Using pip (alternative)

```bash
# Clone the repository
git clone https://github.com/aviadr1/gemini-imagen.git
cd gemini-imagen

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev,s3]"

# Install pre-commit hooks
pre-commit install
```

## Running Tests

### Using uv

```bash
# Run unit tests only (no API keys required)
uv run pytest tests/ -v -m "not integration"

# Run all tests including integration (requires API keys)
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ -v -m "not integration" --cov=gemini_imagen --cov-report=html

# Run specific test file
uv run pytest tests/test_gemini_image_wrapper.py -v
```

### Using make (with uv)

```bash
make test    # Runs: uv run pytest (unit tests only)
```

### Test Categories

- **Unit tests**: Mocked tests, no API keys required
- **Integration tests**: Require real API keys (`-m integration`)
  - `GOOGLE_API_KEY` - for Gemini API tests
  - `GV_AWS_*` - for S3 integration tests
  - `LANGSMITH_API_KEY` - for LangSmith tracing tests

Integration tests are automatically skipped if credentials are missing.

## Code Quality

### Linting and Formatting

```bash
# Run linter
uv run ruff check --fix src/ examples/ tests/
# Or use make:
make lint

# Format code
uv run ruff format src/ examples/ tests/
# Or use make:
make format

# Type checking
uv run mypy src/gemini_imagen --ignore-missing-imports

# Run all pre-commit hooks
uv run pre-commit run --all-files
# Or use make:
make pre-commit
```

### Code Style Guidelines

- Follow PEP 8
- Use type hints for all functions and methods
- Write clear docstrings for public APIs
- Keep functions focused and small
- Use meaningful variable names
- Prefer composition over inheritance
- Write tests for new features

### Pre-commit Hooks

The project uses pre-commit hooks that automatically:
- Fix trailing whitespace
- Fix end of files
- Check YAML/JSON/TOML syntax
- Check for large files and merge conflicts
- Run ruff linter and formatter
- Run mypy type checking

All hooks are configured to **autofix** issues where possible (not just report failures).

## Building and Publishing

### Quick Release Process

**One command to release:**
```bash
# Patch release (0.1.0 -> 0.1.1) - default
./scripts/release.sh

# Minor release (0.1.0 -> 0.2.0)
./scripts/release.sh minor

# Major release (0.1.0 -> 1.0.0)
./scripts/release.sh major

# Test on TestPyPI first
./scripts/release.sh patch --test
```

The release script automatically:
1. Bumps the version (patch/minor/major)
2. Commits the version change
3. Creates and pushes a git tag
4. Installs dependencies
5. Runs linters (ruff + mypy)
6. Runs tests
7. Builds the package
8. Verifies with twine
9. Uploads to PyPI (with confirmation)

### Manual Version Bump

```bash
# Bump version manually
uv run python scripts/bump_version.py patch  # 0.1.0 -> 0.1.1
uv run python scripts/bump_version.py minor  # 0.1.0 -> 0.2.0
uv run python scripts/bump_version.py major  # 0.1.0 -> 1.0.0
```

### Manual Build/Publish

```bash
# Build package
make build

# Publish to PyPI (requires credentials)
make publish
```

## CI/CD

This project uses GitHub Actions for continuous integration:

### CI Pipeline

Runs on every push and pull request:
- **Lint job**: Runs ruff (linter + formatter) and mypy
- **Test job**: Runs pytest with coverage on Python 3.12 and 3.13
- **Integration test job**: Only on main branch pushes, requires secrets
- **Build job**: Builds the package and checks with twine

### Pre-commit Workflow

Runs all pre-commit hooks on pull requests and pushes.

### Release Pipeline

Automatically publishes to PyPI on version tags:
- Triggered by pushing tags like `v1.0.0`
- Creates GitHub releases with artifacts

### Dependabot

Automatically updates dependencies weekly.

## Pull Request Process

1. **Create a branch** for your feature:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** and ensure:
   - Code follows existing style (checked by ruff)
   - Type hints are used (checked by mypy)
   - Docstrings are added for public APIs
   - Tests are added/updated
   - All tests pass
   - Pre-commit hooks pass

3. **Update documentation** if needed:
   - Update README.md for user-facing changes
   - Update docstrings for API changes
   - Add examples if adding new features

4. **Commit your changes**:
   - Write clear commit messages
   - Reference issue numbers if applicable
   - Pre-commit hooks will run automatically

5. **Push to your fork** and submit a pull request:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Wait for review** and address any feedback

### Pull Request Checklist

- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] Code formatted with ruff
- [ ] Type hints added
- [ ] Pre-commit hooks passing
- [ ] No breaking changes (or documented in CHANGELOG)

## Reporting Bugs

Please use [GitHub Issues](https://github.com/aviadr1/gemini-imagen/issues) to report bugs. Include:

- **Clear description** of the issue
- **Steps to reproduce** the problem
- **Expected behavior** vs **actual behavior**
- **Environment details**:
  - Python version
  - OS and version
  - gemini-imagen version
  - Relevant dependency versions
- **Error messages** or stack traces
- **Sample code** to reproduce (if applicable)

## Feature Requests

Feature requests are welcome! Please:

- **Check existing issues** to avoid duplicates
- **Describe the use case** clearly
- **Explain why it would be valuable** to the project
- **Provide examples** of how it would be used

## Questions and Discussions

- Open a [GitHub Issue](https://github.com/aviadr1/gemini-imagen/issues) for questions
- Join discussions in existing issues
- Check the [examples/](examples/) directory for usage examples

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to gemini-imagen! 🎨
