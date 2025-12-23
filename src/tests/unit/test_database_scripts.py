"""
Unit Tests for Database Setup Scripts

Tests for the database setup scripts and utilities.
"""

import pytest
import os
import tempfile
from pathlib import Path


class TestDatabaseScripts:
    """Test database setup scripts."""
    
    def test_setup_script_exists(self):
        """Test that setup_database.sh script exists."""
        script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "setup_database.sh"
        assert script_path.exists(), "setup_database.sh script should exist"
        assert script_path.is_file(), "setup_database.sh should be a file"
        assert os.access(script_path, os.X_OK), "setup_database.sh should be executable"
    
    def test_create_tables_sql_exists(self):
        """Test that create_tables.sql script exists."""
        script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "create_tables.sql"
        assert script_path.exists(), "create_tables.sql script should exist"
        assert script_path.is_file(), "create_tables.sql should be a file"
    
    def test_test_connection_script_exists(self):
        """Test that test_database_connection.py script exists."""
        script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "test_database_connection.py"
        assert script_path.exists(), "test_database_connection.py script should exist"
        assert script_path.is_file(), "test_database_connection.py should be a file"
    
    def test_sql_file_contains_required_tables(self):
        """Test that create_tables.sql contains all required table definitions."""
        script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "create_tables.sql"
        content = script_path.read_text()
        
        required_tables = [
            'CREATE TABLE.*users',
            'CREATE TABLE.*permissions',
            'CREATE TABLE.*user_permissions',
            'CREATE TABLE.*role_templates',
            'CREATE TABLE.*role_template_permissions',
            'CREATE TABLE.*sessions',
            'CREATE TABLE.*conversations',
            'CREATE TABLE.*qa_pairs',
            'CREATE TABLE.*feedback',
            'CREATE TABLE.*training_data_export'
        ]
        
        for pattern in required_tables:
            assert pytest.importorskip("re").search(pattern, content, pytest.importorskip("re").IGNORECASE), \
                f"create_tables.sql should contain {pattern}"
    
    def test_sql_file_contains_permissions_insert(self):
        """Test that create_tables.sql contains permissions INSERT statements."""
        script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "create_tables.sql"
        content = script_path.read_text()
        
        assert 'INSERT INTO permissions' in content, "Should contain permissions INSERT"
        assert 'view_chat' in content, "Should contain view_chat permission"
        assert 'operational_admin' in content, "Should contain operational_admin template"
        assert 'general_user' in content, "Should contain general_user template"




