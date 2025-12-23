"""
Unit Tests for Database Connection

Tests the database connection configuration and ensures
the TCP connection with password authentication works correctly.
"""

import pytest
import os
from pathlib import Path


class TestDatabaseConfiguration:
    """Tests for database configuration."""
    
    def test_env_file_exists(self):
        """Test that .env file exists in project root."""
        env_path = Path(__file__).resolve().parent.parent.parent.parent / '.env'
        assert env_path.exists(), f".env file not found at {env_path}"
    
    def test_database_url_from_env(self):
        """Test that DATABASE_URL is loaded from .env file."""
        from dotenv import load_dotenv
        env_path = Path(__file__).resolve().parent.parent.parent.parent / '.env'
        load_dotenv(env_path)
        
        database_url = os.getenv('DATABASE_URL')
        assert database_url is not None, "DATABASE_URL not set in .env"
        assert 'postgresql://' in database_url, "DATABASE_URL should be PostgreSQL URL"
    
    def test_database_url_uses_tcp(self):
        """Test that DATABASE_URL uses TCP connection (not Unix socket)."""
        from dotenv import load_dotenv
        env_path = Path(__file__).resolve().parent.parent.parent.parent / '.env'
        load_dotenv(env_path)
        
        database_url = os.getenv('DATABASE_URL')
        assert database_url is not None
        
        # TCP connection should have host:port in URL
        assert '@localhost' in database_url or '@127.0.0.1' in database_url, \
            "DATABASE_URL should use TCP connection with host"
        assert ':5432' in database_url, "DATABASE_URL should specify port 5432"
    
    def test_database_url_has_credentials(self):
        """Test that DATABASE_URL includes user credentials."""
        from dotenv import load_dotenv
        env_path = Path(__file__).resolve().parent.parent.parent.parent / '.env'
        load_dotenv(env_path)
        
        database_url = os.getenv('DATABASE_URL')
        assert database_url is not None
        
        # Should have user:password format
        assert 'chatbot_user:' in database_url, \
            "DATABASE_URL should include chatbot_user credentials"


class TestDatabaseEngine:
    """Tests for database engine creation."""
    
    def test_engine_creation(self):
        """Test that database engine can be created."""
        from src.database.database import engine
        
        assert engine is not None, "Database engine should be created"
    
    def test_engine_url_is_tcp(self):
        """Test that engine uses TCP connection URL."""
        from src.database.database import DATABASE_URL
        
        # Verify it's using TCP, not Unix socket
        # Unix socket URLs look like: postgresql:///dbname
        # TCP URLs look like: postgresql://user:pass@host:port/dbname
        assert '@' in DATABASE_URL, "Engine should use TCP connection with credentials"


class TestDatabaseConnection:
    """Tests for actual database connectivity."""
    
    def test_database_connection(self, db_session):
        """Test that database connection works."""
        from sqlalchemy import text
        
        result = db_session.execute(text("SELECT 1"))
        assert result.scalar() == 1
    
    def test_database_tables_exist(self, db_session):
        """Test that required tables exist."""
        from sqlalchemy import text
        
        result = db_session.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('users', 'permissions', 'user_permissions')
        """))
        
        tables = [row[0] for row in result.fetchall()]
        
        assert 'users' in tables, "users table should exist"
        assert 'permissions' in tables, "permissions table should exist"
        assert 'user_permissions' in tables, "user_permissions table should exist"
    
    def test_can_query_users(self, db_session):
        """Test that users table can be queried."""
        from src.database.models import User
        
        # This should not raise an error
        users = db_session.query(User).limit(1).all()
        assert isinstance(users, list)
    
    def test_can_query_permissions(self, db_session):
        """Test that permissions table can be queried."""
        from src.database.models import Permission
        
        permissions = db_session.query(Permission).all()
        assert isinstance(permissions, list)
        # Should have default permissions seeded
        assert len(permissions) > 0, "Permissions should be seeded in database"


class TestUserCreation:
    """Tests for user creation via database."""
    
    def test_create_user_with_hashed_password(self, db_session):
        """Test creating a user with properly hashed password."""
        from src.database.crud import create_user
        from src.auth.password import hash_password, verify_password
        
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        user = create_user(
            db=db_session,
            username="db_test_user",
            email="db_test@example.com",
            password_hash=hashed,
            user_type="general_user"
        )
        
        assert user is not None
        assert user.id is not None
        assert user.username == "db_test_user"
        
        # Verify password can be verified
        assert verify_password(password, user.password_hash)
    
    def test_user_permissions_relationship(self, db_session):
        """Test that user permissions relationship works."""
        from src.database.crud import create_user, assign_role_template_to_user, get_user_permissions
        from src.auth.password import hash_password
        
        user = create_user(
            db=db_session,
            username="perm_rel_user",
            email="perm_rel@example.com",
            password_hash=hash_password("TestPass123!"),
            user_type="general_user"
        )
        
        # Assign role template
        assign_role_template_to_user(db_session, user.id, "general_user")
        
        # Get permissions
        permissions = get_user_permissions(db_session, user.id)
        
        assert isinstance(permissions, list)
        assert len(permissions) > 0, "User should have permissions from role template"




