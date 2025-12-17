"""
Unit Tests for JWT Authentication

Tests JWT token creation, validation, and expiration.
"""

import pytest
from datetime import datetime, timedelta
from src.auth.auth import (
    create_access_token,
    decode_access_token,
    get_token_expiration,
    is_token_expired
)


class TestJWTTokenCreation:
    """Tests for JWT token creation."""
    
    def test_create_access_token(self):
        """Test that create_access_token creates a valid token."""
        data = {
            "sub": "1",
            "username": "test_user",
            "user_type": "general_user",
            "permissions": ["view_chat"]
        }
        token = create_access_token(data)
        
        assert token is not None
        assert len(token) > 0
        assert isinstance(token, str)
    
    def test_token_contains_user_data(self):
        """Test that token contains user data."""
        data = {
            "sub": "123",
            "username": "john_doe",
            "user_type": "operational_admin",
            "permissions": ["view_admin_dashboard"]
        }
        token = create_access_token(data)
        payload = decode_access_token(token)
        
        assert payload is not None
        assert payload.get("sub") == "123"
        assert payload.get("username") == "john_doe"
        assert payload.get("user_type") == "operational_admin"
        assert payload.get("permissions") == ["view_admin_dashboard"]
    
    def test_token_has_expiration(self):
        """Test that token has expiration timestamp."""
        data = {"sub": "1", "username": "test"}
        token = create_access_token(data)
        payload = decode_access_token(token)
        
        assert payload is not None
        assert "exp" in payload
        assert "iat" in payload
        assert payload["exp"] > payload["iat"]


class TestJWTTokenValidation:
    """Tests for JWT token validation."""
    
    def test_decode_valid_token(self):
        """Test that valid token decodes correctly."""
        data = {"sub": "1", "username": "test"}
        token = create_access_token(data)
        payload = decode_access_token(token)
        
        assert payload is not None
        assert payload.get("sub") == "1"
    
    def test_decode_invalid_token(self):
        """Test that invalid token returns None."""
        invalid_token = "invalid.token.here"
        payload = decode_access_token(invalid_token)
        
        assert payload is None
    
    def test_decode_empty_token(self):
        """Test that empty token returns None."""
        payload = decode_access_token("")
        assert payload is None


class TestTokenExpiration:
    """Tests for token expiration."""
    
    def test_get_token_expiration(self):
        """Test that get_token_expiration returns datetime."""
        data = {"sub": "1"}
        token = create_access_token(data)
        exp = get_token_expiration(token)
        
        assert exp is not None
        assert isinstance(exp, datetime)
        assert exp > datetime.utcnow()
    
    def test_is_token_expired_false(self):
        """Test that valid token is not expired."""
        data = {"sub": "1"}
        token = create_access_token(data)
        
        assert is_token_expired(token) == False
    
    def test_is_token_expired_invalid(self):
        """Test that invalid token is considered expired."""
        invalid_token = "invalid"
        assert is_token_expired(invalid_token) == True

