.PHONY: help install install-dev sync test lint format clean build publish

help:
	@echo "Available commands:"
	@echo "  make sync         - Sync dependencies with uv (recommended)"
	@echo "  make install      - Install package with pip"
	@echo "  make install-dev  - Install package with dev dependencies (pip)"
	@echo "  make test         - Run tests with uv"
	@echo "  make lint         - Run linters with uv"
	@echo "  make format       - Format code with uv"
	@echo "  make clean        - Clean build artifacts"
	@echo "  make build        - Build package"
	@echo "  make publish      - Publish to PyPI"

sync:
	uv lock
	uv sync --all-extras
	uv run pre-commit install

install:
	pip install -e .

install-dev:
	pip install -e ".[dev,s3]"
	pre-commit install

test:
	uv run pytest tests/ -v -m "not integration" --cov=gemini_imagen --cov-report=term --cov-report=html

test-all:
	uv run pytest tests/ -v --cov=gemini_imagen --cov-report=term --cov-report=html

test-integration:
	uv run pytest tests/ -v -m integration

lint:
	uv run ruff check src/ examples/ tests/
	uv run mypy src/gemini_imagen --ignore-missing-imports

format:
	uv run ruff format src/ examples/ tests/
	uv run ruff check --fix src/ examples/ tests/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

publish: build
	python -m twine upload dist/*

pre-commit:
	uv run pre-commit run --all-files
