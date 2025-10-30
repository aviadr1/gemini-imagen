#!/bin/bash
# Release script: Build and publish to PyPI
# Usage: ./scripts/release.sh [patch|minor|major] [--test]
#   Default bump type is 'patch' if not specified

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
BUMP_TYPE="patch"
USE_TEST_PYPI=false

for arg in "$@"; do
    case $arg in
        patch|minor|major)
            BUMP_TYPE="$arg"
            ;;
        --test)
            USE_TEST_PYPI=true
            ;;
        *)
            echo -e "${RED}Error: Invalid argument '$arg'${NC}"
            echo "Usage: ./scripts/release.sh [patch|minor|major] [--test]"
            exit 1
            ;;
    esac
done

if [ "$USE_TEST_PYPI" = true ]; then
    echo -e "${YELLOW}Using TestPyPI${NC}"
fi

# Get current version
OLD_VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
echo -e "${GREEN}Current version: ${OLD_VERSION}${NC}"

# Bump version
echo -e "${GREEN}Bumping ${BUMP_TYPE} version...${NC}"
uv run python scripts/bump_version.py "$BUMP_TYPE"

# Get new version
VERSION=$(grep '^version = ' pyproject.toml | cut -d'"' -f2)
echo -e "${GREEN}New version: ${VERSION}${NC}"

# Commit version bump
echo -e "${GREEN}Committing version bump...${NC}"
git add pyproject.toml
git commit -m "Bump version to ${VERSION}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Create and push tag
echo -e "${GREEN}Creating tag v${VERSION}...${NC}"
git tag "v${VERSION}"

echo -e "${GREEN}Pushing commit and tag...${NC}"
git push && git push --tags

# Ensure dependencies are installed
echo -e "${GREEN}Installing dependencies...${NC}"
uv sync --extra dev --extra s3

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
