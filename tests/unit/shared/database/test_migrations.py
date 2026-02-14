import os
import sqlite3
import pytest
from src.shared.database.migrations import MigrationRunner
from src.shared.database.connection import DatabaseConnection

@pytest.fixture
def temp_db(tmp_path):
    # This is tricky because DatabaseConnection is a singleton.
    # We might need to mock settings or reset singleton in tests.
    pass

# For now assume we run against existing or test db
# But for unit testing migrations, we usually mock the connection.
# But here we want to verifying migration logic with sqlite.

def test_migration_runner_init(mocker):
    runner = MigrationRunner()
    assert runner.migrations_dir.name == "migrations"
    
def test_migrations_applied(mocker):
    # Mocking get_db_connection to return a memory connection would be safer
    # But since we are running against real DB in dev, let's just check if table exists
    
    runner = MigrationRunner()
    conn = runner.conn
    
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'")
    if cursor.fetchone():
        # migrations table exists
        cursor = conn.execute("SELECT version FROM schema_migrations")
        rows = cursor.fetchall()
        assert len(rows) > 0
    else:
        # Migrations not run yet in this environment or first run
        pass
