"""Application settings loaded and validated from the environment."""

from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration shared by the API and its integrations."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    database_url: str
    application_cycle: str
    cors_origins: str
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str = "resumes"
    minio_secure: bool
    brevo_smtp_host: str
    brevo_smtp_port: int
    brevo_smtp_login: str
    brevo_smtp_key: str
    email_from: str
    email_from_name: str
    app_env: Literal["development", "test", "production"] = "development"

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        origins = [origin.strip() for origin in value.split(",")]
        if not origins or any(not origin for origin in origins):
            raise ValueError("CORS_ORIGINS must contain explicit origins")
        if "*" in origins:
            raise ValueError("CORS_ORIGINS cannot contain a wildcard origin")
        return ",".join(origins)

    @property
    def allowed_origins(self) -> list[str]:
        """Return configured frontend origins as a trimmed allowlist."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
