"""
Pytest configuration and fixtures for FlexCube AI Assistant tests
"""

import pytest
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Load .env file for test configuration
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass


@pytest.fixture(scope="session")
def database_url():
    """
    Get database URL from environment or use default test database.
    
    Priority:
    1. TEST_DATABASE_URL environment variable
    2. DATABASE_URL from .env file (TCP connection with password)
    3. Unix socket connection (peer auth - requires running as postgres user)
    """
    return os.getenv(
        'TEST_DATABASE_URL',
        os.getenv(
            'DATABASE_URL',
            'postgresql://chatbot_user:chatbot_secure_pass_2024@localhost:5432/flexcube_chatbot'
        )
    )


@pytest.fixture(scope="session")
def db_engine(database_url):
    """
    Create database engine for testing.
    """
    engine = create_engine(database_url)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    Create a database session for testing.
    Rolls back after each test.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def test_user(db_session):
    """
    Create a test user for testing.
    """
    from src.database.crud import create_user
    from src.auth.password import hash_password
    
    user = create_user(
        db=db_session,
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("TestPass123!"),
        full_name="Test User",
        user_type="general_user"
    )
    return user

