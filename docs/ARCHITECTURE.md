# System Architecture

## High-Level Flow
```
User (Browser)
      │
      ▼
┌─────────────┐
│   Nginx     │ ← SSL termination, routing
└──────┬──────┘
       │
       ├─────────────────┐
       ▼                 ▼
┌─────────────┐   ┌─────────────┐
│ Open WebUI  │   │  FastAPI    │ ← Custom endpoints
└──────┬──────┘   └──────┬──────┘
       │                 │
       └────────┬────────┘
                ▼
       ┌─────────────────┐
       │   LlamaIndex    │ ← RAG orchestration
       └────────┬────────┘
                │
       ┌────────┴────────┐
       ▼                 ▼
┌─────────────┐   ┌─────────────┐
│   Qdrant    │   │   Ollama    │
│ (Vector DB) │   │ (LLM/Vision)│
└─────────────┘   └─────────────┘
```

## Data Flow - Text Query

1. User types question in Open WebUI
2. Request goes to FastAPI
3. LlamaIndex embeds query using BGE-large
4. Qdrant searches for relevant document chunks
5. Retrieved chunks + query sent to Mistral via Ollama
6. Mistral generates answer
7. Response returned to user with sources

## Data Flow - Screenshot Query

1. User uploads screenshot in Open WebUI
2. Image sent to LLaVA via Ollama
3. LLaVA extracts: screen name, error code, error message
4. Extracted text becomes the query
5. Same RAG flow as text query
6. Response returned to user

## Port Assignments

| Service | Internal Port | External Access |
|---------|---------------|-----------------|
| Nginx | 80, 443 | Yes (public) |
| Open WebUI | 3000 | Via Nginx |
| FastAPI | 8000 | Via Nginx |
| Ollama | 11434 | Internal only |
| Qdrant | 6333 | Internal only |

## Docker Network

All services run in a shared Docker network called `flexcube-net`.
Services communicate using container names as hostnames.
