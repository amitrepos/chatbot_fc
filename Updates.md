# Updates Log

## 2025-12-13 23:20 - Fallback to General Knowledge for Non-RAG Questions

**Timestamp:** 2025-12-13 23:20:00

**Action:** Implemented two-tier query flow: RAG first, then general knowledge fallback

**New Flow:**
1. User asks a question
2. System retrieves relevant chunks from RAG (FlexCube documents)
3. LLM tries to answer using RAG context
4. **If LLM says context is irrelevant AND question is NOT FlexCube-related:**
   - Make a second LLM call WITHOUT RAG context
   - LLM answers from its general knowledge
   - Source shows "AI Model (General Knowledge)"
5. **If question IS FlexCube-related:**
   - Use RAG answer
   - Show document sources

**Example Results:**
- "What is the capital of Germany?" → "Berlin..." (Source: AI Model)
- "What is Microfinance Account Processing?" → RAG answer (Source: OracleFlexcubeManual.pdf)

**Technical Changes:**
- Added second LLM call path in `query_engine.py`
- Direct LLM completion with general knowledge prompt
- Preserved RAG flow for FlexCube-related questions

## 2025-12-13 23:10 - Improved Source Attribution (AI Model vs RAG)

**Timestamp:** 2025-12-13 23:10:00

**Action:** Improved source attribution to distinguish between AI model knowledge and RAG sources

**Changes:**
1. **LLM Irrelevance Detection:** Added detection for phrases like:
   - "doesn't pertain", "not related to", "no information regarding"
   - "context doesn't", "provided context", "not relevant to"
   - "sorry for any confusion", "outside the scope"
   
2. **Source Clearing Logic:** 
   - If LLM explicitly says context was not useful → clear sources
   - If question is general (not FlexCube-related) → clear sources

3. **UI Update:**
   - When sources are empty → Show "AI Model (General Knowledge)" with blue styling
   - When sources have files → Show file names with green styling
   - Makes it clear where the answer came from

**Result:**
- FlexCube questions → Shows document sources (e.g., OracleFlexcubeManual.pdf)
- General questions → Shows "AI Model (General Knowledge)"

## 2025-12-13 23:00 - Fix Source Clearing for General Questions

**Timestamp:** 2025-12-13 23:00:00

**Action:** Fixed issue where sources were shown for general questions unrelated to FlexCube

**Changes:**
1. **Source List Initialization:** Sources list is now explicitly initialized as empty at the start of each query
2. **Relevance Checking:** Added similarity score checking (> 0.3 threshold) to determine if retrieved nodes are relevant
3. **FlexCube Keyword Detection:** Added logic to detect if question/answer is FlexCube-related using keywords
4. **Conditional Source Display:** Sources are only shown if:
   - Retrieved nodes have good relevance scores (> 0.3), OR
   - Question/answer contains FlexCube-related keywords
5. **Source Clearing:** General questions that don't match FlexCube content will return empty sources list

**Technical Details:**
- Sources list is cleared at the start of each `query()` call
- Similarity scores from vector retrieval are checked before extracting sources
- FlexCube keywords: flexcube, oracle, banking, account, transaction, loan, deposit, customer, error, module, screen
- If question is general and not FlexCube-related, sources are cleared even if retrieved

## 2025-12-13 22:50 - Restore Time Estimates

**Timestamp:** 2025-12-13 22:50:00

**Action:** Restored time estimate messages in loading states

**Changes:**
- Text Query: "Processing your question... This may take 20-90 seconds"
- Image Query: "Analyzing image and searching for solutions... This may take 30-120 seconds"

**Reason:** Users need to know approximate processing time to manage expectations.

## 2025-12-13 22:45 - Major UI Enhancements

**Timestamp:** 2025-12-13 22:45:00

**Action:** Complete UI overhaul with tabbed interface, image upload, and document management

**New Features:**
1. **Tabbed Interface:**
   - Text Query tab (existing functionality)
   - Image Query tab (UI ready, backend placeholder for Phase 5)
   - Documents tab (upload, list, delete)

2. **Image Upload UI:**
   - Drag & drop support
   - Image preview
   - File validation (size, type)
   - Ready for LLaVA integration in Phase 5

3. **Document Management:**
   - Upload documents with progress indicator
   - List all indexed documents with file sizes
   - Delete documents from filesystem
   - Note: Full reindex needed to remove chunks from Qdrant

4. **UI/UX Improvements:**
   - Modern gradient design
   - Responsive layout (mobile-friendly)
   - Better loading states and animations
   - Improved color scheme and spacing
   - Better error handling and user feedback

5. **New API Endpoints:**
   - POST /api/query/image (placeholder for Phase 5)
   - DELETE /api/documents/{filename}

**Technical Details:**
- Complete rewrite of HTML/CSS/JavaScript
- Added drag-and-drop functionality
- Progress bars for document uploads
- Enhanced conversation history display
- Mobile-responsive design with media queries

## 2025-12-13 22:30 - UI Title Update

**Timestamp:** 2025-12-13 22:30:00

**Action:** Changed UI title from "FlexCube AI Assistant" to "Ask-NUO"

**Changes:**
- Updated browser tab title to "Ask-NUO"
- Updated main heading to "Ask-NUO"
- API server restarted to apply changes

## 2025-12-13 22:20 - Document Re-indexing

**Timestamp:** 2025-12-13 22:20:13

**Action:** Re-indexed all documents including newly added FGL.pdf

**Results:**
- Total documents: 3 (sample_flexcube.txt, OracleFlexcubeManual.pdf, FGL.pdf)
- Total chunks indexed: 394
- Indexing time: 161.73 seconds (~2.7 minutes)
- Collection: flexcube_docs

**Source Extraction Fix:**
- Updated `src/rag/query_engine.py` to retrieve source nodes directly from retriever before querying
- This ensures sources are always extracted from the retrieved document chunks
- Sources are now displayed as filenames in the UI

## 2025-12-13 - Phase 1: Infrastructure Setup

### Step 1 - Server State Check

**Timestamp:** 2025-12-13

**Server Configuration:**
| Component | Status | Details |
|-----------|--------|---------|
| OS | ✅ Installed | Rocky Linux 8.10 (Green Obsidian) |
| Docker | ✅ Installed | Version 26.1.3 |
| Docker Compose | ✅ Installed | Version 2.27.0 |
| Ollama | ❌ Not Installed | Needs installation |
| Docker Service | ✅ Running | Active |

**Hardware Resources:**
| Resource | Value |
|----------|-------|
| Total RAM | 30GB |
| Used RAM | 15GB |
| Available RAM | 11GB |
| Swap | 31GB (unused) |
| Total Disk | 338GB |
| Used Disk | 207GB (64%) |
| Available Disk | 118GB |

**Firewall Open Ports:**
- SSH (22) - via services
- HTTP (80)
- HTTPS (443) - via services
- Additional ports: 3000, 3001, 3002, 3003, 3005, 3006, 3007, 4200, 5000, 5173, 5432, 5555, 7001, 7002, 8080, 8443, 1521, 1555, 24

**Running Docker Containers:**
- n8n (workflow automation) - running
- hello-world (test) - exited

**RAM Usage Breakdown:**
| Service/Application | Memory Usage | Percentage |
|---------------------|--------------|------------|
| Oracle WebLogic (FC_MS) | ~6.6 GB | 21.2% |
| Gradle Daemon (Java) | ~2.9 GB | 9.4% |
| Oracle Database Processes | ~6-7 GB | ~20% |
| Next.js Server | ~1.3 GB | 4.1% |
| MySQL | ~865 MB | 2.7% |
| WebLogic AdminServer | ~815 MB | 2.5% |
| n8n (Docker) | ~460 MB | 1.5% |
| System Services | ~2-3 GB | ~8% |
| **Total Used** | **~15 GB** | **~50%** |
| **Available** | **~11 GB** | **~37%** |

**Key Services Running:**
- Oracle FlexCube (WebLogic + Database) - Production banking system
- MySQL Database Server
- PostgreSQL 16
- MongoDB
- Nginx (reverse proxy)
- n8n (workflow automation)
- Next.js application
- PM2 process manager

**Memory Concern:**
- Current available RAM: 11GB
- Required for AI stack: ~16GB (Mistral 5GB + LLaVA 5GB + Qdrant 4GB + BGE 2GB)
- **Shortfall: ~5GB**

**Action Required:**
- Install Ollama
- Pull Mistral 7B model
- Pull LLaVA 7B model
- Deploy Qdrant
- **Note:** May need to optimize existing services or consider model size adjustments

---

### Step 2-5 - Infrastructure Installation Complete

**Timestamp:** 2025-12-13 21:08 UTC

**Installation Summary:**

| Component | Status | Details |
|-----------|--------|---------|
| Ollama | ✅ Installed | Version 0.13.3 |
| Mistral 7B Q4 | ✅ Downloaded | 4.4 GB, Model ID: 6577803aa9a0 |
| LLaVA 7B Q4 | ✅ Downloaded | 4.7 GB, Model ID: 8dd30f6b0cb1 |
| Qdrant | ✅ Running | Container: qdrant, Network: flexcube-net |
| Docker Network | ✅ Created | flexcube-net (bridge) |

**Service Endpoints:**
- Ollama API: `http://localhost:11434` ✅ Working
- Qdrant REST API: `http://localhost:6333` ✅ Working
- Qdrant gRPC API: `http://localhost:6334` ✅ Working

**Verification Tests:**
- ✅ Ollama API responds correctly
- ✅ Mistral model generates responses (tested)
- ✅ Qdrant health check passes
- ✅ Qdrant collections endpoint accessible
- ✅ Docker volumes created for persistence

**Current Memory Status (After Installation):**
| Resource | Value |
|----------|-------|
| Total RAM | 30GB |
| Used RAM | 19GB (up from 15GB) |
| Available RAM | 7.8GB (down from 11GB) |
| Swap Used | 586MB (previously unused) |
| Qdrant Container | 84.5MB |
| n8n Container | 432.6MB |

**Disk Usage:**
- Total: 338GB
- Used: 219GB (68%, up from 207GB/64%)
- Available: 106GB (down from 118GB)
- Models downloaded: ~9GB (Mistral 4.4GB + LLaVA 4.7GB)

**Notes:**
- Models are stored in `/usr/share/ollama/.ollama/models`
- Qdrant data persisted in Docker volume `docker_qdrant_storage`
- Swap is now being used (586MB), which is expected with the models loaded
- Memory usage increased by ~4GB after model downloads (models are loaded on-demand)
- All services are operational and ready for Phase 2 (RAG Pipeline)

---

## 2025-12-13 - Phase 2: RAG Pipeline Setup

### Step 2.1-2.4 - RAG Pipeline Complete

**Timestamp:** 2025-12-13

**Python Environment:**
| Component | Status | Details |
|-----------|--------|---------|
| Python Version | ✅ Installed | Python 3.11.13 |
| Virtual Environment | ✅ Created | `/var/www/chatbot_FC/venv` |
| Dependencies | ✅ Installed | All packages installed successfully |

**Installed Packages:**
- ✅ LlamaIndex 0.14.10 (RAG framework)
- ✅ llama-index-vector-stores-qdrant 0.9.0 (Qdrant integration)
- ✅ llama-index-embeddings-huggingface 0.6.1 (BGE embeddings)
- ✅ sentence-transformers 5.2.0 (Embedding models)
- ✅ qdrant-client 1.16.2 (Qdrant client)
- ✅ torch 2.9.1 (PyTorch for embeddings)
- ✅ transformers 4.57.3 (HuggingFace transformers)
- ✅ fastapi 0.124.4 (API framework for Phase 3)
- ✅ pypdf2 3.0.1 (PDF processing)
- ✅ python-docx 1.2.0 (DOCX processing)

**RAG Pipeline Components Created:**

1. **Document Loader** (`src/rag/document_loader.py`)
   - Supports PDF, DOCX, and TXT files
   - Automatic format detection
   - Directory loading capability

2. **Text Chunking** (`src/rag/chunking.py`)
   - Sentence-based chunking
   - Configurable chunk size (1024 chars) and overlap (200 chars)
   - Optimized for technical documentation

3. **BGE Embeddings** (`src/rag/embeddings.py`)
   - BAAI/bge-large-en-v1.5 model
   - 1024-dimensional vectors
   - CPU-optimized for no-GPU environment

4. **Qdrant Integration** (`src/rag/vector_store.py`)
   - Vector store wrapper
   - Automatic collection creation
   - Cosine similarity search

5. **Ollama LLM Integration** (`src/rag/ollama_llm.py`)
   - Custom LLM wrapper for Ollama API
   - Mistral 7B model integration
   - Streaming support

6. **Query Engine** (`src/rag/query_engine.py`)
   - Vector retrieval + LLM generation
   - Source citation
   - Top-K similarity search (K=5)

7. **Pipeline Orchestrator** (`src/rag/pipeline.py`)
   - Complete RAG workflow
   - Document indexing
   - Query processing

**Project Structure:**
```
/var/www/chatbot_FC/
├── venv/                    # Python virtual environment
├── src/
│   ├── rag/                 # RAG pipeline modules
│   │   ├── __init__.py
│   │   ├── embeddings.py
│   │   ├── document_loader.py
│   │   ├── chunking.py
│   │   ├── vector_store.py
│   │   ├── ollama_llm.py
│   │   ├── query_engine.py
│   │   └── pipeline.py
│   ├── api/                 # API layer (Phase 3)
│   ├── utils/               # Utilities
│   └── test_rag.py          # Test script
├── data/
│   └── documents/           # FlexCube documents directory
├── docker/
│   └── docker-compose.yml    # Qdrant configuration
├── requirements.txt         # Python dependencies
└── .gitignore              # Git ignore rules
```

**Testing:**
- ✅ Test script created: `src/test_rag.py`
- ✅ **RAG Pipeline Tested and Verified** (2025-12-13 21:30 UTC)
- ✅ All 4 test queries passed successfully
- ✅ Document indexing working (332 chunks indexed)
- ✅ Vector retrieval working (Qdrant queries successful)
- ✅ LLM generation working (Mistral via Ollama responding)
- ✅ Source citation working

**Test Results:**
1. ✅ "What is FlexCube?" - Answered correctly
2. ✅ "How do I handle ERR_ACC_NOT_FOUND error?" - Answered with solution
3. ✅ "What types of accounts does FlexCube support?" - Listed account types
4. ✅ "How are transactions processed?" - Provided detailed explanation

**Performance Notes:**
- Query response time: ~20-90 seconds (CPU inference, expected)
- Embedding generation: Fast (~1-2 seconds)
- Vector search: Very fast (~100ms)
- LLM generation: Slower (~20-90 seconds, CPU-only)

**Next Steps:**
- Add FlexCube PDF/DOCX documents to `/var/www/chatbot_FC/data/documents/`
- Run test script: `source venv/bin/activate && python src/test_rag.py`
- Proceed to Phase 3: API Layer (FastAPI endpoints)

---

## 2025-01-27 - Next Steps Analysis

**Timestamp:** 2025-01-27

**Action:** Analyzed PROJECT_SPEC.md to identify logical next steps that don't disturb Phase I infrastructure work.

**Analysis Document Created:**
- ✅ Created `/var/www/chatbot_FC/docs/NEXT_STEPS_ANALYSIS.md`
- Comprehensive analysis of next steps based on PROJECT_SPEC.md requirements
- Identified safe-to-implement features (no infrastructure changes)

**Key Findings:**

1. **Phase I Status:** ✅ COMPLETE (all infrastructure installed and working)

2. **Critical Missing Feature:** Screenshot/Image Query Support (Phase 5)
   - Explicitly required in PROJECT_SPEC.md
   - "Users often screenshot errors rather than typing them"
   - LLaVA model already installed (ready to use)

3. **Safe Next Steps (No Infrastructure Changes):**
   - Complete Phase 3 missing endpoints (reindex, delete)
   - Implement Phase 5 vision support (screenshot queries)
   - Add performance monitoring
   - Improve error handling and documentation

4. **Recommended Implementation Order:**
   - Option A: Complete Phase 3 first (conservative, 3-5 hours)
   - Option B: Jump to Phase 5 (aggressive, 5-8 hours) ⭐ RECOMMENDED
   - Option C: Parallel work (efficient, 4-6 hours)

**Next Action:** Review NEXT_STEPS_ANALYSIS.md for detailed recommendations.

