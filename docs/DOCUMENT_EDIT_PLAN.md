# Document Edit & Module/Submodule Mapping Plan

## Overview
This plan outlines the implementation of document editing functionality that allows users to update module and submodule mappings for uploaded documents directly from the document upload section. Users will be able to edit and update the module/submodule categorization for any document that has been uploaded.

## Current State Analysis

### Existing Functionality
1. **Database Schema**: `document_metadata` table exists with:
   - `module` and `submodule` fields (VARCHAR)
   - Document metadata is created during upload via `create_document_metadata()`
   - Update function exists: `update_document_metadata()` in CRUD

2. **Admin Endpoints** (Admin-only):
   - `PUT /api/admin/documents/{document_id}/metadata` - Updates document metadata (requires admin permission)

3. **User-Facing Endpoints**:
   - `GET /api/documents` - Lists documents from filesystem only (no metadata from DB)
   - `POST /api/documents/upload` - Uploads document and creates metadata
   - `DELETE /api/documents/{filename}` - Deletes document

4. **Frontend**:
   - Documents tab shows document list with filename, size, chunks
   - No module/submodule display
   - No edit functionality
   - Delete button only

### Gaps Identified
1. `/api/documents` endpoint doesn't return metadata from database (module/submodule)
2. No user-facing endpoint to update document metadata (only admin endpoint exists)
3. Frontend doesn't display module/submodule information
4. Frontend has no edit UI for documents

---

## Implementation Plan

### Phase 1: Backend API Enhancements

#### 1.1 Update GET `/api/documents` Endpoint
**File**: `src/api/main.py`

**Changes**:
- Modify endpoint to fetch documents from database metadata instead of filesystem
- Join with `document_metadata` table to include module/submodule info
- Return document ID, filename, module, submodule, size, chunks, upload date
- Maintain backward compatibility if metadata doesn't exist

**Expected Response Format**:
```json
{
  "documents": [
    {
      "id": 1,
      "filename": "document.pdf",
      "file_path": "/var/www/chatbot_FC/data/documents/document.pdf",
      "module": "Loan",
      "submodule": "New",
      "size": 1024000,
      "chunks": 50,
      "uploaded_at": "2024-01-15T10:30:00Z",
      "file_type": "pdf"
    }
  ],
  "total": 1
}
```

**Implementation Steps**:
1. Import `get_all_document_metadata` from `src.database.crud`
2. Fetch documents from database instead of filesystem scan
3. Map DocumentMetadata objects to response format
4. Handle documents that exist in filesystem but not in database (backward compatibility)

---

#### 1.2 Create PUT `/api/documents/{document_id}/metadata` Endpoint (User-Facing)
**File**: `src/api/main.py`

**Purpose**: Allow authenticated users to update module/submodule for documents they have access to

**Request Body**:
```json
{
  "module": "Loan",  // Optional, can be null to clear
  "submodule": "New"  // Optional, can be null to clear
}
```

**Response**: Updated document metadata

**Permission**: Requires `upload_documents` permission (users who can upload should be able to edit)

**Implementation Steps**:
1. Create request model: `UpdateDocumentMetadataRequest` (reuse existing `DocumentMetadataUpdateRequest`)
2. Add endpoint with authentication and permission check
3. Use existing `update_document_metadata()` CRUD function
4. Handle document reindexing if needed (optional - for Phase 2)
5. Return updated document metadata

**Considerations**:
- Should we allow users to edit documents they didn't upload? (Consider: Yes, as long as they have `upload_documents` permission)
- Should we log who made the change? (Consider: Add `updated_by` and `updated_at` fields if needed in future)

---

#### 1.3 Update CRUD Functions (If Needed)
**File**: `src/database/crud.py`

**Review**:
- `update_document_metadata()` - Already exists, verify it handles null values correctly
- Consider adding `get_document_metadata_by_id()` usage (already exists)

**Potential Enhancement**:
- Add `last_updated_by` and `last_updated_at` tracking (optional, for future audit trail)

---

### Phase 2: Frontend UI Enhancements

#### 2.1 Update Document List Display
**File**: `src/api/main.py` (HTML template)

**Changes to `loadDocuments()` function**:
1. Update API call to use enhanced `/api/documents` endpoint
2. Display module and submodule information for each document
3. Show "Not categorized" if module/submodule is null
4. Add "Edit" button next to "Delete" button

**UI Layout Update**:
```html
<div class="document-item">
  <div class="document-info">
    <div class="document-name">filename.pdf</div>
    <div class="document-meta">
      Size: 1.2 MB • 50 chunks
      <span class="module-tag">Module: Loan</span>
      <span class="submodule-tag">Submodule: New</span>
    </div>
  </div>
  <div class="document-actions">
    <button class="secondary" onclick="editDocument(ID)">Edit</button>
    <button class="danger" onclick="deleteDocument('filename')">Delete</button>
  </div>
</div>
```

**CSS Additions**:
- Style for module/submodule tags
- Style for edit button
- Spacing for action buttons

---

#### 2.2 Create Edit Document Modal
**File**: `src/api/main.py` (HTML template)

**Modal Structure**:
- Modal overlay with form
- Document filename display (read-only)
- Module dropdown (pre-populated with current value)
- Submodule dropdown (pre-populated with current value, filtered by selected module)
- Save and Cancel buttons

**JavaScript Functions**:
1. `editDocument(documentId)` - Opens modal, loads current document data
2. `loadDocumentForEdit(documentId)` - Fetches document details for editing
3. `saveDocumentMetadata(documentId)` - Sends PUT request to update metadata
4. `closeEditModal()` - Closes modal
5. Update `loadSubmodulesForModule()` to work in edit modal context

**Implementation Steps**:
1. Add modal HTML structure to Documents tab
2. Add CSS for modal styling
3. Implement JavaScript functions
4. Handle API responses (success/error)
5. Reload document list after successful update
6. Show success/error messages

---

#### 2.3 Module/Submodule Dropdown Integration
**Enhancement**: Reuse existing `loadModules()` and `loadSubmodulesForModule()` functions

**Changes**:
- Ensure modules/submodules load correctly in edit modal
- Pre-select current module/submodule values in dropdowns
- Handle case where module/submodule is null (show "-- Select --")

---

### Phase 3: Optional Enhancements

#### 3.1 Document Reindexing (Optional - Future Enhancement)
**Consideration**: When module/submodule is updated, should we reindex the document in Qdrant?

**Current Behavior**: Documents are indexed with module/submodule in metadata during upload. If we update module/submodule in database but not in Qdrant, there will be inconsistency.

**Options**:
1. **Immediate reindexing** (recommended): When metadata is updated, trigger reindexing to update Qdrant chunks
2. **Batch reindexing**: Provide admin endpoint to reindex all documents
3. **Lazy reindexing**: Update on next query (not recommended due to inconsistency)

**Implementation** (if chosen):
- Call `pipeline.index_documents()` with updated module/submodule
- Update `last_indexed_at` timestamp
- Handle errors gracefully

---

#### 3.2 Audit Trail (Optional - Future Enhancement)
**Add Fields**:
- `last_updated_by` (user ID)
- `last_updated_at` (timestamp)

**Purpose**: Track who last modified document metadata

---

#### 3.3 Permission Granularity (Optional)
**Consideration**: Should we add separate permission like `edit_documents` or use `upload_documents`?

**Recommendation**: Use existing `upload_documents` permission for now, add granular permissions later if needed.

---

## Database Schema Review

### Current Schema (No Changes Needed)
```sql
CREATE TABLE document_metadata (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(500) NOT NULL,
    file_path TEXT NOT NULL UNIQUE,
    module VARCHAR(100),
    submodule VARCHAR(100),
    uploaded_by INTEGER REFERENCES users(id),
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_indexed_at TIMESTAMP,
    chunk_count INTEGER DEFAULT 0,
    file_size BIGINT,
    file_type VARCHAR(20)
);
```

**Status**: Schema is sufficient for this feature. No migration needed.

---

## API Endpoints Summary

### New/Modified Endpoints

| Endpoint | Method | Auth | Permission | Description |
|----------|--------|------|------------|-------------|
| `/api/documents` | GET | Yes | `view_documents` | **Modified**: Now returns metadata from DB including module/submodule |
| `/api/documents/{document_id}/metadata` | PUT | Yes | `upload_documents` | **New**: User-facing endpoint to update document metadata |

### Existing Endpoints (No Changes)

| Endpoint | Method | Auth | Permission | Description |
|----------|--------|------|------------|-------------|
| `/api/documents/upload` | POST | Yes | `upload_documents` | Upload new document |
| `/api/documents/{filename}` | DELETE | Yes | `delete_documents` | Delete document |
| `/api/admin/documents/{document_id}/metadata` | PUT | Yes | `view_admin_dashboard` | Admin endpoint (unchanged) |

---

## Implementation Checklist

### Backend
- [ ] Update `GET /api/documents` to return metadata from database
- [ ] Handle backward compatibility (documents without metadata)
- [ ] Create `PUT /api/documents/{document_id}/metadata` endpoint
- [ ] Add permission check (`upload_documents`)
- [ ] Add request/response models
- [ ] Error handling and validation
- [ ] Unit tests for new/modified endpoints
- [ ] Integration tests

### Frontend
- [ ] Update `loadDocuments()` to use enhanced API response
- [ ] Display module/submodule in document list
- [ ] Add "Edit" button to each document item
- [ ] Create edit modal HTML structure
- [ ] Add modal CSS styling
- [ ] Implement `editDocument()` function
- [ ] Implement `loadDocumentForEdit()` function
- [ ] Implement `saveDocumentMetadata()` function
- [ ] Implement `closeEditModal()` function
- [ ] Pre-populate dropdowns with current values
- [ ] Handle module change to reload submodules
- [ ] Handle null module/submodule values
- [ ] Show success/error messages
- [ ] Reload document list after update
- [ ] Test edit functionality end-to-end

### Testing
- [ ] Test document list displays metadata correctly
- [ ] Test editing document with existing module/submodule
- [ ] Test editing document with null module/submodule
- [ ] Test changing module clears/resets submodule appropriately
- [ ] Test permission checks
- [ ] Test error handling (document not found, etc.)
- [ ] Test with different user permissions

### Documentation
- [ ] Update API documentation
- [ ] Add user guide for editing documents
- [ ] Update CHANGELOG

---

## Risk Assessment

### Low Risk
- Using existing CRUD functions
- Reusing existing permission model
- No database schema changes

### Medium Risk
- Frontend complexity (modal, dropdowns, API integration)
- Backward compatibility for documents without metadata

### Mitigation
- Thorough testing of edit functionality
- Handle edge cases (null values, missing metadata)
- Clear error messages for users

---

## Estimated Effort

- **Backend Changes**: 2-3 hours
  - API endpoint modifications: 1 hour
  - New endpoint creation: 1 hour
  - Testing: 1 hour

- **Frontend Changes**: 4-5 hours
  - Document list update: 1 hour
  - Edit modal UI: 2 hours
  - JavaScript functionality: 1.5 hours
  - Testing and refinement: 1.5 hours

- **Testing**: 2 hours
  - Unit tests: 1 hour
  - Integration tests: 1 hour

**Total Estimated Time**: 8-10 hours

---

## Dependencies

- Existing `document_metadata` table must exist
- `update_document_metadata()` CRUD function must exist (already exists)
- User must have `upload_documents` permission
- Modules/submodules API endpoints must be available (`/api/modules`, `/api/submodules`)

---

## Success Criteria

1. ✅ Users can see module/submodule for each document in the list
2. ✅ Users can click "Edit" button to open edit modal
3. ✅ Users can select/change module and submodule in modal
4. ✅ Changes are saved to database via API
5. ✅ Document list updates immediately after save
6. ✅ Appropriate error messages shown for failures
7. ✅ Permission checks work correctly
8. ✅ Backward compatibility maintained for documents without metadata

---

## Notes

- We're NOT modifying the document file itself, only the metadata
- Reindexing in Qdrant is optional and can be added later
- This feature uses existing permission model (no new permissions needed)
- Admin endpoint remains unchanged and continues to work
- The edit functionality is available to all users with `upload_documents` permission

