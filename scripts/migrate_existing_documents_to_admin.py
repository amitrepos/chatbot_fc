#!/usr/bin/env python3
"""
Migrate Existing Documents to Admin Ownership

This script assigns all existing documents (where uploaded_by is NULL) to the admin user.
This is required for the document ownership-based visibility feature.

The script is idempotent - safe to run multiple times. It will only update documents
where uploaded_by is NULL, so documents already assigned to users will not be changed.

Run this script before implementing document ownership-based visibility.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database.database import get_db
from src.database.models import DocumentMetadata, User
from src.database.crud import get_user_by_username
from sqlalchemy.orm import Session
from loguru import logger

# Default admin username
DEFAULT_ADMIN_USERNAME = "admin"


def migrate_documents_to_admin(db: Session) -> dict:
    """
    Assign all documents with NULL uploaded_by to the admin user.
    
    Args:
        db: Database session
        
    Returns:
        dict: Migration results with counts
    """
    # Find admin user
    admin_user = get_user_by_username(db, DEFAULT_ADMIN_USERNAME)
    
    if not admin_user:
        # Try to find any operational_admin user
        admin_user = db.query(User).filter(
            User.user_type == "operational_admin"
        ).first()
        
        if not admin_user:
            raise ValueError(
                f"Admin user not found. Please create an admin user first by running:\n"
                f"  python3 scripts/seed_admin_user.py"
            )
    
    logger.info(f"Found admin user: {admin_user.username} (ID: {admin_user.id}, Type: {admin_user.user_type})")
    
    # Count documents with NULL uploaded_by
    null_documents = db.query(DocumentMetadata).filter(
        DocumentMetadata.uploaded_by.is_(None)
    ).all()
    
    null_count = len(null_documents)
    logger.info(f"Found {null_count} documents with NULL uploaded_by")
    
    if null_count == 0:
        logger.info("✅ No documents need migration - all documents already have owners")
        total_documents = db.query(DocumentMetadata).count()
        admin_documents = db.query(DocumentMetadata).filter(
            DocumentMetadata.uploaded_by == admin_user.id
        ).count()
        return {
            "updated": 0,
            "total_documents": total_documents,
            "admin_documents": admin_documents,
            "admin_user_id": admin_user.id,
            "admin_username": admin_user.username,
            "remaining_null": 0
        }
    
    # Update documents to assign to admin
    updated_count = db.query(DocumentMetadata).filter(
        DocumentMetadata.uploaded_by.is_(None)
    ).update(
        {DocumentMetadata.uploaded_by: admin_user.id},
        synchronize_session=False
    )
    
    db.commit()
    
    logger.info(f"✅ Updated {updated_count} documents to be owned by admin user '{admin_user.username}'")
    
    # Verify the update
    remaining_null = db.query(DocumentMetadata).filter(
        DocumentMetadata.uploaded_by.is_(None)
    ).count()
    
    if remaining_null > 0:
        logger.warning(f"⚠️  Warning: {remaining_null} documents still have NULL uploaded_by after update")
    else:
        logger.info("✅ All documents now have owners assigned")
    
    # Get total document count
    total_documents = db.query(DocumentMetadata).count()
    admin_documents = db.query(DocumentMetadata).filter(
        DocumentMetadata.uploaded_by == admin_user.id
    ).count()
    
    return {
        "updated": updated_count,
        "total_documents": total_documents,
        "admin_documents": admin_documents,
        "admin_user_id": admin_user.id,
        "admin_username": admin_user.username,
        "remaining_null": remaining_null
    }


def main():
    """Main function to migrate documents to admin ownership."""
    logger.info("=" * 60)
    logger.info("FlexCube Chatbot - Migrate Documents to Admin Ownership")
    logger.info("=" * 60)
    logger.info("")
    logger.info("This script will assign all existing documents (where uploaded_by is NULL)")
    logger.info("to the admin user for document ownership-based visibility.")
    logger.info("")
    
    try:
        # Get database session
        db = next(get_db())
        
        # Perform migration
        results = migrate_documents_to_admin(db)
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ Migration completed successfully!")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Migration Results:")
        logger.info(f"  Documents updated: {results['updated']}")
        logger.info(f"  Total documents: {results['total_documents']}")
        logger.info(f"  Admin-owned documents: {results['admin_documents']}")
        logger.info(f"  Admin user: {results['admin_username']} (ID: {results['admin_user_id']})")
        
        if results.get('remaining_null', 0) > 0:
            logger.warning(f"  ⚠️  Documents still with NULL: {results['remaining_null']}")
        
        logger.info("")
        logger.info("✅ All existing documents are now marked as admin-owned")
        logger.info("   General users will only see documents they upload themselves")
        logger.info("   Admin users will see all documents")
        logger.info("")
        
    except Exception as e:
        logger.error(f"❌ Error migrating documents: {e}")
        logger.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()

