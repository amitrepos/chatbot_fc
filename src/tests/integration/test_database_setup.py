"""
Integration Tests for Database Setup (Step 1)

Tests that verify:
- Database exists and is accessible
- All required tables exist
- Permissions and role templates are seeded correctly
- Indexes are created
"""

import pytest
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
import os


@pytest.fixture(scope="module")
def db_engine():
    """Create database engine for integration tests."""
    # Use Unix socket connection (peer authentication)
    # This works when running tests as postgres user or via sudo -u postgres
    database_url = os.getenv(
        'TEST_DATABASE_URL',
        'postgresql:///flexcube_chatbot'  # Unix socket - no password needed
    )
    engine = create_engine(database_url)
    yield engine
    engine.dispose()


class TestDatabaseExists:
    """Test that database exists and is accessible."""
    
    def test_database_connection(self, db_engine):
        """Test that we can connect to the database."""
        with db_engine.connect() as conn:
            result = conn.execute(text("SELECT current_database();"))
            db_name = result.fetchone()[0]
            assert db_name == 'flexcube_chatbot'
    
    def test_database_version(self, db_engine):
        """Test that PostgreSQL version is accessible."""
        with db_engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            assert 'PostgreSQL' in version


class TestTablesExist:
    """Test that all required tables exist."""
    
    @pytest.fixture
    def inspector(self, db_engine):
        """Get database inspector."""
        return inspect(db_engine)
    
    @pytest.fixture
    def expected_tables(self):
        """List of expected tables."""
        return [
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
    
    def test_all_tables_exist(self, inspector, expected_tables):
        """Test that all 10 required tables exist."""
        tables = inspector.get_table_names()
        for table in expected_tables:
            assert table in tables, f"Table {table} is missing"
    
    def test_table_count(self, inspector, expected_tables):
        """Test that exactly 10 tables exist."""
        tables = inspector.get_table_names()
        # Filter out system tables if any
        user_tables = [t for t in tables if not t.startswith('pg_')]
        assert len(user_tables) == len(expected_tables)


class TestPermissionsSeeded:
    """Test that permissions are seeded correctly."""
    
    def test_permissions_count(self, db_engine):
        """Test that 15 permissions are seeded."""
        with db_engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM permissions;"))
            count = result.fetchone()[0]
            assert count == 15, f"Expected 15 permissions, found {count}"
    
    def test_permission_categories(self, db_engine):
        """Test that permissions have correct categories."""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT category FROM permissions ORDER BY category;
            """))
            categories = [row[0] for row in result.fetchall()]
            expected_categories = ['chat', 'dashboard', 'data', 'documents', 'system', 'users']
            for cat in expected_categories:
                assert cat in categories, f"Category {cat} is missing"
    
    def test_specific_permissions_exist(self, db_engine):
        """Test that key permissions exist."""
        required_permissions = [
            'view_chat',
            'view_image_query',
            'view_admin_dashboard',
            'export_training_data',
            'create_users',
            'manage_system_settings'
        ]
        with db_engine.connect() as conn:
            for perm in required_permissions:
                result = conn.execute(
                    text("SELECT COUNT(*) FROM permissions WHERE name = :name"),
                    {"name": perm}
                )
                count = result.fetchone()[0]
                assert count == 1, f"Permission {perm} is missing"


class TestRoleTemplatesSeeded:
    """Test that role templates are seeded correctly."""
    
    def test_role_templates_count(self, db_engine):
        """Test that 2 role templates exist."""
        with db_engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM role_templates;"))
            count = result.fetchone()[0]
            assert count == 2, f"Expected 2 role templates, found {count}"
    
    def test_operational_admin_template(self, db_engine):
        """Test that operational_admin template exists with all permissions."""
        with db_engine.connect() as conn:
            # Check template exists
            result = conn.execute(text("""
                SELECT COUNT(*) FROM role_templates WHERE name = 'operational_admin';
            """))
            assert result.fetchone()[0] == 1
            
            # Check it has all 15 permissions
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM role_template_permissions rtp
                JOIN role_templates rt ON rtp.role_template_id = rt.id
                WHERE rt.name = 'operational_admin';
            """))
            perm_count = result.fetchone()[0]
            assert perm_count == 15, f"operational_admin should have 15 permissions, found {perm_count}"
    
    def test_general_user_template(self, db_engine):
        """Test that general_user template exists with 4 permissions."""
        with db_engine.connect() as conn:
            # Check template exists
            result = conn.execute(text("""
                SELECT COUNT(*) FROM role_templates WHERE name = 'general_user';
            """))
            assert result.fetchone()[0] == 1
            
            # Check it has 4 permissions
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM role_template_permissions rtp
                JOIN role_templates rt ON rtp.role_template_id = rt.id
                WHERE rt.name = 'general_user';
            """))
            perm_count = result.fetchone()[0]
            assert perm_count == 4, f"general_user should have 4 permissions, found {perm_count}"
            
            # Check specific permissions
            result = conn.execute(text("""
                SELECT p.name
                FROM role_template_permissions rtp
                JOIN role_templates rt ON rtp.role_template_id = rt.id
                JOIN permissions p ON rtp.permission_id = p.id
                WHERE rt.name = 'general_user'
                ORDER BY p.name;
            """))
            permissions = [row[0] for row in result.fetchall()]
            expected = ['upload_documents', 'view_chat', 'view_documents', 'view_image_query']
            assert set(permissions) == set(expected)


class TestIndexesExist:
    """Test that required indexes exist."""
    
    def test_users_indexes(self, db_engine):
        """Test that users table has required indexes."""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'users' AND schemaname = 'public';
            """))
            indexes = [row[0] for row in result.fetchall()]
            assert any('username' in idx.lower() for idx in indexes)
            assert any('email' in idx.lower() for idx in indexes)
    
    def test_qa_pairs_indexes(self, db_engine):
        """Test that qa_pairs table has required indexes."""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'qa_pairs' AND schemaname = 'public';
            """))
            indexes = [row[0] for row in result.fetchall()]
            assert any('user_id' in idx.lower() for idx in indexes)
            assert any('conversation_id' in idx.lower() for idx in indexes)
    
    def test_jsonb_indexes(self, db_engine):
        """Test that JSONB indexes exist for qa_pairs."""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'qa_pairs' 
                AND (indexname LIKE '%sources%' OR indexname LIKE '%expansion%');
            """))
            indexes = [row[0] for row in result.fetchall()]
            assert len(indexes) >= 2, "JSONB indexes for sources and expansion should exist"


class TestForeignKeys:
    """Test that foreign key constraints exist."""
    
    def test_users_foreign_key_created_by(self, db_engine):
        """Test that users.created_by references users.id."""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_name = 'users' 
                AND tc.constraint_type = 'FOREIGN KEY'
                AND kcu.column_name = 'created_by';
            """))
            assert result.fetchone()[0] >= 1
    
    def test_user_permissions_foreign_keys(self, db_engine):
        """Test that user_permissions has foreign keys."""
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.table_constraints
                WHERE table_name = 'user_permissions' 
                AND constraint_type = 'FOREIGN KEY';
            """))
            fk_count = result.fetchone()[0]
            assert fk_count >= 2, "user_permissions should have at least 2 foreign keys"


class TestDatabaseIntegrity:
    """Test database integrity and constraints."""
    
    def test_unique_constraints(self, db_engine):
        """Test that unique constraints exist."""
        with db_engine.connect() as conn:
            # Check users.username is unique
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.table_constraints
                WHERE table_name = 'users' 
                AND constraint_type = 'UNIQUE'
                AND constraint_name LIKE '%username%';
            """))
            assert result.fetchone()[0] >= 1
            
            # Check permissions.name is unique
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.table_constraints
                WHERE table_name = 'permissions' 
                AND constraint_type = 'UNIQUE'
                AND constraint_name LIKE '%name%';
            """))
            assert result.fetchone()[0] >= 1
    
    def test_not_null_constraints(self, db_engine):
        """Test that required NOT NULL constraints exist."""
        with db_engine.connect() as conn:
            # Check users.username is NOT NULL
            result = conn.execute(text("""
                SELECT is_nullable 
                FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'username';
            """))
            assert result.fetchone()[0] == 'NO'
            
            # Check permissions.name is NOT NULL
            result = conn.execute(text("""
                SELECT is_nullable 
                FROM information_schema.columns
                WHERE table_name = 'permissions' AND column_name = 'name';
            """))
            assert result.fetchone()[0] == 'NO'

