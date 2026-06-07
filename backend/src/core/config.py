"""
Pydantic Settings for PrimoAuditAI v2.
Loads from environment variables and .env files.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql+asyncpg://primoauditai:primoauditai@localhost:5432/primoauditai_v2"

    # Security
    api_keys: str = "pa_dev_key"
    cors_allowed_origins: str = "http://localhost:3000"

    # App
    log_level: str = "INFO"
    log_format: str = "json"  # json or text
    app_name: str = "PrimoAuditAI v2"
    app_version: str = "2.0.0"

    @property
    def api_key_list(self) -> list[str]:
        return [k.strip() for k in self.api_keys.split(",") if k.strip()]

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]


# Singleton
_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    global _settings
    _settings = None
