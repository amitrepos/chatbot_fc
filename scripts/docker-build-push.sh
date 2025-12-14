#!/bin/bash
# =============================================================================
# FlexCube AI Assistant - Docker Build and Push Script
# =============================================================================
# This script builds the Docker image and pushes it to Docker Hub.
# 
# Prerequisites:
#   1. Docker installed and running
#   2. Docker Hub account created
#   3. Logged in to Docker Hub: docker login
#
# Usage:
#   ./docker-build-push.sh <dockerhub-username>
#   Example: ./docker-build-push.sh mycompany
# =============================================================================

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if username is provided
if [ -z "$1" ]; then
    echo -e "${RED}Error: Docker Hub username required${NC}"
    echo ""
    echo "Usage: $0 <dockerhub-username>"
    echo "Example: $0 mycompany"
    exit 1
fi

DOCKER_USERNAME=$1
IMAGE_NAME="flexcube-ai-assistant"
VERSION="1.0.0"
FULL_IMAGE_NAME="${DOCKER_USERNAME}/${IMAGE_NAME}"

echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗"
echo "║  🐳 Docker Build and Push Script                               ║"
echo "╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Navigate to project directory
cd /var/www/chatbot_FC

# =============================================================================
# Step 1: Build the Docker image
# =============================================================================
echo -e "${YELLOW}[1/4] Building Docker image...${NC}"
echo "  Image: ${FULL_IMAGE_NAME}:${VERSION}"
echo ""

docker build -t ${FULL_IMAGE_NAME}:${VERSION} -t ${FULL_IMAGE_NAME}:latest .

echo -e "${GREEN}  ✓ Build complete${NC}"
echo ""

# =============================================================================
# Step 2: Test the image locally
# =============================================================================
echo -e "${YELLOW}[2/4] Testing image...${NC}"

# Quick test - just check if the image can start
docker run --rm -d --name test_asknuo -p 8001:8000 ${FULL_IMAGE_NAME}:latest
sleep 5

# Check if container is running
if docker ps | grep -q test_asknuo; then
    echo -e "${GREEN}  ✓ Container started successfully${NC}"
    docker stop test_asknuo 2>/dev/null || true
else
    echo -e "${RED}  ✗ Container failed to start${NC}"
    docker logs test_asknuo 2>/dev/null || true
    docker stop test_asknuo 2>/dev/null || true
    exit 1
fi
echo ""

# =============================================================================
# Step 3: Push to Docker Hub
# =============================================================================
echo -e "${YELLOW}[3/4] Pushing to Docker Hub...${NC}"
echo "  Pushing: ${FULL_IMAGE_NAME}:${VERSION}"
echo "  Pushing: ${FULL_IMAGE_NAME}:latest"
echo ""

# Check if logged in
if ! docker info 2>/dev/null | grep -q "Username"; then
    echo -e "${YELLOW}  Please log in to Docker Hub:${NC}"
    docker login
fi

# Push both tags
docker push ${FULL_IMAGE_NAME}:${VERSION}
docker push ${FULL_IMAGE_NAME}:latest

echo -e "${GREEN}  ✓ Push complete${NC}"
echo ""

# =============================================================================
# Step 4: Summary
# =============================================================================
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗"
echo "║  ✅ BUILD AND PUSH COMPLETED                                   ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║  Images pushed:                                                ║"
echo "║  • ${FULL_IMAGE_NAME}:${VERSION}                    "
echo "║  • ${FULL_IMAGE_NAME}:latest                        "
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║  To deploy on a new server:                                    ║"
echo "║                                                                ║"
echo "║  1. Pull the image:                                           ║"
echo "║     docker pull ${FULL_IMAGE_NAME}:latest           "
echo "║                                                                ║"
echo "║  2. Use docker-compose.full.yml to start all services         ║"
echo "║                                                                ║"
echo "║  3. Pull AI models:                                           ║"
echo "║     docker exec ollama ollama pull mistral:7b                 ║"
echo "║     docker exec ollama ollama pull llava:7b                   ║"
echo "╚════════════════════════════════════════════════════════════════╝${NC}"

