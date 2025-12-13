# FlexCube AI Assistant

An AI-powered support assistant for Oracle FlexCube Universal Banking software.

## Features

- **Text Queries**: Ask questions about FlexCube configuration, errors, workflows
- **Screenshot Support**: Upload FlexCube error screenshots for automatic analysis
- **RAG-based**: Answers grounded in your FlexCube documentation
- **Fully Local**: No data leaves your server, complete privacy

## Tech Stack

- **LLM**: Mistral 7B (text) + LLaVA 7B (vision) via Ollama
- **RAG**: LlamaIndex + Qdrant
- **API**: FastAPI
- **UI**: Open WebUI
- **Infrastructure**: Docker, Nginx, Rocky Linux

## Quick Start
```bash
# Start all services
cd /var/www/chatbot_FC/docker
docker-compose up -d

# Check status
docker-compose ps
```

## Documentation

- [Project Specification](docs/PROJECT_SPEC.md)
- [Tech Stack](docs/TECH_STACK.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)

## Directory Structure
```
/var/www/chatbot_FC/
├── .cursorrules          # AI coding assistant instructions
├── README.md             # This file
├── docs/                 # Documentation
├── docker/               # Docker configurations
├── src/                  # Application source code
└── data/documents/       # FlexCube PDFs and manuals
```

## Server Details

- **IP**: 65.109.226.36
- **OS**: Rocky Linux
- **RAM**: 32GB
- **vCPU**: 16

## License

Private - Internal Use Only
