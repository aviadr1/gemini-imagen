#!/bin/bash
# Release script: Create git tag which triggers CI/CD to build and publish
# Usage: ./scripts/release.sh [patch|minor|major|VERSION]
#   Default bump type is 'patch' if not specified
#   Or specify exact version like: ./scripts/release.sh 1.2.3

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

if [ $# -gt 0 ]; then
    BUMP_TYPE="$1"
fi

# Validate bump type
if [[ ! "$BUMP_TYPE" =~ ^(patch|minor|major|[0-9]+\.[0-9]+\.[0-9]+)$ ]]; then
    echo -e "${RED}Error: Invalid argument '$BUMP_TYPE'${NC}"
    echo "Usage: ./scripts/release.sh [patch|minor|major|VERSION]"
    echo "Examples:"
    echo "  ./scripts/release.sh          # Bump patch version"
    echo "  ./scripts/release.sh minor    # Bump minor version"
    echo "  ./scripts/release.sh 1.2.3    # Set specific version"
    exit 1
fi

# Get current version from latest tag
CURRENT_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "v0.0.0")
OLD_VERSION=${CURRENT_TAG#v}  # Remove 'v' prefix
echo -e "${GREEN}Current version: ${OLD_VERSION}${NC}"

# Check git status
if [ -n "$(git status --porcelain)" ]; then
    echo -e "${RED}Error: Working directory is not clean${NC}"
    echo -e "${YELLOW}Please commit or stash your changes first${NC}"
    git status --short
    exit 1
fi

# Make sure we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${YELLOW}Warning: Not on main branch (currently on ${CURRENT_BRANCH})${NC}"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Release cancelled${NC}"
        exit 0
    fi
fi

# Pull latest changes
echo -e "${GREEN}Pulling latest changes...${NC}"
git pull

# Ensure dependencies are installed
echo -e "${GREEN}Installing dependencies...${NC}"
uv sync --extra dev --extra s3

# Run linters
echo -e "${GREEN}Running linters...${NC}"
uv run ruff check --fix --unsafe-fixes src/ examples/
uv run ruff format src/ examples/
uv run mypy src/gemini_imagen --ignore-missing-imports

# Run tests
echo -e "${GREEN}Running tests...${NC}"
uv run pytest tests/ -v -m "not integration"

# Calculate new version
if [[ "$BUMP_TYPE" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    # Explicit version specified
    VERSION="$BUMP_TYPE"
else
    # Calculate bump from current version
    IFS='.' read -r -a version_parts <<< "$OLD_VERSION"
    major="${version_parts[0]}"
    minor="${version_parts[1]}"
    patch="${version_parts[2]}"

    case $BUMP_TYPE in
        major)
            VERSION="$((major + 1)).0.0"
            ;;
        minor)
            VERSION="${major}.$((minor + 1)).0"
            ;;
        patch)
            VERSION="${major}.${minor}.$((patch + 1))"
            ;;
    esac
fi

echo -e "${GREEN}New version: ${VERSION}${NC}"

# Confirm release
read -p "Create release v${VERSION}? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Release cancelled${NC}"
    exit 0
fi

# Create and push tag (this triggers CI/CD)
echo -e "${GREEN}Creating tag v${VERSION}...${NC}"
git tag "v${VERSION}"

echo -e "${GREEN}Pushing tag...${NC}"
git push origin "v${VERSION}"

echo -e "${GREEN}✓ Release v${VERSION} created!${NC}"
echo -e "${YELLOW}The GitHub Actions workflow will now:${NC}"
echo -e "  1. Build the package"
echo -e "  2. Publish to PyPI"
echo -e "  3. Create a GitHub release"
echo -e ""
echo -e "Monitor progress at: https://github.com/aviadr1/gemini-imagen/actions"
