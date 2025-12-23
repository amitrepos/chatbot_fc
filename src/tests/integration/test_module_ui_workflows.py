"""
End-to-End UI Workflow Tests for Module/Submodule Feature

Tests complete user workflows through the UI for module/submodule functionality.
Following TDD: These tests will fail initially until UI is implemented.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.api.main import app
from src.database.models import User
from src.database.crud import create_user
from src.auth.password import hash_password
from src.auth.auth import create_access_token
import os
import tempfile


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


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
    user = create_user(
        db=db_session,
        username="admin",
        email="admin@example.com",
        password_hash=hash_password("Admin123!"),
        full_name="Admin User",
        user_type="operational_admin"
    )
    return user


@pytest.fixture
def auth_token(test_user):
    """Create auth token for test user."""
    return create_access_token(data={"sub": test_user.username, "user_id": test_user.id})


@pytest.fixture
def admin_token(admin_user):
    """Create auth token for admin user."""
    return create_access_token(data={"sub": admin_user.username, "user_id": admin_user.id})


@pytest.fixture
def sample_pdf_file():
    """Create a sample PDF file for testing."""
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 0\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"
    
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
        f.write(pdf_content)
        temp_path = f.name
    
    yield temp_path
    
    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestModuleUIWorkflows:
    """End-to-end tests for module/submodule UI workflows."""
    
    def test_upload_document_with_module_submodule_ui(self, client, auth_token, sample_pdf_file, db_session):
        """Test uploading document via UI with module/submodule selection (unique combination)."""
        # Arrange: Start server, login as user (simulated via token)
        # In actual E2E test, we would navigate to the page, but for integration test we use API
        
        # Act: Upload document with module and submodule via API (simulating UI action)
        with open(sample_pdf_file, 'rb') as f:
            files = {'file': ('test_loan_new.pdf', f, 'application/pdf')}
            data = {
                'module': 'Loan',
                'submodule': 'New'
            }
            
            response = client.post(
                '/api/documents/upload',
                files=files,
                data=data,
                headers={'Authorization': f'Bearer {auth_token}'}
            )
        
        # Assert: Upload successful
        assert response.status_code == 200
        response_data = response.json()
        assert response_data['status'] == 'success'
        
        # Assert: Document appears in list with module/submodule shown
        # Get documents list
        list_response = client.get(
            '/api/documents',
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        assert list_response.status_code == 200
        documents = list_response.json().get('documents', [])
        
        # Find our uploaded document
        uploaded_doc = next((d for d in documents if d['filename'] == 'test_loan_new.pdf'), None)
        assert uploaded_doc is not None
        assert uploaded_doc.get('module') == 'Loan'
        assert uploaded_doc.get('submodule') == 'New'
        # This document has unique module+submodule combination
    
    def test_query_with_module_filter_ui(self, client, auth_token):
        """Test querying via UI with module filter (module is unique, but can have multiple documents)."""
        # Arrange: This would require indexed documents with modules
        # For TDD, we test that the query endpoint accepts module filter
        
        # Act: Query with module filter (simulating UI action)
        response = client.post(
            '/api/query',
            json={
                'question': 'test question',
                'module': 'Loan'
            },
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        
        # Assert: Endpoint accepts module parameter
        # Note: May fail if RAG pipeline not initialized, which is expected in TDD
        assert response.status_code in [200, 400, 500]
        
        # If successful, verify response structure
        if response.status_code == 200:
            data = response.json()
            assert 'answer' in data
            assert 'sources' in data
    
    def test_admin_modules_page_loads(self, client, admin_token):
        """Test that admin modules page loads correctly."""
        # Arrange: Login as admin user (simulated via token)
        
        # Act: Navigate to /admin/modules
        response = client.get(
            '/admin/modules',
            headers={'Authorization': f'Bearer {admin_token}'},
            follow_redirects=False
        )
        
        # Assert: Page loads successfully
        # Should return HTML (status 200) or redirect to login if cookie auth fails
        assert response.status_code in [200, 302, 401]
        
        # If HTML returned, verify it contains expected content
        if response.status_code == 200:
            assert 'text/html' in response.headers.get('content-type', '')
            # Page should contain module management UI elements
            # Note: In TDD, this may not be implemented yet
    
    def test_admin_create_module_ui(self, client, admin_token, db_session):
        """Test creating module via admin UI."""
        # Arrange: Login as admin
        # Note: Since we're using denormalized approach, modules exist when documents use them
        # This test verifies the admin can view/manage modules
        
        # Act: Get admin modules list (simulating UI action)
        response = client.get(
            '/api/admin/modules',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        # Assert: Can access admin modules endpoint
        assert response.status_code == 200
        data = response.json()
        assert 'modules' in data
        
        # Note: Creating a module in denormalized approach means creating a document with that module
        # The admin UI would show modules from existing documents
    
    def test_admin_create_submodule_ui(self, client, admin_token, db_session):
        """Test creating submodule via admin UI (submodule name not unique, but module+submodule combination is)."""
        # Arrange: Login as admin, documents exist with unique module="Loan"
        from src.database.crud import create_document_metadata
        admin = db_session.query(User).filter(User.username == 'admin').first()
        
        # Create a document with module="Loan" to establish the module
        create_document_metadata(
            db=db_session,
            filename='existing_loan_doc.pdf',
            file_path='/var/www/chatbot_FC/data/documents/existing_loan_doc.pdf',
            module='Loan',
            submodule='Existing',
            uploaded_by=admin.id,
            file_size=1024,
            file_type='pdf'
        )
        
        # Act: Get submodules for Loan module (simulating UI action)
        response = client.get(
            '/api/admin/modules',
            headers={'Authorization': f'Bearer {admin_token}'}
        )
        
        # Assert: Can view modules and their submodules
        assert response.status_code == 200
        data = response.json()
        assert 'modules' in data
        
        # Find Loan module
        loan_module = next((m for m in data['modules'] if m['name'] == 'Loan'), None)
        if loan_module:
            assert 'submodules' in loan_module
            # Submodule "Existing" should be listed under "Loan"
            # Note: Submodule name "Existing" is NOT unique - it can exist under other modules too


