# Contributing to gemini-imagen

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/gemini-imagen.git
   cd gemini-imagen
   ```

3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

## Development Setup

We use modern Python tooling with **uv** as the primary package manager:
- **uv** for fast dependency management (recommended)
- **pytest** for testing
- **ruff** for linting and formatting
- **mypy** for type checking

### Using uv (recommended)

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/aviadr1/gemini-imagen.git
cd gemini-imagen

# Lock and sync all dependencies
uv lock
uv sync --all-extras

# Install pre-commit hooks
uv run pre-commit install
```

### Using pip (alternative)

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev,s3]"
pre-commit install
```

## Making Changes

1. Create a new branch for your feature:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and ensure:
   - Code follows existing style
   - Type hints are used
   - Docstrings are added for public APIs
   - Tests are added/updated

3. Run tests:
   ```bash
   uv run pytest tests/ -v
   # Or use make:
   make test
   ```

4. Format and lint code:
   ```bash
   uv run ruff format src/ examples/ tests/
   uv run ruff check --fix src/ examples/ tests/
   # Or use make:
   make format
   ```

## Pull Request Process

1. Update documentation if needed
2. Add an entry to CHANGELOG.md (if exists)
3. Push to your fork and submit a pull request
4. Wait for review and address any feedback

## Code Style

- Follow PEP 8
- Use type hints
- Write clear docstrings
- Keep functions focused and small
- Use meaningful variable names

## Testing

- Add tests for new features
- Ensure existing tests pass
- Aim for high test coverage

## Reporting Bugs

Please use GitHub Issues to report bugs. Include:
- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, OS, etc.)

## Feature Requests

Feature requests are welcome! Please:
- Check if it's already been requested
- Describe the use case clearly
- Explain why it would be valuable

## Questions?

Feel free to open an issue for questions or join discussions.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
