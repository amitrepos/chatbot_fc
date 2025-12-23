"""
Unit Tests for Password Hashing Utilities

Tests password hashing, verification, and strength validation.
"""

import pytest
from src.auth.password import hash_password, verify_password, validate_password_strength


class TestPasswordHashing:
    """Tests for password hashing functions."""
    
    def test_hash_password_creates_hash(self):
        """Test that hash_password creates a bcrypt hash."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert hashed is not None
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt hash format
        assert hashed != password  # Should not be plaintext
    
    def test_verify_password_correct(self):
        """Test that verify_password returns True for correct password."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) == True
    
    def test_verify_password_incorrect(self):
        """Test that verify_password returns False for incorrect password."""
        password = "TestPassword123!"
        wrong_password = "WrongPassword123!"
        hashed = hash_password(password)
        
        assert verify_password(wrong_password, hashed) == False
    
    def test_hash_password_different_hashes(self):
        """Test that same password produces different hashes (salt)."""
        password = "TestPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1) == True
        assert verify_password(password, hash2) == True


class TestPasswordStrength:
    """Tests for password strength validation."""
    
    def test_valid_password(self):
        """Test that a valid password passes validation."""
        password = "ValidPass123!"
        is_valid, error = validate_password_strength(password)
        assert is_valid == True
        assert error == ""
    
    def test_password_too_short(self):
        """Test that password shorter than 8 characters fails."""
        password = "Short1"
        is_valid, error = validate_password_strength(password)
        assert is_valid == False
        assert "8 characters" in error
    
    def test_password_no_uppercase(self):
        """Test that password without uppercase fails."""
        password = "lowercase123"
        is_valid, error = validate_password_strength(password)
        assert is_valid == False
        assert "uppercase" in error.lower()
    
    def test_password_no_lowercase(self):
        """Test that password without lowercase fails."""
        password = "UPPERCASE123"
        is_valid, error = validate_password_strength(password)
        assert is_valid == False
        assert "lowercase" in error.lower()
    
    def test_password_no_number(self):
        """Test that password without number fails."""
        password = "NoNumberHere"
        is_valid, error = validate_password_strength(password)
        assert is_valid == False
        assert "number" in error.lower()
    
    def test_password_minimum_requirements(self):
        """Test password with minimum requirements (no special char needed)."""
        password = "MinPass123"
        is_valid, error = validate_password_strength(password)
        assert is_valid == True
        assert error == ""




