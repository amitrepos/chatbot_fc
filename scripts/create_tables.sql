-- FlexCube Chatbot - Database Schema
-- Phase 7: User Authentication & RBAC
-- Run this after creating database and user

-- ============================================================================
-- 1. USERS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
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

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_user_type ON users(user_type);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- ============================================================================
-- 2. PERMISSIONS TABLE (Role-Based Access Control)
-- ============================================================================
CREATE TABLE IF NOT EXISTS permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    category VARCHAR(50)  -- 'chat', 'documents', 'dashboard', 'users', 'data', 'analytics', 'system'
);

-- Insert predefined permissions
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
('manage_system_settings', 'Modify system configuration', 'system')
ON CONFLICT (name) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_permissions_category ON permissions(category);

-- ============================================================================
-- 3. USER PERMISSIONS TABLE (Many-to-Many: Users ↔ Permissions)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_permissions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    granted_by INTEGER REFERENCES users(id),  -- Admin who granted permission
    
    UNIQUE(user_id, permission_id)
);

CREATE INDEX IF NOT EXISTS idx_user_permissions_user_id ON user_permissions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_permissions_permission_id ON user_permissions(permission_id);

-- ============================================================================
-- 4. ROLE TEMPLATES TABLE (Predefined permission sets)
-- ============================================================================
CREATE TABLE IF NOT EXISTS role_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    is_system_template BOOLEAN DEFAULT TRUE  -- Cannot be deleted
);

-- Insert predefined role templates
INSERT INTO role_templates (name, description, is_system_template) VALUES
('operational_admin', 'Full system access with all privileges', TRUE),
('general_user', 'Standard user with basic chat and document viewing', TRUE)
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- 5. ROLE TEMPLATE PERMISSIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS role_template_permissions (
    id SERIAL PRIMARY KEY,
    role_template_id INTEGER REFERENCES role_templates(id) ON DELETE CASCADE,
    permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
    
    UNIQUE(role_template_id, permission_id)
);

CREATE INDEX IF NOT EXISTS idx_role_template_permissions_template_id ON role_template_permissions(role_template_id);
CREATE INDEX IF NOT EXISTS idx_role_template_permissions_permission_id ON role_template_permissions(permission_id);

-- Insert permissions for role templates
-- Operational Admin: All permissions
INSERT INTO role_template_permissions (role_template_id, permission_id)
SELECT rt.id, p.id
FROM role_templates rt, permissions p
WHERE rt.name = 'operational_admin'
ON CONFLICT DO NOTHING;

-- General User: Basic permissions only
INSERT INTO role_template_permissions (role_template_id, permission_id)
SELECT rt.id, p.id
FROM role_templates rt, permissions p
WHERE rt.name = 'general_user'
  AND p.name IN ('view_chat', 'view_image_query', 'view_documents', 'upload_documents')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- 6. SESSIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,  -- JWT token hash
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_token_hash ON sessions(token_hash);
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at);

-- ============================================================================
-- 7. CONVERSATIONS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),  -- Auto-generated from first question
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations(created_at DESC);

-- ============================================================================
-- 8. QA PAIRS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS qa_pairs (
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

CREATE INDEX IF NOT EXISTS idx_qa_pairs_conversation_id ON qa_pairs(conversation_id);
CREATE INDEX IF NOT EXISTS idx_qa_pairs_user_id ON qa_pairs(user_id);
CREATE INDEX IF NOT EXISTS idx_qa_pairs_created_at ON qa_pairs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_qa_pairs_sources ON qa_pairs USING gin(sources);  -- JSONB index
CREATE INDEX IF NOT EXISTS idx_qa_pairs_expansion ON qa_pairs USING gin(query_expansion);  -- JSONB index

-- Full-text search index for answers (optional, for searching answer content)
CREATE INDEX IF NOT EXISTS idx_qa_pairs_answer_fts ON qa_pairs 
    USING gin(to_tsvector('english', answer));

-- ============================================================================
-- 9. FEEDBACK TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS feedback (
    id SERIAL PRIMARY KEY,
    qa_pair_id INTEGER REFERENCES qa_pairs(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    
    -- Feedback data
    rating INTEGER NOT NULL,  -- 1 = dislike, 2 = like
    feedback_text TEXT,  -- Optional user comment
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(qa_pair_id, user_id)  -- One feedback per user per answer
);

CREATE INDEX IF NOT EXISTS idx_feedback_qa_pair_id ON feedback(qa_pair_id);
CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_rating ON feedback(rating);

-- ============================================================================
-- 10. TRAINING DATA EXPORT TABLE (Future)
-- ============================================================================
CREATE TABLE IF NOT EXISTS training_data_export (
    id SERIAL PRIMARY KEY,
    export_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_pairs INTEGER,
    total_feedback INTEGER,
    export_status VARCHAR(20),  -- 'pending', 'completed', 'failed'
    file_path VARCHAR(500)
);

CREATE INDEX IF NOT EXISTS idx_training_data_export_status ON training_data_export(export_status);
CREATE INDEX IF NOT EXISTS idx_training_data_export_date ON training_data_export(export_date DESC);

-- ============================================================================
-- GRANT PERMISSIONS
-- ============================================================================
-- Grant all privileges to chatbot_user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO chatbot_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO chatbot_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO chatbot_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO chatbot_user;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
SELECT 'Database schema created successfully!' AS status;
SELECT COUNT(*) AS total_tables FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
SELECT COUNT(*) AS total_permissions FROM permissions;
SELECT COUNT(*) AS total_role_templates FROM role_templates;

