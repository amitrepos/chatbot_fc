# Updates Log

## 2025-12-23 - Document Ownership Update

**Timestamp:** 2025-12-23 16:41:00

**Action:** Updated all existing documents to be owned by admin user

**Changes Made:**
- Updated all 4 documents in `document_metadata` table to have `uploaded_by = 60` (admin user)
- Previously, documents were owned by different users (some by admin, one by amitkumarmishra@gmail.com)
- Now all documents are consistently owned by the admin user

**Documents Updated:**
- `.placeholder_LOAN_New.txt`
- `.placeholder_LOAN_Modify.txt`
- `Omokai First add.docx`
- `.placeholder_LOAN.txt`

**Reason:** There is no "system" user, so all documents should be owned by the admin user for consistency.

**Verification:** All documents verified to be owned by admin user (ID: 60)

---

## 2025-01-27 - Document Edit Implementation: Step 1 Complete

**Timestamp:** 2025-01-27

**Action:** Completed Step 1 - Updated GET `/api/documents` endpoint to return metadata from database

**Changes Made:**
1. **Enhanced GET `/api/documents` Endpoint:**
   - Modified to fetch documents from `document_metadata` database table instead of filesystem scan only
   - Added authentication requirement (`get_current_user` dependency)
   - Added permission check (`view_documents` permission required)
   - Returns comprehensive metadata including:
     - `id`: Document ID from database
     - `filename`: Original filename
     - `file_path`: Full file path
     - `module`: Module name (if categorized)
     - `submodule`: Submodule name (if categorized)
     - `size`: File size in bytes (from filesystem for accuracy)
     - `chunks`: Number of indexed chunks
     - `uploaded_at`: Upload timestamp (ISO format)
     - `file_type`: File extension (pdf, docx, txt)
   - Maintains backward compatibility: Documents that exist in filesystem but not in database are still returned (with null metadata)
   - Documents sorted by filename for consistent ordering

**Implementation Details:**
- Uses `get_all_document_metadata()` CRUD function to fetch from database
- Creates file_path map for quick lookup to avoid duplicates
- Checks filesystem for documents not in database (backward compatibility)
- Uses filesystem file size (more accurate than stored size)
- Handles missing files gracefully (uses stored size if file doesn't exist)

**Files Modified:**
- `src/api/main.py`: Updated `list_documents()` endpoint (lines 2191-2280)

**Response Format:**
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
  "total": 1,
  "total_chunks": 394
}
```

**Testing Status:** Ready for verification
- ✅ No linting errors
- ✅ Code follows existing patterns
- ✅ Backward compatibility maintained
- ⏳ Needs user verification via API test

**Next Step:** Step 2 - Create PUT `/api/documents/{document_id}/metadata` endpoint

---

## 2025-01-27 - Document Edit Implementation: Step 2 Complete

**Timestamp:** 2025-01-27

**Action:** Completed Step 2 - Created PUT `/api/documents/{document_id}/metadata` endpoint (user-facing)

**Changes Made:**
1. **New PUT `/api/documents/{document_id}/metadata` Endpoint:**
   - Allows authenticated users to update document metadata (module/submodule)
   - Requires `upload_documents` permission (same as upload endpoint)
   - Takes `document_id` as path parameter
   - Accepts `DocumentMetadataUpdateRequest` body with optional `module` and `submodule` fields
   - Returns updated `DocumentMetadataResponse` with all document metadata
   - Uses existing CRUD functions: `get_document_metadata_by_id()` and `update_document_metadata()`
   - Includes proper error handling (404 for not found, 500 for update failures)
   - Logs update operations for audit trail

**Implementation Details:**
- Reuses existing `DocumentMetadataUpdateRequest` model (already defined)
- Reuses existing `DocumentMetadataResponse` model (already defined)
- Follows same pattern as admin endpoint but with user permission
- Updates metadata using file_path (as required by CRUD function)
- Returns full document metadata including uploader information

**Request Format:**
```json
PUT /api/documents/1/metadata
{
  "module": "Loan",
  "submodule": "New"
}
```

**Response Format:**
```json
{
  "id": 1,
  "filename": "document.pdf",
  "file_path": "/var/www/chatbot_FC/data/documents/document.pdf",
  "module": "Loan",
  "submodule": "New",
  "uploaded_by": 1,
  "uploaded_at": "2024-01-15T10:30:00Z",
  "last_indexed_at": "2024-01-15T10:35:00Z",
  "chunk_count": 50,
  "file_size": 1024000,
  "file_type": "pdf",
  "uploader_username": "admin"
}
```

**Files Modified:**
- `src/api/main.py`: Added `update_document_metadata()` endpoint (lines 2283-2346)

**Security:**
- ✅ Requires authentication (`get_current_user` dependency)
- ✅ Requires `upload_documents` permission
- ✅ Validates document exists before updating
- ✅ Logs update operations with user info

**Testing Status:** Ready for verification
- ✅ No linting errors
- ✅ Follows existing code patterns
- ✅ Reuses existing models and CRUD functions
- ⏳ Needs user verification via API test

**Next Step:** Phase 2 - Frontend UI enhancements (display module/submodule, add edit button, create edit modal)

---

## 2025-01-27 - Document Edit Implementation: Frontend Complete

**Timestamp:** 2025-01-27

**Action:** Completed Frontend UI enhancements - Added module/submodule display and edit functionality

**Changes Made:**

1. **Document List Display Updates:**
   - Added CSS styling for module and submodule tags (`.module-tag`, `.submodule-tag`)
   - Updated `loadDocuments()` function to display module/submodule information for each document
   - Shows colored tags: purple for module, darker purple for submodule
   - Displays "Not categorized" text if no module/submodule assigned
   - Added `.document-actions` CSS class for button grouping

2. **Edit Button:**
   - Added "Edit" button next to "Delete" button for each document
   - Only shown for documents that exist in database (have an ID)
   - Uses existing `secondary` button class styling

3. **Edit Modal:**
   - Created modal HTML structure with overlay
   - Modal includes form with module and submodule dropdowns
   - Pre-populates current module/submodule values
   - Includes Cancel and Save buttons
   - Closes when clicking outside modal or on Cancel button

4. **JavaScript Functions:**
   - `editDocument(documentId)` - Opens modal, fetches document data, populates form
   - `closeEditModal()` - Closes the edit modal
   - `loadModulesForEdit()` - Loads modules for edit dropdown
   - `loadSubmodulesForEditModule(module)` - Loads submodules filtered by selected module
   - `saveDocumentMetadata(documentId)` - Sends PUT request to update metadata, shows success message
   - Added click-outside handler to close modal

**UI Features:**
- Module tags: Blue background (#667eea) with white text
- Submodule tags: Purple background (#764ba2) with white text
- Edit button appears between document info and Delete button
- Modal has clean, modern design matching existing UI
- Success message appears after successful update (disappears after 3 seconds)
- Document list automatically refreshes after update

**Files Modified:**
- `src/api/main.py`: 
  - Added CSS for module/submodule tags (lines ~1085-1105)
  - Updated `loadDocuments()` function (lines ~1685-1720)
  - Added edit modal HTML (lines ~1234-1250)
  - Added JavaScript functions for editing (lines ~1755-1900)
  - Added modal close handler (line ~1520)

**User Experience:**
1. User sees module/submodule tags next to each document in the list
2. User clicks "Edit" button on a document
3. Modal opens with current module/submodule pre-selected
4. User changes module/submodule selections
5. User clicks "Save Changes"
6. Changes saved to database via API
7. Document list refreshes to show updated metadata
8. Success message appears briefly

**Testing Status:** Ready for verification
- ✅ No linting errors
- ✅ Follows existing UI patterns
- ✅ Integrates with existing API endpoints
- ⏳ Needs user verification in browser

---

## 2025-01-27 - Document Edit & Module/Submodule Mapping Plan

**Timestamp:** 2025-01-27

**Action:** Created comprehensive implementation plan for document editing functionality

**Plan Document Created:**
- `docs/DOCUMENT_EDIT_PLAN.md` - Complete plan for adding document edit functionality

**Overview:**
This plan outlines the implementation of document editing functionality that allows users to update module and submodule mappings for uploaded documents directly from the document upload section. Users will be able to edit and update the module/submodule categorization for any document that has been uploaded.

**Key Features Planned:**
1. Enhanced GET `/api/documents` endpoint to return metadata from database (module/submodule)
2. New PUT `/api/documents/{document_id}/metadata` endpoint for users to update document metadata
3. Frontend UI enhancements to display module/submodule in document list
4. Edit modal with dropdowns for module/submodule selection
5. Save functionality to update database

**Implementation Phases:**
- Phase 1: Backend API Enhancements (2-3 hours)
- Phase 2: Frontend UI Enhancements (4-5 hours)
- Phase 3: Optional Enhancements (document reindexing, audit trail)

**Estimated Total Time:** 8-10 hours

**Files Created:**
- `docs/DOCUMENT_EDIT_PLAN.md` - Comprehensive implementation plan with detailed steps, API specifications, UI mockups, and testing checklist

**Status:** Plan created and ready for review before implementation

---

## 2025-12-23 - Document Ownership-Based Visibility Implementation Complete

**Timestamp:** 2025-12-23 16:30:00

**Action:** Implemented complete document ownership-based visibility feature

**Context:**
- User requirement: Documents should be visible based on ownership
  - Admin users: See ALL documents
  - General users: See only documents they uploaded
- Existing documents need to be marked as admin-owned

**Implementation Complete - All Phases:**

### Phase 1: Database Migration ✅
- Created `scripts/migrate_existing_documents_to_admin.py`
- Script assigns all documents with NULL `uploaded_by` to admin user
- Idempotent (safe to run multiple times)
- Tested and verified working

### Phase 2: Database CRUD Functions ✅
- Added `get_user_accessible_documents()` to `src/database/crud.py`
  - Admin users: Returns all documents
  - General users: Returns only documents they uploaded
  - Supports module/submodule filtering and pagination
- Added `can_user_access_document()` to `src/database/crud.py`
  - Checks if user can access a specific document
  - Admin users: Always returns True
  - General users: Returns True only if they uploaded the document

### Phase 3: API Endpoints ✅
- Updated `GET /api/documents`:
  - Now uses `get_user_accessible_documents()` instead of `get_all_document_metadata()`
  - Filters documents by ownership (admin sees all, users see only their own)
  - Returns `uploaded_by` and `uploader_username` in response
  - Filesystem documents only shown to admin users (backward compatibility)
- Updated `DELETE /api/documents/{filename}`:
  - Added authentication requirement
  - Added ownership check using `can_user_access_document()`
  - Returns 403 Forbidden if user tries to delete document they don't own (unless admin)
  - Deletes from both database and filesystem

### Phase 4: Frontend Updates ✅
- Updated `loadDocuments()` JavaScript function:
  - Now sends authentication token in request headers
  - Displays ownership information: "Uploaded by: You" or "Uploaded by: {username}"
  - Handles 401 unauthorized responses (redirects to login)
- Updated `deleteDocument()` JavaScript function:
  - Now sends authentication token in request headers
  - Handles 403 Forbidden responses with user-friendly error messages
  - Shows specific error message when user tries to delete document they don't own

### Phase 5: Testing ✅
- Created `src/tests/integration/test_document_ownership.py`
- Comprehensive test coverage:
  - CRUD function tests (admin sees all, users see only own)
  - API endpoint tests (list and delete operations)
  - Ownership validation tests
  - Permission denial tests

**Files Created:**
- `scripts/migrate_existing_documents_to_admin.py` - Migration script
- `src/tests/integration/test_document_ownership.py` - Integration tests
- `docs/DOCUMENT_OWNERSHIP_VISIBILITY_PLAN.md` - Implementation plan

**Files Modified:**
- `src/database/crud.py` - Added ownership filtering functions
- `src/api/main.py` - Updated API endpoints and frontend JavaScript

**Key Features:**
- ✅ Admin users can see and delete all documents
- ✅ General users can only see and delete documents they uploaded
- ✅ Ownership information displayed in UI
- ✅ Proper error handling and user feedback
- ✅ Backward compatibility maintained
- ✅ All existing documents marked as admin-owned via migration

**Security:**
- Ownership checks enforced at API level (server-side)
- Frontend changes are for UX only
- Proper authentication and authorization on all endpoints

**Status:** ✅ Implementation complete and tested

## 2025-01-XX - Cursor PDF Viewer Setup

**Timestamp:** 2025-01-XX

**Action:** Added solutions for viewing PDFs properly in Cursor IDE

**Problem:**
- PDFs opened in Cursor display as raw binary/ASCII data instead of visual content
- Cursor IDE doesn't have built-in PDF viewer like it does for images

**Solutions Provided:**

1. **PDF Reader MCP Server (Recommended)**
   - Created setup guide: `docs/CURSOR_PDF_VIEWER_SETUP.md`
   - Created installation script: `scripts/setup_pdf_mcp_server.sh`
   - MCP (Model Context Protocol) server integrates with Cursor
   - Enables proper PDF reading and text extraction within Cursor
   - Configuration instructions included

2. **PDF to Images Converter (Alternative)**
   - Created script: `scripts/pdf_to_images_viewer.py`
   - Converts PDF pages to PNG images
   - Cursor can display images properly, so this provides a workaround
   - Supports custom output directories and DPI settings
   - Usage: `python scripts/pdf_to_images_viewer.py "path/to/file.pdf"`

**Files Created:**
- `docs/CURSOR_PDF_VIEWER_SETUP.md` - Complete setup guide with all solutions
- `scripts/pdf_to_images_viewer.py` - PDF to PNG converter script
- `scripts/setup_pdf_mcp_server.sh` - Automated MCP server setup script

**Usage:**
```bash
# Option 1: Setup MCP Server (recommended for long-term use)
bash scripts/setup_pdf_mcp_server.sh

# Option 2: Convert PDF to images (quick solution)
python scripts/pdf_to_images_viewer.py "data/documents/file.pdf"
```

**Benefits:**
- MCP Server: Seamless integration, works automatically with Cursor
- Image Converter: Simple, no configuration needed, works immediately
- Both solutions allow proper viewing of PDF content in Cursor IDE

## 2025-01-XX - PDF Image Extraction Page Matching Fix

**Timestamp:** 2025-01-XX

**Action:** Fixed PDF image extraction to correctly match images to pages based on content, not just object location

**Problem Identified:**
- Screenshots extracted from PDF were reported as being from "Page 1" (Table of Contents)
- But images actually showed Media Maintenance screens which appear on Page 2
- Root cause: PDF has unusual structure where same 40 images are stored on both Page 1 and Page 2
- PyMuPDF reports images based on where image objects are stored, not where they visually appear

**Solution Implemented:**
1. **New Function**: `find_best_matching_page()` in `process_pdf_images_incremental.py`
   - Analyzes LLaVA description of the image
   - Extracts Function IDs and keywords (e.g., "MEDIA MAINTENANCE", "MSDMEDMT")
   - Searches surrounding pages (±2 pages) for matching text content
   - Returns page number with best content match

2. **Updated Extraction Flow**:
   - Extract images from PDF (as before)
   - Get LLaVA description of image
   - Extract Function ID from description
   - **NEW**: Match image to correct page based on text content
   - Use matched page number for output and context

**Technical Details:**
- Function searches for keywords in page text
- Scores pages based on keyword matches (Function ID matches get +10 points)
- Updates page number if better match found
- Logs page corrections for transparency

**Files Modified:**
- `scripts/process_pdf_images_incremental.py`: Added `find_best_matching_page()` function and integrated into processing loop

**Documentation Created:**
- `data/documents/PDF_EXTRACTION_ISSUE_ANALYSIS.md`: Detailed analysis of the problem
- `data/documents/PDF_EXTRACTION_FIX_SUMMARY.md`: Summary of solution and testing steps

**Expected Results:**
- Before: Screenshots labeled as "Page 1" with Table of Contents context
- After: Screenshots labeled as "Page 2" with Media Maintenance context ✅

**Next Steps:**
1. Test fix with 2-page PDF extract
2. Re-extract all images from full PDF if successful
3. Consider applying same fix to `process_pdf_images.py` (non-incremental version)

---

## 2025-12-17 - Step 6 Progress & Comprehensive Authentication Tests

**Timestamp:** 2025-12-17 21:10:00

**Action:** Fixed integration tests and created comprehensive authentication test suite

**Issues Fixed:**

1. **`get_user_permissions()` return type bug:**
   - Bug: Code was treating permissions as objects with `.name` attribute
   - Fix: Permissions are already strings, removed incorrect attribute access
   - Affected endpoints: `/api/auth/me` and `/api/auth/refresh`

2. **Password validation not working:**
   - Bug: `validate_password_strength()` returns tuple, code expected exception
   - Fix: Changed to check return value `(is_valid, error_message)` properly

3. **Integration tests timing out:**
   - Bug: Tests using `test_user_with_token` fixture didn't work with TestClient
   - Cause: Fixtures create data in transaction (rolled back), TestClient uses separate DB session
   - Fix: Tests now create users via API (`POST /api/auth/register`) instead of fixtures

4. **Test users persisting between runs:**
   - Bug: Static usernames caused "already registered" errors
   - Fix: All tests now use UUID-based unique usernames

**New/Updated Tests (83+ tests passing):**

**Unit Tests (`src/tests/unit/`):**
- `test_password.py`: 10 tests (password hashing, strength validation)
- `test_auth.py`: 9 tests (JWT creation, validation, expiration)
- `test_permissions.py`: 5 tests (permission checking)
- `test_crud_operations.py`: 16 tests (CRUD for conversations, Q&A, feedback)
- `test_database_connection.py`: 12 tests (NEW - database config, connection, tables)

**Integration Tests (`src/tests/integration/test_api_endpoints.py`):**
- `TestAuthEndpoints`: 19 tests
  - Registration: creates user, rejects duplicates, validates password/email
  - Login: returns token, rejects invalid, supports email login
  - Logout: works, requires auth
  - Token refresh: works, requires auth
  - Protected endpoints: validate tokens
- `TestFaviconEndpoint`: 2 tests
- `TestHealthEndpoint`: 2 tests
- `TestFullAuthenticationFlow`: 3 tests

**Files Modified:**
- `src/api/main.py`: Fixed permission handling, password validation
- `src/tests/integration/test_api_endpoints.py`: Updated all auth tests to use API
- `src/tests/unit/test_database_connection.py`: NEW - database connection tests
- `src/tests/conftest.py`: Updated database URL for TCP connection
- `docs/IMPLEMENTATION_STEPS.md`: Updated progress tracking

**Step 6 Progress (80% complete):**
- ✅ Login/signup page
- ✅ JWT token storage (localStorage)
- ✅ API request interceptor
- ✅ Feedback buttons (like/dislike)
- ✅ Conversation history (in-memory)
- ✅ User profile dropdown
- ✅ Route protection
- ⬜ Role-based UI rendering (pending)
- ⬜ Admin UI pages (pending)

---

## 2025-01-27 - Step 5: Feedback Endpoints Implementation

**Timestamp:** 2025-01-27

**Action:** Completed Step 5 of Phase 7: Enhanced Feedback Endpoints

**Changes:**

1. **Updated POST `/api/feedback` Endpoint:**
   - Removed ownership restriction - any authenticated user can now provide feedback on any Q&A pair
   - Maintains existing functionality: accepts qa_pair_id, rating (1=dislike, 2=like), optional comment
   - Automatically updates existing feedback if user has already provided feedback for the same Q&A pair

2. **New GET `/api/feedback/qa-pair/{qa_pair_id}` Endpoint:**
   - Retrieves all feedback for a specific Q&A pair
   - Returns detailed feedback information including:
     - Feedback ID, Q&A pair ID, user ID, username
     - Rating (1 or 2), optional feedback text
     - Creation timestamp
   - Returns total count of feedback entries
   - Requires authentication

3. **New DELETE `/api/feedback/{feedback_id}` Endpoint:**
   - Allows users to delete their own feedback
   - Validates ownership - users can only delete feedback they created
   - Returns 204 No Content on successful deletion
   - Requires authentication

4. **New Response Models:**
   - `FeedbackDetailResponse`: Detailed feedback information with user details
   - `FeedbackListResponse`: List of feedback with total count

5. **Comprehensive Test Coverage:**
   - Updated existing test to verify any user can provide feedback
   - Added test for GET endpoint (retrieval, authentication, validation)
   - Added tests for DELETE endpoint (success, authentication, ownership validation)
   - All tests passing

**Technical Details:**
- Endpoints use existing CRUD operations from `src/database/crud.py`
- Proper error handling with HTTP status codes (404, 403, 400)
- Logging for audit trail
- Follows existing authentication and permission patterns

**Files Modified:**
- `src/api/main.py`: Added GET and DELETE endpoints, updated POST endpoint, added response models
- `src/tests/integration/test_api_endpoints.py`: Updated and added comprehensive tests

**Deliverables:**
- ✅ Feedback endpoints working (POST, GET, DELETE)
- ✅ Like/dislike stored in database
- ✅ Feedback linked to Q&A pairs
- ✅ Users can view/delete their feedback
- ✅ Any authenticated user can provide feedback on any Q&A pair
- ✅ Comprehensive test coverage

---

## 2025-12-17 - Query Expansion for Improved Semantic Retrieval

**Timestamp:** 2025-12-17 18:50:00

**Action:** Implemented semantic query expansion to improve RAG retrieval

**Problem Solved:**
- User queries like "How many users logged in?" failed to retrieve documents containing semantically similar phrases like "user sign-ins", "connected users", or "authentication count"
- Single-vector search was too narrow to bridge vocabulary gaps between questions and documents

**New Components:**

1. **QueryExpander Class** (`src/rag/query_expander.py`)
   - Uses Mistral LLM to generate synonyms and alternative phrasings
   - Extracts key terms and their synonyms
   - Creates a combined, semantically-enriched query for better embedding matches
   
2. **MultiQueryRetriever** (`src/rag/query_expander.py`)
   - Optional mode that retrieves using multiple expanded queries
   - Merges and deduplicates results from all queries
   - Re-ranks by similarity score

**How It Works:**
```
User: "How many users logged in?"
            ↓
Query Expansion (LLM):
  - Key Terms: logged in → signed in, authenticated, connected
  - Key Terms: users → accounts, sessions, clients
  - Alternative: "Count of authenticated users"
  - Alternative: "User login statistics"
            ↓
Combined Query: "How many users logged in? signed in authenticated 
                 connected accounts sessions authentication statistics"
            ↓
Vector Search (with enriched query)
            ↓
Better Semantic Matches Retrieved
```

**Configuration Options:**
- `enable_query_expansion`: Enable/disable expansion (default: True)
- `expansion_mode`: 
  - `"combined"`: Single enriched query (faster, default)
  - `"multi"`: Multiple queries merged (better recall, slower)

**Unit Tests Added:**
- TestQueryExpansionParsing (4 tests)
- TestQueryExpansionExamples (2 tests)  
- TestMultiQueryRetrieverLogic (2 tests)
- Total: 27 tests passing

**Performance Impact:**
- Adds ~5-10 seconds for LLM expansion call
- Significantly improves recall for vocabulary-mismatched queries
- No impact on FlexCube-specific queries (keywords match directly)

---

## 2025-12-14 - Clipboard Paste Support for Image Query

**Timestamp:** 2025-12-14

**Action:** Added clipboard paste functionality to Image Query section

**Changes:**
1. **UI Updates:**
   - Updated image upload area text to mention paste support: "Click, drag & drop, or paste image here"
   - Added visual tip: "💡 Tip: Press Ctrl+V (or Cmd+V on Mac) to paste from clipboard"

2. **JavaScript Functionality:**
   - Added `setupClipboardPaste()` function that listens for paste events
   - Only processes paste when Image Query tab is active (doesn't interfere with text input)
   - Detects image data in clipboard using Clipboard API
   - Converts clipboard image blob to File object with timestamp-based filename
   - Reuses existing `handleImageFile()` function for validation and preview
   - Provides visual feedback (brief green highlight) when image is pasted

3. **Technical Details:**
   - Uses `document.addEventListener('paste')` to detect clipboard paste events
   - Checks if image tab is active before processing
   - Extracts image from `e.clipboardData.items`
   - Validates image type and size using existing validation logic
   - Works seamlessly with existing drag & drop and file picker methods

**User Experience:**
- Users can now paste screenshots directly from clipboard into Image Query tab
- No need to save screenshot to file first
- Works with screenshots copied from any source (Snipping Tool, screenshots, etc.)
- Visual feedback confirms successful paste

## 2025-12-14 00:10 - Docker Configuration & Cleanup Scripts

**Timestamp:** 2025-12-14 00:10:00

**Action:** Created deployment and maintenance scripts

**New Files:**
1. **`Dockerfile`** - Container image for the FastAPI application
2. **`docker-compose.full.yml`** - Complete stack (Qdrant + Ollama + App)
3. **`scripts/cleanup.sh`** - Complete removal script
4. **`scripts/docker-build-push.sh`** - Build and push to Docker Hub
5. **`scripts/deploy-new-server.sh`** - Fresh server deployment
6. **`scripts/README.md`** - Documentation for scripts

**Usage:**
- Build & Push: `./scripts/docker-build-push.sh <dockerhub-username>`
- Deploy New Server: `sudo bash scripts/deploy-new-server.sh <username>`
- Cleanup: `sudo bash scripts/cleanup.sh`

## 2025-12-13 23:25 - Enhanced Document Management UI

**Timestamp:** 2025-12-13 23:25:00

**Action:** Improved Documents tab with upload, reindex controls

**Features:**
1. **Document Upload (Automatic Indexing):**
   - Drag & drop support for documents
   - Multiple file upload
   - Supports PDF, DOCX, TXT (up to 50MB)
   - Progress indicator during upload
   - **NEW: Documents are auto-indexed immediately** - no need to reindex!

2. **Index Management:**
   - "Rebuild Index (after deletions)" button - only needed after deleting docs
   - Progress bar during rebuilding
   - Status messages (success/error)
   - Total chunks display

3. **Document List:**
   - Shows all uploaded documents
   - File size display
   - Delete button per document
   - Refresh list button

4. **New API Endpoint:**
   - `POST /api/documents/reindex` - Rebuilds entire search index (only for cleanup after deletions)

**Workflow:**
1. Upload document(s) via drag & drop or click → **Automatically indexed!**
2. Query immediately using Text or Image tabs
3. Only use "Rebuild Index" after deleting documents

**Dependencies Added:**
- `docx2txt` - For DOCX file support

## 2025-12-13 23:15 - Phase 5: Vision Support (Screenshot Queries)

**Timestamp:** 2025-12-13 23:15:00

**Action:** Implemented LLaVA vision model integration for screenshot analysis

**New Files:**
- `src/rag/vision.py` - FlexCubeVision class for LLaVA integration

**Features:**
1. **Screenshot Analysis with LLaVA:**
   - Accepts PNG, JPG images
   - Extracts: error code, error message, screen name, description
   - Creates optimized RAG query from extracted info

2. **Vision Pipeline Flow:**
   ```
   Screenshot → LLaVA Analysis → Extract Info → Create Query → RAG Search → Answer
   ```

3. **Extraction Prompt:**
   - Specialized prompt for FlexCube errors
   - Looks for error codes (ERR_XXX, ORA-XXXXX)
   - Identifies screen/module names
   - Creates suggested search queries

4. **API Endpoint:**
   - POST /api/query/image (fully implemented)
   - Returns extraction summary + RAG solution
   - Shows sources from documentation

**Example Response:**
```json
{
    "answer": "**Extracted from Screenshot:**\n- **Error Code:** ERR_ACC_001\n- **Screen:** Customer Maintenance\n\n**Solution:**\n...",
    "sources": ["OracleFlexcubeManual.pdf"],
    "processing_time": 20.37
}
```

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

---

## 2025-01-17 - Module/Submodule Filtering: Test Cases Written (TDD)

**Timestamp:** 2025-01-17

**Action:** Created comprehensive test suite for module/submodule filtering feature following Test-Driven Development (TDD) approach.

**Test Files Created (44 tests, ~1600 lines of test code):**

1. **Unit Tests:**
   - `src/tests/unit/test_document_metadata.py` (189 lines, 5 tests)
     - DocumentMetadata model tests
     - Model creation, relationships, constraints
   - `src/tests/unit/test_module_crud.py` (405 lines, 11 tests)
     - CRUD operations tests
     - Distinct module/submodule queries
     - Update operations

2. **Integration Tests:**
   - `src/tests/integration/test_module_api_endpoints.py` (541 lines, 18 tests)
     - Document upload with module/submodule
     - Query filtering endpoints
     - Module/submodule list endpoints
     - Admin module management endpoints
   - `src/tests/integration/test_module_filtering_rag.py` (239 lines, 5 tests)
     - RAG pipeline indexing with module/submodule
     - Query filtering in RAG pipeline
     - Backward compatibility tests
   - `src/tests/integration/test_module_ui_workflows.py` (226 lines, 5 tests)
     - UI workflow tests
     - Admin UI tests

**Key Constraints Reflected in Tests:**
- ✅ **Module names ARE unique** - Each module is unique (e.g., "Loan", "Account")
- ✅ **Submodule names are NOT unique** - Same submodule name can exist under different modules (e.g., "New" under "Loan" and "Account")
- ✅ **Module + Submodule combination IS unique** - Each document has one unique module+submodule pair

**Test Scenarios Covered:**
- Creating document metadata with/without module/submodule
- Getting distinct modules (unique modules)
- Getting distinct submodules (non-unique names, filtered by module)
- Query filtering by module alone (returns all docs with that unique module)
- Query filtering by module+submodule (returns only exact unique combination)
- Backward compatibility (all existing functionality continues to work)
- Admin module/submodule management
- UI workflows

**Documentation Created:**
- `docs/MODULE_SUBMODULE_FILTERING_PLAN.md` - Complete implementation plan
- `docs/MODULE_SUBMODULE_TEST_PLAN.md` - Comprehensive test plan
- `docs/MODULE_SUBMODULE_TEST_EXECUTION.md` - Test execution guide

**TDD Status:**
- ✅ **Phase 1: Tests Written** - All 44 tests ready to run
- ⏳ **Phase 2: Database Layer** - Not implemented yet (tests will fail)
- ⏳ **Phase 3: RAG Pipeline** - Not implemented yet (tests will fail)
- ⏳ **Phase 4: API Endpoints** - Not implemented yet (tests will fail)
- ⏳ **Phase 5: Frontend UI** - Not implemented yet (tests will fail)

**Next Steps:**
1. Run tests to verify they fail (red phase in TDD)
2. Implement database layer (document_metadata table, model, CRUD)
3. Implement RAG pipeline filtering
4. Implement API endpoints
5. Implement frontend UI
6. Verify all tests pass (green phase)

**Files Created:**
- `src/tests/unit/test_document_metadata.py`
- `src/tests/unit/test_module_crud.py`
- `src/tests/integration/test_module_api_endpoints.py`
- `src/tests/integration/test_module_filtering_rag.py`
- `src/tests/integration/test_module_ui_workflows.py`
- `docs/MODULE_SUBMODULE_TEST_EXECUTION.md`

**Total Test Code:** ~1600 lines
**Total Tests:** 44 tests
**Test Coverage Goal:** >90% for new code

