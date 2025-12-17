# Implementation Plan

## Phase 1: Infrastructure Setup

### Step 1.1: System Preparation
- Update Rocky Linux packages
- Install Docker and Docker Compose
- Configure firewall (open ports 80, 443, 22)
- Set up project directory structure

### Step 1.2: Ollama Setup
- Install Ollama
- Pull Mistral 7B model
- Pull LLaVA 7B model
- Verify models run correctly

### Step 1.3: Qdrant Setup
- Deploy Qdrant via Docker
- Configure persistence volume
- Verify Qdrant is accessible

### Step 1.4: Verification
- Test Ollama API responses
- Test Qdrant connection
- Document baseline performance

---

## Phase 2: RAG Pipeline

### Step 2.1: Document Processing
- Set up LlamaIndex
- Configure BGE-large embeddings
- Create document loader for PDFs
- Implement text chunking strategy

### Step 2.2: Indexing
- Index sample FlexCube documents
- Store vectors in Qdrant
- Test retrieval quality

### Step 2.3: Query Pipeline
- Build query engine with LlamaIndex
- Connect to Mistral for generation
- Implement source citation

### Step 2.4: Verification
- Test with sample FlexCube questions
- Evaluate answer quality
- Tune chunking and retrieval parameters

---

## Phase 3: API Layer

### Step 3.1: FastAPI Setup
- Create FastAPI application structure
- Implement health check endpoints
- Add CORS configuration

### Step 3.2: Query Endpoints
- POST /query - text questions
- POST /query/image - screenshot questions
- GET /documents - list indexed documents

### Step 3.3: Document Management
- POST /documents/upload - add new documents
- DELETE /documents/{id} - remove documents
- POST /documents/reindex - rebuild index

---

## Phase 4: User Interface

### Step 4.1: Open WebUI Setup
- Deploy Open WebUI via Docker
- Connect to Ollama
- Configure for local-only access

### Step 4.2: Customization
- Add FlexCube branding (optional)
- Configure system prompts
- Enable file upload for screenshots

---

## Phase 5: Vision Support

### Step 5.1: Vision Pipeline
- Test LLaVA with FlexCube screenshots
- Build image preprocessing
- Create extraction prompts

### Step 5.2: Integration
- Connect vision output to RAG pipeline
- Handle mixed text+image queries

---

## Phase 6: Production Hardening

### Step 6.1: Nginx Setup
- Configure reverse proxy
- Set up SSL with Let's Encrypt
- Add rate limiting

### Step 6.2: Security
- Disable root SSH (create deploy user)
- Configure firewall rules
- Set up fail2ban

### Step 6.3: Monitoring
- Add basic health monitoring
- Set up log aggregation
- Configure alerts
