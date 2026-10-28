"""Application settings loaded from the environment."""

from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

NAME_MIN_LENGTH = 2
NAME_MAX_LENGTH = 100
USN_MIN_LENGTH = 5
USN_MAX_LENGTH = 20
ALLOWED_DOMAINS = frozenset(
    {"technology", "photography", "design", "marketing", "social-media"}
)


class Settings(BaseSettings):
    """Runtime configuration shared by the API and its services."""

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
    max_resume_mb: int = 5
    rate_limit_enabled: bool = False
    rate_limit_requests: int = 5
    rate_limit_window_seconds: int = 60

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        origins = [origin.strip() for origin in value.split(",")]
        if not origins or any(not origin for origin in origins):
            raise ValueError("CORS_ORIGINS must contain explicit origins")
        if "*" in origins:
            raise ValueError("CORS_ORIGINS cannot contain a wildcard origin")
        return ",".join(origins)

    @field_validator("max_resume_mb")
    @classmethod
    def validate_max_resume_mb(cls, value: int) -> int:
        if value < 1:
            raise ValueError("MAX_RESUME_MB must be positive")
        return value

    @field_validator("rate_limit_requests", "rate_limit_window_seconds")
    @classmethod
    def validate_rate_limit_values(cls, value: int) -> int:
        if value < 1:
            raise ValueError("Rate limit values must be positive")
        return value

    @property
    def allowed_origins(self) -> list[str]:
        """Return the comma-separated CORS allowlist as trimmed origins."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def max_resume_bytes(self) -> int:
        """Maximum upload size, in bytes."""
        return self.max_resume_mb * 1024 * 1024
