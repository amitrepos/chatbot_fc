# Module/Submodule Filtering Implementation Plan (Simplified)

## Overview
This document outlines a **simplified, minimal-change** implementation plan for adding module and submodule filtering to the FlexCube AI Assistant. This feature will allow users to:
1. Categorize documents by module and submodule during upload (denormalized storage)
2. Filter searches by module and submodule
3. View available modules/submodules from existing document data

**Key Requirements:**
- ✅ **Backward compatible** - existing functionality continues to work
- ✅ **Minimal code changes** - work with existing codebase
- ✅ **Simple denormalized approach** - no complex relationships

---

## Architecture Overview

### Current Flow
```
Document Upload → Document Loader → Chunker → Embeddings → Qdrant (with metadata)
Query → Query Engine → Qdrant Retrieval → LLM → Answer
```

### New Flow (with filtering)
```
Document Upload (with module/submodule) → Document Loader → Chunker → Embeddings → Qdrant (with module/submodule in metadata)
Query (question + module/submodule filters) → Query Engine → Qdrant Filtered Retrieval → LLM → Answer
```

**Example:**
- Question: "How to get new loans in a new branch"
- Module: "Loan" (selected from dropdown)
- Submodule: "New" (selected from dropdown)
- Result: Search question text, but only retrieve chunks from documents tagged with module="Loan" and submodule="New"

---

## Database Schema Changes

### Single New Table: `document_metadata` (Denormalized)

**Simple approach - store module/submodule as VARCHAR strings (no foreign keys):**

```sql
CREATE TABLE IF NOT EXISTS document_metadata (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(500) NOT NULL,  -- Original filename
    file_path TEXT NOT NULL UNIQUE,  -- Full path to document
    module VARCHAR(100),  -- Module name (e.g., "Loan", "Account", "Transaction")
    submodule VARCHAR(100),  -- Submodule name (e.g., "New", "Existing", "Transfer")
    uploaded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_indexed_at TIMESTAMP,
    chunk_count INTEGER DEFAULT 0,
    file_size BIGINT,  -- Size in bytes
    file_type VARCHAR(20)  -- pdf, docx, txt
);

CREATE INDEX IF NOT EXISTS idx_document_metadata_filename ON document_metadata(filename);
CREATE INDEX IF NOT EXISTS idx_document_metadata_module ON document_metadata(module);
CREATE INDEX IF NOT EXISTS idx_document_metadata_submodule ON document_metadata(submodule);
CREATE INDEX IF NOT EXISTS idx_document_metadata_module_submodule ON document_metadata(module, submodule);
CREATE INDEX IF NOT EXISTS idx_document_metadata_uploaded_by ON document_metadata(uploaded_by);
```

**Why Denormalized?**
- ✅ **Simpler** - No joins needed
- ✅ **Faster queries** - Direct filtering
- ✅ **Easier to manage** - Just update strings
- ✅ **Minimal code changes** - No complex relationships
- ✅ **Flexible** - Users can type any module/submodule name

**Note:** 
- Module and submodule are stored as simple strings
- We can get distinct modules/submodules by querying: `SELECT DISTINCT module FROM document_metadata WHERE module IS NOT NULL`
- For admin UI, we can build dropdowns from existing data
- Qdrant will store the same module/submodule strings in chunk metadata for fast filtering

---

## Backend Implementation (Minimal Changes)

### Phase 1: Database Model & CRUD (1 hour)

#### 1.1 SQLAlchemy Model (`src/database/models.py`)

Add one simple model class:

```python
class DocumentMetadata(Base):
    """
    Document metadata model for tracking document categorization.
    
    Stores module and submodule as simple strings (denormalized).
    """
    __tablename__ = "document_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500), nullable=False)
    file_path = Column(Text, unique=True, nullable=False)
    module = Column(String(100), index=True)  # Simple string, e.g., "Loan"
    submodule = Column(String(100), index=True)  # Simple string, e.g., "New"
    uploaded_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    last_indexed_at = Column(DateTime(timezone=True))
    chunk_count = Column(Integer, default=0)
    file_size = Column(BigInteger)
    file_type = Column(String(20))
    
    # Relationship
    user = relationship("User", foreign_keys=[uploaded_by])
```

#### 1.2 Simple CRUD Operations (`src/database/crud.py`)

Add minimal functions:

```python
def create_document_metadata(
    db: Session,
    filename: str,
    file_path: str,
    module: Optional[str] = None,
    submodule: Optional[str] = None,
    uploaded_by: Optional[int] = None,
    file_size: Optional[int] = None,
    file_type: Optional[str] = None
) -> DocumentMetadata:
    """Create document metadata record."""
    metadata = DocumentMetadata(
        filename=filename,
        file_path=file_path,
        module=module,
        submodule=submodule,
        uploaded_by=uploaded_by,
        file_size=file_size,
        file_type=file_type
    )
    db.add(metadata)
    db.commit()
    db.refresh(metadata)
    return metadata

def get_document_metadata(db: Session, file_path: str) -> Optional[DocumentMetadata]:
    """Get document metadata by file path."""
    return db.query(DocumentMetadata).filter(DocumentMetadata.file_path == file_path).first()

def get_distinct_modules(db: Session) -> List[str]:
    """Get all distinct module names from existing documents."""
    result = db.query(DocumentMetadata.module).filter(
        DocumentMetadata.module.isnot(None)
    ).distinct().all()
    return [row[0] for row in result if row[0]]

def get_distinct_submodules(db: Session, module: Optional[str] = None) -> List[str]:
    """Get all distinct submodule names, optionally filtered by module."""
    query = db.query(DocumentMetadata.submodule).filter(
        DocumentMetadata.submodule.isnot(None)
    )
    if module:
        query = query.filter(DocumentMetadata.module == module)
    result = query.distinct().all()
    return [row[0] for row in result if row[0]]

def update_document_metadata(
    db: Session,
    file_path: str,
    module: Optional[str] = None,
    submodule: Optional[str] = None
) -> Optional[DocumentMetadata]:
    """Update module/submodule for a document."""
    metadata = get_document_metadata(db, file_path)
    if metadata:
        if module is not None:
            metadata.module = module
        if submodule is not None:
            metadata.submodule = submodule
        db.commit()
        db.refresh(metadata)
    return metadata
```

---

### Phase 2: RAG Pipeline Integration (Minimal Changes)

#### 2.1 Document Loader Enhancement (`src/rag/document_loader.py`)

**Minimal change - just add module/submodule to metadata:**

```python
def load_file(self, file_path: str, module: Optional[str] = None, submodule: Optional[str] = None) -> List[Document]:
    """Load a document file, automatically detecting the format."""
    # ... existing code ...
    
    # After loading documents, add module/submodule to metadata
    for doc in documents:
        if module:
            doc.metadata["module"] = module
        if submodule:
            doc.metadata["submodule"] = submodule
    
    return documents
```

**Backward Compatibility:**
- If `module`/`submodule` are `None`, documents work as before

#### 2.2 Pipeline Enhancement (`src/rag/pipeline.py`)

**Minimal change - pass module/submodule to loader:**

```python
def index_documents(
    self,
    file_paths: Optional[List[str]] = None,
    directory: Optional[str] = None,
    module: Optional[str] = None,  # New: optional module
    submodule: Optional[str] = None  # New: optional submodule
) -> int:
    """Index documents into the vector store."""
    # ... existing code ...
    
    # Load documents with module/submodule
    if file_paths:
        all_documents = []
        for file_path in file_paths:
            docs = self.document_loader.load_file(file_path, module=module, submodule=submodule)
            all_documents.extend(docs)
    # ... rest of existing code ...
```

**Backward Compatibility:**
- If `module`/`submodule` are `None`, indexing works as before

#### 2.3 Query Engine Enhancement (`src/rag/query_engine.py`)

**Minimal change - add Qdrant metadata filtering:**

```python
def query(
    self, 
    question: str,
    module: Optional[str] = None,  # New: optional module filter
    submodule: Optional[str] = None  # New: optional submodule filter
) -> tuple[str, List[str]]:
    """Query the RAG system with optional module/submodule filtering."""
    
    # Build Qdrant filter if module/submodule specified
    from qdrant_client.models import Filter, FieldCondition, MatchValue
    
    filter_conditions = []
    if module is not None:
        filter_conditions.append(
            FieldCondition(key="module", match=MatchValue(value=module))
        )
    if submodule is not None:
        filter_conditions.append(
            FieldCondition(key="submodule", match=MatchValue(value=submodule))
        )
    
    # Apply filter to retriever if conditions exist
    if filter_conditions:
        qdrant_filter = Filter(must=filter_conditions)
        # Modify retriever to use filter (implementation depends on LlamaIndex version)
        # For LlamaIndex 0.9+, we can pass filter to retriever
        # For older versions, we may need to filter after retrieval
    
    # ... rest of existing query logic ...
```

**Note:** The exact implementation depends on LlamaIndex version. We'll need to check how to pass filters to the Qdrant retriever.

**Backward Compatibility:**
- If `module`/`submodule` are `None`, query searches all documents (current behavior)

---

### Phase 3: API Endpoints (Minimal Changes)

#### 3.1 Document Upload Enhancement (`src/api/main.py`)

**Modify existing `/api/documents/upload` endpoint:**

```python
@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    module: Optional[str] = Form(None),  # New: optional module (string)
    submodule: Optional[str] = Form(None),  # New: optional submodule (string)
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("upload_documents")),
    db: Session = Depends(get_db)
):
    """Upload and index a document with optional module/submodule."""
    try:
        pipeline = get_pipeline()
        
        # Save uploaded file (existing code)
        data_dir = "/var/www/chatbot_FC/data/documents"
        os.makedirs(data_dir, exist_ok=True)
        file_path = os.path.join(data_dir, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"Uploaded file: {file.filename} ({len(content)} bytes)")
        
        # Index the document with module/submodule (minimal change)
        num_chunks = pipeline.index_documents(
            file_paths=[file_path],
            module=module,  # Pass as string
            submodule=submodule  # Pass as string
        )
        
        # Store document metadata in PostgreSQL (new)
        from src.database.crud import create_document_metadata
        create_document_metadata(
            db,
            filename=file.filename,
            file_path=file_path,
            module=module,
            submodule=submodule,
            uploaded_by=current_user.id,
            chunk_count=num_chunks,
            file_size=len(content),
            file_type=file.filename.split('.')[-1].lower()
        )
        
        return {
            "status": "success",
            "filename": file.filename,
            "size": len(content),
            "chunks_indexed": num_chunks,
            "module": module,
            "submodule": submodule
        }
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**Backward Compatibility:**
- If `module`/`submodule` are not provided, document uploads work as before

#### 3.2 Query Enhancement (`src/api/main.py`)

**Modify existing `/api/query` and `/api/query/image` endpoints:**

```python
class QueryRequest(BaseModel):
    """Query request model."""
    question: str
    top_k: Optional[int] = 5
    module: Optional[str] = None  # New: optional module filter (string)
    submodule: Optional[str] = None  # New: optional submodule filter (string)

@app.post("/api/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("view_chat")),
    db: Session = Depends(get_db)
):
    """Process a text query with optional module/submodule filtering."""
    try:
        pipeline = get_pipeline()
        
        # Query with optional filters (minimal change)
        answer, sources = pipeline.query(
            question=request.question,
            module=request.module,  # Pass as string
            submodule=request.submodule  # Pass as string
        )
        
        # ... rest of existing code (create Q&A pair, etc.) ...
```

**Backward Compatibility:**
- If `module`/`submodule` are not provided, queries search all documents (current behavior)

#### 3.3 New Endpoints for Dropdowns (`src/api/main.py`)

**Add simple endpoints to get available modules/submodules:**

```python
@app.get("/api/modules")
async def get_modules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all distinct module names for dropdown."""
    from src.database.crud import get_distinct_modules
    modules = get_distinct_modules(db)
    return {"modules": sorted(modules)}

@app.get("/api/submodules")
async def get_submodules(
    module: Optional[str] = None,  # Optional: filter by module
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all distinct submodule names for dropdown, optionally filtered by module."""
    from src.database.crud import get_distinct_submodules
    submodules = get_distinct_submodules(db, module=module)
    return {"submodules": sorted(submodules)}
```

---

### Phase 4: Frontend UI Updates (Minimal Changes)

#### 4.1 Document Upload UI Enhancement

**Modify Documents Tab in main UI (`src/api/main.py` - HTML section):**

**Add two dropdowns before file upload:**

```html
<!-- Add this before the file upload area -->
<div class="query-section">
    <label><strong>Module (Optional):</strong></label>
    <select id="moduleSelect" style="width: 100%; padding: 12px; border: 2px solid #e9ecef; border-radius: 8px; font-size: 14px; margin-bottom: 10px;">
        <option value="">All Modules</option>
        <!-- Will be populated by JavaScript -->
    </select>
    
    <label><strong>Submodule (Optional):</strong></label>
    <select id="submoduleSelect" style="width: 100%; padding: 12px; border: 2px solid #e9ecef; border-radius: 8px; font-size: 14px; margin-bottom: 10px;">
        <option value="">All Submodules</option>
        <!-- Will be populated by JavaScript -->
    </select>
</div>
```

**Add JavaScript to:**
1. Load modules/submodules from API on page load
2. Update submodule dropdown when module changes
3. Include module/submodule in form data when uploading

```javascript
// Load modules for dropdown
async function loadModules() {
    try {
        const response = await fetch('/api/modules');
        const data = await response.json();
        const select = document.getElementById('moduleSelect');
        data.modules.forEach(module => {
            const option = document.createElement('option');
            option.value = module;
            option.textContent = module;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading modules:', error);
    }
}

// Load submodules when module changes
document.getElementById('moduleSelect').addEventListener('change', async function() {
    const module = this.value;
    const select = document.getElementById('submoduleSelect');
    select.innerHTML = '<option value="">All Submodules</option>';
    
    if (module) {
        try {
            const response = await fetch(`/api/submodules?module=${encodeURIComponent(module)}`);
            const data = await response.json();
            data.submodules.forEach(submodule => {
                const option = document.createElement('option');
                option.value = submodule;
                option.textContent = submodule;
                select.appendChild(option);
            });
        } catch (error) {
            console.error('Error loading submodules:', error);
        }
    }
});

// Modify uploadDocument function to include module/submodule
async function uploadDocument(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    const module = document.getElementById('moduleSelect').value;
    const submodule = document.getElementById('submoduleSelect').value;
    
    if (module) formData.append('module', module);
    if (submodule) formData.append('submodule', submodule);
    
    // ... rest of upload logic ...
}
```

#### 4.2 Query UI Enhancement

**Modify Text Query and Image Query tabs:**

**Add two dropdowns above the question input (similar to upload UI):**

```html
<!-- Add this before the question textarea -->
<div class="query-section">
    <label><strong>Filter by Module (Optional):</strong></label>
    <select id="queryModuleSelect" style="width: 100%; padding: 12px; border: 2px solid #e9ecef; border-radius: 8px; font-size: 14px; margin-bottom: 10px;">
        <option value="">All Modules</option>
        <!-- Will be populated by JavaScript -->
    </select>
    
    <label><strong>Filter by Submodule (Optional):</strong></label>
    <select id="querySubmoduleSelect" style="width: 100%; padding: 12px; border: 2px solid #e9ecef; border-radius: 8px; font-size: 14px; margin-bottom: 10px;">
        <option value="">All Submodules</option>
        <!-- Will be populated by JavaScript -->
    </select>
</div>
```

**Modify `askQuestion()` function to include filters:**

```javascript
async function askQuestion() {
    const question = document.getElementById('question').value.trim();
    const module = document.getElementById('queryModuleSelect').value;
    const submodule = document.getElementById('querySubmoduleSelect').value;
    
    // ... existing validation ...
    
    const requestBody = {
        question: question,
        top_k: 5
    };
    
    if (module) requestBody.module = module;
    if (submodule) requestBody.submodule = submodule;
    
    const response = await fetch('/api/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
    });
    
    // ... rest of existing code ...
}
```

#### 4.3 Admin UI: Module/Submodule Management Screen (Simplified - Single Table)

**New Admin Page: `/admin/modules`**

**Single tabular UI - one page, one table:**

A simple table-based interface where admins can define modules and their submodules in one place.

**UI Layout:**
```
┌─────────────────────────────────────────────────────────────────────┐
│  Module & Submodule Management                    [Add Module]       │
├─────────────────────────────────────────────────────────────────────┤
│  Module        │  Submodules                    │  Actions         │
├────────────────┼─────────────────────────────────┼──────────────────┤
│  Loan          │  New, Existing, Transfer        │  [Edit] [Delete] │
│  Account       │  Create, Update, Delete         │  [Edit] [Delete] │
│  Transaction   │  Deposit, Withdrawal            │  [Edit] [Delete] │
└────────────────┴─────────────────────────────────┴──────────────────┘
```

**Features:**
1. **Single Table:**
   - Columns: Module | Submodules (comma-separated list) | Actions
   - All modules and submodules visible in one table
   - Simple, clean interface

2. **Add Module:**
   - Click "Add Module" button (top right)
   - Modal: Enter module name → Submit
   - Adds new row to table (with empty submodules)

3. **Add Submodule:**
   - Click "+" icon next to submodules in a row
   - Modal: Enter submodule name → Submit
   - Adds submodule to that module's comma-separated list

4. **Edit Module:**
   - Click "Edit" button on row
   - Inline edit: Change module name directly in table cell
   - Updates all documents using that module

5. **Delete Module:**
   - Click "Delete" button on row
   - Confirmation: "Delete module and all its submodules?"
   - Only allowed if no documents use it

6. **Edit Submodule:**
   - Click on submodule name in comma-separated list
   - Inline edit: Change submodule name
   - Updates all documents using that submodule

7. **Delete Submodule:**
   - Click "×" icon next to submodule name
   - Confirmation: "Delete this submodule?"
   - Removes from comma-separated list, updates documents

**Note:** Since we're using denormalized storage, modules/submodules only exist when documents use them. The admin screen shows what exists in documents and allows managing document assignments.

**API Endpoints Needed:**

```python
# Admin endpoints for managing modules/submodules
@app.post("/api/admin/modules")
async def create_module(
    name: str = Form(...),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("manage_system_settings")),
    db: Session = Depends(get_db)
):
    """Create a new module (if it doesn't exist in document_metadata)."""
    # Check if module already exists in any document
    existing = db.query(DocumentMetadata).filter(
        DocumentMetadata.module == name
    ).first()
    if existing:
        return {"status": "exists", "message": f"Module '{name}' already exists"}
    
    # Module will be created when first document uses it
    # This endpoint just validates the name
    return {"status": "ready", "message": f"Module '{name}' is ready to use"}

@app.get("/api/admin/modules")
async def list_modules_with_stats(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("view_admin_dashboard")),
    db: Session = Depends(get_db)
):
    """Get all modules with statistics (document count, submodule count)."""
    from sqlalchemy import func
    result = db.query(
        DocumentMetadata.module,
        func.count(DocumentMetadata.id).label('doc_count'),
        func.count(func.distinct(DocumentMetadata.submodule)).label('submodule_count')
    ).filter(
        DocumentMetadata.module.isnot(None)
    ).group_by(DocumentMetadata.module).all()
    
    modules = []
    for row in result:
        # Get submodules for this module
        submodules = db.query(DocumentMetadata.submodule).filter(
            DocumentMetadata.module == row.module,
            DocumentMetadata.submodule.isnot(None)
        ).distinct().all()
        
        modules.append({
            "name": row.module,
            "document_count": row.doc_count,
            "submodule_count": row.submodule_count,
            "submodules": [s[0] for s in submodules]
        })
    
    return {"modules": modules}

@app.get("/api/admin/modules/{module_name}/submodules")
async def list_submodules_for_module(
    module_name: str,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("view_admin_dashboard")),
    db: Session = Depends(get_db)
):
    """Get all submodules for a specific module with document counts."""
    from sqlalchemy import func
    result = db.query(
        DocumentMetadata.submodule,
        func.count(DocumentMetadata.id).label('doc_count')
    ).filter(
        DocumentMetadata.module == module_name,
        DocumentMetadata.submodule.isnot(None)
    ).group_by(DocumentMetadata.submodule).all()
    
    submodules = [{"name": row.submodule, "document_count": row.doc_count} for row in result]
    return {"submodules": submodules}

@app.put("/api/admin/documents/{document_id}/metadata")
async def update_document_metadata(
    document_id: int,
    module: Optional[str] = Form(None),
    submodule: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("manage_system_settings")),
    db: Session = Depends(get_db)
):
    """Update module/submodule for a specific document."""
    from src.database.crud import update_document_metadata, get_document_metadata
    metadata = db.query(DocumentMetadata).filter(DocumentMetadata.id == document_id).first()
    if not metadata:
        raise HTTPException(404, "Document not found")
    
    # Update metadata
    if module is not None:
        metadata.module = module
    if submodule is not None:
        metadata.submodule = submodule
    
    db.commit()
    
    # TODO: Re-index document in Qdrant with new module/submodule
    # This requires updating the chunks in Qdrant
    
    return {"status": "success", "message": "Document metadata updated"}

@app.get("/api/admin/documents")
async def list_all_documents_with_metadata(
    module: Optional[str] = None,
    submodule: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("view_admin_dashboard")),
    db: Session = Depends(get_db)
):
    """List all documents with their module/submodule assignment."""
    query = db.query(DocumentMetadata)
    if module:
        query = query.filter(DocumentMetadata.module == module)
    if submodule:
        query = query.filter(DocumentMetadata.submodule == submodule)
    
    documents = query.all()
    return {
        "documents": [
            {
                "id": doc.id,
                "filename": doc.filename,
                "module": doc.module,
                "submodule": doc.submodule,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                "chunk_count": doc.chunk_count,
                "file_size": doc.file_size
            }
            for doc in documents
        ]
    }
```

**UI Implementation (HTML/JavaScript in `src/api/main.py`):**

```python
@app.get("/admin/modules", response_class=HTMLResponse)
async def admin_modules_page(
    current_user: Optional[User] = Depends(get_admin_dashboard_user)
):
    """Admin page for managing modules and submodules."""
    if not current_user:
        return HTMLResponse(
            content='<script>window.location.href="/login";</script>',
            status_code=200
        )
    
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Module Management - Ask-NUO</title>
        <style>
            /* Similar styles to other admin pages */
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 1400px;
                margin: 0 auto;
                background: white;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            .content { padding: 30px; }
            .section {
                margin-bottom: 30px;
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
            }
            .section h2 {
                margin-bottom: 15px;
                color: #495057;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 8px;
                overflow: hidden;
            }
            table th, table td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #e9ecef;
            }
            table th {
                background: #f8f9fa;
                font-weight: 600;
                color: #495057;
            }
            .btn {
                padding: 8px 16px;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                margin: 2px;
            }
            .btn-primary { background: #667eea; color: white; }
            .btn-danger { background: #dc3545; color: white; }
            .btn-success { background: #28a745; color: white; }
            .modal {
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
            }
            .modal-content {
                background: white;
                margin: 15% auto;
                padding: 20px;
                border-radius: 8px;
                width: 400px;
            }
            .form-group {
                margin-bottom: 15px;
            }
            .form-group label {
                display: block;
                margin-bottom: 5px;
                font-weight: 600;
            }
            .form-group input, .form-group select {
                width: 100%;
                padding: 8px;
                border: 1px solid #e9ecef;
                border-radius: 4px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div>
                    <h1>📚 Module & Submodule Management</h1>
                    <p style="margin-top: 5px; opacity: 0.9;">Define and manage document categories</p>
                </div>
                <div class="nav-links">
                    <a href="/" style="color: white; text-decoration: none; padding: 8px 16px; background: rgba(255,255,255,0.2); border-radius: 6px; margin-right: 10px;">🏠 Home</a>
                    <a href="/admin/dashboard" style="color: white; text-decoration: none; padding: 8px 16px; background: rgba(255,255,255,0.2); border-radius: 6px; margin-right: 10px;">📈 Dashboard</a>
                    <a href="#" onclick="logout(); return false;" style="color: white; text-decoration: none; padding: 8px 16px; background: rgba(255,255,255,0.2); border-radius: 6px;">🚪 Logout</a>
                </div>
            </div>
            <div class="content">
                <!-- Modules Section -->
                <div class="section">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <h2>📦 Modules</h2>
                        <button class="btn btn-primary" onclick="showCreateModuleModal()">+ Add Module</button>
                    </div>
                    <div id="modulesList">Loading modules...</div>
                </div>
                
                <!-- Submodules Section -->
                <div class="section">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                        <h2>📋 Submodules</h2>
                        <button class="btn btn-primary" onclick="showCreateSubmoduleModal()">+ Add Submodule</button>
                    </div>
                    <div id="submodulesList">Loading submodules...</div>
                </div>
                
                <!-- Documents Section -->
                <div class="section">
                    <h2>📄 Documents</h2>
                    <div id="documentsList">Loading documents...</div>
                </div>
            </div>
        </div>
        
        <!-- Create Module Modal -->
        <div id="createModuleModal" class="modal">
            <div class="modal-content">
                <h3>Create New Module</h3>
                <div class="form-group">
                    <label>Module Name:</label>
                    <input type="text" id="newModuleName" placeholder="e.g., Loan, Account, Transaction">
                </div>
                <div style="display: flex; gap: 10px; justify-content: flex-end;">
                    <button class="btn btn-primary" onclick="createModule()">Create</button>
                    <button class="btn" onclick="closeModal('createModuleModal')">Cancel</button>
                </div>
            </div>
        </div>
        
        <!-- Create Submodule Modal -->
        <div id="createSubmoduleModal" class="modal">
            <div class="modal-content">
                <h3>Create New Submodule</h3>
                <div class="form-group">
                    <label>Module:</label>
                    <select id="newSubmoduleModule">
                        <option value="">Select Module</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Submodule Name:</label>
                    <input type="text" id="newSubmoduleName" placeholder="e.g., New, Existing, Transfer">
                </div>
                <div style="display: flex; gap: 10px; justify-content: flex-end;">
                    <button class="btn btn-primary" onclick="createSubmodule()">Create</button>
                    <button class="btn" onclick="closeModal('createSubmoduleModal')">Cancel</button>
                </div>
            </div>
        </div>
        
        <script>
            let authToken = localStorage.getItem('auth_token');
            if (!authToken) {
                window.location.href = '/login';
            }
            
            // Load modules, submodules, and documents
            async function loadModules() {
                try {
                    const response = await fetch('/api/admin/modules', {
                        headers: { 'Authorization': `Bearer ${authToken}` }
                    });
                    if (response.status === 401) {
                        window.location.href = '/login';
                        return;
                    }
                    const data = await response.json();
                    
                    // Render modules table
                    if (data.modules && data.modules.length > 0) {
                        document.getElementById('modulesList').innerHTML = `
                            <table>
                                <thead>
                                    <tr>
                                        <th>Module Name</th>
                                        <th>Documents</th>
                                        <th>Submodules</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${data.modules.map(m => `
                                        <tr>
                                            <td><strong>${escapeHtml(m.name)}</strong></td>
                                            <td>${m.document_count}</td>
                                            <td>${m.submodule_count}</td>
                                            <td>
                                                <button class="btn btn-danger" onclick="deleteModule('${escapeHtml(m.name)}')">Delete</button>
                                            </td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        `;
                    } else {
                        document.getElementById('modulesList').innerHTML = '<p>No modules defined yet. Create one to get started!</p>';
                    }
                } catch (error) {
                    console.error('Error loading modules:', error);
                    document.getElementById('modulesList').innerHTML = '<p style="color: #dc3545;">Error loading modules.</p>';
                }
            }
            
            async function loadSubmodules() {
                // Similar implementation for submodules
                // Group by module for hierarchical display
            }
            
            async function loadDocuments() {
                // Load all documents with their module/submodule assignments
            }
            
            function showCreateModuleModal() {
                document.getElementById('createModuleModal').style.display = 'block';
            }
            
            function showCreateSubmoduleModal() {
                // Load modules into dropdown first
                loadModulesForSubmodule();
                document.getElementById('createSubmoduleModal').style.display = 'block';
            }
            
            function closeModal(modalId) {
                document.getElementById(modalId).style.display = 'none';
            }
            
            async function createModule() {
                const name = document.getElementById('newModuleName').value.trim();
                if (!name) {
                    alert('Please enter a module name');
                    return;
                }
                
                try {
                    const response = await fetch('/api/admin/modules', {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${authToken}`,
                            'Content-Type': 'application/x-www-form-urlencoded'
                        },
                        body: `name=${encodeURIComponent(name)}`
                    });
                    
                    if (response.ok) {
                        alert('Module created successfully!');
                        closeModal('createModuleModal');
                        loadModules();
                    } else {
                        const data = await response.json();
                        alert(data.detail || 'Error creating module');
                    }
                } catch (error) {
                    alert('Error creating module: ' + error.message);
                }
            }
            
            function escapeHtml(text) {
                const div = document.createElement('div');
                div.textContent = text;
                return div.innerHTML;
            }
            
            function logout() {
                if (confirm('Are you sure you want to logout?')) {
                    localStorage.removeItem('auth_token');
                    localStorage.removeItem('user_info');
                    window.location.href = '/login';
                }
            }
            
            // Load data on page load
            loadModules();
            loadSubmodules();
            loadDocuments();
        </script>
    </body>
    </html>
    """
    return html_content
```

**Add to Admin Navigation:**

Update the admin dashboard header to include a link to `/admin/modules`:

```html
<a href="/admin/modules">📚 Modules</a>
```

---

## Migration Strategy

### Step 1: Database Migration (5 minutes)

1. Create migration script: `scripts/add_document_metadata_table.sql`
2. Run migration to create `document_metadata` table
3. Verify table created successfully

### Step 2: Backend Implementation (Backward Compatible)

1. Add database model (Phase 1)
2. Add CRUD operations (Phase 1)
3. Enhance RAG pipeline (Phase 2) - make module/submodule optional
4. Add API endpoints (Phase 3) - make filters optional
5. Test: Upload document without module/submodule → should work
6. Test: Query without filters → should work (searches all)

### Step 3: Frontend Implementation

1. Enhance document upload UI (add dropdowns)
2. Enhance query UI (add filter dropdowns)
3. Test: Upload with module/submodule → should work
4. Test: Query with filters → should filter results

### Step 4: Testing

1. **Unit Tests:**
   - Test document metadata CRUD operations
   - Test query filtering logic

2. **Integration Tests:**
   - Test document upload with/without module/submodule
   - Test query with/without filters

3. **Manual Testing:**
   - Upload document without module → should work
   - Upload document with module/submodule → should work
   - Query without filters → should search all
   - Query with module filter → should only search that module
   - Query with submodule filter → should only search that submodule

---

## Backward Compatibility Guarantees

### ✅ Guaranteed Behaviors:

1. **Existing Documents:**
   - All existing documents continue to work
   - Documents without module/submodule are searchable in "all documents" mode
   - No data loss or corruption

2. **Existing Queries:**
   - Queries without module/submodule filters work exactly as before
   - No breaking changes to API response format
   - Query performance unchanged for unfiltered queries

3. **Existing API Endpoints:**
   - All existing endpoints continue to work
   - New parameters are optional
   - Response formats unchanged (new fields added, not removed)

4. **Existing UI:**
   - Main UI continues to work without module/submodule selection
   - Dropdowns are optional - users can ignore them
   - No forced migration of existing documents

---

## Implementation Phases & Timeline

### Phase 1: Write Tests First (TDD) (2-3 hours)
- Write unit tests for DocumentMetadata model (5 tests)
- Write unit tests for CRUD operations (11 tests)
- Write integration tests for API endpoints (18 tests)
- Write integration tests for RAG filtering (5 tests)
- Write UI workflow tests (5 tests)
- **All tests should FAIL initially (red)** - functionality not implemented yet

### Phase 2: Database & Models (1 hour)
- Create database table
- Add SQLAlchemy model
- Add CRUD operations
- **Run tests** - Unit tests should PASS (green)

### Phase 3: RAG Pipeline Integration (1-2 hours)
- Enhance document loader (add metadata)
- Enhance pipeline indexing (pass module/submodule)
- Enhance query engine filtering (Qdrant filter)
- **Run tests** - RAG integration tests should PASS (green)

### Phase 4: API Endpoints (1-2 hours)
- Enhance document upload endpoint
- Enhance query endpoints
- Add module/submodule list endpoints
- Add admin module management endpoints
- **Run tests** - API integration tests should PASS (green)

### Phase 5: Frontend UI (2-3 hours)
- Enhance document upload UI (add dropdowns)
- Enhance query UI (add filter dropdowns)
- Add JavaScript for dropdown population
- **Create admin module/submodule management screen** (`/admin/modules`) - single table UI
- Add admin navigation link
- **Run tests** - UI workflow tests should PASS (green)

### Phase 6: Final Testing & Documentation (1 hour)
- Run all tests together
- Manual testing
- Update documentation

**Total Estimated Time: 8-11 hours** (includes TDD approach with test-first development)

---

## File Changes Summary

### New Files:
- `scripts/add_document_metadata_table.sql` (simple table creation)

### Modified Files:
- `src/database/models.py` (add DocumentMetadata class)
- `src/database/crud.py` (add simple CRUD functions)
- `src/rag/document_loader.py` (add module/submodule to metadata)
- `src/rag/pipeline.py` (pass module/submodule to loader)
- `src/rag/query_engine.py` (add Qdrant filtering)
- `src/api/main.py` (enhance endpoints, add UI dropdowns)
- `src/tests/unit/test_document_metadata.py` (new test file - 5 tests)
- `src/tests/unit/test_module_crud.py` (new test file - 11 tests)
- `src/tests/integration/test_module_api_endpoints.py` (new test file - 18 tests)
- `src/tests/integration/test_module_filtering_rag.py` (new test file - 5 tests)
- `src/tests/integration/test_module_ui_workflows.py` (new test file - 5 tests)
- `docs/MODULE_SUBMODULE_TEST_PLAN.md` (comprehensive test plan - TDD approach)

---

## Success Criteria

✅ **Implementation is successful when:**
1. **Admin can define modules/submodules** via `/admin/modules` screen
2. Users can upload documents with module/submodule selection (optional)
3. Users can filter queries by module/submodule (optional)
4. Dropdowns are populated from defined modules/submodules
5. All existing functionality continues to work without changes
6. All tests pass
7. Documentation is updated

---

## Notes

- **Qdrant Metadata Filtering:** Qdrant supports filtering by metadata using `Filter` objects. We'll use `FieldCondition` with `MatchValue` to filter by `module` and `submodule` strings.
- **LlamaIndex Integration:** LlamaIndex Document objects have a `metadata` dict that gets stored in Qdrant. We'll add `module` and `submodule` strings to this metadata.
- **Performance:** Filtered queries should be faster than unfiltered queries (smaller search space), especially as the document corpus grows.
- **Flexibility:** Since module/submodule are just strings, users can type any values. We can build dropdowns from existing data, but users aren't restricted to predefined values.

---

---

## Test Plan Reference

**See `docs/MODULE_SUBMODULE_TEST_PLAN.md` for comprehensive test plan:**
- 44 total tests planned
- TDD approach: Write tests first, then implement
- Unit tests: 16 tests
- Integration tests: 23 tests
- UI workflow tests: 5 tests

---

**Document Version:** 3.0 (Simplified + TDD)  
**Last Updated:** 2025-01-17  
**Status:** Planning Complete - Ready for TDD Implementation
