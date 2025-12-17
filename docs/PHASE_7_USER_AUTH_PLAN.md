# Phase 7: User Authentication & Feedback System - Implementation Plan

**Status:** Planning Phase  
**Created:** 2025-12-17

---

## 🎯 Objectives

1. **User Authentication**: Users must create account and login before using the system
2. **Role-Based Access Control (RBAC)**: User types with different privileges
   - **Operational Admin**: Full access to all features and admin screens
   - **General User**: Restricted access to basic features
3. **Q&A Storage**: Store all questions and answers in a database
4. **Feedback System**: Like/dislike buttons for each answer (similar to ChatGPT)
5. **Training Data Collection**: All interactions stored for future model fine-tuning

---

## 📊 High-Level Architecture

```
┌─────────────────┐
│   Web Browser   │
│  (Login UI)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   FastAPI App   │
│  ┌───────────┐  │
│  │ Auth API  │  │ ← JWT Tokens
│  └───────────┘  │
│  ┌───────────┐  │
│  │ Query API │  │ ← Protected Routes
│  └───────────┘  │
│  ┌───────────┐  │
│  │FeedbackAPI│  │ ← Like/Dislike
│  └───────────┘  │
└────────┬────────┘
         │
         ├─────────────────┐
         ▼                 ▼
┌─────────────────┐  ┌─────────────────┐
│  PostgreSQL DB  │  │  RAG Pipeline   │
│  - Users        │  │  (Existing)      │
│  - Sessions     │  │                 │
│  - Conversations│  │                 │
│  - Q&A Pairs    │  │                 │
│  - Feedback     │  │                 │
└─────────────────┘  └─────────────────┘
```

---

## 🗄️ Database Schema Design

### **Database Choice: PostgreSQL 16** ✅
- Already running on server
- Production-ready, ACID compliant
- Good for relational data (users, conversations, feedback)
- Supports JSONB columns for flexible metadata
- **Storage Analysis:** Even 1 million Q&A pairs = ~5 GB (very manageable)
- **TEXT columns:** Can store answers up to 1 GB each (more than enough)
- **See:** `docs/STORAGE_ARCHITECTURE_ANALYSIS.md` for detailed analysis

### **Tables:**

#### 1. **users**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,  -- bcrypt hashed
    full_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    user_type VARCHAR(30) DEFAULT 'general_user',  -- 'operational_admin' or 'general_user'
    created_by INTEGER REFERENCES users(id),  -- Admin who created this user
    notes TEXT  -- Admin notes about user
);
```

#### 1a. **permissions** (Role-Based Access Control)
```sql
CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,  -- e.g., 'view_admin_dashboard', 'export_training_data'
    description TEXT,
    category VARCHAR(50)  -- 'dashboard', 'data', 'users', 'system'
);

-- Predefined permissions
INSERT INTO permissions (name, description, category) VALUES
('view_chat', 'Access chat interface to ask questions', 'chat'),
('view_image_query', 'Use image/screenshot query feature', 'chat'),
('view_documents', 'View and manage uploaded documents', 'documents'),
('upload_documents', 'Upload new documents to the system', 'documents'),
('delete_documents', 'Delete documents from the system', 'documents'),
('reindex_documents', 'Rebuild document search index', 'documents'),
('view_admin_dashboard', 'Access admin dashboard with statistics', 'dashboard'),
('view_user_management', 'View and manage user accounts', 'users'),
('create_users', 'Create new user accounts', 'users'),
('edit_users', 'Edit existing user accounts', 'users'),
('deactivate_users', 'Deactivate user accounts', 'users'),
('view_all_conversations', 'View all users conversations (not just own)', 'data'),
('export_training_data', 'Export Q&A pairs for model training', 'data'),
('view_analytics', 'View system analytics and statistics', 'dashboard'),
('manage_system_settings', 'Modify system configuration', 'system');
```

#### 1b. **user_permissions** (Many-to-Many: Users ↔ Permissions)
```sql
CREATE TABLE user_permissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by INTEGER REFERENCES users(id),  -- Admin who granted permission
    
    UNIQUE(user_id, permission_id)
);

-- Indexes for performance
CREATE INDEX idx_user_permissions_user_id ON user_permissions(user_id);
CREATE INDEX idx_user_permissions_permission_id ON user_permissions(permission_id);
```

#### 1c. **role_templates** (Predefined permission sets)
```sql
CREATE TABLE role_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,  -- 'operational_admin', 'general_user'
    description TEXT,
    is_system_template BOOLEAN DEFAULT TRUE  -- Cannot be deleted
);

-- Predefined role templates
INSERT INTO role_templates (name, description, is_system_template) VALUES
('operational_admin', 'Full system access with all privileges', TRUE),
('general_user', 'Standard user with basic chat and document viewing', TRUE);

-- Link templates to permissions
CREATE TABLE role_template_permissions (
    id SERIAL PRIMARY KEY,
    role_template_id INTEGER REFERENCES role_templates(id) ON DELETE CASCADE,
    permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
    
    UNIQUE(role_template_id, permission_id)
);

-- Operational Admin: All permissions
-- General User: Only basic permissions (view_chat, view_image_query, view_documents, upload_documents)
```

#### 2. **sessions**
```sql
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,  -- JWT token hash
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT
);
```

#### 3. **conversations**
```sql
CREATE TABLE conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),  -- Auto-generated from first question
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### 4. **qa_pairs**
```sql
CREATE TABLE qa_pairs (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- Question data
    question TEXT NOT NULL,
    question_type VARCHAR(20) DEFAULT 'text',  -- 'text' or 'image'
    image_path VARCHAR(500),  -- If image query
    
    -- Answer data
    answer TEXT NOT NULL,
    sources JSONB,  -- Array of source filenames
    answer_source_type VARCHAR(50),  -- 'rag', 'general_knowledge', 'vision'
    
    -- Query expansion metadata (for training)
    query_expansion JSONB,  -- Original + expanded queries
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_time_seconds DECIMAL(10, 2)
);
```

#### 5. **feedback**
```sql
CREATE TABLE feedback (
    id SERIAL PRIMARY KEY,
    qa_pair_id INTEGER REFERENCES qa_pairs(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- Feedback data
    rating INTEGER NOT NULL,  -- 1 = dislike, 2 = like
    feedback_text TEXT,  -- Optional user comment
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(qa_pair_id, user_id)  -- One feedback per user per answer
);
```

#### 6. **training_data_export** (Future)
```sql
CREATE TABLE training_data_export (
    id SERIAL PRIMARY KEY,
    export_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_pairs INTEGER,
    total_feedback INTEGER,
    export_status VARCHAR(20),  -- 'pending', 'completed', 'failed'
    file_path VARCHAR(500)
);
```

---

## 🔐 Authentication Flow

### **1. User Registration**
```
POST /api/auth/register
Body: {
    "username": "john_doe",
    "email": "john@example.com",
    "password": "SecurePass123!",
    "full_name": "John Doe"
}

Response: {
    "user_id": 1,
    "username": "john_doe",
    "message": "User created successfully"
}
```

### **2. User Login**
```
POST /api/auth/login
Body: {
    "username": "john_doe",  // or email
    "password": "SecurePass123!"
}

Response: {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 86400,  // 24 hours
    "user": {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com",
        "user_type": "general_user",  // or "operational_admin"
        "permissions": ["view_chat", "view_image_query", "view_documents"]  // User's permissions
    }
}
```

### **3. Protected Routes (Permission-Based)**
- All endpoints require JWT token in header:
  ```
  Authorization: Bearer <token>
  ```
- **Permission checking:** Each endpoint checks if user has required permission
- **Role-based access:** Different endpoints accessible based on user_type and permissions

### **4. Permission Assignment**
- **On Registration:** New users automatically get `general_user` role template permissions
- **Admin Assignment:** Operational admins can assign/revoke permissions to any user
- **Role Templates:** Quick assignment of permission sets via role templates

### **4. Token Refresh** (Optional)
```
POST /api/auth/refresh
Headers: Authorization: Bearer <token>
```

---

## 🔒 Security Considerations

### **Password Security**
- Use `bcrypt` for password hashing (cost factor: 12)
- Never store plaintext passwords
- Enforce password policy:
  - Minimum 8 characters
  - At least 1 uppercase, 1 lowercase, 1 number
  - Optional: special character

### **JWT Tokens**
- Secret key stored in environment variable
- Token expiration: 24 hours (configurable)
- Token stored in `HttpOnly` cookie (more secure) OR localStorage
- Include user_id, username, user_type, permissions in token payload
- Permissions cached in token to reduce database queries

### **API Security**
- Rate limiting per user (e.g., 100 queries/hour)
- CORS restrictions (only allow specific origins in production)
- Input validation and sanitization
- SQL injection prevention (use SQLAlchemy ORM)

### **Session Management**
- Store active sessions in database
- Logout invalidates token
- "Logout all devices" option

---

## 📡 API Endpoints

### **Authentication Endpoints**
| Endpoint | Method | Auth Required | Description |
|----------|--------|---------------|-------------|
| `/api/auth/register` | POST | No | Create new user account |
| `/api/auth/login` | POST | No | Login and get JWT token |
| `/api/auth/logout` | POST | Yes | Invalidate current token |
| `/api/auth/me` | GET | Yes | Get current user info |
| `/api/auth/refresh` | POST | Yes | Refresh JWT token |

### **Query Endpoints (Updated)**
| Endpoint | Method | Auth Required | Permission Required | Description |
|----------|--------|---------------|---------------------|-------------|
| `/api/query` | POST | Yes | `view_chat` | Store Q&A in database |
| `/api/query/image` | POST | Yes | `view_image_query` | Store Q&A + image path |

### **Feedback Endpoints**
| Endpoint | Method | Auth Required | Description |
|----------|--------|---------------|-------------|
| `/api/feedback` | POST | Yes | Submit like/dislike |
| `/api/feedback/{qa_id}` | GET | Yes | Get feedback for Q&A |
| `/api/feedback/{qa_id}` | DELETE | Yes | Remove feedback |

### **User Data Endpoints**
| Endpoint | Method | Auth Required | Permission Required | Description |
|----------|--------|---------------|---------------------|-------------|
| `/api/conversations` | GET | Yes | `view_chat` | List user's conversations |
| `/api/conversations/{id}` | GET | Yes | `view_chat` | Get conversation with Q&A pairs |
| `/api/conversations/{id}` | DELETE | Yes | `view_chat` | Delete conversation |
| `/api/qa-pairs` | GET | Yes | `view_chat` | List user's Q&A pairs (paginated) |

### **Document Management Endpoints**
| Endpoint | Method | Auth Required | Permission Required | Description |
|----------|--------|---------------|---------------------|-------------|
| `/api/documents` | GET | Yes | `view_documents` | List all documents |
| `/api/documents/upload` | POST | Yes | `upload_documents` | Upload new document |
| `/api/documents/{filename}` | DELETE | Yes | `delete_documents` | Delete document |
| `/api/documents/reindex` | POST | Yes | `reindex_documents` | Rebuild search index |

### **Admin Endpoints** (Operational Admin Only)
| Endpoint | Method | Auth Required | Permission Required | Description |
|----------|--------|---------------|---------------------|-------------|
| `/api/admin/dashboard` | GET | Yes | `view_admin_dashboard` | Get admin dashboard stats |
| `/api/admin/users` | GET | Yes | `view_user_management` | List all users |
| `/api/admin/users` | POST | Yes | `create_users` | Create new user |
| `/api/admin/users/{id}` | GET | Yes | `view_user_management` | Get user details |
| `/api/admin/users/{id}` | PUT | Yes | `edit_users` | Update user (including permissions) |
| `/api/admin/users/{id}` | DELETE | Yes | `deactivate_users` | Deactivate user |
| `/api/admin/users/{id}/permissions` | GET | Yes | `view_user_management` | Get user permissions |
| `/api/admin/users/{id}/permissions` | POST | Yes | `edit_users` | Grant permission to user |
| `/api/admin/users/{id}/permissions/{perm_id}` | DELETE | Yes | `edit_users` | Revoke permission from user |
| `/api/admin/conversations` | GET | Yes | `view_all_conversations` | List all users' conversations |
| `/api/admin/qa-pairs` | GET | Yes | `export_training_data` | Export all Q&A for training |
| `/api/admin/analytics` | GET | Yes | `view_analytics` | Get system analytics |
| `/api/admin/feedback-stats` | GET | Yes | `view_analytics` | Feedback statistics |
| `/api/admin/training-data/export` | POST | Yes | `export_training_data` | Export training data as JSON/CSV |
| `/api/admin/system/settings` | GET | Yes | `manage_system_settings` | Get system settings |
| `/api/admin/system/settings` | PUT | Yes | `manage_system_settings` | Update system settings |

---

## 🎨 UI Changes

### **1. Login/Signup Page**
- **Route:** `/login` (default landing page)
- **Features:**
  - Login form (username/email + password)
  - "Don't have account? Sign up" link
  - Signup form (username, email, password, confirm password, full name)
  - Password strength indicator
  - "Remember me" checkbox
  - Forgot password link (future)

### **2. Main Chat Interface (Updated)**
- **Protected Route:** `/chat` (redirect to `/login` if not authenticated)
- **New Features:**
  - User profile dropdown (top right)
    - Username display
    - "My Conversations" link
    - "Logout" button
  - **Like/Dislike buttons** below each answer:
    - 👍 Like (green)
    - 👎 Dislike (red)
    - Visual feedback when clicked
    - Optional: "Add comment" textarea
  - **Conversation History Sidebar:**
    - List of past conversations
    - Click to load conversation
    - Delete conversation option

### **3. My Conversations Page**
- **Route:** `/conversations`
- **Permission Required:** `view_chat`
- **Features:**
  - List all user's conversations (paginated)
  - Search/filter conversations
  - View Q&A pairs for each conversation
  - Export conversation as JSON/CSV (for user)

### **4. Admin Dashboard** (Operational Admin Only)
- **Route:** `/admin/dashboard`
- **Permission Required:** `view_admin_dashboard`
- **Features:**
  - System statistics:
    - Total users (active/inactive)
    - Total conversations
    - Total Q&A pairs
    - Total feedback (likes/dislikes)
    - Average response time
    - Most active users
    - Popular questions
  - Charts and graphs (using Chart.js or similar)
  - Recent activity feed
  - Quick actions (export data, manage users)

### **5. User Management** (Operational Admin Only)
- **Route:** `/admin/users`
- **Permission Required:** `view_user_management`
- **Features:**
  - List all users with filters (active/inactive, user_type)
  - Search users by username/email
  - Create new user (`create_users` permission)
  - Edit user details (`edit_users` permission)
  - Deactivate/activate users (`deactivate_users` permission)
  - **Permission Management:**
    - View user's current permissions
    - Grant/revoke individual permissions
    - Assign role templates (quick permission sets)
  - User activity log (last login, conversation count)

### **6. Analytics & Reports** (Operational Admin Only)
- **Route:** `/admin/analytics`
- **Permission Required:** `view_analytics`
- **Features:**
  - Query analytics:
    - Most asked questions
    - Questions by category
    - Average answer quality (based on feedback)
    - Response time trends
  - User engagement metrics
  - Document usage statistics
  - Feedback analysis (like/dislike ratios)

### **7. Training Data Export** (Operational Admin Only)
- **Route:** `/admin/training-data`
- **Permission Required:** `export_training_data`
- **Features:**
  - Filter Q&A pairs by:
    - Date range
    - User type
    - Feedback (only liked, only disliked, all)
    - Source type (RAG, general knowledge, vision)
  - Export formats: JSON, CSV
  - Preview before export
  - Download or email export file
  - Export history (previous exports)

### **8. System Settings** (Operational Admin Only)
- **Route:** `/admin/settings`
- **Permission Required:** `manage_system_settings`
- **Features:**
  - RAG pipeline settings
  - Query expansion toggle
  - Rate limiting configuration
  - Email notifications (future)
  - Backup settings

---

## 🔐 Role-Based Access Control (RBAC) System

### **User Types**

#### **1. Operational Admin**
- **Default Permissions:** All permissions granted
- **Access:**
  - ✅ All chat features
  - ✅ All document management
  - ✅ Admin dashboard
  - ✅ User management
  - ✅ Analytics & reports
  - ✅ Training data export
  - ✅ System settings
- **Use Cases:**
  - System administrators
  - IT support staff
  - Data analysts preparing training sets

#### **2. General User**
- **Default Permissions:**
  - ✅ `view_chat` - Ask questions
  - ✅ `view_image_query` - Upload screenshots
  - ✅ `view_documents` - View document list
  - ✅ `upload_documents` - Upload new documents
  - ❌ `delete_documents` - Cannot delete
  - ❌ `reindex_documents` - Cannot rebuild index
  - ❌ All admin features
- **Use Cases:**
  - End users asking FlexCube questions
  - Support staff (read-only access)
  - Regular employees

### **Permission System**

#### **Permission Categories:**

1. **Chat Permissions:**
   - `view_chat` - Access chat interface
   - `view_image_query` - Use image/screenshot queries

2. **Document Permissions:**
   - `view_documents` - View document list
   - `upload_documents` - Upload documents
   - `delete_documents` - Delete documents
   - `reindex_documents` - Rebuild search index

3. **Dashboard Permissions:**
   - `view_admin_dashboard` - Access admin dashboard

4. **User Management Permissions:**
   - `view_user_management` - View user list
   - `create_users` - Create new users
   - `edit_users` - Edit users and permissions
   - `deactivate_users` - Deactivate users

5. **Data Permissions:**
   - `view_all_conversations` - View all users' conversations
   - `export_training_data` - Export Q&A pairs

6. **Analytics Permissions:**
   - `view_analytics` - View analytics and reports

7. **System Permissions:**
   - `manage_system_settings` - Modify system configuration

### **Permission Assignment Flow**

```
1. User registers → Gets 'general_user' role template
2. Role template → Automatically grants default permissions
3. Admin can:
   - Grant additional permissions individually
   - Revoke permissions
   - Assign different role template
   - Create custom permission sets
```

### **Permission Checking in Code**

#### **FastAPI Dependency Example:**
```python
from fastapi import Depends, HTTPException
from src.auth.dependencies import get_current_user, require_permission

@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("upload_documents"))
):
    # User has 'upload_documents' permission
    # Proceed with upload
    pass

@app.get("/api/admin/dashboard")
async def admin_dashboard(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permission("view_admin_dashboard"))
):
    # Only operational admins can access
    # Return dashboard data
    pass
```

#### **UI Permission Checking:**
```javascript
// Check if user has permission
function hasPermission(permission) {
    const user = JSON.parse(localStorage.getItem('user'));
    return user.permissions.includes(permission);
}

// Show/hide UI elements
if (hasPermission('view_admin_dashboard')) {
    document.getElementById('admin-menu').style.display = 'block';
}

// Disable buttons
if (!hasPermission('delete_documents')) {
    document.getElementById('delete-btn').disabled = true;
}
```

### **Default Permission Sets**

#### **Operational Admin Template:**
```json
{
    "name": "operational_admin",
    "permissions": [
        "view_chat",
        "view_image_query",
        "view_documents",
        "upload_documents",
        "delete_documents",
        "reindex_documents",
        "view_admin_dashboard",
        "view_user_management",
        "create_users",
        "edit_users",
        "deactivate_users",
        "view_all_conversations",
        "export_training_data",
        "view_analytics",
        "manage_system_settings"
    ]
}
```

#### **General User Template:**
```json
{
    "name": "general_user",
    "permissions": [
        "view_chat",
        "view_image_query",
        "view_documents",
        "upload_documents"
    ]
}
```

### **Permission Management UI (Admin Only)**

**User Edit Screen:**
- Display current permissions (checkboxes)
- Grant/revoke individual permissions
- Quick actions:
  - "Assign Operational Admin" button
  - "Assign General User" button
  - "Custom Permissions" mode

**Permission Audit:**
- Track who granted/revoked permissions
- Log permission changes
- Show permission history per user

---

## 📦 Implementation Steps

### **Step 1: Database Setup** (2-3 hours)
1. Create PostgreSQL database: `flexcube_chatbot`
2. Create database user: `chatbot_user`
3. Run migration scripts to create tables
4. Set up SQLAlchemy models
5. Test database connection

### **Step 2: Authentication & RBAC Module** (6-7 hours)
1. Install dependencies: `python-jose[cryptography]`, `passlib[bcrypt]`, `python-multipart`
2. Create `src/auth/` module:
   - `models.py` - SQLAlchemy models (User, Permission, UserPermission, RoleTemplate)
   - `auth.py` - JWT token generation/validation (include permissions in payload)
   - `password.py` - Password hashing utilities
   - `permissions.py` - Permission checking utilities
   - `dependencies.py` - FastAPI dependencies:
     - `get_current_user` - Extract user from JWT
     - `require_permission(permission_name)` - Check if user has permission
     - `require_user_type(user_type)` - Check if user has specific type
3. Create auth endpoints in `src/api/main.py`
4. Add middleware for token validation
5. Initialize default permissions and role templates in database

### **Step 3: Database Models** (4-5 hours)
1. Create `src/database/` module:
   - `database.py` - Database connection (SQLAlchemy)
   - `models.py` - All table models:
     - User, Session, Conversation, QAPair, Feedback
     - Permission, UserPermission, RoleTemplate, RoleTemplatePermission
   - `crud.py` - Database operations (Create, Read, Update, Delete)
   - `permissions_crud.py` - Permission management operations
2. Create migration scripts (Alembic)
3. Seed database with default permissions and role templates

### **Step 4: Update Query Endpoints** (2-3 hours)
1. Add authentication requirement to `/api/query` and `/api/query/image`
2. Store Q&A pairs in database after each query
3. Link Q&A to conversation (create new or use existing)
4. Store query expansion metadata for training

### **Step 5: Feedback Endpoints** (2-3 hours)
1. Create `/api/feedback` POST endpoint
2. Validate user owns the Q&A pair
3. Store feedback in database
4. Update Q&A pair with feedback count

### **Step 6: UI Updates** (8-10 hours)
1. Create login/signup page (HTML/JS)
2. Add JWT token storage (localStorage or cookie)
3. Add token to all API requests (interceptor)
4. Add like/dislike buttons to answer display
5. Add conversation history sidebar
6. Add user profile dropdown (with user_type display)
7. **Role-based UI rendering:**
   - Hide/show features based on permissions
   - Show "Admin" menu item only for operational_admin
   - Disable buttons if user lacks permission
8. **Admin UI Pages:**
   - Admin Dashboard (`/admin/dashboard`)
   - User Management (`/admin/users`)
   - Analytics (`/admin/analytics`)
   - Training Data Export (`/admin/training-data`)
   - System Settings (`/admin/settings`)
9. Protect routes (redirect to login if not authenticated)
10. Permission-based route guards (redirect if no permission)

### **Step 7: RBAC Implementation** (4-5 hours)
1. Create permission checking utilities
2. Add permission dependencies to all endpoints
3. Implement role template assignment on user creation
4. Create admin endpoints for permission management
5. Add permission checking in UI (show/hide features)
6. Test permission system thoroughly

### **Step 8: Testing** (4-5 hours)
1. Unit tests for auth module
2. Unit tests for permission system
3. Integration tests for protected endpoints
4. Test permission-based access control
5. Test feedback system
6. Test conversation storage
7. Security testing (SQL injection, XSS, CSRF)
8. Test role templates and permission assignment

### **Step 9: Documentation** (1-2 hours)
1. Update API documentation
2. Create user guide
3. Update `Updates.md`

**Total Estimated Time: 30-40 hours** (increased due to RBAC complexity)

---

## 🔧 Technical Stack Additions

### **New Python Dependencies**
```txt
# Authentication
python-jose[cryptography]==3.3.0  # JWT tokens
passlib[bcrypt]==1.7.4            # Password hashing
python-multipart==0.0.6            # Form data (already installed)

# Database
sqlalchemy==2.0.23                # ORM
psycopg2-binary==2.9.9             # PostgreSQL driver
alembic==1.13.1                    # Database migrations
```

### **Database Connection String**
```python
# Environment variable
DATABASE_URL=postgresql://chatbot_user:password@localhost:5432/flexcube_chatbot
```

---

## 📈 Data Collection for Training

### **Export Format (Future)**
```json
{
    "export_date": "2025-12-17T10:00:00Z",
    "total_pairs": 1250,
    "pairs": [
        {
            "question": "How many users logged in?",
            "answer": "Based on the documentation...",
            "sources": ["OracleFlexcubeManual.pdf"],
            "query_expansion": {
                "original": "How many users logged in?",
                "expanded": ["Count of authenticated users", "User login statistics"],
                "key_terms": {
                    "logged in": ["signed in", "authenticated"],
                    "users": ["accounts", "sessions"]
                }
            },
            "feedback": {
                "likes": 5,
                "dislikes": 1,
                "user_feedback": [
                    {"user_id": 1, "rating": 2, "comment": "Very helpful"},
                    {"user_id": 2, "rating": 1, "comment": "Not accurate"}
                ]
            },
            "metadata": {
                "processing_time": 12.5,
                "answer_source": "rag",
                "created_at": "2025-12-17T09:30:00Z"
            }
        }
    ]
}
```

---

## 🚀 Deployment Considerations

### **Database Backup**
- Daily automated backups of PostgreSQL
- Backup location: `/var/backups/flexcube_chatbot/`
- Retention: 30 days

### **Migration Strategy**
- Use Alembic for version-controlled migrations
- Test migrations on staging first
- Rollback plan for each migration

### **Environment Variables**
```bash
# .env file
DATABASE_URL=postgresql://chatbot_user:password@localhost:5432/flexcube_chatbot
JWT_SECRET_KEY=<generate-strong-secret>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
BCRYPT_ROUNDS=12
```

---

## ✅ Success Criteria

1. ✅ Users can register and login
2. ✅ **Role-based access control working:**
   - Operational admins have full access
   - General users have restricted access
   - Permissions enforced on all endpoints
3. ✅ All queries require authentication
4. ✅ All Q&A pairs stored in database
5. ✅ Users can like/dislike answers
6. ✅ Conversation history accessible
7. ✅ **Admin features accessible:**
   - Admin dashboard visible only to admins
   - User management functional
   - Analytics and reports working
   - Training data export working
8. ✅ Data exportable for training
9. ✅ Security best practices followed
10. ✅ UI is intuitive and responsive
11. ✅ **Permission system:**
    - Permissions can be granted/revoked
    - Role templates work correctly
    - UI shows/hides features based on permissions

---

## 🔄 Future Enhancements

1. **Password Reset**: Email-based password reset flow
2. **Two-Factor Authentication**: Optional 2FA for admin users
3. **User Roles**: Admin, moderator, regular user
4. **Analytics Dashboard**: View feedback statistics, popular questions
5. **Export Tools**: Admin UI to export training data
6. **API Rate Limiting**: Per-user query limits
7. **Session Management**: View active sessions, logout all devices

---

## 📝 Next Steps

1. **Review this plan** with stakeholders
2. **Approve database schema** design
3. **Set up PostgreSQL database** and user
4. **Start with Step 1** (Database Setup)
5. **Iterate through steps** sequentially
6. **Test thoroughly** before production deployment

---

---

## 📋 RBAC Enhancement Summary

### **Key Additions:**

1. **User Types:**
   - `operational_admin` - Full system access
   - `general_user` - Restricted access

2. **Permission System:**
   - 15+ granular permissions
   - Permission-based endpoint protection
   - Role templates for quick assignment
   - Individual permission grant/revoke

3. **New Database Tables:**
   - `permissions` - All available permissions
   - `user_permissions` - User ↔ Permission mapping
   - `role_templates` - Predefined permission sets
   - `role_template_permissions` - Template ↔ Permission mapping

4. **Admin Features:**
   - Admin Dashboard (`/admin/dashboard`)
   - User Management (`/admin/users`)
   - Analytics & Reports (`/admin/analytics`)
   - Training Data Export (`/admin/training-data`)
   - System Settings (`/admin/settings`)

5. **Security:**
   - Permissions included in JWT token
   - Permission checking on every protected endpoint
   - UI elements hidden/disabled based on permissions
   - Audit trail for permission changes

### **Permission Categories:**
- **Chat:** `view_chat`, `view_image_query`
- **Documents:** `view_documents`, `upload_documents`, `delete_documents`, `reindex_documents`
- **Dashboard:** `view_admin_dashboard`
- **Users:** `view_user_management`, `create_users`, `edit_users`, `deactivate_users`
- **Data:** `view_all_conversations`, `export_training_data`
- **Analytics:** `view_analytics`
- **System:** `manage_system_settings`

---

**Ready to proceed?** Let me know which step you'd like to start with!

