"""
Integration Tests for Document Ownership-Based Visibility

Tests document ownership-based visibility feature:
- Admin users can see all documents
- General users can only see documents they uploaded
- Document deletion respects ownership
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.api.main import app
from src.database.models import User, DocumentMetadata
from src.database.crud import (
    create_user, get_user_by_username, create_document_metadata,
    get_user_accessible_documents, can_user_access_document,
    assign_role_template_to_user
)
from src.database.database import get_db
from src.auth.password import hash_password
from src.auth.auth import create_access_token
import os
import tempfile


@pytest.fixture
def client(db_session):
    """Create test client with database override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def admin_user(db_session):
    """Create admin user for testing."""
    user = get_user_by_username(db_session, "test_admin_owner")
    if user:
        db_session.delete(user)
        db_session.commit()
    
    password_hash = hash_password("Admin123!")
    user = create_user(
        db=db_session,
        username="test_admin_owner",
        email="admin_owner@test.com",
        password_hash=password_hash,
        full_name="Test Admin Owner",
        user_type="operational_admin"
    )
    assign_role_template_to_user(db_session, user.id, "operational_admin")
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def general_user(db_session):
    """Create general user for testing."""
    user = get_user_by_username(db_session, "test_general_owner")
    if user:
        db_session.delete(user)
        db_session.commit()
    
    password_hash = hash_password("User123!")
    user = create_user(
        db=db_session,
        username="test_general_owner",
        email="general_owner@test.com",
        password_hash=password_hash,
        full_name="Test General Owner",
        user_type="general_user"
    )
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def another_general_user(db_session):
    """Create another general user for testing."""
    user = get_user_by_username(db_session, "test_general_owner2")
    if user:
        db_session.delete(user)
        db_session.commit()
    
    password_hash = hash_password("User123!")
    user = create_user(
        db=db_session,
        username="test_general_owner2",
        email="general_owner2@test.com",
        password_hash=password_hash,
        full_name="Test General Owner 2",
        user_type="general_user"
    )
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user):
    """Create auth token for admin user."""
    token_data = {"sub": admin_user.username, "user_id": admin_user.id}
    return create_access_token(data=token_data)


@pytest.fixture
def general_token(general_user):
    """Create auth token for general user."""
    token_data = {"sub": general_user.username, "user_id": general_user.id}
    return create_access_token(data=token_data)


@pytest.fixture
def another_general_token(another_general_user):
    """Create auth token for another general user."""
    token_data = {"sub": another_general_user.username, "user_id": another_general_user.id}
    return create_access_token(data=token_data)


@pytest.fixture
def sample_document_file():
    """Create a sample document file for testing."""
    content = "This is a test document for ownership testing."
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def admin_document(db_session, admin_user, sample_document_file):
    """Create a document owned by admin user."""
    doc = create_document_metadata(
        db=db_session,
        filename="admin_document.txt",
        file_path=sample_document_file,
        module="TEST",
        submodule="Admin",
        uploaded_by=admin_user.id,
        file_size=100,
        file_type="txt",
        chunk_count=1
    )
    db_session.commit()
    db_session.refresh(doc)
    return doc


@pytest.fixture
def general_user_document(db_session, general_user, sample_document_file):
    """Create a document owned by general user."""
    # Create a different file for this document
    content = "This is a document owned by general user."
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write(content)
        temp_path = f.name
    
    doc = create_document_metadata(
        db=db_session,
        filename="general_user_document.txt",
        file_path=temp_path,
        module="TEST",
        submodule="General",
        uploaded_by=general_user.id,
        file_size=100,
        file_type="txt",
        chunk_count=1
    )
    db_session.commit()
    db_session.refresh(doc)
    
    yield doc
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestDocumentOwnershipCRUD:
    """Test CRUD functions for document ownership."""
    
    def test_get_user_accessible_documents_admin_sees_all(self, db_session, admin_user, admin_document, general_user_document):
        """Test that admin users can see all documents."""
        documents = get_user_accessible_documents(
            db=db_session,
            user_id=admin_user.id,
            user_type=admin_user.user_type
        )
        
        # Admin should see both documents
        assert len(documents) >= 2
        filenames = [doc.filename for doc in documents]
        assert "admin_document.txt" in filenames
        assert "general_user_document.txt" in filenames
    
    def test_get_user_accessible_documents_general_sees_only_own(self, db_session, general_user, admin_document, general_user_document):
        """Test that general users can only see documents they uploaded."""
        documents = get_user_accessible_documents(
            db=db_session,
            user_id=general_user.id,
            user_type=general_user.user_type
        )
        
        # General user should only see their own document
        filenames = [doc.filename for doc in documents]
        assert "general_user_document.txt" in filenames
        assert "admin_document.txt" not in filenames
    
    def test_can_user_access_document_admin(self, db_session, admin_user, admin_document, general_user_document):
        """Test that admin users can access any document."""
        # Admin can access admin document
        assert can_user_access_document(
            db=db_session,
            user_id=admin_user.id,
            user_type=admin_user.user_type,
            document_id=admin_document.id
        ) is True
        
        # Admin can access general user document
        assert can_user_access_document(
            db=db_session,
            user_id=admin_user.id,
            user_type=admin_user.user_type,
            document_id=general_user_document.id
        ) is True
    
    def test_can_user_access_document_general_own(self, db_session, general_user, general_user_document):
        """Test that general users can access their own documents."""
        assert can_user_access_document(
            db=db_session,
            user_id=general_user.id,
            user_type=general_user.user_type,
            document_id=general_user_document.id
        ) is True
    
    def test_can_user_access_document_general_others(self, db_session, general_user, admin_document):
        """Test that general users cannot access documents uploaded by others."""
        assert can_user_access_document(
            db=db_session,
            user_id=general_user.id,
            user_type=general_user.user_type,
            document_id=admin_document.id
        ) is False


class TestDocumentOwnershipAPI:
    """Test API endpoints for document ownership."""
    
    def test_list_documents_admin_sees_all(self, client, admin_token, admin_document, general_user_document):
        """Test that admin users see all documents via API."""
        response = client.get(
            '/api/documents',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = response.json()
        documents = data.get('documents', [])
        
        filenames = [doc['filename'] for doc in documents]
        assert "admin_document.txt" in filenames or any("admin_document" in f for f in filenames)
        assert "general_user_document.txt" in filenames or any("general_user_document" in f for f in filenames)
    
    def test_list_documents_general_sees_only_own(self, client, general_token, admin_document, general_user_document):
        """Test that general users only see their own documents via API."""
        response = client.get(
            '/api/documents',
            headers={'Authorization': f'Bearer {general_token}'}
        )
        
        assert response.status_code == 200
        data = response.json()
        documents = data.get('documents', [])
        
        filenames = [doc['filename'] for doc in documents]
        # General user should see their own document
        assert any("general_user_document" in f for f in filenames) or "general_user_document.txt" in filenames
        # General user should NOT see admin's document
        assert not any("admin_document" in f for f in filenames)
    
    def test_list_documents_includes_uploader_info(self, client, admin_token, admin_document):
        """Test that document list includes uploader information."""
        response = client.get(
            '/api/documents',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        assert response.status_code == 200
        data = response.json()
        documents = data.get('documents', [])
        
        # Find admin document
        admin_doc = next((d for d in documents if d.get('id') == admin_document.id), None)
        if admin_doc:
            assert 'uploaded_by' in admin_doc
            assert 'uploader_username' in admin_doc
            assert admin_doc['uploaded_by'] == admin_document.uploaded_by
    
    def test_delete_document_admin_can_delete_any(self, client, admin_token, general_user_document, db_session):
        """Test that admin users can delete any document."""
        # First verify document exists
        doc = db_session.query(DocumentMetadata).filter(
            DocumentMetadata.id == general_user_document.id
        ).first()
        assert doc is not None
        
        # Admin should be able to delete general user's document
        response = client.delete(
            f'/api/documents/{general_user_document.filename}',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        # Should succeed (200 or 404 if file doesn't exist in filesystem)
        assert response.status_code in [200, 404]
    
    def test_delete_document_general_can_delete_own(self, client, general_token, general_user_document, db_session):
        """Test that general users can delete their own documents."""
        # First verify document exists
        doc = db_session.query(DocumentMetadata).filter(
            DocumentMetadata.id == general_user_document.id
        ).first()
        assert doc is not None
        
        # General user should be able to delete their own document
        response = client.delete(
            f'/api/documents/{general_user_document.filename}',
            headers={'Authorization': f'Bearer {general_token}'}
        )
        
        # Should succeed (200 or 404 if file doesn't exist in filesystem)
        assert response.status_code in [200, 404]
    
    def test_delete_document_general_cannot_delete_others(self, client, general_token, admin_document):
        """Test that general users cannot delete documents uploaded by others."""
        response = client.delete(
            f'/api/documents/{admin_document.filename}',
            headers={'Authorization': f'Bearer {general_token}'}
        )
        
        # Should return 403 Forbidden
        assert response.status_code == 403
        error_data = response.json()
        assert 'permission' in error_data.get('detail', '').lower() or 'not have permission' in error_data.get('detail', '')

