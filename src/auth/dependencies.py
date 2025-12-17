"""
FastAPI Dependencies for Authentication and Authorization

This module provides FastAPI dependencies for:
- Extracting current user from JWT token
- Checking user permissions
- Requiring specific user types
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional, List
from loguru import logger

from ..database.database import get_db
from ..database.models import User, Permission
from .auth import decode_access_token
from .permissions import has_permission, is_user_type


# HTTP Bearer token security scheme
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency to get current authenticated user from JWT token.
    
    Extracts JWT token from Authorization header, decodes it, and fetches
    the user from database. Raises 401 if token is invalid or user not found.
    
    Args:
        credentials: HTTP Bearer token from Authorization header
        db: Database session
        
    Returns:
        User: Current authenticated user
        
    Raises:
        HTTPException: 401 if token invalid or user not found
        
    Usage:
        @app.get("/protected")
        def protected_route(current_user: User = Depends(get_current_user)):
            return {"user_id": current_user.id}
    """
    token = credentials.credentials
    
    # Decode token
    payload = decode_access_token(token)
    if payload is None:
        logger.warning("Invalid token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extract user_id from token
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        logger.warning("Token missing user_id (sub)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Fetch user from database
    try:
        user_id_int = int(user_id)
        user = db.query(User).filter(User.id == user_id_int).first()
        
        if user is None:
            logger.warning(f"User {user_id} not found in database")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            logger.warning(f"User {user_id} is inactive")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )
        
        logger.debug(f"Authenticated user: {user.username} (id: {user.id})")
        return user
        
    except ValueError:
        logger.error(f"Invalid user_id format: {user_id}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[str]:
    """
    FastAPI dependency to get current user's permissions.
    
    Fetches all permissions for the current user from database.
    
    Args:
        current_user: Current authenticated user (from get_current_user)
        db: Database session
        
    Returns:
        List[str]: List of permission names
        
    Usage:
        @app.get("/admin")
        def admin_route(permissions: List[str] = Depends(get_current_user_permissions)):
            if "view_admin_dashboard" not in permissions:
                raise HTTPException(403, "Permission denied")
    """
    from ..database.crud import get_user_permissions
    
    permission_names = get_user_permissions(db, current_user.id)
    logger.debug(f"User {current_user.username} has {len(permission_names)} permissions")
    return permission_names


def require_permission(permission_name: str):
    """
    FastAPI dependency factory to require a specific permission.
    
    Creates a dependency that checks if the current user has the required permission.
    Raises 403 if user lacks the permission.
    
    Args:
        permission_name: Name of the required permission
        
    Returns:
        Dependency function
        
    Usage:
        @app.post("/documents/upload")
        def upload_document(
            current_user: User = Depends(get_current_user),
            _: None = Depends(require_permission("upload_documents"))
        ):
            # User has upload_documents permission
            pass
    """
    def permission_check(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> None:
        # Get user permissions using CRUD function
        from ..database.crud import get_user_permissions
        
        permission_names = get_user_permissions(db, current_user.id)
        
        if not has_permission(permission_names, permission_name):
            logger.warning(
                f"User {current_user.username} (id: {current_user.id}) "
                f"lacks required permission: {permission_name}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission_name}",
            )
        
        logger.debug(f"User {current_user.username} has permission: {permission_name}")
    
    return permission_check


def require_user_type(required_type: str):
    """
    FastAPI dependency factory to require a specific user type.
    
    Creates a dependency that checks if the current user has the required user type.
    Raises 403 if user type doesn't match.
    
    Args:
        required_type: Required user type (operational_admin or general_user)
        
    Returns:
        Dependency function
        
    Usage:
        @app.get("/admin/dashboard")
        def admin_dashboard(
            current_user: User = Depends(get_current_user),
            _: None = Depends(require_user_type("operational_admin"))
        ):
            # User is operational_admin
            pass
    """
    def user_type_check(current_user: User = Depends(get_current_user)) -> None:
        if not is_user_type(current_user.user_type, required_type):
            logger.warning(
                f"User {current_user.username} (type: {current_user.user_type}) "
                f"does not have required type: {required_type}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User type required: {required_type}",
            )
        
        logger.debug(f"User {current_user.username} has type: {required_type}")
    
    return user_type_check

