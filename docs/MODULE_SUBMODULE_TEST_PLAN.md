# Module/Submodule Filtering - Test Plan (TDD Approach)

## Overview
This document outlines the comprehensive test plan for the module/submodule filtering feature. Following **Test-Driven Development (TDD)**, we will write tests first, then implement the functionality.

**Important Constraint:**
- **Module names ARE unique** - Each module is unique (e.g., "Loan", "Account", "Transaction")
- **Submodule names are NOT unique** - The same submodule name can exist under different modules (e.g., "New" can be under "Loan" and also under "Account")
- **Module + Submodule combination IS unique** - Each document has one unique module+submodule pair
- **Example:** "Loan" + "New" is a unique combination, and "Account" + "New" is a different unique combination (same submodule name, but different modules)

**Test Strategy:**
1. Write unit tests for database models and CRUD operations
2. Write integration tests for API endpoints
3. Write integration tests for RAG pipeline filtering
4. Write end-to-end tests for UI workflows
5. Implement functionality to make tests pass

---

## Test Structure

```
src/tests/
├── unit/
│   ├── test_document_metadata.py          # Unit tests for DocumentMetadata model
│   └── test_module_crud.py                # Unit tests for CRUD operations
├── integration/
│   ├── test_module_api_endpoints.py       # API endpoint tests
│   ├── test_module_filtering_rag.py       # RAG pipeline filtering tests
│   └── test_module_ui_workflows.py       # UI workflow tests
└── conftest.py                            # Shared fixtures
```

---

## Phase 1: Unit Tests

### 1.1 DocumentMetadata Model Tests (`src/tests/unit/test_document_metadata.py`)

**Test Cases:**

```python
class TestDocumentMetadataModel:
    """Unit tests for DocumentMetadata SQLAlchemy model."""
    
    def test_create_document_metadata_with_module_submodule(self):
        """Test creating document metadata with module and submodule."""
        # Arrange
        # Act
        # Assert: metadata created with module="Loan", submodule="New"
    
    def test_create_document_metadata_without_module_submodule(self):
        """Test creating document metadata without module/submodule (backward compatible)."""
        # Arrange
        # Act
        # Assert: metadata created with module=None, submodule=None
    
    def test_document_metadata_unique_file_path(self):
        """Test that file_path must be unique."""
        # Arrange: Create metadata with file_path="/path/to/doc.pdf"
        # Act: Try to create another with same file_path
        # Assert: Raises IntegrityError
    
    def test_document_metadata_foreign_key_user(self):
        """Test foreign key relationship with User."""
        # Arrange: Create user
        # Act: Create metadata with uploaded_by=user.id
        # Assert: Relationship works, can access metadata.user
    
    def test_document_metadata_module_submodule_can_be_null(self):
        """Test that module and submodule can be NULL (backward compatible)."""
        # Arrange
        # Act: Create metadata with module=None, submodule=None
        # Assert: No error, both fields are NULL
```

**Expected Test Count:** 5 tests

---

### 1.2 CRUD Operations Tests (`src/tests/unit/test_module_crud.py`)

**Test Cases:**

```python
class TestModuleCRUD:
    """Unit tests for module/submodule CRUD operations."""
    
    def test_create_document_metadata(self):
        """Test creating document metadata record."""
        # Arrange: filename, file_path, module, submodule
        # Act: create_document_metadata(...)
        # Assert: Record created in database with correct values
    
    def test_get_document_metadata_by_file_path(self):
        """Test retrieving document metadata by file path."""
        # Arrange: Create metadata with file_path="/path/to/doc.pdf"
        # Act: get_document_metadata(db, "/path/to/doc.pdf")
        # Assert: Returns correct metadata object
    
    def test_get_document_metadata_not_found(self):
        """Test retrieving non-existent document metadata."""
        # Arrange
        # Act: get_document_metadata(db, "/nonexistent/path.pdf")
        # Assert: Returns None
    
    def test_get_distinct_modules(self):
        """Test getting all distinct module names (modules are unique)."""
        # Arrange: Create 3 documents:
        #   - doc1: module="Loan", submodule="New"
        #   - doc2: module="Account", submodule="Create"
        #   - doc3: module="Loan", submodule="Existing" (same module name, different submodule)
        # Act: get_distinct_modules(db)
        # Assert: Returns ["Account", "Loan"] (sorted, unique module names - modules are unique)
    
    def test_get_distinct_modules_empty(self):
        """Test getting distinct modules when none exist."""
        # Arrange: No documents with modules
        # Act: get_distinct_modules(db)
        # Assert: Returns empty list []
    
    def test_get_distinct_submodules_all(self):
        """Test getting all distinct submodule names (submodules are NOT unique - same name can exist under different modules)."""
        # Arrange: Create documents:
        #   - doc1: module="Loan", submodule="New"
        #   - doc2: module="Account", submodule="New" (same submodule name "New", but different module)
        #   - doc3: module="Loan", submodule="Existing"
        # Act: get_distinct_submodules(db)
        # Assert: Returns ["Existing", "New"] (sorted, unique submodule names - "New" appears once even though it exists under both "Loan" and "Account")
    
    def test_get_distinct_submodules_filtered_by_module(self):
        """Test getting submodules filtered by module (module+submodule combinations are unique)."""
        # Arrange:
        #   - doc1: module="Loan", submodule="New"
        #   - doc2: module="Loan", submodule="Existing"
        #   - doc3: module="Account", submodule="New" (same submodule name, but different module)
        # Act: get_distinct_submodules(db, module="Loan")
        # Assert: Returns ["Existing", "New"] (only submodules for "Loan" module, not "Account" + "New")
    
    def test_update_document_metadata_module(self):
        """Test updating module for a document."""
        # Arrange: Create metadata with module="Loan"
        # Act: update_document_metadata(db, file_path, module="Account")
        # Assert: Module updated to "Account"
    
    def test_update_document_metadata_submodule(self):
        """Test updating submodule for a document."""
        # Arrange: Create metadata with submodule="New"
        # Act: update_document_metadata(db, file_path, submodule="Existing")
        # Assert: Submodule updated to "Existing"
    
    def test_update_document_metadata_both(self):
        """Test updating both module and submodule."""
        # Arrange: Create metadata
        # Act: update_document_metadata(db, file_path, module="Loan", submodule="New")
        # Assert: Both updated
    
    def test_update_document_metadata_not_found(self):
        """Test updating non-existent document metadata."""
        # Arrange
        # Act: update_document_metadata(db, "/nonexistent/path.pdf", module="Loan")
        # Assert: Returns None
```

**Expected Test Count:** 11 tests

---

## Phase 2: Integration Tests - API Endpoints

### 2.1 Document Upload API Tests (`src/tests/integration/test_module_api_endpoints.py`)

**Test Cases:**

```python
class TestDocumentUploadWithModule:
    """Integration tests for document upload with module/submodule."""
    
    def test_upload_document_with_module_submodule(self):
        """Test uploading document with module and submodule."""
        # Arrange: Create user, get auth token, prepare PDF file
        # Act: POST /api/documents/upload with module="Loan", submodule="New"
        # Assert:
        #   - Response status 200
        #   - Document metadata created in database
        #   - module="Loan", submodule="New" stored correctly
    
    def test_upload_document_without_module_submodule(self):
        """Test uploading document without module/submodule (backward compatible)."""
        # Arrange: Create user, get auth token, prepare PDF file
        # Act: POST /api/documents/upload (no module/submodule params)
        # Assert:
        #   - Response status 200
        #   - Document uploaded successfully
        #   - module=None, submodule=None in metadata
    
    def test_upload_document_with_module_only(self):
        """Test uploading document with module but no submodule."""
        # Arrange
        # Act: POST /api/documents/upload with module="Loan" only
        # Assert:
        #   - Response status 200
        #   - module="Loan", submodule=None stored
    
    def test_upload_document_module_stored_in_qdrant_metadata(self):
        """Test that module/submodule are stored in Qdrant chunk metadata."""
        # Arrange: Upload document with module="Loan", submodule="New"
        # Act: Query Qdrant directly for chunks
        # Assert: Chunks have metadata["module"]="Loan", metadata["submodule"]="New"
```

**Expected Test Count:** 4 tests

---

### 2.2 Query API Tests (`src/tests/integration/test_module_api_endpoints.py`)

**Test Cases:**

```python
class TestQueryWithModuleFilter:
    """Integration tests for query endpoint with module/submodule filtering."""
    
    def test_query_without_filters(self):
        """Test query without module/submodule filters (backward compatible)."""
        # Arrange: Index documents, create user, get auth token
        # Act: POST /api/query with question only (no filters)
        # Assert:
        #   - Response status 200
        #   - Answer returned
        #   - Searches all documents (no filtering)
    
    def test_query_with_module_filter(self):
        """Test query filtered by module (module is unique, but can have multiple documents with different submodules)."""
        # Arrange:
        #   - Index document1.pdf with module="Loan", submodule="New"
        #   - Index document2.pdf with module="Loan", submodule="Existing" (same unique module "Loan", different submodule)
        #   - Index document3.pdf with module="Account", submodule="Create" (different unique module)
        #   - Create user, get auth token
        # Act: POST /api/query with question="test" + module="Loan"
        # Assert:
        #   - Response status 200
        #   - Answer returned
        #   - Sources include document1.pdf AND document2.pdf (both have unique module="Loan", different submodules)
        #   - Sources do NOT include document3.pdf (different unique module="Account")
    
    def test_query_with_submodule_filter(self):
        """Test query filtered by module+submodule combination (unique combination - submodule name not unique, but combination is)."""
        # Arrange:
        #   - Index document1.pdf with module="Loan", submodule="New"
        #   - Index document2.pdf with module="Loan", submodule="Existing"
        #   - Index document3.pdf with module="Account", submodule="New" (same submodule name "New", but different unique module)
        # Act: POST /api/query with question="test" + module="Loan" + submodule="New"
        # Assert:
        #   - Response status 200
        #   - Sources only include document1.pdf (unique combination: module="Loan" + submodule="New")
        #   - Sources do NOT include document2.pdf (different submodule: "Existing")
        #   - Sources do NOT include document3.pdf (different unique module: "Account", even though submodule="New" is the same name)
    
    def test_query_with_invalid_module_filter(self):
        """Test query with non-existent module filter."""
        # Arrange: Index documents, create user
        # Act: POST /api/query with module="NonExistent"
        # Assert:
        #   - Response status 200 (filter just returns no results)
        #   - Answer may be from general knowledge fallback
    
    def test_query_module_filter_improves_performance(self):
        """Test that module filtering reduces search space (performance test)."""
        # Arrange:
        #   - Index 100 documents, 10 with module="Loan"
        # Act: Query with module="Loan" vs without filter
        # Assert: Filtered query is faster (or at least same speed)
```

**Expected Test Count:** 5 tests

---

### 2.3 Module/Submodule List API Tests (`src/tests/integration/test_module_api_endpoints.py`)

**Test Cases:**

```python
class TestModuleListAPI:
    """Integration tests for module/submodule list endpoints."""
    
    def test_get_modules_list(self):
        """Test GET /api/modules endpoint."""
        # Arrange:
        #   - Create documents with modules: "Loan", "Account", "Loan"
        #   - Create user, get auth token
        # Act: GET /api/modules
        # Assert:
        #   - Response status 200
        #   - Returns {"modules": ["Account", "Loan"]} (sorted, unique)
    
    def test_get_modules_list_empty(self):
        """Test GET /api/modules when no modules exist."""
        # Arrange: No documents with modules
        # Act: GET /api/modules
        # Assert: Returns {"modules": []}
    
    def test_get_submodules_list_all(self):
        """Test GET /api/submodules endpoint (all submodules)."""
        # Arrange: Create documents with various submodules
        # Act: GET /api/submodules
        # Assert: Returns all distinct submodules
    
    def test_get_submodules_list_filtered_by_module(self):
        """Test GET /api/submodules?module=Loan endpoint."""
        # Arrange:
        #   - Document with module="Loan", submodule="New"
        #   - Document with module="Account", submodule="New"
        # Act: GET /api/submodules?module=Loan
        # Assert: Returns only submodules for "Loan" module
```

**Expected Test Count:** 4 tests

---

### 2.4 Admin Module Management API Tests (`src/tests/integration/test_module_api_endpoints.py`)

**Test Cases:**

```python
class TestAdminModuleManagement:
    """Integration tests for admin module/submodule management endpoints."""
    
    def test_get_admin_modules_with_stats(self):
        """Test GET /api/admin/modules endpoint (modules are unique, aggregated by unique module)."""
        # Arrange:
        #   - Create admin user
        #   - Create documents:
        #     * doc1: module="Loan", submodule="New"
        #     * doc2: module="Loan", submodule="Existing" (same unique module "Loan", different submodule)
        #     * doc3: module="Account", submodule="New" (different unique module, same submodule name "New")
        # Act: GET /api/admin/modules (with admin auth)
        # Assert:
        #   - Response status 200
        #   - Returns unique modules with aggregated stats:
        #     * "Loan" (unique module): document_count=2, submodule_count=2 (has "New" and "Existing")
        #     * "Account" (unique module): document_count=1, submodule_count=1 (has "New")
    
    def test_get_admin_modules_requires_permission(self):
        """Test that GET /api/admin/modules requires admin permission."""
        # Arrange: Create regular user (not admin)
        # Act: GET /api/admin/modules (with regular user auth)
        # Assert: Response status 403 (Forbidden)
    
    def test_get_admin_documents_list(self):
        """Test GET /api/admin/documents endpoint."""
        # Arrange: Create documents with module/submodule
        # Act: GET /api/admin/documents (with admin auth)
        # Assert:
        #   - Response status 200
        #   - Returns list of documents with metadata
    
    def test_get_admin_documents_filtered_by_module(self):
        """Test GET /api/admin/documents?module=Loan endpoint (module is unique)."""
        # Arrange: Create documents:
        #   - doc1: module="Loan", submodule="New"
        #   - doc2: module="Loan", submodule="Existing" (same unique module "Loan", different submodule)
        #   - doc3: module="Account", submodule="New" (different unique module)
        # Act: GET /api/admin/documents?module=Loan
        # Assert: Returns doc1 AND doc2 (both have unique module="Loan"), not doc3 (different unique module="Account")
    
    def test_update_document_metadata(self):
        """Test PUT /api/admin/documents/{id}/metadata endpoint."""
        # Arrange:
        #   - Create document with module="Loan"
        #   - Create admin user
        # Act: PUT /api/admin/documents/{id}/metadata with module="Account"
        # Assert:
        #   - Response status 200
        #   - Document metadata updated in database
```

**Expected Test Count:** 5 tests

---

## Phase 3: Integration Tests - RAG Pipeline

### 3.1 RAG Pipeline Filtering Tests (`src/tests/integration/test_module_filtering_rag.py`)

**Test Cases:**

```python
class TestRAGPipelineModuleFiltering:
    """Integration tests for RAG pipeline with module/submodule filtering."""
    
    def test_index_document_with_module_submodule(self):
        """Test indexing document with module and submodule (unique combination)."""
        # Arrange: Create pipeline, prepare document
        # Act: pipeline.index_documents(file_paths=[path], module="Loan", submodule="New")
        # Assert:
        #   - Document indexed successfully
        #   - Chunks in Qdrant have metadata["module"]="Loan"
        #   - Chunks in Qdrant have metadata["submodule"]="New"
        #   - This creates a unique module+submodule combination for this document
    
    def test_index_document_without_module_submodule(self):
        """Test indexing document without module/submodule (backward compatible)."""
        # Arrange: Create pipeline, prepare document
        # Act: pipeline.index_documents(file_paths=[path])  # No module/submodule
        # Assert:
        #   - Document indexed successfully
        #   - Chunks in Qdrant don't have module/submodule in metadata
    
    def test_query_with_module_filter(self):
        """Test querying with module filter (module is unique, but can have multiple documents with different submodules)."""
        # Arrange:
        #   - Index doc1.pdf with module="Loan", submodule="New"
        #   - Index doc2.pdf with module="Loan", submodule="Existing" (same unique module "Loan", different submodule)
        #   - Index doc3.pdf with module="Account", submodule="Create" (different unique module)
        #   - Create query engine
        # Act: pipeline.query("test question", module="Loan")
        # Assert:
        #   - Returns answer
        #   - Sources include doc1.pdf AND doc2.pdf (both have unique module="Loan", different submodules)
        #   - Sources do NOT include doc3.pdf (different unique module="Account")
    
    def test_query_with_submodule_filter(self):
        """Test querying with module+submodule filter (unique combination - submodule name not unique, but combination is)."""
        # Arrange:
        #   - Index doc1.pdf with module="Loan", submodule="New"
        #   - Index doc2.pdf with module="Loan", submodule="Existing"
        #   - Index doc3.pdf with module="Account", submodule="New" (same submodule name "New", but different unique module)
        # Act: pipeline.query("test", module="Loan", submodule="New")
        # Assert:
        #   - Sources only include doc1.pdf (unique combination: module="Loan" + submodule="New")
        #   - Sources do NOT include doc2.pdf (different submodule: "Existing")
        #   - Sources do NOT include doc3.pdf (different unique module: "Account", even though submodule="New" is the same name)
    
    def test_query_without_filters_searches_all(self):
        """Test that query without filters searches all documents (ignores module/submodule)."""
        # Arrange:
        #   - Index doc1.pdf with module="Loan", submodule="New"
        #   - Index doc2.pdf with module="Account", submodule="Create"
        #   - Index doc3.pdf with module="Loan", submodule="Existing"
        # Act: pipeline.query("test")  # No filters
        # Assert:
        #   - Searches all documents (no filtering)
        #   - Sources can come from any document regardless of module/submodule
```

**Expected Test Count:** 5 tests

---

## Phase 4: End-to-End UI Tests

### 4.1 UI Workflow Tests (`src/tests/integration/test_module_ui_workflows.py`)

**Test Cases:**

```python
class TestModuleUIWorkflows:
    """End-to-end tests for module/submodule UI workflows."""
    
    def test_upload_document_with_module_submodule_ui(self):
        """Test uploading document via UI with module/submodule selection (unique combination)."""
        # Arrange: Start server, login as user
        # Act:
        #   1. Navigate to Documents tab
        #   2. Select module="Loan" from dropdown
        #   3. Select submodule="New" from dropdown (creates unique combination)
        #   4. Upload PDF file
        # Assert:
        #   - Upload successful
        #   - Document appears in list with module="Loan", submodule="New" shown
        #   - This document has unique module+submodule combination
    
    def test_query_with_module_filter_ui(self):
        """Test querying via UI with module filter (module is unique, but can have multiple documents)."""
        # Arrange:
        #   - Index doc1.pdf with module="Loan", submodule="New"
        #   - Index doc2.pdf with module="Loan", submodule="Existing" (same unique module "Loan", different submodule)
        #   - Index doc3.pdf with module="Account", submodule="Create" (different unique module)
        #   - Login as user
        # Act:
        #   1. Navigate to Text Query tab
        #   2. Select module="Loan" from filter dropdown (no submodule selected)
        #   3. Enter question and submit
        # Assert:
        #   - Answer returned
        #   - Sources include doc1.pdf AND doc2.pdf (both have unique module="Loan", different submodules)
        #   - Sources do NOT include doc3.pdf (different unique module="Account")
    
    def test_admin_modules_page_loads(self):
        """Test that admin modules page loads correctly."""
        # Arrange: Login as admin user
        # Act: Navigate to /admin/modules
        # Assert:
        #   - Page loads successfully
        #   - Table displays modules and submodules
    
    def test_admin_create_module_ui(self):
        """Test creating module via admin UI."""
        # Arrange: Login as admin
        # Act:
        #   1. Navigate to /admin/modules
        #   2. Click "Add Module"
        #   3. Enter module name="Loan"
        #   4. Submit
        # Assert:
        #   - Module appears in table
        #   - Can be selected in upload/query dropdowns
    
    def test_admin_create_submodule_ui(self):
        """Test creating submodule via admin UI (submodule name not unique, but module+submodule combination is)."""
        # Arrange: Login as admin, documents exist with unique module="Loan"
        # Act:
        #   1. Navigate to /admin/modules
        #   2. Click "Add Submodule"
        #   3. Select unique module="Loan"
        #   4. Enter submodule name="New" (this name can also exist under other unique modules)
        #   5. Submit (this creates a document assignment, not a standalone submodule)
        # Assert:
        #   - Submodule "New" appears under unique module "Loan" in table
        #   - Can be selected in upload/query dropdowns
        #   - Note: Submodule name "New" is NOT unique - it can also exist under other unique modules (e.g., "Account" + "New")
```

**Expected Test Count:** 5 tests

---

## Test Execution Order (TDD)

### Step 1: Write Unit Tests (Phase 1)
1. Write `test_document_metadata.py` - 5 tests
2. Write `test_module_crud.py` - 11 tests
3. **Run tests** - All should FAIL (red) - functionality not implemented yet

### Step 2: Implement Database Layer
1. Create `document_metadata` table migration
2. Add `DocumentMetadata` model
3. Implement CRUD functions
4. **Run tests** - Unit tests should PASS (green)

### Step 3: Write Integration Tests (Phase 2 & 3)
1. Write `test_module_api_endpoints.py` - 18 tests
2. Write `test_module_filtering_rag.py` - 5 tests
3. **Run tests** - All should FAIL (red)

### Step 4: Implement Backend
1. Enhance document loader
2. Enhance pipeline
3. Enhance query engine
4. Add API endpoints
5. **Run tests** - Integration tests should PASS (green)

### Step 5: Write UI Tests (Phase 4)
1. Write `test_module_ui_workflows.py` - 5 tests
2. **Run tests** - All should FAIL (red)

### Step 6: Implement Frontend
1. Add dropdowns to upload UI
2. Add filters to query UI
3. Create admin modules page
4. **Run tests** - UI tests should PASS (green)

---

## Test Coverage Goals

- **Unit Tests:** 100% coverage of CRUD operations
- **Integration Tests:** All API endpoints covered
- **RAG Pipeline Tests:** All filtering scenarios covered
- **UI Tests:** Critical user workflows covered

**Total Expected Tests:** ~44 tests

---

## Test Fixtures Needed

### Database Fixtures (`src/tests/conftest.py`)

```python
@pytest.fixture
def sample_document_metadata(db):
    """Create sample document metadata for testing."""
    # Create metadata with module="Loan", submodule="New"
    pass

@pytest.fixture
def multiple_documents_with_modules(db):
    """Create multiple documents with different modules and submodules."""
    # Create documents demonstrating:
    #   - Module "Loan" is unique (but can have multiple documents with different submodules)
    #   - Submodule "New" is NOT unique (same name can exist under different unique modules)
    #   - Each document has unique module+submodule combination
    # Documents:
    #   - doc1: module="Loan" (unique), submodule="New"
    #   - doc2: module="Loan" (same unique module), submodule="Existing" (different submodule)
    #   - doc3: module="Account" (different unique module), submodule="New" (same submodule name, but different module)
    #   - doc4: module="Account" (same unique module), submodule="Create"
    pass

@pytest.fixture
def indexed_documents_with_modules(pipeline):
    """Index documents with modules for RAG testing."""
    # Index documents with different modules
    pass
```

---

## Test Data Setup

### Test Documents
- `test_loan_new.pdf` - Module: "Loan" (unique), Submodule: "New"
- `test_loan_existing.pdf` - Module: "Loan" (same unique module), Submodule: "Existing" (different submodule)
- `test_account_new.pdf` - Module: "Account" (different unique module), Submodule: "New" (same submodule name, but different module)
- `test_account_create.pdf` - Module: "Account" (same unique module), Submodule: "Create"
- `test_no_module.pdf` - No module/submodule (backward compatibility)

**Note:** These test documents demonstrate:
- Module "Loan" is unique (but can have multiple documents with different submodules)
- Submodule "New" is NOT unique (same name can exist under different unique modules: "Loan" + "New" vs "Account" + "New")
- Each document has a unique module+submodule combination

---

## Success Criteria

✅ **Tests are successful when:**
1. All 44 tests pass
2. Test coverage > 90% for new code
3. All backward compatibility tests pass
4. All performance tests show filtering improves speed
5. All UI workflow tests pass

---

---

## Test Files Status

### ✅ Tests Written (Ready to Run)

1. **`src/tests/unit/test_document_metadata.py`** - 5 tests ✅
2. **`src/tests/unit/test_module_crud.py`** - 11 tests ✅
3. **`src/tests/integration/test_module_api_endpoints.py`** - 18 tests ✅
4. **`src/tests/integration/test_module_filtering_rag.py`** - 5 tests ✅
5. **`src/tests/integration/test_module_ui_workflows.py`** - 5 tests ✅

**Total: 44 tests written and ready to run**

### Expected Initial Status
- **All tests will FAIL initially** (red phase in TDD)
- This is expected and correct - functionality not implemented yet
- As we implement features, tests will turn green (pass)

### Running Tests
See `docs/MODULE_SUBMODULE_TEST_EXECUTION.md` for detailed test execution instructions.

---

**Document Version:** 2.0 (Tests Written)  
**Last Updated:** 2025-01-17  
**Status:** Tests Written - Ready for TDD Implementation

