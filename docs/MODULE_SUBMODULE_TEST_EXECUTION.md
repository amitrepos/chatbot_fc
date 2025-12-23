# Module/Submodule Filtering - Test Execution Guide

## Overview
This document provides instructions for running the module/submodule filtering tests following the TDD (Test-Driven Development) approach.

## Test Files Created

### Unit Tests
1. **`src/tests/unit/test_document_metadata.py`** (5 tests)
   - Tests for DocumentMetadata SQLAlchemy model
   - Tests model creation, relationships, constraints

2. **`src/tests/unit/test_module_crud.py`** (11 tests)
   - Tests for CRUD operations
   - Tests distinct module/submodule queries
   - Tests update operations

### Integration Tests
3. **`src/tests/integration/test_module_api_endpoints.py`** (18 tests)
   - Document upload with module/submodule
   - Query filtering
   - Module/submodule list endpoints
   - Admin module management endpoints

4. **`src/tests/integration/test_module_filtering_rag.py`** (5 tests)
   - RAG pipeline indexing with module/submodule
   - Query filtering in RAG pipeline
   - Backward compatibility tests

5. **`src/tests/integration/test_module_ui_workflows.py`** (5 tests)
   - UI workflow tests
   - Admin UI tests

**Total: 44 tests**

---

## Running Tests

### Prerequisites
1. Database running (PostgreSQL)
2. Qdrant running (for RAG tests)
3. Ollama running (for RAG tests)
4. Virtual environment activated

### Step 1: Run All Tests (Expected: All Fail - Red Phase)

```bash
cd /var/www/chatbot_FC
source venv/bin/activate

# Run all module/submodule tests
python -m pytest src/tests/unit/test_document_metadata.py \
                 src/tests/unit/test_module_crud.py \
                 src/tests/integration/test_module_api_endpoints.py \
                 src/tests/integration/test_module_filtering_rag.py \
                 src/tests/integration/test_module_ui_workflows.py \
                 -v --tb=short
```

**Expected Result:** All tests should FAIL (red) because functionality is not implemented yet.

### Step 2: Run Unit Tests Only

```bash
# Run unit tests
python -m pytest src/tests/unit/test_document_metadata.py \
                 src/tests/unit/test_module_crud.py \
                 -v
```

### Step 3: Run Integration Tests Only

```bash
# Run API integration tests
python -m pytest src/tests/integration/test_module_api_endpoints.py -v

# Run RAG integration tests (requires Qdrant and Ollama)
python -m pytest src/tests/integration/test_module_filtering_rag.py -v

# Run UI workflow tests
python -m pytest src/tests/integration/test_module_ui_workflows.py -v
```

### Step 4: Run Specific Test Class

```bash
# Run specific test class
python -m pytest src/tests/unit/test_document_metadata.py::TestDocumentMetadataModel -v

# Run specific test
python -m pytest src/tests/unit/test_document_metadata.py::TestDocumentMetadataModel::test_create_document_metadata_with_module_submodule -v
```

---

## TDD Workflow

### Phase 1: Write Tests (✅ COMPLETED)
- All 44 tests written
- Tests are ready to run
- **Expected:** All tests FAIL (red)

### Phase 2: Implement Database Layer
1. Create `document_metadata` table migration
2. Add `DocumentMetadata` model to `src/database/models.py`
3. Implement CRUD functions in `src/database/crud.py`
4. **Run tests:** `pytest src/tests/unit/ -v`
5. **Expected:** Unit tests PASS (green)

### Phase 3: Implement RAG Pipeline
1. Enhance `src/rag/document_loader.py`
2. Enhance `src/rag/pipeline.py`
3. Enhance `src/rag/query_engine.py`
4. **Run tests:** `pytest src/tests/integration/test_module_filtering_rag.py -v`
5. **Expected:** RAG tests PASS (green)

### Phase 4: Implement API Endpoints
1. Enhance document upload endpoint
2. Enhance query endpoints
3. Add module/submodule list endpoints
4. Add admin endpoints
5. **Run tests:** `pytest src/tests/integration/test_module_api_endpoints.py -v`
6. **Expected:** API tests PASS (green)

### Phase 5: Implement Frontend UI
1. Add dropdowns to upload UI
2. Add filters to query UI
3. Create admin modules page
4. **Run tests:** `pytest src/tests/integration/test_module_ui_workflows.py -v`
5. **Expected:** UI tests PASS (green)

### Phase 6: Final Verification
1. Run all tests together
2. **Expected:** All 44 tests PASS (green)

---

## Test Coverage

After implementation, check test coverage:

```bash
python -m pytest src/tests/unit/test_document_metadata.py \
                 src/tests/unit/test_module_crud.py \
                 --cov=src/database \
                 --cov-report=term-missing
```

---

## Common Issues

### Issue: Tests fail with "Module not found"
**Solution:** Ensure virtual environment is activated and PYTHONPATH is set correctly.

### Issue: Database connection errors
**Solution:** Check `.env` file has correct `DATABASE_URL` and PostgreSQL is running.

### Issue: Qdrant connection errors (RAG tests)
**Solution:** Ensure Qdrant is running on `localhost:6333`.

### Issue: Ollama connection errors (RAG tests)
**Solution:** Ensure Ollama is running and models are downloaded.

---

## Test Status Tracking

- [ ] Phase 1: Tests written (✅ COMPLETED)
- [ ] Phase 2: Database layer implemented
- [ ] Phase 3: RAG pipeline implemented
- [ ] Phase 4: API endpoints implemented
- [ ] Phase 5: Frontend UI implemented
- [ ] Phase 6: All tests passing

---

**Last Updated:** 2025-01-17  
**Status:** Tests Written - Ready for TDD Implementation


