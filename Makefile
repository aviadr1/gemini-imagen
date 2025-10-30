.PHONY: help install install-dev test lint format clean build publish

help:
	@echo "Available commands:"
	@echo "  make install      - Install package"
	@echo "  make install-dev  - Install package with dev dependencies"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo "  make clean        - Clean build artifacts"
	@echo "  make build        - Build package"
	@echo "  make publish      - Publish to PyPI"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev,s3]"
	pre-commit install

test:
	pytest tests/ -v --cov=gemini_imagen --cov-report=term --cov-report=html

lint:
	ruff check src/ examples/ tests/
	mypy src/gemini_imagen --ignore-missing-imports

format:
	ruff format src/ examples/ tests/
	ruff check --fix src/ examples/ tests/

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
	pre-commit run --all-files
