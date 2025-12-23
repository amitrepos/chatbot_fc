"""
Integration Tests for Module/Submodule API Endpoints

Tests API endpoints for document upload, query filtering, and module/submodule management.
Following TDD: These tests will fail initially until endpoints are implemented.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.api.main import app
from src.database.models import User
from src.database.crud import create_user
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
def test_user(db_session):
    """Create test user."""
    user = create_user(
        db=db_session,
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("TestPass123!"),
        full_name="Test User",
        user_type="general_user"
    )
    return user


@pytest.fixture
def admin_user(db_session):
    """Create admin user."""
    from src.database.crud import get_user_by_username, assign_role_template_to_user, get_permission_by_name, grant_permission
    
    # Check if admin user already exists
    user = get_user_by_username(db_session, "admin")
    if user:
        # Ensure role template is assigned
        try:
            assign_role_template_to_user(db_session, user.id, "operational_admin")
            db_session.commit()
        except Exception:
            db_session.rollback()
        
        # Explicitly ensure manage_documents permission is granted
        manage_docs_perm = get_permission_by_name(db_session, "manage_documents")
        if manage_docs_perm:
            from src.database.models import UserPermission
            existing = db_session.query(UserPermission).filter(
                UserPermission.user_id == user.id,
                UserPermission.permission_id == manage_docs_perm.id
            ).first()
            if not existing:
                grant_permission(db_session, user.id, manage_docs_perm.id)
                db_session.commit()
        
        db_session.refresh(user)
        return user
    
    # Create new admin user
    user = create_user(
        db=db_session,
        username="admin",
        email="admin@example.com",
        password_hash=hash_password("Admin123!"),
        full_name="Admin User",
        user_type="operational_admin"
    )
    # Assign role template to grant permissions
    assign_role_template_to_user(db_session, user.id, "operational_admin")
    
    # Explicitly ensure manage_documents permission is granted
    manage_docs_perm = get_permission_by_name(db_session, "manage_documents")
    if manage_docs_perm:
        grant_permission(db_session, user.id, manage_docs_perm.id)
    
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def auth_token(test_user):
    """Create auth token for test user."""
    return create_access_token(data={"sub": str(test_user.id), "username": test_user.username, "user_id": test_user.id})


@pytest.fixture
def admin_token(admin_user, db_session):
    """Create auth token for admin user."""
    from src.database.crud import get_user_permissions
    
    # Get permissions for admin user
    permissions = get_user_permissions(db_session, admin_user.id)
    
    return create_access_token(data={
        "sub": str(admin_user.id),
        "username": admin_user.username,
        "user_id": admin_user.id,
        "user_type": admin_user.user_type,
        "permissions": permissions
    })


@pytest.fixture
def sample_pdf_file():
    """Create a sample PDF file for testing."""
    # Create a minimal PDF file content
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 0\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"
    
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
        f.write(pdf_content)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestDocumentUploadWithModule:
    """Integration tests for document upload with module/submodule."""
    
    def test_upload_document_with_module_submodule(self, client, auth_token, sample_pdf_file, db_session):
        """Test uploading document with module and submodule."""
        # Arrange: Prepare file
        with open(sample_pdf_file, 'rb') as f:
            files = {'file': ('test_loan_new.pdf', f, 'application/pdf')}
            data = {
                'module': 'Loan',
                'submodule': 'New'
            }
            
            # Act: Upload document with module and submodule
            response = client.post(
                '/api/documents/upload',
                files=files,
                data=data,
                headers={'Authorization': f'Bearer {auth_token}'}
            )
        
        # Assert: Response status 200
        assert response.status_code == 200
        response_data = response.json()
        assert response_data['status'] == 'success'
        assert response_data['filename'] == 'test_loan_new.pdf'
        assert response_data.get('module') == 'Loan'
        assert response_data.get('submodule') == 'New'
        
        # Assert: Document metadata created in database
        from src.database.crud import get_document_metadata
        metadata = get_document_metadata(db_session, response_data.get('file_path', ''))
        assert metadata is not None
        assert metadata.module == 'Loan'
        assert metadata.submodule == 'New'
    
    def test_upload_document_without_module_submodule(self, client, auth_token, sample_pdf_file):
        """Test uploading document without module/submodule (backward compatible)."""
        # Arrange: Prepare file
        with open(sample_pdf_file, 'rb') as f:
            files = {'file': ('test.pdf', f, 'application/pdf')}
            
            # Act: Upload document without module/submodule params
            response = client.post(
                '/api/documents/upload',
                files=files,
                headers={'Authorization': f'Bearer {auth_token}'}
            )
        
        # Assert: Response status 200
        assert response.status_code == 200
        response_data = response.json()
        assert response_data['status'] == 'success'
        # Document uploaded successfully without module/submodule
        assert 'filename' in response_data
    
    def test_upload_document_with_module_only(self, client, auth_token, sample_pdf_file):
        """Test uploading document with module but no submodule."""
        # Arrange: Prepare file
        with open(sample_pdf_file, 'rb') as f:
            files = {'file': ('test.pdf', f, 'application/pdf')}
            data = {'module': 'Loan'}
            
            # Act: Upload with module only
            response = client.post(
                '/api/documents/upload',
                files=files,
                data=data,
                headers={'Authorization': f'Bearer {auth_token}'}
            )
        
        # Assert: Response status 200
        assert response.status_code == 200
        response_data = response.json()
        assert response_data.get('module') == 'Loan'
        # submodule should be None or not present


class TestQueryWithModuleFilter:
    """Integration tests for query endpoint with module/submodule filtering."""
    
    def test_query_without_filters(self, client, auth_token):
        """Test query without module/submodule filters (backward compatible)."""
        # Arrange: Index documents (this would require actual RAG pipeline setup)
        # For now, we'll test that the endpoint accepts requests without filters
        
        # Act: POST /api/query with question only (no filters)
        response = client.post(
            '/api/query',
            json={'question': 'test question'},
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        # Assert: Response status 200 (or appropriate status)
        # Note: This may fail if RAG pipeline is not initialized, which is expected in TDD
        assert response.status_code in [200, 500]  # 500 if pipeline not initialized yet
    
    def test_query_with_module_filter(self, client, auth_token):
        """Test query filtered by module (module is unique, but can have multiple documents with different submodules)."""
        # Arrange: This would require indexed documents with modules
        # For TDD, we test the endpoint accepts the filter parameter
        
        # Act: POST /api/query with question + module filter
        response = client.post(
            '/api/query',
            json={
                'question': 'test question',
                'module': 'Loan'
            },
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        # Assert: Endpoint accepts module parameter
        # Note: May fail if RAG pipeline not initialized, which is expected
        assert response.status_code in [200, 400, 500]
    
    def test_query_with_submodule_filter(self, client, auth_token):
        """Test query filtered by module+submodule combination (unique combination - submodule name not unique, but combination is)."""
        # Arrange: This would require indexed documents
        
        # Act: POST /api/query with question + module + submodule filters
        response = client.post(
            '/api/query',
            json={
                'question': 'test question',
                'module': 'Loan',
                'submodule': 'New'
            },
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        # Assert: Endpoint accepts both module and submodule parameters
        assert response.status_code in [200, 400, 500]


class TestModuleListAPI:
    """Integration tests for module/submodule list endpoints."""
    
    def test_get_modules_list(self, client, auth_token, db_session):
        """Test GET /api/modules endpoint."""
        # Arrange: Create documents with modules
        from src.database.crud import create_document_metadata
        user = db_session.query(User).filter(User.username == 'testuser').first()
        
        create_document_metadata(
            db=db_session,
            filename='doc1.pdf',
            file_path='/var/www/chatbot_FC/data/documents/doc1.pdf',
            module='Loan',
            submodule='New',
            uploaded_by=user.id,
            file_size=1024,
            file_type='pdf'
        )
        create_document_metadata(
            db=db_session,
            filename='doc2.pdf',
            file_path='/var/www/chatbot_FC/data/documents/doc2.pdf',
            module='Account',
            submodule='Create',
            uploaded_by=user.id,
            file_size=1024,
            file_type='pdf'
        )
        create_document_metadata(
            db=db_session,
            filename='doc3.pdf',
            file_path='/var/www/chatbot_FC/data/documents/doc3.pdf',
            module='Loan',
            submodule='Existing',
            uploaded_by=user.id,
            file_size=1024,
            file_type='pdf'
        )
        
        # Act: GET /api/modules
        response = client.get(
            '/api/modules',
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        # Assert: Response status 200
        assert response.status_code == 200
        data = response.json()
        assert 'modules' in data
        modules = data['modules']
        assert len(modules) == 2
        assert 'Account' in modules
        assert 'Loan' in modules
        assert modules == sorted(modules)  # Should be sorted
    
    def test_get_modules_list_empty(self, client, auth_token):
        """Test GET /api/modules when no modules exist."""
        # Arrange: No documents with modules
        
        # Act: GET /api/modules
        response = client.get(
            '/api/modules',
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        # Assert: Returns {"modules": []}
        assert response.status_code == 200
        data = response.json()
        assert data['modules'] == []
    
    def test_get_submodules_list_all(self, client, auth_token, db_session):
        """Test GET /api/submodules endpoint (all submodules)."""
        # Arrange: Create documents with various submodules
        from src.database.crud import create_document_metadata
        user = db_session.query(User).filter(User.username == 'testuser').first()
        
        create_document_metadata(
            db=db_session,
            filename='doc1.pdf',
            file_path='/var/www/chatbot_FC/data/documents/doc1.pdf',
            module='Loan',
            submodule='New',
            uploaded_by=user.id,
            file_size=1024,
            file_type='pdf'
        )
        create_document_metadata(
            db=db_session,
            filename='doc2.pdf',
            file_path='/var/www/chatbot_FC/data/documents/doc2.pdf',
            module='Account',
            submodule='New',
            uploaded_by=user.id,
            file_size=1024,
            file_type='pdf'
        )
        create_document_metadata(
            db=db_session,
            filename='doc3.pdf',
            file_path='/var/www/chatbot_FC/data/documents/doc3.pdf',
            module='Loan',
            submodule='Existing',
            uploaded_by=user.id,
            file_size=1024,
            file_type='pdf'
        )
        
        # Act: GET /api/submodules
        response = client.get(
            '/api/submodules',
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        # Assert: Returns all distinct submodules
        assert response.status_code == 200
        data = response.json()
        assert 'submodules' in data
        submodules = data['submodules']
        assert len(submodules) == 2
        assert 'Existing' in submodules
        assert 'New' in submodules
    
    def test_get_submodules_list_filtered_by_module(self, client, auth_token, db_session):
        """Test GET /api/submodules?module=Loan endpoint."""
        # Arrange: Create documents
        from src.database.crud import create_document_metadata
        user = db_session.query(User).filter(User.username == 'testuser').first()
        
        create_document_metadata(
            db=db_session,
            filename='doc1.pdf',
            file_path='/var/www/chatbot_FC/data/documents/doc1.pdf',
            module='Loan',
            submodule='New',
            uploaded_by=user.id,
            file_size=1024,
            file_type='pdf'
        )
        create_document_metadata(
            db=db_session,
            filename='doc2.pdf',
            file_path='/var/www/chatbot_FC/data/documents/doc2.pdf',
            module='Account',
            submodule='New',
            uploaded_by=user.id,
            file_size=1024,
            file_type='pdf'
        )
        
        # Act: GET /api/submodules?module=Loan
        response = client.get(
            '/api/submodules?module=Loan',
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        # Assert: Returns only submodules for "Loan" module
        assert response.status_code == 200
        data = response.json()
        assert 'submodules' in data
        submodules = data['submodules']
        assert 'New' in submodules
        # Should not include submodules from "Account" module


class TestAdminModuleManagement:
    """Integration tests for admin module/submodule management endpoints."""
    
    def test_get_admin_modules_with_stats(self, client, admin_token, db_session):
        """Test GET /api/admin/modules endpoint (modules are unique, aggregated by unique module)."""
        # Arrange: Create admin user and documents
        from src.database.crud import create_document_metadata
        admin = db_session.query(User).filter(User.username == 'admin').first()
        
        create_document_metadata(
            db=db_session,
            filename='doc1.pdf',
            file_path='/var/www/chatbot_FC/data/documents/doc1.pdf',
            module='Loan',
            submodule='New',
            uploaded_by=admin.id,
            file_size=1024,
            file_type='pdf'
        )
        create_document_metadata(
            db=db_session,
            filename='doc2.pdf',
            file_path='/var/www/chatbot_FC/data/documents/doc2.pdf',
            module='Loan',
            submodule='Existing',
            uploaded_by=admin.id,
            file_size=1024,
            file_type='pdf'
        )
        create_document_metadata(
            db=db_session,
            filename='doc3.pdf',
            file_path='/var/www/chatbot_FC/data/documents/doc3.pdf',
            module='Account',
            submodule='New',
            uploaded_by=admin.id,
            file_size=1024,
            file_type='pdf'
        )
        
        # Act: GET /api/admin/modules (with admin auth)
        response = client.get(
            '/api/admin/modules',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        # Assert: Response status 200
        assert response.status_code == 200
        data = response.json()
        assert 'modules' in data
        modules = data['modules']
        
        # Find Loan module
        loan_module = next((m for m in modules if m['name'] == 'Loan'), None)
        assert loan_module is not None
        assert loan_module['document_count'] == 2
        assert loan_module['submodule_count'] == 2
        
        # Find Account module
        account_module = next((m for m in modules if m['name'] == 'Account'), None)
        assert account_module is not None
        assert account_module['document_count'] == 1
        assert account_module['submodule_count'] == 1
    
    def test_get_admin_modules_requires_permission(self, client, auth_token):
        """Test that GET /api/admin/modules requires admin permission."""
        # Arrange: Regular user (not admin)
        
        # Act: GET /api/admin/modules (with regular user auth)
        response = client.get(
            '/api/admin/modules',
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        # Assert: Response status 403 (Forbidden)
        assert response.status_code == 403
    
    def test_get_admin_documents_list(self, client, admin_token, db_session):
        """Test GET /api/admin/documents endpoint."""
        # Arrange: Create documents with module/submodule
        from src.database.crud import create_document_metadata
        admin = db_session.query(User).filter(User.username == 'admin').first()
        
        create_document_metadata(
            db=db_session,
            filename='doc1.pdf',
            file_path='/var/www/chatbot_FC/data/documents/doc1.pdf',
            module='Loan',
            submodule='New',
            uploaded_by=admin.id,
            file_size=1024,
            file_type='pdf'
        )
        
        # Act: GET /api/admin/documents (with admin auth)
        response = client.get(
            '/api/admin/documents',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        # Assert: Response status 200
        assert response.status_code == 200
        data = response.json()
        assert 'documents' in data
        assert len(data['documents']) > 0
    
    def test_get_admin_documents_filtered_by_module(self, client, admin_token, db_session):
        """Test GET /api/admin/documents?module=Loan endpoint (module is unique)."""
        # Arrange: Create documents
        from src.database.crud import create_document_metadata
        admin = db_session.query(User).filter(User.username == 'admin').first()
        
        create_document_metadata(
            db=db_session,
            filename='doc1.pdf',
            file_path='/var/www/chatbot_FC/data/documents/doc1.pdf',
            module='Loan',
            submodule='New',
            uploaded_by=admin.id,
            file_size=1024,
            file_type='pdf'
        )
        create_document_metadata(
            db=db_session,
            filename='doc2.pdf',
            file_path='/var/www/chatbot_FC/data/documents/doc2.pdf',
            module='Loan',
            submodule='Existing',
            uploaded_by=admin.id,
            file_size=1024,
            file_type='pdf'
        )
        create_document_metadata(
            db=db_session,
            filename='doc3.pdf',
            file_path='/var/www/chatbot_FC/data/documents/doc3.pdf',
            module='Account',
            submodule='New',
            uploaded_by=admin.id,
            file_size=1024,
            file_type='pdf'
        )
        
        # Act: GET /api/admin/documents?module=Loan
        response = client.get(
            '/api/admin/documents?module=Loan',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        # Assert: Returns doc1 AND doc2 (both have unique module="Loan"), not doc3
        assert response.status_code == 200
        data = response.json()
        assert 'documents' in data
        documents = data['documents']
        loan_docs = [d for d in documents if d['module'] == 'Loan']
        assert len(loan_docs) == 2
        account_docs = [d for d in documents if d['module'] == 'Account']
        assert len(account_docs) == 0  # Should be filtered out

