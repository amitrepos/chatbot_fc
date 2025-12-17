"""
Integration Tests for Admin Endpoints

Tests that verify:
- Admin endpoints require authentication
- Admin endpoints require proper permissions
- Admin dashboard returns correct statistics
- User management endpoints work correctly
- Analytics endpoints return data
- Training data export works
- System settings endpoints work
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.api.main import app
from src.database.database import get_db, Base
from src.database.models import User
from src.database.crud import create_user, get_user_by_username, assign_role_template_to_user
from src.auth.password import hash_password
from src.auth.auth import create_access_token


# Test database URL - use test database or in-memory
TEST_DATABASE_URL = os.getenv(
    'TEST_DATABASE_URL',
    'postgresql://chatbot_user:chatbot_secure_pass_2024@localhost:5432/flexcube_chatbot'
)

# Create test engine and session
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create a test database session."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a test client with database override."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_user(db_session):
    """Get or create an admin user for testing."""
    # Check if admin user already exists
    user = get_user_by_username(db_session, "test_admin")
    
    if user:
        # User exists - ensure it has the correct role template
        # Check if role template is assigned (this is idempotent)
        try:
            assign_role_template_to_user(db_session, user.id, "operational_admin")
            db_session.commit()
            db_session.refresh(user)
        except Exception:
            # Role template might already be assigned, that's fine
            db_session.rollback()
            db_session.refresh(user)
        
        return user
    
    # User doesn't exist - create it
    password_hash = hash_password("Admin123!")
    user = create_user(
        db=db_session,
        username="test_admin",
        email="test_admin@test.com",
        password_hash=password_hash,
        full_name="Test Admin",
        user_type="operational_admin"
    )
    
    # Assign role template
    assign_role_template_to_user(db_session, user.id, "operational_admin")
    db_session.commit()
    db_session.refresh(user)
    
    return user


@pytest.fixture(scope="function")
def general_user(db_session):
    """Get or create a general user for testing."""
    # Check if user already exists
    user = get_user_by_username(db_session, "test_user")
    
    if user:
        # User exists - ensure it has the correct role template
        # Check if role template is assigned (this is idempotent)
        try:
            assign_role_template_to_user(db_session, user.id, "general_user")
            db_session.commit()
            db_session.refresh(user)
        except Exception:
            # Role template might already be assigned, that's fine
            db_session.rollback()
            db_session.refresh(user)
        
        # Ensure user is active
        if not user.is_active:
            user.is_active = True
            db_session.commit()
            db_session.refresh(user)
        
        return user
    
    # User doesn't exist - create it
    password_hash = hash_password("User123!")
    user = create_user(
        db=db_session,
        username="test_user",
        email="test_user@test.com",
        password_hash=password_hash,
        full_name="Test User",
        user_type="general_user"
    )
    
    # Assign role template
    assign_role_template_to_user(db_session, user.id, "general_user")
    db_session.commit()
    db_session.refresh(user)
    
    return user


@pytest.fixture(scope="function")
def admin_token(admin_user):
    """Get JWT token for admin user."""
    from src.database.crud import get_user_permissions
    
    # Get permissions
    permissions = get_user_permissions(TestingSessionLocal(), admin_user.id)
    
    # Create token
    token_data = {
        "sub": str(admin_user.id),
        "username": admin_user.username,
        "user_type": admin_user.user_type,
        "permissions": permissions
    }
    return create_access_token(data=token_data)


@pytest.fixture(scope="function")
def user_token(general_user):
    """Get JWT token for general user."""
    from src.database.crud import get_user_permissions
    
    # Get permissions
    permissions = get_user_permissions(TestingSessionLocal(), general_user.id)
    
    # Create token
    token_data = {
        "sub": str(general_user.id),
        "username": general_user.username,
        "user_type": general_user.user_type,
        "permissions": permissions
    }
    return create_access_token(data=token_data)


class TestAdminAuthentication:
    """Test that admin endpoints require authentication."""
    
    def test_admin_dashboard_requires_auth(self, client):
        """Test that admin dashboard requires authentication."""
        response = client.get("/admin/dashboard")
        assert response.status_code == 401  # Unauthorized
    
    def test_admin_users_requires_auth(self, client):
        """Test that admin users endpoint requires authentication."""
        response = client.get("/api/admin/users")
        assert response.status_code == 401  # Unauthorized
    
    def test_admin_analytics_requires_auth(self, client):
        """Test that admin analytics endpoint requires authentication."""
        response = client.get("/api/admin/analytics")
        assert response.status_code == 401  # Unauthorized
    
    def test_admin_dashboard_requires_permission(self, client, user_token):
        """Test that admin dashboard requires admin permission."""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = client.get("/admin/dashboard", headers=headers)
        assert response.status_code == 403  # Forbidden - no permission
    
    def test_admin_users_requires_permission(self, client, user_token):
        """Test that admin users endpoint requires admin permission."""
        headers = {"Authorization": f"Bearer {user_token}"}
        response = client.get("/api/admin/users", headers=headers)
        assert response.status_code == 403  # Forbidden - no permission


class TestAdminDashboard:
    """Test admin dashboard endpoint."""
    
    def test_admin_dashboard_returns_stats(self, client, admin_token):
        """Test that admin dashboard returns statistics."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get("/api/admin/dashboard", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "total_users" in data
        assert "active_users" in data
        assert "inactive_users" in data
        assert "total_conversations" in data
        assert "total_qa_pairs" in data
        assert "total_feedback" in data
        assert "likes_count" in data
        assert "dislikes_count" in data
        assert "most_active_users" in data
        assert "recent_activity" in data
        
        # Check data types
        assert isinstance(data["total_users"], int)
        assert isinstance(data["active_users"], int)
        assert isinstance(data["total_conversations"], int)
        assert isinstance(data["total_qa_pairs"], int)
        assert isinstance(data["total_feedback"], int)
        assert isinstance(data["most_active_users"], list)
        assert isinstance(data["recent_activity"], list)
    
    def test_admin_dashboard_page_loads(self, client, admin_token):
        """Test that admin dashboard page loads."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get("/admin/dashboard", headers=headers)
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "Admin Dashboard" in response.text


class TestAdminUsers:
    """Test admin user management endpoints."""
    
    def test_list_users(self, client, admin_token, admin_user, general_user):
        """Test listing all users."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get("/api/admin/users", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "users" in data
        assert "total" in data
        assert isinstance(data["users"], list)
        assert data["total"] >= 2  # At least admin and general user
        
        # Check user structure
        user = data["users"][0]
        assert "id" in user
        assert "username" in user
        assert "email" in user
        assert "user_type" in user
        assert "is_active" in user
        assert "permissions" in user
    
    def test_get_user_details(self, client, admin_token, general_user):
        """Test getting user details."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get(f"/api/admin/users/{general_user.id}", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == general_user.id
        assert data["username"] == general_user.username
        assert data["email"] == general_user.email
        assert "permissions" in data
        assert "conversation_count" in data
        assert "qa_pair_count" in data
    
    def test_create_user(self, client, admin_token, db_session):
        """Test creating a new user."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Use a unique username to avoid conflicts
        import time
        unique_username = f"new_test_user_{int(time.time())}"
        
        user_data = {
            "username": unique_username,
            "email": f"{unique_username}@test.com",
            "password": "NewUser123!",
            "full_name": "New Test User",
            "user_type": "general_user"
        }
        
        response = client.post("/api/admin/users", json=user_data, headers=headers)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["username"] == unique_username
        assert data["email"] == f"{unique_username}@test.com"
        assert data["user_type"] == "general_user"
        assert "permissions" in data
        
        # Cleanup: delete the created user
        created_user = get_user_by_username(db_session, unique_username)
        if created_user:
            db_session.delete(created_user)
            db_session.commit()
    
    def test_update_user(self, client, admin_token, general_user, db_session):
        """Test updating a user."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        
        # Store original values for restoration
        original_full_name = general_user.full_name
        original_user_type = general_user.user_type
        
        update_data = {
            "full_name": "Updated Name",
            "user_type": "operational_admin"
        }
        
        response = client.put(
            f"/api/admin/users/{general_user.id}",
            json=update_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["full_name"] == "Updated Name"
        assert data["user_type"] == "operational_admin"
        
        # Restore original values for other tests
        user = db_session.query(User).filter(User.id == general_user.id).first()
        user.full_name = original_full_name
        user.user_type = original_user_type
        db_session.commit()
        db_session.refresh(user)
    
    def test_deactivate_user(self, client, admin_token, general_user):
        """Test deactivating a user."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.delete(
            f"/api/admin/users/{general_user.id}",
            headers=headers
        )
        
        assert response.status_code == 204
        
        # Verify user is deactivated
        db = TestingSessionLocal()
        user = db.query(User).filter(User.id == general_user.id).first()
        assert user.is_active == False
        db.close()


class TestAdminAnalytics:
    """Test admin analytics endpoints."""
    
    def test_get_analytics(self, client, admin_token):
        """Test getting system analytics."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get("/api/admin/analytics", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert "query_analytics" in data
        assert "user_analytics" in data
        assert "feedback_analytics" in data
        assert "time_series_data" in data
        
        # Check query analytics
        assert "total_queries" in data["query_analytics"]
        assert "text_queries" in data["query_analytics"]
        assert "image_queries" in data["query_analytics"]
        assert "popular_questions" in data["query_analytics"]
        
        # Check user analytics
        assert "total_users" in data["user_analytics"]
        assert "active_users" in data["user_analytics"]
        
        # Check feedback analytics
        assert "total_feedback" in data["feedback_analytics"]
        assert "likes" in data["feedback_analytics"]
        assert "dislikes" in data["feedback_analytics"]


class TestAdminTrainingData:
    """Test training data export endpoints."""
    
    def test_export_training_data_json(self, client, admin_token):
        """Test exporting training data as JSON."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        export_data = {
            "format": "json",
            "include_feedback": True
        }
        
        response = client.post(
            "/api/admin/training-data/export",
            json=export_data,
            headers=headers
        )
        
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        data = response.json()
        assert isinstance(data, list)
    
    def test_export_training_data_csv(self, client, admin_token):
        """Test exporting training data as CSV."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        export_data = {
            "format": "csv",
            "include_feedback": False
        }
        
        response = client.post(
            "/api/admin/training-data/export",
            json=export_data,
            headers=headers
        )
        
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]


class TestAdminSettings:
    """Test system settings endpoints."""
    
    def test_get_settings(self, client, admin_token):
        """Test getting system settings."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get("/api/admin/system/settings", headers=headers)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "max_file_size_mb" in data
        assert "allowed_file_types" in data
        assert "max_conversation_history" in data
        assert "session_timeout_minutes" in data
        assert "enable_feedback" in data
        assert "enable_analytics" in data
    
    def test_update_settings(self, client, admin_token):
        """Test updating system settings."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        settings = {
            "max_file_size_mb": 20,
            "allowed_file_types": ["pdf", "docx"],
            "enable_feedback": False
        }
        
        response = client.put(
            "/api/admin/system/settings",
            json=settings,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Settings updated successfully"
        assert "settings" in data


class TestAdminPermissions:
    """Test admin permission management."""
    
    def test_get_user_permissions(self, client, admin_token, general_user):
        """Test getting user permissions."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get(
            f"/api/admin/users/{general_user.id}/permissions",
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "user_id" in data
        assert "username" in data
        assert "permissions" in data
        assert "available_permissions" in data
        assert isinstance(data["permissions"], list)
        assert isinstance(data["available_permissions"], list)
    
    def test_grant_permission(self, client, admin_token, general_user):
        """Test granting a permission to a user."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        permission_data = {
            "permission_name": "view_admin_dashboard"
        }
        
        response = client.post(
            f"/api/admin/users/{general_user.id}/permissions",
            json=permission_data,
            headers=headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "view_admin_dashboard" in data["message"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

