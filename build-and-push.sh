#!/bin/bash
# Wingman - Build and Push Docker Image Script

set -e

echo "🚀 Wingman Docker Image Build Script"
echo "======================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="ghcr.io/treestandk/wingman"
TAG="${1:-latest}"
FULL_IMAGE="${IMAGE_NAME}:${TAG}"

echo ""
echo "Building: ${FULL_IMAGE}"
echo ""

# Build the image
echo "📦 Building Docker image..."
docker build -t "${FULL_IMAGE}" .

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Build successful!${NC}"
else
    echo -e "${RED}✗ Build failed!${NC}"
    exit 1
fi

echo ""
echo "🏷️  Image tagged as: ${FULL_IMAGE}"
echo ""

# Ask if user wants to push
read -p "Do you want to push to GitHub Container Registry? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "🔐 Logging in to GitHub Container Registry..."
    echo "   You'll need a GitHub Personal Access Token with 'write:packages' permission"
    echo ""

    read -p "Enter GitHub username: " GITHUB_USERNAME
    read -sp "Enter GitHub Personal Access Token: " GITHUB_TOKEN
    echo ""

    echo "${GITHUB_TOKEN}" | docker login ghcr.io -u "${GITHUB_USERNAME}" --password-stdin

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Login successful!${NC}"

        echo ""
        echo "📤 Pushing image to GitHub Container Registry..."
        docker push "${FULL_IMAGE}"

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Push successful!${NC}"
            echo ""
            echo "🎉 Image pushed successfully!"
            echo ""
            echo "⚠️  IMPORTANT: Make the package public"
            echo "   1. Go to: https://github.com/treestandk?tab=packages"
            echo "   2. Click on 'wingman' package"
            echo "   3. Click 'Package settings'"
            echo "   4. Scroll down to 'Danger Zone'"
            echo "   5. Click 'Change visibility' → 'Public'"
            echo ""
        else
            echo -e "${RED}✗ Push failed!${NC}"
            exit 1
        fi
    else
        echo -e "${RED}✗ Login failed!${NC}"
        exit 1
    fi
else
    echo ""
    echo "ℹ️  Image built locally but not pushed to registry"
    echo ""
    echo "To use this local image in TrueNAS SCALE:"
    echo "1. Save the image: docker save ${FULL_IMAGE} | gzip > wingman.tar.gz"
    echo "2. Copy to TrueNAS: scp wingman.tar.gz root@truenas-ip:/tmp/"
    echo "3. Load on TrueNAS: docker load -i /tmp/wingman.tar.gz"
    echo ""
fi

echo ""
echo "✅ Done!"
