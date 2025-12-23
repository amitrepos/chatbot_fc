#!/usr/bin/env python3
"""
Test Database Connection Script
Tests PostgreSQL connection and verifies tables exist
"""

import sys
import os
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError

# Database connection string
# Can be overridden with DATABASE_URL environment variable
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://chatbot_user:chatbot_pass@localhost:5432/flexcube_chatbot'
)


def test_connection():
    """Test database connection."""
    print("=" * 60)
    print("Testing Database Connection")
    print("=" * 60)
    print(f"Database URL: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'hidden'}")
    print()
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Test connection
        print("Step 1: Testing connection...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✅ Connected to PostgreSQL")
            print(f"   Version: {version.split(',')[0]}")
        print()
        
        # Check if database exists
        print("Step 2: Checking database...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT current_database();"))
            db_name = result.fetchone()[0]
            print(f"✅ Connected to database: {db_name}")
        print()
        
        # Check tables
        print("Step 3: Checking tables...")
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        expected_tables = [
            'users',
            'permissions',
            'user_permissions',
            'role_templates',
            'role_template_permissions',
            'sessions',
            'conversations',
            'qa_pairs',
            'feedback',
            'training_data_export'
        ]
        
        print(f"   Found {len(tables)} tables")
        print()
        
        missing_tables = []
        for table in expected_tables:
            if table in tables:
                print(f"   ✅ {table}")
            else:
                print(f"   ❌ {table} (missing)")
                missing_tables.append(table)
        
        print()
        
        if missing_tables:
            print(f"⚠️  Warning: {len(missing_tables)} tables are missing!")
            print(f"   Missing: {', '.join(missing_tables)}")
            print("   Run: psql -U chatbot_user -d flexcube_chatbot -f scripts/create_tables.sql")
            return False
        
        # Check permissions
        print("Step 4: Checking permissions...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM permissions;"))
            perm_count = result.fetchone()[0]
            print(f"   ✅ Found {perm_count} permissions")
            
            if perm_count < 15:
                print(f"   ⚠️  Expected 15 permissions, found {perm_count}")
        
        print()
        
        # Check role templates
        print("Step 5: Checking role templates...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM role_templates;"))
            template_count = result.fetchone()[0]
            print(f"   ✅ Found {template_count} role templates")
            
            if template_count < 2:
                print(f"   ⚠️  Expected 2 role templates, found {template_count}")
        
        print()
        
        print("=" * 60)
        print("✅ Database connection test PASSED!")
        print("=" * 60)
        return True
        
    except SQLAlchemyError as e:
        print("=" * 60)
        print("❌ Database connection test FAILED!")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        print("Troubleshooting:")
        print("1. Check if PostgreSQL is running: systemctl status postgresql")
        print("2. Check if database exists: psql -l | grep flexcube_chatbot")
        print("3. Check if user exists: psql -U postgres -c '\\du' | grep chatbot_user")
        print("4. Verify DATABASE_URL is correct")
        return False
    except Exception as e:
        print("=" * 60)
        print("❌ Unexpected error!")
        print("=" * 60)
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)




