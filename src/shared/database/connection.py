"""Database connection management using SQLite."""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager

from src.config.settings import settings
from src.shared.utils.logger import get_logger

logger = get_logger("shared.database.connection")


class DatabaseConnection:
    _instance = None
    _connection = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _create_connection(self) -> sqlite3.Connection:
        db_path = settings.database_url.replace("sqlite:///", "")
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row

        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")

        return conn

    @property
    def connection(self) -> sqlite3.Connection:
        if self._connection is None:
            self._connection = self._create_connection()
        return self._connection

    @contextmanager
    def get_db(self) -> Generator[sqlite3.Connection]:
        conn = self.connection
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database transaction failed: {e!s}")
            raise
        # We don't close the connection here because we're using a singleton connection
        # for SQLite in this simple architecture.


def get_db_connection() -> sqlite3.Connection:
    return DatabaseConnection().connection


@contextmanager
def get_db_cursor() -> Generator[sqlite3.Cursor]:
    with DatabaseConnection().get_db() as conn:
        yield conn.cursor()
