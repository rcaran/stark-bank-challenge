import os
from pathlib import Path
from typing import List

from src.shared.database.connection import get_db_connection
from src.shared.utils.logger import get_logger

logger = get_logger("shared.database.migrations")

class MigrationRunner:
    def __init__(self, migrations_dir: str = "migrations"):
        self.migrations_dir = Path(migrations_dir)
        self.conn = get_db_connection()

    def _init_migrations_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def _get_applied_migrations(self) -> List[str]:
        cursor = self.conn.execute("SELECT version FROM schema_migrations")
        return [row["version"] for row in cursor.fetchall()]

    def run_migrations(self):
        logger.info("Starting migrations...")
        self._init_migrations_table()

        applied = self._get_applied_migrations()
        migration_files = sorted(
            [f for f in os.listdir(self.migrations_dir) if f.endswith(".sql")]
        )

        for file in migration_files:
            if file not in applied:
                logger.info(f"Applying migration: {file}")
                self._apply_migration(file)
            else:
                logger.debug(f"Migration {file} already applied")

        logger.info("Migrations completed successfully")

    def _apply_migration(self, filename: str):
        file_path = self.migrations_dir / filename
        with open(file_path, "r") as f:
            sql_script = f.read()

        try:
            with self.conn:
                self.conn.executescript(sql_script)
                self.conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES (?)",
                    (filename,)
                )
        except Exception as e:
            logger.error(f"Failed to apply migration {filename}: {str(e)}")
            raise

if __name__ == "__main__":
    runner = MigrationRunner()
    runner.run_migrations()
