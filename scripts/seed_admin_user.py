#!/usr/bin/env python3
"""
Seed Default Admin User

This script creates a default admin user for the FlexCube chatbot system.
The default admin credentials are:
- Username: admin
- Email: admin@flexcube.local
- Password: Admin123!

Run this script after setting up the database to create the initial admin user.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.database import get_db, engine
from src.database.models import Base, User
from src.database.crud import (
    get_user_by_username,
    create_user,
    assign_role_template_to_user
)
from src.auth.password import hash_password
from sqlalchemy.orm import Session
from loguru import logger

# Default admin credentials
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_EMAIL = "admin@flexcube.local"
DEFAULT_ADMIN_PASSWORD = "Admin123!"  # Meets password requirements: 8+ chars, uppercase, lowercase, number
DEFAULT_ADMIN_FULL_NAME = "System Administrator"
DEFAULT_ADMIN_USER_TYPE = "operational_admin"


def seed_admin_user(db: Session) -> bool:
    """
    Create default admin user if it doesn't exist.
    
    Args:
        db: Database session
        
    Returns:
        bool: True if user was created, False if already exists
    """
    # Check if admin user already exists
    existing_user = get_user_by_username(db, DEFAULT_ADMIN_USERNAME)
    if existing_user:
        logger.info(f"Admin user '{DEFAULT_ADMIN_USERNAME}' already exists (ID: {existing_user.id})")
        logger.info("Skipping admin user creation.")
        return False
    
    # Hash password
    password_hash = hash_password(DEFAULT_ADMIN_PASSWORD)
    
    # Create admin user
    admin_user = create_user(
        db=db,
        username=DEFAULT_ADMIN_USERNAME,
        email=DEFAULT_ADMIN_EMAIL,
        password_hash=password_hash,
        full_name=DEFAULT_ADMIN_FULL_NAME,
        user_type=DEFAULT_ADMIN_USER_TYPE,
        created_by=None  # System-created user
    )
    
    # Assign operational_admin role template (grants all permissions)
    assign_role_template_to_user(db, admin_user.id, DEFAULT_ADMIN_USER_TYPE)
    
    logger.info(f"✅ Default admin user created successfully!")
    logger.info(f"   Username: {DEFAULT_ADMIN_USERNAME}")
    logger.info(f"   Email: {DEFAULT_ADMIN_EMAIL}")
    logger.info(f"   Password: {DEFAULT_ADMIN_PASSWORD}")
    logger.info(f"   User Type: {DEFAULT_ADMIN_USER_TYPE}")
    logger.info(f"   User ID: {admin_user.id}")
    
    return True


def main():
    """Main function to seed admin user."""
    logger.info("=" * 60)
    logger.info("FlexCube Chatbot - Seed Default Admin User")
    logger.info("=" * 60)
    logger.info("")
    
    try:
        # Get database session
        db = next(get_db())
        
        # Create admin user
        created = seed_admin_user(db)
        
        if created:
            logger.info("")
            logger.info("=" * 60)
            logger.info("✅ Admin user seeded successfully!")
            logger.info("=" * 60)
            logger.info("")
            logger.info("Default Admin Credentials:")
            logger.info(f"  Username: {DEFAULT_ADMIN_USERNAME}")
            logger.info(f"  Password: {DEFAULT_ADMIN_PASSWORD}")
            logger.info(f"  Email: {DEFAULT_ADMIN_EMAIL}")
            logger.info("")
            logger.info("⚠️  IMPORTANT: Change the default password after first login!")
            logger.info("")
        else:
            logger.info("")
            logger.info("=" * 60)
            logger.info("ℹ️  Admin user already exists - no action needed")
            logger.info("=" * 60)
            logger.info("")
        
    except Exception as e:
        logger.error(f"❌ Error seeding admin user: {e}")
        logger.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()




