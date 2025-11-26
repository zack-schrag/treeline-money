#!/bin/bash
set -e

# Treeline Release Script
# Automates version bumping, tagging, and GitHub release creation
# Usage: ./scripts/release.sh <version>
# Example: ./scripts/release.sh v0.2.0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if version argument provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Version argument required${NC}"
    echo "Usage: ./scripts/release.sh <version>"
    echo "Example: ./scripts/release.sh v0.2.0"
    exit 1
fi

VERSION=$1

# Remove 'v' prefix if present for pyproject.toml
VERSION_NUMBER=${VERSION#v}

# Validate version format (should be semver)
if ! [[ $VERSION_NUMBER =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo -e "${RED}Error: Invalid version format. Use semver (e.g., 0.2.0 or v0.2.0)${NC}"
    exit 1
fi

# Ensure we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo -e "${RED}Error: Must be on main branch to create a release${NC}"
    echo "Current branch: $CURRENT_BRANCH"
    exit 1
fi

# Ensure working directory is clean
if ! git diff-index --quiet HEAD --; then
    echo -e "${RED}Error: Working directory has uncommitted changes${NC}"
    echo "Please commit or stash changes before releasing"
    git status --short
    exit 1
fi

# Pull latest changes
echo -e "${YELLOW}Pulling latest changes from origin/main...${NC}"
git pull origin main

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI (gh) is not installed${NC}"
    echo "Install with: brew install gh"
    exit 1
fi

# Check if gh is authenticated
if ! gh auth status &> /dev/null; then
    echo -e "${RED}Error: GitHub CLI is not authenticated${NC}"
    echo "Run: gh auth login"
    exit 1
fi

echo -e "${GREEN}Creating release ${VERSION}${NC}"
echo ""

# Update version in pyproject.toml
echo -e "${YELLOW}Updating version in cli/pyproject.toml...${NC}"
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/^version = \".*\"/version = \"${VERSION_NUMBER}\"/" cli/pyproject.toml
else
    # Linux
    sed -i "s/^version = \".*\"/version = \"${VERSION_NUMBER}\"/" cli/pyproject.toml
fi

# Verify the change
UPDATED_VERSION=$(grep "^version = " cli/pyproject.toml | cut -d'"' -f2)
if [ "$UPDATED_VERSION" != "$VERSION_NUMBER" ]; then
    echo -e "${RED}Error: Failed to update version in pyproject.toml${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Updated version to ${VERSION_NUMBER}${NC}"

# Update uv.lock to match new version
echo -e "${YELLOW}Updating uv.lock...${NC}"
cd cli
uv lock
cd ..
echo -e "${GREEN}✓ Updated uv.lock${NC}"

# Commit version bump
echo -e "${YELLOW}Committing version bump...${NC}"
git add cli/pyproject.toml cli/uv.lock
git commit -m "Bump version to ${VERSION}"
echo -e "${GREEN}✓ Committed version bump${NC}"

# Create git tag
echo -e "${YELLOW}Creating git tag ${VERSION}...${NC}"
git tag -a "${VERSION}" -m "Release ${VERSION}"
echo -e "${GREEN}✓ Created tag ${VERSION}${NC}"

# Push commits and tags
echo -e "${YELLOW}Pushing to origin...${NC}"
git push origin main
git push origin "${VERSION}"
echo -e "${GREEN}✓ Pushed commits and tags${NC}"

# Create GitHub release
echo -e "${YELLOW}Creating GitHub release...${NC}"
gh release create "${VERSION}" \
    --title "Release ${VERSION}" \
    --generate-notes \
    --verify-tag

echo ""
echo -e "${GREEN}✓ Release ${VERSION} created successfully!${NC}"
echo ""
echo "The GitHub Actions workflow will now:"
echo "  1. Run tests"
echo "  2. Publish to PyPI"
echo "  3. Build binaries for all platforms"
echo "  4. Upload binaries to the GitHub Release"
echo ""
echo "Monitor progress at: https://github.com/zack-schrag/treeline-money/actions"
echo "View release at: https://github.com/zack-schrag/treeline-money/releases/tag/${VERSION}"
