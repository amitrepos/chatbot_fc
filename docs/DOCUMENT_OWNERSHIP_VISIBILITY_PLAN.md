# Document Ownership-Based Visibility Plan

**Date:** 2025-12-23  
**Status:** Planning Complete - Ready for Implementation

---

## 🎯 Objective

Implement document ownership-based visibility so that:
- **Admin users** can see ALL documents (including existing ones marked as admin-owned)
- **General users** can only see documents they uploaded themselves
- Existing documents (uploaded before this feature) should be marked as admin-owned

---

## 📋 Current State Analysis

### Current Implementation
1. **`GET /api/documents`** endpoint:
   - Currently lists files from filesystem (`/var/www/chatbot_FC/data/documents`)
   - Does NOT use database `document_metadata` table
   - Does NOT filter by ownership
   - Returns all files regardless of user

2. **Database Schema:**
   - `document_metadata` table has `uploaded_by` field (Integer, ForeignKey to users.id)
   - Field is nullable (can be marked as admin for existing documents)
   - Relationship exists: `user = relationship("User", foreign_keys=[uploaded_by])`

3. **Document Upload:**
   - `POST /api/documents/upload` already sets `uploaded_by=current_user.id`
   - Uses `create_document_metadata()` which accepts `uploaded_by` parameter

4. **Document Deletion:**
   - `DELETE /api/documents/{filename}` does NOT check ownership
   - Anyone can delete any document

---

## 🔧 Implementation Plan

### Phase 1: Database Migration - Mark Existing Documents as Admin-Owned

**Goal:** Assign all existing documents (where `uploaded_by` is NULL) to the admin user.

**Steps:**
1. Create migration script: `scripts/migrate_existing_documents_to_admin.py`
2. Script should:
   - Find admin user (user_type = 'operational_admin', username = 'admin')
   - Update all `document_metadata` records where `uploaded_by IS NULL`
   - Set `uploaded_by = admin_user.id`
   - Log how many documents were updated
   - Handle case where admin user doesn't exist (create it or error)

**Files to Create:**
- `scripts/migrate_existing_documents_to_admin.py`

---

### Phase 2: Database CRUD - Add Ownership Filtering Functions

**Goal:** Add CRUD functions to filter documents by ownership.

**Steps:**
1. Add function to `src/database/crud.py`:
   ```python
   def get_user_accessible_documents(
       db: Session,
       user_id: int,
       user_type: str,
       module: Optional[str] = None,
       submodule: Optional[str] = None,
       skip: int = 0,
       limit: int = 100
   ) -> List[DocumentMetadata]:
       """
       Get documents accessible to a user based on ownership.
       
       - Admin users (operational_admin): See ALL documents
       - General users: See only documents they uploaded (uploaded_by = user_id)
       
       Args:
           db: Database session
           user_id: Current user's ID
           user_type: Current user's type (operational_admin or general_user)
           module: Optional module filter
           submodule: Optional submodule filter
           skip: Pagination offset
           limit: Pagination limit
           
       Returns:
           List of DocumentMetadata records
       """
   ```

2. Add function to check document ownership:
   ```python
   def can_user_access_document(
       db: Session,
       user_id: int,
       user_type: str,
       document_id: int
   ) -> bool:
       """
       Check if user can access a specific document.
       
       - Admin users: Can access any document
       - General users: Can only access documents they uploaded
       
       Returns:
           bool: True if user can access, False otherwise
       """
   ```

**Files to Modify:**
- `src/database/crud.py`

---

### Phase 3: API Endpoints - Update to Use Database and Filter by Ownership

**Goal:** Update API endpoints to use database and enforce ownership filtering.

#### 3.1 Update `GET /api/documents`

**Current:** Lists files from filesystem  
**New:** Query database with ownership filtering

**Changes:**
1. Add authentication requirement: `current_user: User = Depends(get_current_user)`
2. Use `get_user_accessible_documents()` instead of filesystem listing
3. Return document metadata with ownership info
4. Include uploader username in response

**Response Format:**
```json
{
  "documents": [
    {
      "id": 1,
      "filename": "document.pdf",
      "size": 1024000,
      "chunks": 50,
      "module": "LOAN",
      "submodule": "New",
      "uploaded_by": 1,
      "uploader_username": "admin",
      "uploaded_at": "2025-12-23T10:00:00Z"
    }
  ],
  "total": 10
}
```

#### 3.2 Update `DELETE /api/documents/{filename}`

**Current:** No ownership check  
**New:** Check ownership before deletion

**Changes:**
1. Add authentication: `current_user: User = Depends(get_current_user)`
2. Find document by filename in database
3. Check ownership using `can_user_access_document()`
4. Return 403 if user doesn't own document (unless admin)
5. Delete from database AND filesystem

**Files to Modify:**
- `src/api/main.py` (endpoints: `GET /api/documents`, `DELETE /api/documents/{filename}`)

---

### Phase 4: Frontend Updates - Display Ownership Info

**Goal:** Update frontend to show ownership information and handle filtered document list.

**Changes:**
1. Update `loadDocuments()` JavaScript function:
   - Already sends auth token (via fetch interceptor)
   - Update to handle new response format with metadata
   - Display uploader username if available
   - Show "You" for current user's documents

2. Update document list display:
   - Show uploader info: "Uploaded by: admin" or "Uploaded by: You"
   - Keep delete button (API will enforce ownership)

**Files to Modify:**
- `src/api/main.py` (HTML/JavaScript section)

---

### Phase 5: Testing

**Test Cases:**

1. **Admin User:**
   - ✅ Can see all documents (including those uploaded by others)
   - ✅ Can delete any document
   - ✅ Sees uploader username for all documents

2. **General User:**
   - ✅ Can only see documents they uploaded
   - ✅ Cannot see documents uploaded by others
   - ✅ Can delete only their own documents
   - ✅ Cannot delete documents uploaded by others (403 error)
   - ✅ Sees "Uploaded by: You" for their documents

3. **Migration:**
   - ✅ All existing documents are marked as admin-owned
   - ✅ New documents are correctly assigned to uploader

4. **Edge Cases:**
   - ✅ User with NULL uploaded_by (shouldn't happen after migration)
   - ✅ Document not found (404)
   - ✅ Unauthorized access (401)
   - ✅ Forbidden access (403)

**Files to Create:**
- `src/tests/integration/test_document_ownership.py`

---

## 📝 Implementation Checklist

### Step 1: Database Migration
- [ ] Create `scripts/migrate_existing_documents_to_admin.py`
- [ ] Test migration script
- [ ] Run migration on production database
- [ ] Verify all documents have `uploaded_by` set

### Step 2: Database CRUD Functions
- [ ] Add `get_user_accessible_documents()` to `src/database/crud.py`
- [ ] Add `can_user_access_document()` to `src/database/crud.py`
- [ ] Write unit tests for new functions

### Step 3: API Endpoints
- [ ] Update `GET /api/documents` to use database and filter by ownership
- [ ] Update `DELETE /api/documents/{filename}` to check ownership
- [ ] Add authentication to both endpoints
- [ ] Update response models if needed

### Step 4: Frontend
- [ ] Update `loadDocuments()` JavaScript function
- [ ] Update document list display to show ownership info
- [ ] Test with admin and general user accounts

### Step 5: Testing
- [ ] Write integration tests for document ownership
- [ ] Test admin user can see all documents
- [ ] Test general user can only see own documents
- [ ] Test deletion permissions
- [ ] Test migration script

### Step 6: Documentation
- [ ] Update API documentation
- [ ] Update user guide if needed
- [ ] Document migration process

---

## 🔍 Technical Details

### Admin User Detection
- Check `user_type == 'operational_admin'`
- Use `is_operational_admin()` from `src/auth/permissions.py`

### Ownership Check Logic
```python
def can_user_access_document(user_id, user_type, document):
    if user_type == 'operational_admin':
        return True  # Admins see all
    return document.uploaded_by == user_id  # Users see only their own
```

### Database Query Example
```python
# For admin users
query = db.query(DocumentMetadata)

# For general users
query = db.query(DocumentMetadata).filter(
    DocumentMetadata.uploaded_by == user_id
)
```

---

## 🚨 Important Notes

1. **Backward Compatibility:**
   - Migration script ensures all existing documents are assigned to admin
   - No data loss expected

2. **Performance:**
   - Database queries are indexed on `uploaded_by` field
   - Should perform well even with many documents

3. **Security:**
   - Ownership checks happen at API level (server-side)
   - Frontend changes are for UX only
   - API enforces all access rules

4. **Migration Safety:**
   - Migration script should be idempotent (safe to run multiple times)
   - Should log all changes
   - Should have rollback option if needed

---

## 📚 Related Files

- `src/api/main.py` - API endpoints
- `src/database/crud.py` - Database CRUD functions
- `src/database/models.py` - DocumentMetadata model
- `src/auth/permissions.py` - User type checking
- `scripts/seed_admin_user.py` - Admin user creation (reference)

---

## ✅ Success Criteria

1. ✅ Admin users can see all documents
2. ✅ General users can only see their own documents
3. ✅ All existing documents are marked as admin-owned
4. ✅ Document deletion respects ownership
5. ✅ Frontend displays ownership information
6. ✅ All tests pass
7. ✅ No security vulnerabilities introduced

---

**Next Steps:** Begin implementation starting with Phase 1 (Database Migration).

