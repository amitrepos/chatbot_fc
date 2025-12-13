# Tech Stack Specification

## Infrastructure

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Server OS | Rocky Linux | 9.x | Base operating system |
| Containerization | Docker | Latest | Service isolation |
| Orchestration | Docker Compose | Latest | Multi-container management |
| Reverse Proxy | Nginx | Latest | SSL, routing, security |
| SSL | Let's Encrypt | - | HTTPS certificates |

## AI/ML Components

| Component | Technology | Version | Memory |
|-----------|------------|---------|--------|
| LLM Runtime | Ollama | Latest | - |
| Text Model | Mistral 7B Q4 | - | ~5GB |
| Vision Model | LLaVA 7B Q4 | - | ~5GB |
| Embeddings | BGE-large-en-v1.5 | - | ~2GB |
| Vector DB | Qdrant | Latest | ~4GB |
| RAG Framework | LlamaIndex | Latest | - |

## Application Layer

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Backend API | FastAPI | Latest | REST endpoints |
| User Interface | Open WebUI | Latest | Chat interface |
| Python | Python | 3.11+ | Runtime |

## Memory Budget (32GB Total)

| Component | Allocation |
|-----------|------------|
| OS + Services | 2GB |
| Mistral 7B Q4 | 5GB |
| LLaVA 7B Q4 | 5GB |
| Qdrant | 4GB |
| BGE-large | 2GB |
| Applications | 2GB |
| Buffer | 12GB |
