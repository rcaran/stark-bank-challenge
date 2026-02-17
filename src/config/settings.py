"""Application configuration settings loaded from environment variables."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
load_dotenv()


@dataclass(frozen=True)
class Settings:
    # App
    app_name: str = os.getenv("APP_NAME", "stark-bank-challenge")
    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    api_host: str = os.getenv("API_HOST", "0.0.0.0")

    # Security
    admin_api_key: str | None = os.getenv("ADMIN_API_KEY")

    # Stark Bank
    starkbank_private_key_content: str = os.getenv("STARKBANK_PRIVATE_KEY_CONTENT", "")
    starkbank_project_id: str = os.getenv("STARKBANK_PROJECT_ID", "")
    starkbank_environment: str = os.getenv("STARKBANK_ENVIRONMENT", "sandbox")

    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./starkbank.db")

    # Scheduler
    scheduler_interval_hours: int = int(os.getenv("SCHEDULER_INTERVAL_HOURS", "3"))
    invoice_generation_min: int = int(os.getenv("INVOICE_GENERATION_MIN", "8"))
    invoice_generation_max: int = int(os.getenv("INVOICE_GENERATION_MAX", "12"))

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() == "development"


# Singleton instance
settings = Settings()
