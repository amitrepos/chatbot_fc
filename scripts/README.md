# FlexCube AI Assistant - Scripts

This folder contains utility scripts for managing the application.

---

## 📁 Available Scripts

### 1. `seed_admin_user.py` - Create Default Admin User
**Purpose:** Creates a default admin user for initial system access.

**Default Credentials:**
- Username: `admin`
- Email: `admin@flexcube.local`
- Password: `Admin123!`

**Usage:**
```bash
cd /var/www/chatbot_FC
python3 scripts/seed_admin_user.py
```

**What it does:**
- Creates admin user if it doesn't exist
- Assigns `operational_admin` role template (all permissions)
- Displays credentials for reference

**⚠️ IMPORTANT:** Change the default password after first login!

**See also:** `docs/ADMIN_USER_SETUP.md` for detailed instructions.

---

### 2. `cleanup.sh` - Complete Removal
**Purpose:** Completely removes all application components to free server space.

**What it removes:**
- Docker containers (Qdrant)
- Docker volumes and networks
- Ollama service and AI models (~10GB)
- Python virtual environment
- Project source code and data
- Firewall port rules

**Usage:**
```bash
sudo bash cleanup.sh
```

**⚠️ WARNING:** This is destructive! All data will be permanently deleted.

---

### 2. `docker-build-push.sh` - Build & Push Docker Image
**Purpose:** Builds the application Docker image and pushes to Docker Hub.

**Prerequisites:**
1. Docker Hub account
2. Logged in: `docker login`

**Usage:**
```bash
./docker-build-push.sh <your-dockerhub-username>
```

**Example:**
```bash
./docker-build-push.sh mycompany
# Creates: mycompany/flexcube-ai-assistant:latest
```

---

### 3. `deploy-new-server.sh` - Fresh Server Deployment
**Purpose:** Deploys the complete application on a new server.

**Requirements:**
- Rocky Linux 8/9 or RHEL-based
- 32GB+ RAM
- 50GB+ disk space
- Root access

**Usage:**
```bash
sudo bash deploy-new-server.sh <dockerhub-username>
```

---

## 🐳 Docker Files

### `Dockerfile` (in project root)
Builds the FastAPI application container.

### `docker-compose.full.yml` (in project root)
Complete stack deployment:
- Qdrant (vector database)
- Ollama (LLM runtime)
- Ask-NUO (application)

---

## 🚀 Quick Reference

### Build and Push to Docker Hub
```bash
cd /var/www/chatbot_FC

# Build image
docker build -t yourusername/flexcube-ai-assistant:latest .

# Login to Docker Hub
docker login

# Push image
docker push yourusername/flexcube-ai-assistant:latest
```

### Deploy on New Server
```bash
# Pull the image
docker pull yourusername/flexcube-ai-assistant:latest

# Start with docker-compose
docker compose -f docker-compose.full.yml up -d

# Pull AI models (one-time)
docker exec ollama ollama pull mistral:7b
docker exec ollama ollama pull llava:7b
```

### Complete Cleanup
```bash
sudo bash scripts/cleanup.sh
```

---

## 📋 Checklist for Docker Hub Push

1. [ ] Test application locally
2. [ ] Update version in `docker-build-push.sh`
3. [ ] Login to Docker Hub: `docker login`
4. [ ] Run build script: `./scripts/docker-build-push.sh yourusername`
5. [ ] Verify on Docker Hub website
6. [ ] Test pull on different machine

---

## 🔒 Security Notes

- Never commit Docker Hub credentials
- Use environment variables for sensitive data
- Consider using Docker Hub access tokens instead of password
- For production, use a private registry


