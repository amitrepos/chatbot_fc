"""
JWT Authentication Utilities

This module provides JWT token generation and validation for user authentication.
Tokens include user information and permissions for role-based access control.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List
from jose import JWTError, jwt
from loguru import logger
import os

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production-min-32-chars")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))


def create_access_token(
    data: Dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    The token payload includes:
    - sub: user_id (subject)
    - username: user's username
    - user_type: operational_admin or general_user
    - permissions: list of permission names
    - exp: expiration timestamp
    - iat: issued at timestamp
    
    Args:
        data: Dictionary containing user data (user_id, username, user_type, permissions)
        expires_delta: Optional custom expiration time
        
    Returns:
        str: Encoded JWT token
        
    Example:
        >>> token = create_access_token({
        ...     "sub": "1",
        ...     "username": "john_doe",
        ...     "user_type": "general_user",
        ...     "permissions": ["view_chat", "view_documents"]
        ... })
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow()
    })
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    logger.debug(f"Created access token for user {data.get('username', 'unknown')}, expires: {expire}")
    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict]:
    """
    Decode and validate a JWT access token.
    
    Args:
        token: JWT token string
        
    Returns:
        Dict: Decoded token payload if valid, None if invalid/expired
        
    Example:
        >>> payload = decode_access_token(token)
        >>> if payload:
        ...     user_id = payload.get("sub")
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error decoding token: {e}")
        return None


def get_token_expiration(token: str) -> Optional[datetime]:
    """
    Get the expiration time of a token without fully decoding it.
    
    Args:
        token: JWT token string
        
    Returns:
        datetime: Expiration time if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        exp_timestamp = payload.get("exp")
        if exp_timestamp:
            return datetime.utcfromtimestamp(exp_timestamp)
        return None
    except Exception as e:
        logger.error(f"Error getting token expiration: {e}")
        return None


def is_token_expired(token: str) -> bool:
    """
    Check if a token is expired.
    
    Args:
        token: JWT token string
        
    Returns:
        bool: True if expired, False if valid
    """
    exp = get_token_expiration(token)
    if exp is None:
        return True
    return datetime.utcnow() > exp

