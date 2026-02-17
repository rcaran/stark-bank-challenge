import sqlite3

from src.shared.database.connection import DatabaseConnection, get_db_connection


def test_database_connection_singleton():
    db1 = DatabaseConnection()
    db2 = DatabaseConnection()

    assert db1 is db2
    assert db1.connection is db2.connection


def test_get_db_connection():
    conn = get_db_connection()
    assert isinstance(conn, sqlite3.Connection)


def test_get_db_cursor():
    from src.shared.database.connection import get_db_cursor

    with get_db_cursor() as cursor:
        assert isinstance(cursor, sqlite3.Cursor)


def test_transaction_management():
    # Only test if context manager works,
    # actual rollback logic tested in integration usually
    db = DatabaseConnection()

    with db.get_db() as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS test_transaction (id INTEGER PRIMARY KEY)"
        )
        conn.execute("INSERT INTO test_transaction (id) VALUES (1)")

    cursor = db.connection.execute("SELECT * FROM test_transaction WHERE id=1")
    row = cursor.fetchone()
    assert row["id"] == 1

    # Cleanup
    db.connection.execute("DROP TABLE IF EXISTS test_transaction")
