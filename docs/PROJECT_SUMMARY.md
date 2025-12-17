# FlexCube AI Assistant (Ask-NUO) - Project Summary

**Last Updated:** 2025-12-14
**Status:** Paused - Ready to resume

---

## 🎯 What We Built

A **RAG-based AI assistant** for Oracle FlexCube banking software that:
- Answers questions from uploaded FlexCube documentation
- Analyzes screenshots of FlexCube errors using LLaVA vision model
- Falls back to LLM general knowledge for non-FlexCube questions
- Runs 100% locally (no cloud APIs) for banking data privacy

---

## ✅ Completed Features (Phases 1-5)

### Phase 1: Infrastructure ✅
- Rocky Linux server (16 vCPU, 32GB RAM)
- Docker + Docker Compose
- Ollama with Mistral 7B (text) + LLaVA 7B (vision)
- Qdrant vector database

### Phase 2: RAG Pipeline ✅
- LlamaIndex framework
- BGE-large embeddings (1024 dimensions)
- Document loaders (PDF, DOCX, TXT)
- Text chunking (500 tokens, 50 overlap)
- **Two-tier query flow:**
  1. Search RAG knowledge base first
  2. Fall back to LLM general knowledge if RAG irrelevant

### Phase 3: API Layer ✅
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/api/query` | POST | Text queries |
| `/api/query/image` | POST | Screenshot queries |
| `/api/documents` | GET | List documents |
| `/api/documents/upload` | POST | Upload & auto-index |
| `/api/documents/{filename}` | DELETE | Delete document |
| `/api/documents/reindex` | POST | Rebuild index |

### Phase 4: User Interface ✅
- Modern tabbed interface (Text / Image / Documents)
- Conversation history (localStorage)
- Document management with drag & drop
- Auto-indexing on upload
- Smart source attribution

### Phase 5: Vision Support ✅
- LLaVA integration for screenshot analysis
- Extracts: error codes, messages, screen names
- Connects extracted info to RAG pipeline

---

## 🚧 Not Yet Done (Phase 6)

### Production Hardening
- [ ] Nginx reverse proxy
- [ ] SSL/HTTPS (Let's Encrypt)
- [ ] Rate limiting
- [ ] Security (deploy user, fail2ban)
- [ ] Systemd service (auto-restart)
- [ ] Monitoring & alerts

---

## 🗂️ Key Files

```
/var/www/chatbot_FC/
├── src/
│   ├── api/main.py           # FastAPI + Web UI (1397 lines)
│   ├── rag/
│   │   ├── query_engine.py   # Two-tier query logic
│   │   ├── pipeline.py       # RAG orchestration
│   │   ├── vision.py         # LLaVA integration
│   │   ├── ollama_llm.py     # Mistral wrapper
│   │   ├── embeddings.py     # BGE embeddings
│   │   ├── vector_store.py   # Qdrant integration
│   │   ├── document_loader.py
│   │   └── chunking.py
│   └── tests/
│       └── test_query_logic.py  # 19 unit tests
├── data/documents/           # Uploaded FlexCube docs
├── docker/docker-compose.yml # Qdrant deployment
├── scripts/
│   ├── cleanup.sh            # Full removal script
│   ├── docker-build-push.sh  # Docker Hub push
│   └── deploy-new-server.sh  # Fresh deployment
├── Dockerfile                # App container
├── docker-compose.full.yml   # Complete stack
├── requirements.txt
└── start_api.sh
```

---

## 🔧 Important Technical Details

### Two-Tier Query Flow (query_engine.py)
1. Check if question contains FlexCube keywords
2. Query RAG with retrieved context
3. If LLM says context is irrelevant AND question is general:
   - Call LLM again WITHOUT RAG context
   - Return answer from general knowledge
   - Sources = [] (empty)
4. If FlexCube question: always show document sources

### Unit Tests
```bash
cd /var/www/chatbot_FC
source venv/bin/activate
python -m pytest src/tests/test_query_logic.py -v
```
**Always run after changes to query_engine.py!**

### Start Server
```bash
cd /var/www/chatbot_FC
source venv/bin/activate
nohup python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 > api.log 2>&1 &
```

### Access
- Web UI: http://65.109.226.36:8000
- API Docs: http://65.109.226.36:8000/docs

---

## 📋 Known Issues / Future Improvements

1. **Response time:** 20-120 seconds (CPU inference is slow)
2. **No auto-restart:** Server stops if system reboots
3. **No HTTPS:** Currently HTTP only
4. **Docker image:** Built but not pushed (need private repo)

---

## 🔑 Credentials & Access

- **Server IP:** 65.109.226.36
- **OS:** Rocky Linux
- **Docker Hub username:** amitrepos291 (image built, not pushed)
- **App Port:** 8000
- **Qdrant Port:** 6333
- **Ollama Port:** 11434

---

## 📝 To Resume Development

1. SSH into server
2. Check if app is running: `curl http://localhost:8000/health`
3. If not running, start with: `bash /var/www/chatbot_FC/start_api.sh`
4. Check logs: `tail -f /var/www/chatbot_FC/api.log`
5. Run tests: `python -m pytest src/tests/test_query_logic.py -v`

---

## 📚 Documentation Files

- `docs/PROJECT_SPEC.md` - Original requirements
- `docs/IMPLEMENTATION_PLAN.md` - Phase breakdown
- `docs/STATUS.md` - Current completion status
- `docs/ARCHITECTURE.md` - System architecture
- `docs/TECH_STACK.md` - Technology choices
- `Updates.md` - Change log with timestamps


