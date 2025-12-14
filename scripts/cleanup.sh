#!/bin/bash
# =============================================================================
# FlexCube AI Assistant - Complete Cleanup Script
# =============================================================================
# WARNING: This script will PERMANENTLY DELETE all data and configurations!
# Use only when you want to completely remove the application.
# =============================================================================
# Created: 2025-12-14
# Usage: sudo bash cleanup.sh
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${RED}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  ⚠️  WARNING: COMPLETE CLEANUP SCRIPT                          ║"
echo "║  This will PERMANENTLY DELETE:                                 ║"
echo "║  - All Docker containers and volumes                           ║"
echo "║  - Ollama and all AI models (~10GB)                           ║"
echo "║  - Project files and virtual environment                       ║"
echo "║  - All indexed documents and vector data                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

read -p "Are you ABSOLUTELY SURE you want to proceed? (type 'YES' to confirm): " confirm

if [ "$confirm" != "YES" ]; then
    echo -e "${YELLOW}Cleanup cancelled. No changes made.${NC}"
    exit 0
fi

echo ""
echo -e "${YELLOW}Starting cleanup in 5 seconds... Press Ctrl+C to cancel.${NC}"
sleep 5

# =============================================================================
# Step 1: Stop running services
# =============================================================================
echo -e "${GREEN}[1/7] Stopping running services...${NC}"

# Stop FastAPI server
echo "  - Stopping FastAPI server..."
pkill -f "uvicorn src.api.main:app" 2>/dev/null || true

# Stop Ollama service
echo "  - Stopping Ollama service..."
systemctl stop ollama 2>/dev/null || true

echo "  ✓ Services stopped"

# =============================================================================
# Step 2: Remove Docker containers and volumes
# =============================================================================
echo -e "${GREEN}[2/7] Removing Docker containers and volumes...${NC}"

# Stop and remove Qdrant container
echo "  - Removing Qdrant container..."
docker stop qdrant 2>/dev/null || true
docker rm qdrant 2>/dev/null || true

# Remove Docker volumes
echo "  - Removing Docker volumes..."
docker volume rm docker_qdrant_storage 2>/dev/null || true
docker volume rm docker_qdrant_config 2>/dev/null || true

# Remove Docker network
echo "  - Removing Docker network..."
docker network rm flexcube-net 2>/dev/null || true

# Optional: Remove all unused Docker resources
echo "  - Pruning unused Docker resources..."
docker system prune -f 2>/dev/null || true

echo "  ✓ Docker cleanup complete"

# =============================================================================
# Step 3: Remove Ollama and models
# =============================================================================
echo -e "${GREEN}[3/7] Removing Ollama and AI models (~10GB)...${NC}"

# Remove Ollama models
echo "  - Removing Mistral 7B model..."
ollama rm mistral:7b 2>/dev/null || true

echo "  - Removing LLaVA 7B model..."
ollama rm llava:7b 2>/dev/null || true

# Uninstall Ollama
echo "  - Uninstalling Ollama..."
systemctl disable ollama 2>/dev/null || true
rm -f /etc/systemd/system/ollama.service 2>/dev/null || true
rm -f /usr/local/bin/ollama 2>/dev/null || true
rm -rf /usr/share/ollama 2>/dev/null || true
rm -rf ~/.ollama 2>/dev/null || true
rm -rf /root/.ollama 2>/dev/null || true

systemctl daemon-reload 2>/dev/null || true

echo "  ✓ Ollama removed"

# =============================================================================
# Step 4: Remove Python virtual environment
# =============================================================================
echo -e "${GREEN}[4/7] Removing Python virtual environment...${NC}"

rm -rf /var/www/chatbot_FC/venv

echo "  ✓ Virtual environment removed"

# =============================================================================
# Step 5: Remove project files
# =============================================================================
echo -e "${GREEN}[5/7] Removing project files...${NC}"

# Option A: Remove everything
# rm -rf /var/www/chatbot_FC

# Option B: Keep docs but remove code and data (safer)
rm -rf /var/www/chatbot_FC/src
rm -rf /var/www/chatbot_FC/data
rm -rf /var/www/chatbot_FC/docker
rm -rf /var/www/chatbot_FC/scripts
rm -f /var/www/chatbot_FC/*.log
rm -f /var/www/chatbot_FC/*.sh
rm -f /var/www/chatbot_FC/requirements.txt
rm -f /var/www/chatbot_FC/Updates.md

echo "  ✓ Project files removed (docs folder kept for reference)"

# =============================================================================
# Step 6: Close firewall ports
# =============================================================================
echo -e "${GREEN}[6/7] Closing firewall ports...${NC}"

firewall-cmd --permanent --remove-port=8000/tcp 2>/dev/null || true
firewall-cmd --permanent --remove-port=6333/tcp 2>/dev/null || true
firewall-cmd --permanent --remove-port=6334/tcp 2>/dev/null || true
firewall-cmd --permanent --remove-port=11434/tcp 2>/dev/null || true
firewall-cmd --reload 2>/dev/null || true

echo "  ✓ Firewall ports closed"

# =============================================================================
# Step 7: Summary
# =============================================================================
echo -e "${GREEN}[7/7] Cleanup complete!${NC}"
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗"
echo "║  ✅ CLEANUP COMPLETED SUCCESSFULLY                              ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║  Removed:                                                      ║"
echo "║  • Docker containers (Qdrant)                                  ║"
echo "║  • Docker volumes and networks                                 ║"
echo "║  • Ollama service and models (~10GB freed)                    ║"
echo "║  • Python virtual environment                                  ║"
echo "║  • Project source code and data                               ║"
echo "║  • Firewall port rules                                        ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║  Kept:                                                         ║"
echo "║  • /var/www/chatbot_FC/docs/ (documentation)                  ║"
echo "║  • Docker installation                                         ║"
echo "║  • Python 3.11 installation                                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo ""
echo "To completely remove everything including docs:"
echo "  rm -rf /var/www/chatbot_FC"
echo ""
echo "To reinstall later, use the Docker image:"
echo "  docker pull yourusername/flexcube-ai-assistant:latest"

