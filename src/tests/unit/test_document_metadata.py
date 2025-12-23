"""
Unit Tests for DocumentMetadata SQLAlchemy Model

Tests the DocumentMetadata model for module/submodule filtering feature.
Following TDD: These tests will fail initially until the model is implemented.
"""

import pytest
from sqlalchemy.exc import IntegrityError
from src.database.models import DocumentMetadata, User
from src.database.database import Base
from src.auth.password import hash_password


class TestDocumentMetadataModel:
    """Unit tests for DocumentMetadata SQLAlchemy model."""
    
    def test_create_document_metadata_with_module_submodule(self, db_session):
        """Test creating document metadata with module and submodule."""
        # Arrange: Create a user first
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=hash_password("TestPass123!"),
            user_type="general_user"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Act: Create document metadata with module and submodule
        metadata = DocumentMetadata(
            filename="test_loan_new.pdf",
            file_path="/var/www/chatbot_FC/data/documents/test_loan_new.pdf",
            module="Loan",
            submodule="New",
            uploaded_by=user.id,
            file_size=1024,
            file_type="pdf",
            chunk_count=10
        )
        db_session.add(metadata)
        db_session.commit()
        db_session.refresh(metadata)
        
        # Assert: Metadata created with correct values
        assert metadata.id is not None
        assert metadata.filename == "test_loan_new.pdf"
        assert metadata.file_path == "/var/www/chatbot_FC/data/documents/test_loan_new.pdf"
        assert metadata.module == "Loan"
        assert metadata.submodule == "New"
        assert metadata.uploaded_by == user.id
        assert metadata.file_size == 1024
        assert metadata.file_type == "pdf"
        assert metadata.chunk_count == 10
    
    def test_create_document_metadata_without_module_submodule(self, db_session):
        """Test creating document metadata without module/submodule (backward compatible)."""
        # Arrange: Create a user first
        user = User(
            username="testuser2",
            email="test2@example.com",
            password_hash=hash_password("TestPass123!"),
            user_type="general_user"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Act: Create document metadata without module/submodule
        metadata = DocumentMetadata(
            filename="test_no_module.pdf",
            file_path="/var/www/chatbot_FC/data/documents/test_no_module.pdf",
            uploaded_by=user.id,
            file_size=2048,
            file_type="pdf",
            chunk_count=15
        )
        db_session.add(metadata)
        db_session.commit()
        db_session.refresh(metadata)
        
        # Assert: Metadata created with module=None, submodule=None
        assert metadata.id is not None
        assert metadata.filename == "test_no_module.pdf"
        assert metadata.module is None
        assert metadata.submodule is None
        assert metadata.uploaded_by == user.id
    
    def test_document_metadata_unique_file_path(self, db_session):
        """Test that file_path must be unique."""
        # Arrange: Create a user first
        user = User(
            username="testuser3",
            email="test3@example.com",
            password_hash=hash_password("TestPass123!"),
            user_type="general_user"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Create first metadata with file_path
        metadata1 = DocumentMetadata(
            filename="test.pdf",
            file_path="/var/www/chatbot_FC/data/documents/test.pdf",
            uploaded_by=user.id,
            file_size=1024,
            file_type="pdf"
        )
        db_session.add(metadata1)
        db_session.commit()
        
        # Act: Try to create another with same file_path
        metadata2 = DocumentMetadata(
            filename="test2.pdf",
            file_path="/var/www/chatbot_FC/data/documents/test.pdf",  # Same file_path
            uploaded_by=user.id,
            file_size=2048,
            file_type="pdf"
        )
        db_session.add(metadata2)
        
        # Assert: Raises IntegrityError
        with pytest.raises(IntegrityError):
            db_session.commit()
    
    def test_document_metadata_foreign_key_user(self, db_session):
        """Test foreign key relationship with User."""
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
        
        # Act: Create metadata with uploaded_by=user.id
        metadata = DocumentMetadata(
            filename="test.pdf",
            file_path="/var/www/chatbot_FC/data/documents/test.pdf",
            uploaded_by=user.id,
            file_size=1024,
            file_type="pdf"
        )
        db_session.add(metadata)
        db_session.commit()
        db_session.refresh(metadata)
        
        # Assert: Relationship works, can access metadata.user
        assert metadata.user is not None
        assert metadata.user.id == user.id
        assert metadata.user.username == "testuser4"
    
    def test_document_metadata_module_submodule_can_be_null(self, db_session):
        """Test that module and submodule can be NULL (backward compatible)."""
        # Arrange: Create a user first
        user = User(
            username="testuser5",
            email="test5@example.com",
            password_hash=hash_password("TestPass123!"),
            user_type="general_user"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Act: Create metadata with module=None, submodule=None
        metadata = DocumentMetadata(
            filename="test.pdf",
            file_path="/var/www/chatbot_FC/data/documents/test.pdf",
            module=None,
            submodule=None,
            uploaded_by=user.id,
            file_size=1024,
            file_type="pdf"
        )
        db_session.add(metadata)
        db_session.commit()
        db_session.refresh(metadata)
        
        # Assert: No error, both fields are NULL
        assert metadata.id is not None
        assert metadata.module is None
        assert metadata.submodule is None


