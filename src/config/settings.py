"""Application configuration settings loaded from environment variables."""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Carrega variáveis do arquivo .env (não sobrescreve variáveis já definidas no ambiente)
load_dotenv(override=False)


@dataclass(frozen=True)
class Settings:
    # App
    app_name: str = field(default="")
    app_env: str = field(default="")
    log_level: str = field(default="")
    api_port: int = field(default=0)
    api_host: str = field(default="")

    # Security
    admin_api_key: str | None = field(default=None)

    # Stark Bank
    starkbank_private_key_content: str = field(default="")
    starkbank_project_id: str = field(default="")
    starkbank_environment: str = field(default="")

    # Database
    database_url: str = field(default="")

    # Scheduler
    scheduler_enabled: bool = field(default=True)
    scheduler_interval_hours: int = field(default=3)
    invoice_generation_min: int = field(default=8)
    invoice_generation_max: int = field(default=12)

    def __post_init__(self) -> None:
        # Lê todas as variáveis de ambiente no momento da instanciação,
        # garantindo que valores injetados pelo Railway (ou qualquer ambiente)
        # sejam capturados corretamente.
        object.__setattr__(self, "app_name", os.getenv("APP_NAME", "stark-bank-challenge"))
        object.__setattr__(self, "app_env", os.getenv("APP_ENV", "development"))
        object.__setattr__(self, "log_level", os.getenv("LOG_LEVEL", "INFO"))
        object.__setattr__(self, "api_port", int(os.getenv("API_PORT", "8000")))
        object.__setattr__(self, "api_host", os.getenv("API_HOST", "0.0.0.0"))

        object.__setattr__(self, "admin_api_key", os.getenv("ADMIN_API_KEY") or None)

        object.__setattr__(
            self,
            "starkbank_private_key_content",
            os.getenv("STARKBANK_PRIVATE_KEY_CONTENT", "").replace("\\n", "\n"),
        )
        object.__setattr__(self, "starkbank_project_id", os.getenv("STARKBANK_PROJECT_ID", ""))
        object.__setattr__(self, "starkbank_environment", os.getenv("STARKBANK_ENVIRONMENT", "sandbox"))

        object.__setattr__(self, "database_url", os.getenv("DATABASE_URL", "sqlite:///./starkbank.db"))

        object.__setattr__(
            self,
            "scheduler_enabled",
            os.getenv("SCHEDULER_ENABLED", "true").lower() not in ("false", "0", "no"),
        )
        object.__setattr__(self, "scheduler_interval_hours", int(os.getenv("SCHEDULER_INTERVAL_HOURS", "3")))
        object.__setattr__(self, "invoice_generation_min", int(os.getenv("INVOICE_GENERATION_MIN", "8")))
        object.__setattr__(self, "invoice_generation_max", int(os.getenv("INVOICE_GENERATION_MAX", "12")))

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() == "development"


# Singleton instance — criado após load_dotenv(), lendo o ambiente no momento certo
settings = Settings()
