-- Add document_metadata table for module/submodule filtering
-- This table stores document categorization information

-- ============================================================================
-- DOCUMENT METADATA TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS document_metadata (
    id SERIAL PRIMARY KEY,
    filename VARCHAR(500) NOT NULL,  -- Original filename
    file_path TEXT NOT NULL UNIQUE,  -- Full path to document
    module VARCHAR(100),  -- Module name (e.g., "Loan", "Account", "Transaction") - unique modules
    submodule VARCHAR(100),  -- Submodule name (e.g., "New", "Existing", "Transfer") - NOT unique, can exist under different modules
    uploaded_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_indexed_at TIMESTAMP,
    chunk_count INTEGER DEFAULT 0,
    file_size BIGINT,  -- Size in bytes
    file_type VARCHAR(20)  -- pdf, docx, txt
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_document_metadata_filename ON document_metadata(filename);
CREATE INDEX IF NOT EXISTS idx_document_metadata_module ON document_metadata(module);
CREATE INDEX IF NOT EXISTS idx_document_metadata_submodule ON document_metadata(submodule);
CREATE INDEX IF NOT EXISTS idx_document_metadata_module_submodule ON document_metadata(module, submodule);
CREATE INDEX IF NOT EXISTS idx_document_metadata_uploaded_by ON document_metadata(uploaded_by);
CREATE INDEX IF NOT EXISTS idx_document_metadata_uploaded_at ON document_metadata(uploaded_at DESC);

-- Grant permissions
GRANT ALL PRIVILEGES ON document_metadata TO chatbot_user;
GRANT ALL PRIVILEGES ON SEQUENCE document_metadata_id_seq TO chatbot_user;

-- ============================================================================
-- VERIFICATION
-- ============================================================================
SELECT 'Document metadata table created successfully!' AS status;
SELECT COUNT(*) AS total_tables FROM information_schema.tables 
WHERE table_schema = 'public' AND table_name = 'document_metadata';


