# Module/Submodule Filtering - Testing Guide

This guide explains how to test the new module/submodule filtering functionality that was implemented.

## Overview

The module/submodule filtering system allows you to:
1. **Categorize documents** by module and submodule when uploading
2. **Filter queries** by module and submodule to narrow search results
3. **Manage document categories** through an admin interface

## Prerequisites

1. **Application is running**: The FastAPI server should be running on port 8000
2. **User account**: You need a user account with appropriate permissions:
   - For general use: `upload_documents` and `view_chat` permissions
   - For admin management: `manage_documents` permission (typically operational_admin users)

## Testing Scenarios

### Test 1: Upload Document with Module/Submodule

**Purpose**: Verify that documents can be categorized during upload.

**Steps**:
1. Navigate to `http://localhost:8000/` (or your server URL)
2. Log in with your credentials
3. Click on the **"📚 Documents"** tab
4. You should see:
   - A file upload area
   - **Two dropdown menus**: "Module (Optional)" and "Submodule (Optional)"
5. Click on the **"Module"** dropdown - it should show:
   - First option: "-- Select Module --"
   - If modules exist, they will be listed below
6. Select a module (or leave it empty for now)
7. Click on the **"Submodule"** dropdown:
   - If a module is selected, it should show submodules for that module
   - If no module is selected, it may show all submodules or be empty
8. Upload a test document (PDF, DOCX, or TXT)
9. Select a module and submodule before/during upload
10. After upload completes, verify:
    - Success message appears
    - Document appears in the documents list

**Expected Result**: Document is uploaded and categorized with the selected module/submodule.

---

### Test 2: Query with Module/Submodule Filters

**Purpose**: Verify that queries can be filtered by module and submodule.

**Steps**:
1. Navigate to the **"📝 Text Query"** tab
2. You should see:
   - A text area for your question
   - **Two dropdown menus** below the question area:
     - "Filter by Module (Optional)"
     - "Filter by Submodule (Optional)"
3. Click on the **"Filter by Module"** dropdown:
   - First option: "-- All Modules --"
   - Available modules listed below
4. Select a module (e.g., "Loan")
5. Click on the **"Filter by Submodule"** dropdown:
   - It should automatically update to show only submodules for the selected module
   - First option: "-- All Submodules --"
6. Optionally select a submodule
7. Enter a question in the text area (e.g., "How do I create a new loan?")
8. Click **"Ask Question"**
9. Verify the response:
    - Answer should be relevant to the filtered module/submodule
    - Sources should come from documents in that category (if applicable)

**Expected Result**: Query results are filtered based on the selected module/submodule combination.

---

### Test 3: Admin Module/Submodule Management Page

**Purpose**: Verify the admin interface for managing document categories.

**Steps**:
1. Log in as a user with `manage_documents` permission (typically operational_admin)
2. Navigate to `http://localhost:8000/admin/modules`
3. You should see a page with:
   - **Header**: "📁 Module & Submodule Management"
   - **Navigation links**: Home, Dashboard, Users, Analytics, Export, Settings, Logout
   - **Main content area** with:
     - **Filter section** with two dropdowns:
       - "All Modules" dropdown
       - "All Submodules" dropdown
       - A "🔍 Filter" button
     - **Documents table** showing:
       - Columns: ID, Filename, Module, Submodule, Uploaded By, Chunks, Size, Actions
       - Each row shows a document with its current module/submodule assignment

**Expected Result**: Admin page loads and displays all documents with their module/submodule assignments.

---

### Test 4: Edit Document Module/Submodule (Admin)

**Purpose**: Verify that admins can update document categories.

**Steps**:
1. On the admin modules page (`/admin/modules`)
2. Find a document in the table
3. Click on the **Module** value (it should be clickable/editable)
4. A prompt dialog should appear asking for the new module name
5. Enter a new module name (e.g., "Account") or leave empty to clear
6. Click OK
7. Verify:
    - The table updates to show the new module
    - The change is saved
8. Click on the **Submodule** value
9. Enter a new submodule name (e.g., "New") or leave empty to clear
10. Click OK
11. Verify the change is saved

**Expected Result**: Document module/submodule can be updated inline.

---

### Test 5: Filter Documents by Module/Submodule (Admin)

**Purpose**: Verify filtering functionality on the admin page.

**Steps**:
1. On the admin modules page
2. Click the **"All Modules"** dropdown
3. Select a specific module (e.g., "Loan")
4. The **"All Submodules"** dropdown should automatically update to show submodules for that module
5. Optionally select a submodule
6. Click the **"🔍 Filter"** button (or the dropdowns may auto-filter)
7. Verify:
    - The documents table updates to show only documents matching the filter
    - The total count updates accordingly

**Expected Result**: Documents are filtered based on selected module/submodule.

---

### Test 6: API Endpoints Testing

**Purpose**: Verify the API endpoints work correctly.

#### 6.1: Get Modules List

```bash
curl -X GET "http://localhost:8000/api/modules" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response**:
```json
{
  "modules": ["Loan", "Account", "Payment"]
}
```

#### 6.2: Get Submodules List (All)

```bash
curl -X GET "http://localhost:8000/api/submodules" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response**:
```json
{
  "submodules": ["New", "Edit", "Delete", "View"]
}
```

#### 6.3: Get Submodules for Specific Module

```bash
curl -X GET "http://localhost:8000/api/submodules?module=Loan" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response**:
```json
{
  "submodules": ["New", "Edit"]
}
```

#### 6.4: Upload Document with Module/Submodule

```bash
curl -X POST "http://localhost:8000/api/documents/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test_document.pdf" \
  -F "module=Loan" \
  -F "submodule=New"
```

**Expected Response**:
```json
{
  "status": "success",
  "filename": "test_document.pdf",
  "size": 12345,
  "chunks_indexed": 10,
  "module": "Loan",
  "submodule": "New",
  "file_path": "/var/www/chatbot_FC/data/documents/test_document.pdf"
}
```

#### 6.5: Query with Module/Submodule Filter

```bash
curl -X POST "http://localhost:8000/api/query" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How do I create a new loan?",
    "module": "Loan",
    "submodule": "New"
  }'
```

**Expected Response**:
```json
{
  "answer": "...",
  "sources": ["document1.pdf", "document2.pdf"],
  "processing_time": 2.5,
  "qa_pair_id": 123
}
```

#### 6.6: Admin - Get Modules with Statistics

```bash
curl -X GET "http://localhost:8000/api/admin/modules" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

**Expected Response**:
```json
{
  "modules": [
    {
      "name": "Loan",
      "document_count": 5,
      "submodule_count": 3,
      "submodules": ["New", "Edit", "View"]
    },
    {
      "name": "Account",
      "document_count": 3,
      "submodule_count": 2,
      "submodules": ["New", "View"]
    }
  ]
}
```

#### 6.7: Admin - List Documents with Filtering

```bash
curl -X GET "http://localhost:8000/api/admin/documents?module=Loan&submodule=New" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
```

**Expected Response**:
```json
{
  "documents": [
    {
      "id": 1,
      "filename": "loan_guide.pdf",
      "file_path": "/var/www/chatbot_FC/data/documents/loan_guide.pdf",
      "module": "Loan",
      "submodule": "New",
      "uploaded_by": 1,
      "uploaded_at": "2024-01-15T10:30:00",
      "chunk_count": 25,
      "file_size": 102400,
      "file_type": "pdf",
      "uploader_username": "admin"
    }
  ],
  "total": 1
}
```

#### 6.8: Admin - Update Document Metadata

```bash
curl -X PUT "http://localhost:8000/api/admin/documents/1/metadata" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "module": "Account",
    "submodule": "New"
  }'
```

**Expected Response**: Updated document metadata object.

---

## Automated Testing

You can also run the automated test suite:

```bash
cd /var/www/chatbot_FC
source venv/bin/activate

# Run all module/submodule related tests
pytest src/tests/unit/test_document_metadata.py -v
pytest src/tests/unit/test_module_crud.py -v
pytest src/tests/integration/test_module_api_endpoints.py -v
pytest src/tests/integration/test_module_filtering_rag.py -v

# Run all tests
pytest src/tests/ -v --tb=short
```

---

## Common Issues and Troubleshooting

### Issue 1: Dropdowns are empty
**Solution**: 
- Make sure you have uploaded at least one document with a module/submodule
- Check browser console for JavaScript errors
- Verify API endpoints are accessible: `/api/modules` and `/api/submodules`

### Issue 2: Admin page shows "Not Found"
**Solution**:
- Verify you're logged in with a user that has `manage_documents` permission
- Check the URL is correct: `/admin/modules` (not `/admin/module`)
- Verify the route is registered in `src/api/main.py`

### Issue 3: Query filtering doesn't work
**Solution**:
- Verify documents have module/submodule assigned
- Check that Qdrant metadata filtering is working
- Review logs for any errors in the query engine

### Issue 4: Module/Submodule not saving on upload
**Solution**:
- Check browser network tab to verify form data is being sent
- Verify the API endpoint `/api/documents/upload` accepts `module` and `submodule` form fields
- Check database to see if `document_metadata` table exists and has the correct schema

---

## Verification Checklist

- [ ] Can upload document with module/submodule
- [ ] Module/submodule dropdowns appear on upload form
- [ ] Module/submodule dropdowns appear on query form
- [ ] Submodule dropdown updates when module is selected
- [ ] Query results are filtered by selected module/submodule
- [ ] Admin modules page is accessible
- [ ] Admin can view all documents with their categories
- [ ] Admin can edit document module/submodule inline
- [ ] Admin can filter documents by module/submodule
- [ ] API endpoints return correct data
- [ ] All automated tests pass

---

## Next Steps

After verifying the basic functionality:
1. Test with multiple documents in different modules
2. Test edge cases (empty modules, special characters, etc.)
3. Verify backward compatibility (documents without module/submodule still work)
4. Test performance with large numbers of documents
5. Verify RAG search quality with filters applied


