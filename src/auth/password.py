"""
Password Hashing Utilities

This module provides secure password hashing using bcrypt.
All passwords are hashed before storage and verified during login.
"""

import bcrypt
from loguru import logger

# Bcrypt rounds = 12 (good balance of security and performance)
BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password (bcrypt hash)
        
    Example:
        >>> hashed = hash_password("MySecurePass123!")
        >>> verify_password("MySecurePass123!", hashed)
        True
    """
    logger.debug("Hashing password")
    # Generate salt and hash password
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Bcrypt hash to verify against
        
    Returns:
        bool: True if password matches, False otherwise
        
    Example:
        >>> verify_password("MySecurePass123!", "$2b$12$...")
        True
    """
    logger.debug("Verifying password")
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password strength according to policy.
    
    Password Policy:
    - Minimum 8 characters
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 number
    - Optional: special character (recommended)
    
    Args:
        password: Password to validate
        
    Returns:
        tuple: (is_valid, error_message)
        - is_valid: True if password meets requirements
        - error_message: Empty if valid, error description if invalid
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one number"
    
    return True, ""

