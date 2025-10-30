# Project Instructions for Claude

## Development Environment

### Package Manager
- This project uses `uv` for Python package management
- Always use `uv run` to run Python commands in the project context
- Use `uv sync` to install dependencies (not `uv pip install`)
- Use `uv sync --extra dev --extra s3` to install with optional dependencies

### Python Version
- Requires Python >= 3.12
- The project supports both Python 3.12 and 3.13

## Code Quality Tools

### Linters and Formatters
- **Ruff**: Used for both linting and formatting
  - Run linter: `uv run ruff check --fix src/ examples/`
  - Run formatter: `uv run ruff format src/ examples/`
- **mypy**: Type checking with `--ignore-missing-imports` flag
  - Run: `uv run mypy src/gemini_imagen --ignore-missing-imports`
- **isort**: Import sorting (configured with black profile, line length 100)

### Pre-commit Hooks
- Pre-commit hooks are configured in `.pre-commit-config.yaml`
- All hooks are set to autofix issues where possible (not fail)
- Poetry check hook was removed as this project doesn't use Poetry

## CI/CD

### GitHub Actions Workflows
1. **CI Workflow** (`.github/workflows/ci.yml`):
   - Lint job: Runs ruff (linter + formatter) and mypy
   - Test job: Runs pytest with coverage on Python 3.12 and 3.13
   - Integration test job: Only on main branch pushes, requires secrets
   - Build job: Builds the package and checks with twine

2. **Pre-commit Workflow** (`.github/workflows/pre-commit.yml`):
   - Runs all pre-commit hooks on pull requests and pushes

### Linter Configuration Philosophy
- Linters should **autofix** issues instead of just reporting failures
- This improves developer experience by having tooling fix issues automatically
- Both pre-commit and CI are configured to apply fixes

## Project Structure

### Source Code
- Main package: `src/gemini_imagen/`
- Examples: `examples/`
- Tests: `tests/`

### Dependencies
- Core dependencies are defined in `pyproject.toml`
- Optional dependency groups:
  - `s3`: AWS S3 support with boto3
  - `dev`: Development tools (pytest, ruff, mypy, etc.)

## Testing

### Running Tests
- Unit tests: `uv run pytest tests/ -v`
- With coverage: `uv run pytest tests/ -v --cov=gemini_imagen --cov-report=xml --cov-report=term`
- Integration tests (requires API keys): `uv run pytest tests/ -v -m integration`
- Skip integration tests: `uv run pytest tests/ -v -m "not integration"`

### Test Configuration
- Configured in `pyproject.toml` under `[tool.pytest.ini_options]`
- Integration tests are marked with `@pytest.mark.integration`

## Common Issues

### Pydantic ConfigDict
- In Pydantic v2, `exclude_none` is not a valid parameter for `ConfigDict`
- Use `arbitrary_types_allowed=True` for allowing non-standard types like PIL Images
- Use field-level `exclude=True` for excluding specific fields

### Ruff Unsafe Fixes
- Some ruff fixes are marked as "unsafe" and require explicit opt-in
- Example: Converting `isinstance(x, (str, Path))` to `isinstance(x, str | Path)`
- Always use `--unsafe-fixes` flag in both pre-commit and CI

## Integration with External Services

### LangSmith
- LangSmith tracing is integrated for logging and monitoring
- Controlled by environment variables:
  - `LANGSMITH_API_KEY`: API key for LangSmith
  - `LANGSMITH_TRACING`: Enable/disable tracing (set to "true")
  - `LANGSMITH_PROJECT`: Project name in LangSmith

### S3 Storage
- Optional S3 support for image storage
- Requires AWS credentials in environment:
  - `GV_AWS_ACCESS_KEY_ID`
  - `GV_AWS_SECRET_ACCESS_KEY`
  - `GV_AWS_STORAGE_BUCKET_NAME`
