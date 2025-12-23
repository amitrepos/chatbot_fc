"""
Unit Tests for Module/Submodule CRUD Operations

Tests CRUD operations for document metadata with module/submodule filtering.
Following TDD: These tests will fail initially until CRUD functions are implemented.
"""

import pytest
from src.database.models import DocumentMetadata, User
from src.database.crud import (
    create_document_metadata,
    get_document_metadata,
    get_distinct_modules,
    get_distinct_submodules,
    update_document_metadata
)
from src.auth.password import hash_password


class TestModuleCRUD:
    """Unit tests for module/submodule CRUD operations."""
    
    def test_create_document_metadata(self, db_session):
        """Test creating document metadata record."""
        # Arrange: Create user
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=hash_password("TestPass123!"),
            user_type="general_user"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Act: Create document metadata
        metadata = create_document_metadata(
            db=db_session,
            filename="test_loan_new.pdf",
            file_path="/var/www/chatbot_FC/data/documents/test_loan_new.pdf",
            module="Loan",
            submodule="New",
            uploaded_by=user.id,
            file_size=1024,
            file_type="pdf"
        )
        
        # Assert: Record created in database with correct values
        assert metadata.id is not None
        assert metadata.filename == "test_loan_new.pdf"
        assert metadata.file_path == "/var/www/chatbot_FC/data/documents/test_loan_new.pdf"
        assert metadata.module == "Loan"
        assert metadata.submodule == "New"
        assert metadata.uploaded_by == user.id
        assert metadata.file_size == 1024
        assert metadata.file_type == "pdf"
    
    def test_get_document_metadata_by_file_path(self, db_session):
        """Test retrieving document metadata by file path."""
        # Arrange: Create user and metadata
        user = User(
            username="testuser2",
            email="test2@example.com",
            password_hash=hash_password("TestPass123!"),
            user_type="general_user"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        metadata = create_document_metadata(
            db=db_session,
            filename="test.pdf",
            file_path="/var/www/chatbot_FC/data/documents/test.pdf",
            module="Loan",
            submodule="New",
            uploaded_by=user.id,
            file_size=1024,
            file_type="pdf"
        )
        
        # Act: Get metadata by file path
        retrieved = get_document_metadata(db_session, "/var/www/chatbot_FC/data/documents/test.pdf")
        
        # Assert: Returns correct metadata object
        assert retrieved is not None
        assert retrieved.id == metadata.id
        assert retrieved.filename == "test.pdf"
        assert retrieved.module == "Loan"
        assert retrieved.submodule == "New"
    
    def test_get_document_metadata_not_found(self, db_session):
        """Test retrieving non-existent document metadata."""
        # Arrange: No metadata created
        
        # Act: Get metadata for non-existent file path
        retrieved = get_document_metadata(db_session, "/nonexistent/path.pdf")
        
        # Assert: Returns None
        assert retrieved is None
    
    def test_get_distinct_modules(self, db_session):
        """Test getting all distinct module names (modules are unique)."""
        # Arrange: Create user
        user = User(
            username="testuser3",
            email="test3@example.com",
            password_hash=hash_password("TestPass123!"),
            user_type="general_user"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Create 3 documents:
        #   - doc1: module="Loan", submodule="New"
        #   - doc2: module="Account", submodule="Create"
        #   - doc3: module="Loan", submodule="Existing" (same unique module name, different submodule)
        create_document_metadata(
            db=db_session,
            filename="doc1.pdf",
            file_path="/var/www/chatbot_FC/data/documents/doc1.pdf",
            module="Loan",
            submodule="New",
            uploaded_by=user.id,
            file_size=1024,
            file_type="pdf"
        )
        create_document_metadata(
            db=db_session,
            filename="doc2.pdf",
            file_path="/var/www/chatbot_FC/data/documents/doc2.pdf",
            module="Account",
            submodule="Create",
            uploaded_by=user.id,
            file_size=1024,
            file_type="pdf"
        )
        create_document_metadata(
            db=db_session,
            filename="doc3.pdf",
            file_path="/var/www/chatbot_FC/data/documents/doc3.pdf",
            module="Loan",
            submodule="Existing",
            uploaded_by=user.id,
            file_size=1024,
            file_type="pdf"
        )
        
        # Act: Get distinct modules
        modules = get_distinct_modules(db_session)
        
        # Assert: Returns ["Account", "Loan"] (sorted, unique module names - modules are unique)
        assert len(modules) == 2
        assert "Account" in modules
        assert "Loan" in modules
        assert modules == sorted(modules)  # Should be sorted
    
    def test_get_distinct_modules_empty(self, db_session):
        """Test getting distinct modules when none exist."""
        # Arrange: No documents with modules
        
        # Act: Get distinct modules
        modules = get_distinct_modules(db_session)
        
        # Assert: Returns empty list []
        assert modules == []
    
    def test_get_distinct_submodules_all(self, db_session):
        """Test getting all distinct submodule names (submodules are NOT unique - same name can exist under different modules)."""
        # Arrange: Create user
        user = User(
            username="testuser4",
            email="test4@example.com",
            password_hash=hash_password("TestPass123!"),
            user_type="general_user"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Create documents:
        #   - doc1: module="Loan", submodule="New"
        #   - doc2: module="Account", submodule="New" (same submodule name "New", but different unique module)
        #   - doc3: module="Loan", submodule="Existing"
        create_document_metadata(
            db=db_session,
            filename="doc1.pdf",
            file_path="/var/www/chatbot_FC/data/documents/doc1.pdf",
            module="Loan",
            submodule="New",
            uploaded_by=user.id,
            file_size=1024,
            file_type="pdf"
        )
        create_document_metadata(
            db=db_session,
            filename="doc2.pdf",
            file_path="/var/www/chatbot_FC/data/documents/doc2.pdf",
            module="Account",
            submodule="New",
            uploaded_by=user.id,
            file_size=1024,
            file_type="pdf"
        )
        create_document_metadata(
            db=db_session,
            filename="doc3.pdf",
            file_path="/var/www/chatbot_FC/data/documents/doc3.pdf",
            module="Loan",
            submodule="Existing",
            uploaded_by=user.id,
            file_size=1024,
            file_type="pdf"
        )
        
        # Act: Get all distinct submodules
        submodules = get_distinct_submodules(db_session)
        
        # Assert: Returns ["Existing", "New"] (sorted, unique submodule names - "New" appears once even though it exists under both "Loan" and "Account")
        assert len(submodules) == 2
        assert "Existing" in submodules
        assert "New" in submodules
        assert submodules == sorted(submodules)  # Should be sorted
    
    def test_get_distinct_submodules_filtered_by_module(self, db_session):
        """Test getting submodules filtered by module (module+submodule combinations are unique)."""
        # Arrange: Create user
        user = User(
            username="testuser5",
            email="test5@example.com",
            password_hash=hash_password("TestPass123!"),
            user_type="general_user"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Create documents:
        #   - doc1: module="Loan", submodule="New"
        #   - doc2: module="Loan", submodule="Existing"
        #   - doc3: module="Account", submodule="New" (same submodule name, but different unique module)
        create_document_metadata(
            db=db_session,
            filename="doc1.pdf",
            file_path="/var/www/chatbot_FC/data/documents/doc1.pdf",
            module="Loan",
            submodule="New",
            uploaded_by=user.id,
            file_size=1024,
            file_type="pdf"
        )
        create_document_metadata(
            db=db_session,
            filename="doc2.pdf",
            file_path="/var/www/chatbot_FC/data/documents/doc2.pdf",
            module="Loan",
            submodule="Existing",
            uploaded_by=user.id,
            file_size=1024,
            file_type="pdf"
        )
        create_document_metadata(
            db=db_session,
            filename="doc3.pdf",
            file_path="/var/www/chatbot_FC/data/documents/doc3.pdf",
            module="Account",
            submodule="New",
            uploaded_by=user.id,
            file_size=1024,
            file_type="pdf"
        )
        
        # Act: Get submodules filtered by module="Loan"
        submodules = get_distinct_submodules(db_session, module="Loan")
        
        # Assert: Returns ["Existing", "New"] (only submodules for "Loan" module, not "Account" + "New")
        assert len(submodules) == 2
        assert "Existing" in submodules
        assert "New" in submodules
        assert submodules == sorted(submodules)
    
    def test_update_document_metadata_module(self, db_session):
        """Test updating module for a document."""
        # Arrange: Create user and metadata
        user = User(
            username="testuser6",
            email="test6@example.com",
            password_hash=hash_password("TestPass123!"),
            user_type="general_user"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        metadata = create_document_metadata(
            db=db_session,
            filename="test.pdf",
            file_path="/var/www/chatbot_FC/data/documents/test.pdf",
            module="Loan",
            submodule="New",
            uploaded_by=user.id,
            file_size=1024,
            file_type="pdf"
        )
        
        # Act: Update module
        updated = update_document_metadata(
            db=db_session,
            file_path="/var/www/chatbot_FC/data/documents/test.pdf",
            module="Account"
        )
        
        # Assert: Module updated to "Account"
        assert updated is not None
        assert updated.module == "Account"
        assert updated.submodule == "New"  # Submodule unchanged
    
    def test_update_document_metadata_submodule(self, db_session):
        """Test updating submodule for a document."""
        # Arrange: Create user and metadata
        user = User(
            username="testuser7",
            email="test7@example.com",
            password_hash=hash_password("TestPass123!"),
            user_type="general_user"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        metadata = create_document_metadata(
            db=db_session,
            filename="test.pdf",
            file_path="/var/www/chatbot_FC/data/documents/test.pdf",
            module="Loan",
            submodule="New",
            uploaded_by=user.id,
            file_size=1024,
            file_type="pdf"
        )
        
        # Act: Update submodule
        updated = update_document_metadata(
            db=db_session,
            file_path="/var/www/chatbot_FC/data/documents/test.pdf",
            submodule="Existing"
        )
        
        # Assert: Submodule updated to "Existing"
        assert updated is not None
        assert updated.submodule == "Existing"
        assert updated.module == "Loan"  # Module unchanged
    
    def test_update_document_metadata_both(self, db_session):
        """Test updating both module and submodule."""
        # Arrange: Create user and metadata
        user = User(
            username="testuser8",
            email="test8@example.com",
            password_hash=hash_password("TestPass123!"),
            user_type="general_user"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        metadata = create_document_metadata(
            db=db_session,
            filename="test.pdf",
            file_path="/var/www/chatbot_FC/data/documents/test.pdf",
            module="Loan",
            submodule="New",
            uploaded_by=user.id,
            file_size=1024,
            file_type="pdf"
        )
        
        # Act: Update both module and submodule
        updated = update_document_metadata(
            db=db_session,
            file_path="/var/www/chatbot_FC/data/documents/test.pdf",
            module="Account",
            submodule="Create"
        )
        
        # Assert: Both updated
        assert updated is not None
        assert updated.module == "Account"
        assert updated.submodule == "Create"
    
    def test_update_document_metadata_not_found(self, db_session):
        """Test updating non-existent document metadata."""
        # Arrange: No metadata created
        
        # Act: Update non-existent document
        updated = update_document_metadata(
            db=db_session,
            file_path="/nonexistent/path.pdf",
            module="Loan"
        )
        
        # Assert: Returns None
        assert updated is None


