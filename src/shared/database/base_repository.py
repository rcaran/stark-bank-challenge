"""Base repository class for database operations."""

from sqlite3 import Cursor, Row
from typing import TypeVar

from src.shared.database.connection import DatabaseConnection
from src.shared.utils.logger import get_logger

logger = get_logger("shared.database.repository")

T = TypeVar("T")


class BaseRepository[T]:
    def __init__(self, db_connection: DatabaseConnection = None):
        if db_connection is None:
            self.db = DatabaseConnection()
        else:
            self.db = db_connection

    def _execute(self, query: str, params: tuple = ()) -> Cursor:
        try:
            with self.db.get_db() as conn:
                logger.debug(f"Executing query: {query}", query_params=str(params))
                return conn.execute(query, params)
        except Exception as e:
            logger.error(f"Error executing query: {query}", error=str(e))
            raise

    def _fetchone(self, query: str, params: tuple = ()) -> Row | None:
        cursor = self._execute(query, params)
        return cursor.fetchone()

    def _fetchall(self, query: str, params: tuple = ()) -> list[Row]:
        cursor = self._execute(query, params)
        return cursor.fetchall()
