"""
Unit Tests for Permission Checking Utilities

Tests permission checking functions.
"""

import pytest
from src.auth.permissions import (
    has_permission,
    has_any_permission,
    has_all_permissions,
    is_user_type,
    is_operational_admin,
    is_general_user,
    filter_permissions_by_category
)


class TestPermissionChecking:
    """Tests for permission checking functions."""
    
    def test_has_permission_true(self):
        """Test has_permission returns True when user has permission."""
        user_perms = ["view_chat", "view_documents", "upload_documents"]
        assert has_permission(user_perms, "view_chat") == True
        assert has_permission(user_perms, "view_documents") == True
    
    def test_has_permission_false(self):
        """Test has_permission returns False when user lacks permission."""
        user_perms = ["view_chat", "view_documents"]
        assert has_permission(user_perms, "delete_documents") == False
        assert has_permission(user_perms, "view_admin_dashboard") == False
    
    def test_has_any_permission_true(self):
        """Test has_any_permission returns True if user has at least one."""
        user_perms = ["view_chat"]
        required = ["view_chat", "view_documents"]
        assert has_any_permission(user_perms, required) == True
    
    def test_has_any_permission_false(self):
        """Test has_any_permission returns False if user has none."""
        user_perms = ["view_chat"]
        required = ["delete_documents", "view_admin_dashboard"]
        assert has_any_permission(user_perms, required) == False
    
    def test_has_all_permissions_true(self):
        """Test has_all_permissions returns True if user has all."""
        user_perms = ["view_chat", "view_documents", "upload_documents"]
        required = ["view_chat", "view_documents"]
        assert has_all_permissions(user_perms, required) == True
    
    def test_has_all_permissions_false(self):
        """Test has_all_permissions returns False if user missing any."""
        user_perms = ["view_chat", "view_documents"]
        required = ["view_chat", "view_documents", "delete_documents"]
        assert has_all_permissions(user_perms, required) == False


class TestUserTypeChecking:
    """Tests for user type checking functions."""
    
    def test_is_user_type_true(self):
        """Test is_user_type returns True for matching types."""
        assert is_user_type("operational_admin", "operational_admin") == True
        assert is_user_type("general_user", "general_user") == True
    
    def test_is_user_type_false(self):
        """Test is_user_type returns False for different types."""
        assert is_user_type("general_user", "operational_admin") == False
        assert is_user_type("operational_admin", "general_user") == False
    
    def test_is_operational_admin_true(self):
        """Test is_operational_admin returns True for admin."""
        assert is_operational_admin("operational_admin") == True
    
    def test_is_operational_admin_false(self):
        """Test is_operational_admin returns False for non-admin."""
        assert is_operational_admin("general_user") == False
    
    def test_is_general_user_true(self):
        """Test is_general_user returns True for general user."""
        assert is_general_user("general_user") == True
    
    def test_is_general_user_false(self):
        """Test is_general_user returns False for admin."""
        assert is_general_user("operational_admin") == False


class TestPermissionFiltering:
    """Tests for permission filtering by category."""
    
    def test_filter_permissions_by_category_chat(self):
        """Test filtering chat permissions."""
        all_perms = ["view_chat", "view_image_query", "view_documents", "upload_documents"]
        chat_perms = filter_permissions_by_category(all_perms, "chat")
        
        assert "view_chat" in chat_perms
        assert "view_image_query" in chat_perms
        assert "view_documents" not in chat_perms
    
    def test_filter_permissions_by_category_documents(self):
        """Test filtering document permissions."""
        all_perms = ["view_documents", "upload_documents", "delete_documents", "view_chat"]
        doc_perms = filter_permissions_by_category(all_perms, "documents")
        
        assert "view_documents" in doc_perms
        assert "upload_documents" in doc_perms
        assert "delete_documents" in doc_perms
        assert "view_chat" not in doc_perms

