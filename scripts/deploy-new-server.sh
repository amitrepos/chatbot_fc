#!/bin/bash
# =============================================================================
# FlexCube AI Assistant - New Server Deployment Script
# =============================================================================
# This script deploys the complete application on a fresh server.
# 
# Requirements:
#   - Rocky Linux 8/9 or similar RHEL-based distro
#   - Minimum 32GB RAM
#   - At least 50GB disk space
#   - Root or sudo access
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/yourrepo/deploy.sh | sudo bash
#   OR
#   sudo bash deploy-new-server.sh <dockerhub-username>
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration - Change these as needed
DOCKER_USERNAME="${1:-yourusername}"  # Your Docker Hub username
PROJECT_DIR="/var/www/chatbot_FC"
IMAGE_NAME="${DOCKER_USERNAME}/flexcube-ai-assistant:latest"

echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗"
echo "║  🚀 FlexCube AI Assistant - Deployment Script                  ║"
echo "╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# =============================================================================
# Step 1: Install Docker
# =============================================================================
echo -e "${YELLOW}[1/6] Installing Docker...${NC}"

if ! command -v docker &> /dev/null; then
    dnf install -y dnf-utils
    dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
    dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl start docker
    systemctl enable docker
    echo -e "${GREEN}  ✓ Docker installed${NC}"
else
    echo -e "${GREEN}  ✓ Docker already installed${NC}"
fi

# =============================================================================
# Step 2: Create project directory
# =============================================================================
echo -e "${YELLOW}[2/6] Creating project directory...${NC}"

mkdir -p ${PROJECT_DIR}/data/documents
mkdir -p ${PROJECT_DIR}/logs

echo -e "${GREEN}  ✓ Directory created: ${PROJECT_DIR}${NC}"

# =============================================================================
# Step 3: Create docker-compose file
# =============================================================================
echo -e "${YELLOW}[3/6] Creating docker-compose configuration...${NC}"

cat > ${PROJECT_DIR}/docker-compose.yml << 'COMPOSE_EOF'
version: '3.8'

services:
  qdrant:
    image: qdrant/qdrant:latest
    container_name: qdrant
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_storage:/qdrant/storage
    networks:
      - flexcube-net
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - flexcube-net
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 20G

  asknuo:
    image: DOCKER_IMAGE_PLACEHOLDER
    container_name: asknuo
    ports:
      - "8000:8000"
    volumes:
      - ./data/documents:/app/data/documents
      - ./logs:/app/logs
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
    networks:
      - flexcube-net
    depends_on:
      - qdrant
      - ollama
    restart: unless-stopped

networks:
  flexcube-net:
    driver: bridge

volumes:
  qdrant_storage:
  ollama_data:
COMPOSE_EOF

# Replace placeholder with actual image name
sed -i "s|DOCKER_IMAGE_PLACEHOLDER|${IMAGE_NAME}|g" ${PROJECT_DIR}/docker-compose.yml

echo -e "${GREEN}  ✓ docker-compose.yml created${NC}"

# =============================================================================
# Step 4: Pull images and start services
# =============================================================================
echo -e "${YELLOW}[4/6] Pulling Docker images and starting services...${NC}"

cd ${PROJECT_DIR}
docker compose pull
docker compose up -d qdrant ollama

echo "  Waiting for Ollama to start..."
sleep 10

echo -e "${GREEN}  ✓ Base services started${NC}"

# =============================================================================
# Step 5: Download AI models
# =============================================================================
echo -e "${YELLOW}[5/6] Downloading AI models (this may take 10-20 minutes)...${NC}"

echo "  Downloading Mistral 7B (~4.4GB)..."
docker exec ollama ollama pull mistral:7b

echo "  Downloading LLaVA 7B (~4.7GB)..."
docker exec ollama ollama pull llava:7b

echo -e "${GREEN}  ✓ AI models downloaded${NC}"

# =============================================================================
# Step 6: Start the application
# =============================================================================
echo -e "${YELLOW}[6/6] Starting Ask-NUO application...${NC}"

docker compose up -d asknuo

echo "  Waiting for application to initialize..."
sleep 30

# Check if running
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo -e "${GREEN}  ✓ Application is running!${NC}"
else
    echo -e "${RED}  ⚠ Application may still be starting. Check logs:${NC}"
    echo "    docker logs asknuo"
fi

# =============================================================================
# Step 7: Configure firewall
# =============================================================================
echo -e "${YELLOW}[Bonus] Configuring firewall...${NC}"

firewall-cmd --permanent --add-port=8000/tcp 2>/dev/null || true
firewall-cmd --reload 2>/dev/null || true

echo -e "${GREEN}  ✓ Firewall configured${NC}"

# =============================================================================
# Summary
# =============================================================================
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗"
echo "║  ✅ DEPLOYMENT COMPLETE!                                       ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║                                                                ║"
echo "║  🌐 Access the application:                                    ║"
echo "║     http://YOUR_SERVER_IP:8000                                ║"
echo "║                                                                ║"
echo "║  📚 Upload FlexCube documents via the Documents tab           ║"
echo "║                                                                ║"
echo "║  🔧 Useful commands:                                          ║"
echo "║     View logs:    docker logs -f asknuo                       ║"
echo "║     Restart:      docker compose restart asknuo               ║"
echo "║     Stop all:     docker compose down                         ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝${NC}"


