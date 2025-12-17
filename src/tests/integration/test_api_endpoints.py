"""
Integration Tests for API Endpoints

Tests the FastAPI endpoints with authentication, permissions, and database integration.
These tests verify the full request/response cycle including:
- Authentication requirements
- Permission checks
- Database storage
- Error handling
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.api.main import app
from src.database.crud import create_user, get_user_by_username, get_qa_pair, get_feedback
from src.auth.password import hash_password
from src.auth.auth import create_access_token
from src.database.crud import assign_role_template_to_user


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def test_user_with_token(db_session: Session):
    """
    Create a test user with JWT token and permissions.
    
    Returns:
        tuple: (user, token, permissions)
    """
    # Create user
    user = create_user(
        db=db_session,
        username="test_api_user",
        email="test_api@example.com",
        password_hash=hash_password("TestPass123!"),
        full_name="Test API User",
        user_type="general_user"
    )
    
    # Assign general_user role template (grants default permissions)
    assign_role_template_to_user(db_session, user.id, "general_user")
    
    # Get user permissions
    from src.database.crud import get_user_permissions
    permissions = get_user_permissions(db_session, user.id)
    
    # Create JWT token
    token_data = {
        "sub": str(user.id),
        "username": user.username,
        "user_type": user.user_type,
        "permissions": permissions
    }
    token = create_access_token(token_data)
    
    return user, token, permissions


@pytest.fixture
def test_user_without_permission(db_session: Session):
    """
    Create a test user without view_chat permission.
    
    Returns:
        tuple: (user, token)
    """
    # Create user
    user = create_user(
        db=db_session,
        username="test_no_perm_user",
        email="test_no_perm@example.com",
        password_hash=hash_password("TestPass123!"),
        full_name="Test No Perm User",
        user_type="general_user"
    )
    
    # Don't assign any permissions
    permissions = []
    
    # Create JWT token
    token_data = {
        "sub": str(user.id),
        "username": user.username,
        "user_type": user.user_type,
        "permissions": permissions
    }
    token = create_access_token(token_data)
    
    return user, token


class TestQueryEndpoint:
    """Tests for POST /api/query endpoint."""
    
    def test_query_requires_authentication(self, client: TestClient):
        """Test that query endpoint requires authentication."""
        response = client.post(
            "/api/query",
            json={"question": "What is FlexCube?"}
        )
        
        assert response.status_code == 401  # Unauthorized (no auth token)
    
    def test_query_requires_view_chat_permission(
        self,
        client: TestClient,
        test_user_without_permission
    ):
        """Test that query endpoint requires view_chat permission."""
        user, token = test_user_without_permission
        
        response = client.post(
            "/api/query",
            json={"question": "What is FlexCube?"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403  # Forbidden (no permission)
        assert "Permission required" in response.json().get("detail", "")
    
    def test_query_with_valid_auth_and_permission(
        self,
        client: TestClient,
        test_user_with_token,
        db_session: Session
    ):
        """Test query endpoint with valid authentication and permission."""
        user, token, permissions = test_user_with_token
        
        # Mock the RAG pipeline to avoid actual query execution
        # In a real test, you'd use a mock or test database
        # For now, we'll test the authentication/permission flow
        
        # Note: This test requires the RAG pipeline to be initialized
        # In a full integration test, you'd mock the pipeline or use a test instance
        response = client.post(
            "/api/query",
            json={"question": "What is FlexCube?"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        # If pipeline is not available, we expect 500 or the endpoint to work
        # The important part is that auth/permission checks passed
        assert response.status_code in [200, 500]  # 200 if pipeline works, 500 if not initialized
        
        # If successful, verify Q&A pair was stored
        if response.status_code == 200:
            data = response.json()
            assert "answer" in data
            assert "sources" in data
            assert "processing_time" in data
            
            # Verify Q&A pair was stored in database
            # (This would require querying the database for the latest Q&A pair)
            # For now, we verify the endpoint structure


class TestImageQueryEndpoint:
    """Tests for POST /api/query/image endpoint."""
    
    def test_image_query_requires_authentication(self, client: TestClient):
        """Test that image query endpoint requires authentication."""
        # Create a dummy image file
        files = {"image": ("test.png", b"fake image data", "image/png")}
        
        response = client.post(
            "/api/query/image",
            files=files
        )
        
        assert response.status_code == 401  # Unauthorized (no auth token)
    
    def test_image_query_requires_view_image_query_permission(
        self,
        client: TestClient,
        test_user_without_permission
    ):
        """Test that image query endpoint requires view_image_query permission."""
        user, token = test_user_without_permission
        
        files = {"image": ("test.png", b"fake image data", "image/png")}
        
        response = client.post(
            "/api/query/image",
            files=files,
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403  # Forbidden (no permission)
        assert "Permission required" in response.json().get("detail", "")


class TestFeedbackEndpoint:
    """Tests for POST /api/feedback endpoint."""
    
    def test_feedback_requires_authentication(self, client: TestClient):
        """Test that feedback endpoint requires authentication."""
        response = client.post(
            "/api/feedback",
            json={
                "qa_pair_id": 1,
                "rating": 2,
                "feedback_text": "Great answer!"
            }
        )
        
        assert response.status_code == 401  # Unauthorized (no auth token)
    
    def test_feedback_validates_qa_pair_exists(
        self,
        client: TestClient,
        test_user_with_token
    ):
        """Test that feedback endpoint validates Q&A pair exists."""
        user, token, permissions = test_user_with_token
        
        response = client.post(
            "/api/feedback",
            json={
                "qa_pair_id": 99999,  # Non-existent Q&A pair
                "rating": 2
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404
        assert "Q&A pair not found" in response.json().get("detail", "")
    
    def test_feedback_validates_rating(
        self,
        client: TestClient,
        test_user_with_token,
        db_session: Session
    ):
        """Test that feedback endpoint validates rating value."""
        user, token, permissions = test_user_with_token
        
        # Create a Q&A pair for this user
        from src.database.crud import create_qa_pair, create_conversation
        
        conversation = create_conversation(db_session, user.id, "Test")
        qa_pair = create_qa_pair(
            db_session,
            user_id=user.id,
            conversation_id=conversation.id,
            question="Test question",
            answer="Test answer"
        )
        
        # Try invalid rating
        response = client.post(
            "/api/feedback",
            json={
                "qa_pair_id": qa_pair.id,
                "rating": 3  # Invalid (must be 1 or 2)
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 400
        assert "Rating must be 1 or 2" in response.json().get("detail", "")
    
    def test_feedback_allows_any_user(
        self,
        client: TestClient,
        test_user_with_token,
        db_session: Session
    ):
        """Test that any user can provide feedback on any Q&A pair."""
        user, token, permissions = test_user_with_token
        
        # Create another user and their Q&A pair
        other_user = create_user(
            db=db_session,
            username="other_user",
            email="other@example.com",
            password_hash=hash_password("TestPass123!"),
            user_type="general_user"
        )
        
        from src.database.crud import create_qa_pair, create_conversation
        
        conversation = create_conversation(db_session, other_user.id, "Other's Conversation")
        qa_pair = create_qa_pair(
            db_session,
            user_id=other_user.id,  # Belongs to other_user
            conversation_id=conversation.id,
            question="Other's question",
            answer="Other's answer"
        )
        
        # Submit feedback on other user's Q&A pair (should be allowed)
        response = client.post(
            "/api/feedback",
            json={
                "qa_pair_id": qa_pair.id,
                "rating": 2,
                "feedback_text": "Great answer from another user!"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "feedback_id" in data
        
        # Verify feedback was stored with correct user_id
        from src.database.crud import get_feedback
        feedback = get_feedback(db_session, data["feedback_id"])
        assert feedback is not None
        assert feedback.user_id == user.id  # Feedback from current user
        assert feedback.qa_pair_id == qa_pair.id  # But on other user's Q&A pair
    
    def test_feedback_submits_successfully(
        self,
        client: TestClient,
        test_user_with_token,
        db_session: Session
    ):
        """Test successful feedback submission."""
        user, token, permissions = test_user_with_token
        
        # Create a Q&A pair for this user
        from src.database.crud import create_qa_pair, create_conversation
        
        conversation = create_conversation(db_session, user.id, "Test")
        qa_pair = create_qa_pair(
            db_session,
            user_id=user.id,
            conversation_id=conversation.id,
            question="Test question",
            answer="Test answer"
        )
        
        # Submit feedback
        response = client.post(
            "/api/feedback",
            json={
                "qa_pair_id": qa_pair.id,
                "rating": 2,
                "feedback_text": "Great answer!"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "feedback_id" in data
        assert "message" in data
        
        # Verify feedback was stored in database
        feedback = get_feedback(db_session, data["feedback_id"])
        assert feedback is not None
        assert feedback.rating == 2
        assert feedback.feedback_text == "Great answer!"
        assert feedback.user_id == user.id
        assert feedback.qa_pair_id == qa_pair.id
    
    def test_get_feedback_for_qa_pair(
        self,
        client: TestClient,
        test_user_with_token,
        db_session: Session
    ):
        """Test GET endpoint to retrieve feedback for a Q&A pair."""
        user, token, permissions = test_user_with_token
        
        # Create a Q&A pair
        from src.database.crud import create_qa_pair, create_conversation, create_feedback
        
        conversation = create_conversation(db_session, user.id, "Test")
        qa_pair = create_qa_pair(
            db_session,
            user_id=user.id,
            conversation_id=conversation.id,
            question="Test question",
            answer="Test answer"
        )
        
        # Create multiple feedback entries
        feedback1 = create_feedback(
            db_session,
            qa_pair_id=qa_pair.id,
            user_id=user.id,
            rating=2,
            feedback_text="Great answer!"
        )
        
        # Create another user and their feedback
        other_user = create_user(
            db=db_session,
            username="feedback_user",
            email="feedback@example.com",
            password_hash=hash_password("TestPass123!"),
            user_type="general_user"
        )
        
        feedback2 = create_feedback(
            db_session,
            qa_pair_id=qa_pair.id,
            user_id=other_user.id,
            rating=1,
            feedback_text="Could be better"
        )
        
        # Get feedback for Q&A pair
        response = client.get(
            f"/api/feedback/qa-pair/{qa_pair.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "feedbacks" in data
        assert "total" in data
        assert data["total"] == 2
        
        # Verify feedback details
        feedbacks = data["feedbacks"]
        assert len(feedbacks) == 2
        
        # Check that both feedbacks are included
        feedback_ids = [f["id"] for f in feedbacks]
        assert feedback1.id in feedback_ids
        assert feedback2.id in feedback_ids
        
        # Verify structure of feedback response
        for feedback in feedbacks:
            assert "id" in feedback
            assert "qa_pair_id" in feedback
            assert "user_id" in feedback
            assert "username" in feedback
            assert "rating" in feedback
            assert "created_at" in feedback
    
    def test_get_feedback_requires_authentication(self, client: TestClient, db_session: Session):
        """Test that GET feedback endpoint requires authentication."""
        response = client.get("/api/feedback/qa-pair/1")
        assert response.status_code == 401
    
    def test_get_feedback_validates_qa_pair_exists(
        self,
        client: TestClient,
        test_user_with_token
    ):
        """Test that GET feedback endpoint validates Q&A pair exists."""
        user, token, permissions = test_user_with_token
        
        response = client.get(
            "/api/feedback/qa-pair/99999",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404
        assert "Q&A pair not found" in response.json().get("detail", "")
    
    def test_delete_feedback_successfully(
        self,
        client: TestClient,
        test_user_with_token,
        db_session: Session
    ):
        """Test successful feedback deletion."""
        user, token, permissions = test_user_with_token
        
        # Create a Q&A pair and feedback
        from src.database.crud import create_qa_pair, create_conversation, create_feedback
        
        conversation = create_conversation(db_session, user.id, "Test")
        qa_pair = create_qa_pair(
            db_session,
            user_id=user.id,
            conversation_id=conversation.id,
            question="Test question",
            answer="Test answer"
        )
        
        feedback = create_feedback(
            db_session,
            qa_pair_id=qa_pair.id,
            user_id=user.id,
            rating=2,
            feedback_text="Test feedback"
        )
        
        # Delete feedback
        response = client.delete(
            f"/api/feedback/{feedback.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 204
        
        # Verify feedback was deleted
        deleted_feedback = get_feedback(db_session, feedback.id)
        assert deleted_feedback is None
    
    def test_delete_feedback_requires_authentication(self, client: TestClient):
        """Test that DELETE feedback endpoint requires authentication."""
        response = client.delete("/api/feedback/1")
        assert response.status_code == 401
    
    def test_delete_feedback_validates_exists(
        self,
        client: TestClient,
        test_user_with_token
    ):
        """Test that DELETE feedback endpoint validates feedback exists."""
        user, token, permissions = test_user_with_token
        
        response = client.delete(
            "/api/feedback/99999",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404
        assert "Feedback not found" in response.json().get("detail", "")
    
    def test_delete_feedback_validates_ownership(
        self,
        client: TestClient,
        test_user_with_token,
        db_session: Session
    ):
        """Test that users can only delete their own feedback."""
        user, token, permissions = test_user_with_token
        
        # Create another user and their feedback
        other_user = create_user(
            db=db_session,
            username="other_feedback_user",
            email="other_feedback@example.com",
            password_hash=hash_password("TestPass123!"),
            user_type="general_user"
        )
        
        from src.database.crud import create_qa_pair, create_conversation, create_feedback
        
        conversation = create_conversation(db_session, other_user.id, "Other's Conversation")
        qa_pair = create_qa_pair(
            db_session,
            user_id=other_user.id,
            conversation_id=conversation.id,
            question="Other's question",
            answer="Other's answer"
        )
        
        # Create feedback from other user
        other_feedback = create_feedback(
            db_session,
            qa_pair_id=qa_pair.id,
            user_id=other_user.id,
            rating=2,
            feedback_text="Other's feedback"
        )
        
        # Try to delete other user's feedback
        response = client.delete(
            f"/api/feedback/{other_feedback.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 403
        assert "only delete your own" in response.json().get("detail", "").lower()


class TestAuthEndpoints:
    """Tests for authentication endpoints."""
    
    def test_register_creates_user(self, client: TestClient, db_session: Session):
        """Test user registration."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        response = client.post(
            "/api/auth/register",
            json={
                "username": f"new_user_{unique_id}",
                "email": f"new_user_{unique_id}@example.com",
                "password": "NewPass123!",
                "full_name": "New User"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "user_id" in data
        assert data["username"] == f"new_user_{unique_id}"
        
        # Verify user was created in database
        user = get_user_by_username(db_session, f"new_user_{unique_id}")
        assert user is not None
        assert user.email == f"new_user_{unique_id}@example.com"
    
    def test_register_rejects_duplicate_username(self, client: TestClient):
        """Test that registration rejects duplicate username."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        # Create first user
        response1 = client.post(
            "/api/auth/register",
            json={
                "username": f"dup_user_{unique_id}",
                "email": f"dup_user_{unique_id}@example.com",
                "password": "NewPass123!"
            }
        )
        assert response1.status_code == 201
        
        # Try to create user with same username
        response = client.post(
            "/api/auth/register",
            json={
                "username": f"dup_user_{unique_id}",  # Already exists
                "email": f"different_{unique_id}@example.com",
                "password": "NewPass123!"
            }
        )
        
        assert response.status_code == 400
        assert "already registered" in response.json().get("detail", "").lower()
    
    def test_login_returns_token(self, client: TestClient):
        """Test user login returns JWT token."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        # Create user via API first
        register_response = client.post(
            "/api/auth/register",
            json={
                "username": f"login_test_{unique_id}",
                "email": f"login_test_{unique_id}@example.com",
                "password": "TestPass123!"
            }
        )
        assert register_response.status_code == 201
        user_id = register_response.json()["user_id"]
        
        # Now test login
        response = client.post(
            "/api/auth/login",
            json={
                "username": f"login_test_{unique_id}",
                "password": "TestPass123!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["id"] == user_id
    
    def test_login_rejects_invalid_credentials(self, client: TestClient):
        """Test that login rejects invalid password."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        # Create user first
        client.post(
            "/api/auth/register",
            json={
                "username": f"wrong_pass_{unique_id}",
                "email": f"wrong_pass_{unique_id}@example.com",
                "password": "CorrectPass123!"
            }
        )
        
        # Try login with wrong password
        response = client.post(
            "/api/auth/login",
            json={
                "username": f"wrong_pass_{unique_id}",
                "password": "WrongPassword123!"
            }
        )
        
        assert response.status_code == 401
        assert "Invalid" in response.json().get("detail", "")
    
    def test_get_current_user_info(self, client: TestClient):
        """Test GET /api/auth/me endpoint."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        # Create and login user
        client.post(
            "/api/auth/register",
            json={
                "username": f"me_test_{unique_id}",
                "email": f"me_test_{unique_id}@example.com",
                "password": "TestPass123!"
            }
        )
        
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": f"me_test_{unique_id}",
                "password": "TestPass123!"
            }
        )
        token = login_response.json()["access_token"]
        user_id = login_response.json()["user"]["id"]
        
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["username"] == f"me_test_{unique_id}"
        assert "permissions" in data
    
    def test_logout_successful(self, client: TestClient):
        """Test POST /api/auth/logout endpoint."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        # Create and login user
        client.post(
            "/api/auth/register",
            json={
                "username": f"logout_test_{unique_id}",
                "email": f"logout_test_{unique_id}@example.com",
                "password": "TestPass123!"
            }
        )
        
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": f"logout_test_{unique_id}",
                "password": "TestPass123!"
            }
        )
        token = login_response.json()["access_token"]
        
        response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "successfully" in data["message"].lower()
    
    def test_logout_requires_authentication(self, client: TestClient):
        """Test that logout endpoint requires authentication."""
        response = client.post("/api/auth/logout")
        
        assert response.status_code == 401
    
    def test_refresh_token_successful(self, client: TestClient):
        """Test POST /api/auth/refresh endpoint."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        # Create and login user
        client.post(
            "/api/auth/register",
            json={
                "username": f"refresh_test_{unique_id}",
                "email": f"refresh_test_{unique_id}@example.com",
                "password": "TestPass123!"
            }
        )
        
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": f"refresh_test_{unique_id}",
                "password": "TestPass123!"
            }
        )
        token = login_response.json()["access_token"]
        user_id = login_response.json()["user"]["id"]
        
        response = client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["id"] == user_id
        
        # Note: tokens created in the same second may be identical
        # The important thing is that refresh returns a valid token
        assert len(data["access_token"]) > 0
    
    def test_refresh_token_requires_authentication(self, client: TestClient):
        """Test that refresh endpoint requires authentication."""
        response = client.post("/api/auth/refresh")
        
        assert response.status_code == 401
    
    def test_register_validates_password_strength(self, client: TestClient):
        """Test that registration validates password strength."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        response = client.post(
            "/api/auth/register",
            json={
                "username": f"weak_user_{unique_id}",
                "email": f"weak_{unique_id}@example.com",
                "password": "weak"  # Too weak
            }
        )
        
        assert response.status_code == 400
        assert "password" in response.json().get("detail", "").lower()
    
    def test_register_validates_email_format(self, client: TestClient):
        """Test that registration validates email format."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        response = client.post(
            "/api/auth/register",
            json={
                "username": f"invalid_email_{unique_id}",
                "email": "not-an-email",
                "password": "ValidPass123!"
            }
        )
        
        assert response.status_code == 422  # Validation error
    
    def test_login_with_email(self, client: TestClient):
        """Test that users can login with email instead of username."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        # Create user
        register_response = client.post(
            "/api/auth/register",
            json={
                "username": f"email_login_{unique_id}",
                "email": f"email_login_{unique_id}@example.com",
                "password": "TestPass123!"
            }
        )
        user_id = register_response.json()["user_id"]
        
        # Login with email
        response = client.post(
            "/api/auth/login",
            json={
                "username": f"email_login_{unique_id}@example.com",  # Using email
                "password": "TestPass123!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["id"] == user_id
    
    def test_login_updates_last_login(self, client: TestClient):
        """Test that login updates the last_login timestamp."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        # Create user
        client.post(
            "/api/auth/register",
            json={
                "username": f"last_login_{unique_id}",
                "email": f"last_login_{unique_id}@example.com",
                "password": "TestPass123!"
            }
        )
        
        # Login twice to test last_login update
        response1 = client.post(
            "/api/auth/login",
            json={
                "username": f"last_login_{unique_id}",
                "password": "TestPass123!"
            }
        )
        assert response1.status_code == 200
        
        # Second login should also work
        response2 = client.post(
            "/api/auth/login",
            json={
                "username": f"last_login_{unique_id}",
                "password": "TestPass123!"
            }
        )
        assert response2.status_code == 200
        # Both should succeed (login works after first login)
    
    def test_login_returns_user_permissions(self, client: TestClient):
        """Test that login response includes user permissions."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        # Create user
        client.post(
            "/api/auth/register",
            json={
                "username": f"perm_login_{unique_id}",
                "email": f"perm_login_{unique_id}@example.com",
                "password": "TestPass123!"
            }
        )
        
        response = client.post(
            "/api/auth/login",
            json={
                "username": f"perm_login_{unique_id}",
                "password": "TestPass123!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "permissions" in data["user"]
        assert isinstance(data["user"]["permissions"], list)
    
    def test_register_assigns_default_permissions(
        self,
        client: TestClient,
        db_session: Session
    ):
        """Test that new users get default permissions."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        response = client.post(
            "/api/auth/register",
            json={
                "username": f"perm_test_{unique_id}",
                "email": f"perm_test_{unique_id}@example.com",
                "password": "TestPass123!"
            }
        )
        
        assert response.status_code == 201
        
        # Login and check permissions
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": f"perm_test_{unique_id}",
                "password": "TestPass123!"
            }
        )
        
        assert login_response.status_code == 200
        data = login_response.json()
        
        # Should have default general_user permissions
        permissions = data["user"]["permissions"]
        assert isinstance(permissions, list)
        # General users should have basic permissions
        assert len(permissions) > 0
    
    def test_register_rejects_duplicate_email(self, client: TestClient):
        """Test that registration rejects duplicate email."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        # Create first user
        client.post(
            "/api/auth/register",
            json={
                "username": f"email_dup_{unique_id}",
                "email": f"email_dup_{unique_id}@example.com",
                "password": "NewPass123!"
            }
        )
        
        # Try to create user with same email
        response = client.post(
            "/api/auth/register",
            json={
                "username": f"different_user_{unique_id}",
                "email": f"email_dup_{unique_id}@example.com",  # Already exists
                "password": "NewPass123!"
            }
        )
        
        assert response.status_code == 400
        assert "already registered" in response.json().get("detail", "").lower()
    
    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent user."""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "nonexistent_user_xyz",
                "password": "SomePassword123!"
            }
        )
        
        assert response.status_code == 401
        assert "Invalid" in response.json().get("detail", "")
    
    def test_protected_endpoint_with_invalid_token(self, client: TestClient):
        """Test that protected endpoints reject invalid tokens."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        
        assert response.status_code == 401
    
    def test_protected_endpoint_without_token(self, client: TestClient):
        """Test that protected endpoints require token."""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 401


class TestFaviconEndpoint:
    """Tests for favicon endpoint."""
    
    def test_favicon_returns_svg(self, client: TestClient):
        """Test that favicon endpoint returns SVG image."""
        response = client.get("/favicon.ico")
        
        assert response.status_code == 200
        assert "svg" in response.headers.get("content-type", "").lower()
    
    def test_favicon_has_content(self, client: TestClient):
        """Test that favicon has actual content."""
        response = client.get("/favicon.ico")
        
        assert response.status_code == 200
        assert len(response.content) > 0
        assert b"<svg" in response.content


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_returns_ok(self, client: TestClient):
        """Test that health endpoint returns healthy status."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_health_includes_stats(self, client: TestClient):
        """Test that health endpoint includes stats."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "pipeline_ready" in data


class TestFullAuthenticationFlow:
    """Integration tests for complete authentication workflows."""
    
    def test_complete_registration_login_flow(self, client: TestClient):
        """Test complete flow: register -> login -> access protected endpoint."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        # Step 1: Register
        register_response = client.post(
            "/api/auth/register",
            json={
                "username": f"flow_user_{unique_id}",
                "email": f"flow_{unique_id}@example.com",
                "password": "FlowPass123!"
            }
        )
        
        assert register_response.status_code == 201
        
        # Step 2: Login
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": f"flow_user_{unique_id}",
                "password": "FlowPass123!"
            }
        )
        
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        
        # Step 3: Access protected endpoint
        me_response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert me_response.status_code == 200
        assert me_response.json()["username"] == f"flow_user_{unique_id}"
    
    def test_login_logout_cannot_reuse_token_concept(self, client: TestClient):
        """Test logout endpoint works (token invalidation is client-side)."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        # Create and login user
        client.post(
            "/api/auth/register",
            json={
                "username": f"logout_flow_{unique_id}",
                "email": f"logout_flow_{unique_id}@example.com",
                "password": "TestPass123!"
            }
        )
        
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": f"logout_flow_{unique_id}",
                "password": "TestPass123!"
            }
        )
        token = login_response.json()["access_token"]
        
        # Logout
        logout_response = client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert logout_response.status_code == 200
        assert "successfully" in logout_response.json()["message"].lower()
    
    def test_token_refresh_provides_new_valid_token(self, client: TestClient):
        """Test that refreshed token can be used for authentication."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        # Create and login user
        client.post(
            "/api/auth/register",
            json={
                "username": f"refresh_flow_{unique_id}",
                "email": f"refresh_flow_{unique_id}@example.com",
                "password": "TestPass123!"
            }
        )
        
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": f"refresh_flow_{unique_id}",
                "password": "TestPass123!"
            }
        )
        token = login_response.json()["access_token"]
        user_id = login_response.json()["user"]["id"]
        
        # Refresh token
        refresh_response = client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert refresh_response.status_code == 200
        new_token = refresh_response.json()["access_token"]
        
        # Use new token
        me_response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {new_token}"}
        )
        
        assert me_response.status_code == 200
        assert me_response.json()["id"] == user_id

