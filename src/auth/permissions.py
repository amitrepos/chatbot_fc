"""
Permission Checking Utilities

This module provides utilities for checking user permissions and roles.
Used for role-based access control (RBAC) throughout the application.
"""

from typing import List, Set, Optional
from loguru import logger


def has_permission(user_permissions: List[str], required_permission: str) -> bool:
    """
    Check if user has a specific permission.
    
    Args:
        user_permissions: List of permission names the user has
        required_permission: Permission name to check for
        
    Returns:
        bool: True if user has the permission, False otherwise
        
    Example:
        >>> has_permission(["view_chat", "view_documents"], "view_chat")
        True
        >>> has_permission(["view_chat"], "delete_documents")
        False
    """
    return required_permission in user_permissions


def has_any_permission(user_permissions: List[str], required_permissions: List[str]) -> bool:
    """
    Check if user has at least one of the required permissions.
    
    Args:
        user_permissions: List of permission names the user has
        required_permissions: List of permission names to check (OR logic)
        
    Returns:
        bool: True if user has at least one permission, False otherwise
        
    Example:
        >>> has_any_permission(["view_chat"], ["view_chat", "view_documents"])
        True
    """
    user_perms_set = set(user_permissions)
    required_perms_set = set(required_permissions)
    return bool(user_perms_set & required_perms_set)


def has_all_permissions(user_permissions: List[str], required_permissions: List[str]) -> bool:
    """
    Check if user has all of the required permissions.
    
    Args:
        user_permissions: List of permission names the user has
        required_permissions: List of permission names to check (AND logic)
        
    Returns:
        bool: True if user has all permissions, False otherwise
        
    Example:
        >>> has_all_permissions(["view_chat", "view_documents"], ["view_chat", "view_documents"])
        True
        >>> has_all_permissions(["view_chat"], ["view_chat", "view_documents"])
        False
    """
    user_perms_set = set(user_permissions)
    required_perms_set = set(required_permissions)
    return required_perms_set.issubset(user_perms_set)


def is_user_type(user_type: str, required_type: str) -> bool:
    """
    Check if user has a specific user type.
    
    Args:
        user_type: User's current type (operational_admin, general_user)
        required_type: Required user type to check
        
    Returns:
        bool: True if user type matches, False otherwise
        
    Example:
        >>> is_user_type("operational_admin", "operational_admin")
        True
        >>> is_user_type("general_user", "operational_admin")
        False
    """
    return user_type == required_type


def is_operational_admin(user_type: str) -> bool:
    """
    Check if user is an operational admin.
    
    Args:
        user_type: User's type
        
    Returns:
        bool: True if operational_admin, False otherwise
    """
    return user_type == "operational_admin"


def is_general_user(user_type: str) -> bool:
    """
    Check if user is a general user.
    
    Args:
        user_type: User's type
        
    Returns:
        bool: True if general_user, False otherwise
    """
    return user_type == "general_user"


def filter_permissions_by_category(permissions: List[str], category: str) -> List[str]:
    """
    Filter permissions by category.
    
    Categories: chat, documents, dashboard, users, data, analytics, system
    
    Args:
        permissions: List of all permission names
        category: Category to filter by
        
    Returns:
        List[str]: Permissions in the specified category
    """
    # This would typically query the database, but for now we'll use a mapping
    category_mapping = {
        "chat": ["view_chat", "view_image_query"],
        "documents": ["view_documents", "upload_documents", "delete_documents", "reindex_documents"],
        "dashboard": ["view_admin_dashboard"],
        "users": ["view_user_management", "create_users", "edit_users", "deactivate_users"],
        "data": ["view_all_conversations", "export_training_data"],
        "analytics": ["view_analytics"],
        "system": ["manage_system_settings"]
    }
    
    category_perms = category_mapping.get(category, [])
    return [p for p in permissions if p in category_perms]

