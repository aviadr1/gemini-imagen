#!/bin/bash
# Release script: Build and publish to PyPI
# Usage: ./scripts/release.sh [--test]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're in the project root
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: Must run from project root${NC}"
    exit 1
fi

# Parse arguments
USE_TEST_PYPI=false
if [ "$1" == "--test" ]; then
    USE_TEST_PYPI=true
    echo -e "${YELLOW}Using TestPyPI${NC}"
fi

# Get current version
VERSION=$(grep -oP 'version = "\K[^"]+' pyproject.toml)
echo -e "${GREEN}Building version: ${VERSION}${NC}"

# Check git status
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}Warning: You have uncommitted changes${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if tag exists
if git rev-parse "v${VERSION}" >/dev/null 2>&1; then
    echo -e "${GREEN}Tag v${VERSION} exists${NC}"
else
    echo -e "${YELLOW}Warning: Tag v${VERSION} does not exist${NC}"
    read -p "Create tag now? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        git tag "v${VERSION}"
        echo -e "${GREEN}Created tag v${VERSION}${NC}"
        echo -e "${YELLOW}Don't forget to push tags: git push --tags${NC}"
    fi
fi

# Clean previous builds
echo -e "${GREEN}Cleaning previous builds...${NC}"
rm -rf dist/ build/ *.egg-info

# Run linters
echo -e "${GREEN}Running linters...${NC}"
uv run ruff check --fix src/ examples/
uv run ruff format src/ examples/
uv run mypy src/gemini_imagen --ignore-missing-imports

# Run tests
echo -e "${GREEN}Running tests...${NC}"
uv run pytest tests/ -v -m "not integration"

# Build package
echo -e "${GREEN}Building package...${NC}"
uv run python -m build

# Check package with twine
echo -e "${GREEN}Checking package with twine...${NC}"
uv run twine check dist/*

# Upload to PyPI
if [ "$USE_TEST_PYPI" = true ]; then
    echo -e "${YELLOW}Uploading to TestPyPI...${NC}"
    echo -e "${YELLOW}Note: You'll need TestPyPI credentials${NC}"
    uv run twine upload --repository testpypi dist/*
    echo -e "${GREEN}Successfully uploaded to TestPyPI!${NC}"
    echo -e "${YELLOW}Install with: pip install --index-url https://test.pypi.org/simple/ gemini-imagen==${VERSION}${NC}"
else
    echo -e "${YELLOW}Ready to upload to PyPI${NC}"
    read -p "Upload to PyPI? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${GREEN}Uploading to PyPI...${NC}"
        uv run twine upload dist/*
        echo -e "${GREEN}Successfully uploaded to PyPI!${NC}"
        echo -e "${GREEN}Install with: pip install gemini-imagen==${VERSION}${NC}"
        echo -e "${GREEN}View at: https://pypi.org/project/gemini-imagen/${VERSION}/${NC}"
    else
        echo -e "${YELLOW}Upload cancelled${NC}"
        echo -e "${YELLOW}You can upload later with: uv run twine upload dist/*${NC}"
    fi
fi
