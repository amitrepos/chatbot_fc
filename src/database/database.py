"""
Database Connection

This module provides SQLAlchemy database connection and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
from loguru import logger
import os
from pathlib import Path

# Load environment variables from .env file FIRST
# This must happen before any DB configuration
try:
    from dotenv import load_dotenv
    # Find .env file in project root
    env_path = Path(__file__).resolve().parent.parent.parent / '.env'
    load_dotenv(env_path)
except ImportError:
    pass  # python-dotenv not installed

# Database URL from environment variable
# Use TCP connection with password auth (works regardless of OS user)
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://chatbot_user:chatbot_secure_pass_2024@localhost:5432/flexcube_chatbot"
)

logger.info(f"Database URL: {DATABASE_URL[:50]}...")

# Create SQLAlchemy engine
# For Unix socket connections, we don't need connection pooling settings
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    pool_pre_ping=True,  # Verify connections before using
    pool_size=5,
    max_overflow=10
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base = declarative_base()


def get_db():
    """
    Dependency function for FastAPI to get database session.
    
    Yields:
        Session: Database session
        
    Usage:
        @app.get("/endpoint")
        def my_endpoint(db: Session = Depends(get_db)):
            # Use db session
            pass
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database (create all tables).
    This is typically done via Alembic migrations, but can be used for testing.
    """
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")

