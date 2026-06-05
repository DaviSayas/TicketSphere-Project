"""Application configuration loaded from environment variables."""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised configuration. All values can be overridden via env vars or .env file."""

    # Database
    DATABASE_URL: str = "sqlite:///./tickets.db"

    # JWT
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440  # 24h

    # SMTP (outbound)
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_FROM: str = "helpdesk@empresa.pt"
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # IMAP (inbound)
    IMAP_HOST: str = "localhost"
    IMAP_PORT: int = 1143
    IMAP_USER: str = "support@empresa.pt"
    IMAP_PASSWORD: str = "password"
    IMAP_USE_SSL: bool = False

    # Scheduler
    ENABLE_SCHEDULER: bool = True
    IMAP_POLL_MINUTES: int = 2
    SLA_CHECK_MINUTES: int = 5

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:8080,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


settings = Settings()
