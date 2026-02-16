from pathlib import Path

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

    def _get_applied_migrations(self) -> list[str]:
        cursor = self.conn.execute("SELECT version FROM schema_migrations")
        return [row["version"] for row in cursor.fetchall()]

    def run_migrations(self):
        logger.info("Starting migrations...")
        self._init_migrations_table()

        applied = self._get_applied_migrations()
        migration_files = sorted(
            [
                f.name
                for f in self.migrations_dir.iterdir()
                if f.suffix == ".sql"
            ]
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
        with file_path.open() as f:
            sql_script = f.read()

        try:
            with self.conn:
                self.conn.executescript(sql_script)
                self.conn.execute(
                    "INSERT INTO schema_migrations (version) VALUES (?)",
                    (filename,)
                )
        except Exception as e:
            logger.error(f"Failed to apply migration {filename}: {e!s}")
            raise

def run_migrations():
    """
    Convenience function to run all migrations.

    This function creates a MigrationRunner instance and runs all
    pending migrations from the migrations directory.
    """
    runner = MigrationRunner()
    runner.run_migrations()


def migrate_database(conn):
    """
    Run migrations on a specific database connection.
    
    This is useful for testing where we want to use a specific
    test database connection instead of the global one.
    
    Args:
        conn: sqlite3.Connection - Database connection to migrate
    """
    migrations_dir = Path("migrations")
    
    # Initialize migrations table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    
    # Get applied migrations
    cursor = conn.execute("SELECT version FROM schema_migrations")
    applied = [row[0] for row in cursor.fetchall()]
    
    # Get migration files
    migration_files = sorted(
        [f.name for f in migrations_dir.iterdir() if f.suffix == ".sql"]
    )
    
    # Apply pending migrations
    for file in migration_files:
        if file not in applied:
            logger.info(f"Applying migration: {file}")
            file_path = migrations_dir / file
            with file_path.open() as f:
                sql_script = f.read()
            
            try:
                with conn:
                    conn.executescript(sql_script)
                    conn.execute(
                        "INSERT INTO schema_migrations (version) VALUES (?)",
                        (file,)
                    )
            except Exception as e:
                logger.error(f"Failed to apply migration {file}: {e!s}")
                raise
        else:
            logger.debug(f"Migration {file} already applied")
    
    logger.info("Migrations completed successfully")


if __name__ == "__main__":
    run_migrations()
