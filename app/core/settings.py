from __future__ import annotations

from typing import Iterable, List

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: str) -> List[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


class Settings(BaseSettings):
    """Centralise configuration with validation for production hardening."""

    db_engine: str = Field(default="postgresql+psycopg", env="DB_ENGINE")
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT")
    db_name: str = Field(default="rota", env="DB_NAME")
    db_user: str = Field(default="rota_user", env="DB_USER")
    db_pass: str = Field(default="supersecret", env="DB_PASS")
    database_url: str | None = Field(default=None, env="DATABASE_URL")
    db_pool_size: int = Field(default=8, env="DB_POOL_SIZE", ge=1, le=32)
    db_max_overflow: int = Field(default=0, env="DB_MAX_OVERFLOW", ge=0, le=32)
    db_pool_timeout: int = Field(default=20, env="DB_POOL_TIMEOUT", ge=1)
    db_pool_recycle: int = Field(default=1800, env="DB_POOL_RECYCLE", ge=30)

    API_ORIGIN: str = Field(default="https://localhost:5173", env="API_ORIGIN")
    JWT_SECRET: str = Field(env="JWT_SECRET")
    CSRF_SECRET: str | None = Field(default=None, env="CSRF_SECRET")
    COOKIE_NAME: str = Field(default="rota_session", env="COOKIE_NAME")
    CSRF_COOKIE_NAME: str = Field(default="rota_csrf", env="CSRF_COOKIE_NAME")
    ENV: str = Field(default="dev", env="ENV")

    cors_allowed_origins: list[str] | str = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "https://localhost:5173",
            "https://127.0.0.1:5173",
        ],
        env="CORS_ALLOWED_ORIGINS",
    )
    cors_allow_headers: list[str] | str = Field(
        default_factory=lambda: [
            "Content-Type",
            "X-CSRF-Token",
            "X-CSRFToken",
            "X-Requested-With",
        ],
        env="CORS_ALLOW_HEADERS",
    )
    cors_expose_headers: list[str] | str = Field(
        default_factory=lambda: ["X-CSRF-Token", "X-CSRFToken"],
        env="CORS_EXPOSE_HEADERS",
    )

    redis_url: str | None = Field(default=None, env="REDIS_URL")
    auth_rate_limit_window_seconds: int = Field(
        default=60, env="AUTH_RATE_LIMIT_WINDOW_SECONDS", ge=1
    )
    auth_rate_limit_max_attempts: int = Field(
        default=10, env="AUTH_RATE_LIMIT_MAX_ATTEMPTS", ge=1
    )

    smtp_host: str | None = Field(default=None, env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_user: str | None = Field(default=None, env="SMTP_USER")
    smtp_password: str | None = Field(default=None, env="SMTP_PASSWORD")
    smtp_starttls: bool = Field(default=True, env="SMTP_STARTTLS")
    smtp_timeout: int = Field(default=20, env="SMTP_TIMEOUT")
    smtp_from_name: str = Field(default="Equipe Rota", env="SMTP_FROM_NAME")
    smtp_from_email: str | None = Field(default=None, env="SMTP_FROM_EMAIL")
    app_base_url: str | None = Field(default=None, env="APP_BASE_URL")
    password_reset_base_url: str | None = Field(
        default=None, env="PASSWORD_RESET_BASE_URL"
    )
    password_reset_path: str = Field(
        default="/redefinir-senha", env="PASSWORD_RESET_PATH"
    )
    rota_brand_color: str = Field(default="#0A3D8F", env="ROTA_BRAND_COLOR")

    model_config = SettingsConfigDict(
        env_file=".env",  # troque para ".env.docker" se rodar no compose
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("JWT_SECRET")
    @classmethod
    def _ensure_jwt_strength(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 16:
            raise ValueError("JWT_SECRET deve ter pelo menos 16 caracteres")
        if value.lower() in {"changeme", "secret", "supersecret"}:
            raise ValueError("JWT_SECRET não pode usar valores triviais")
        return value

    @field_validator("CSRF_SECRET")
    @classmethod
    def _normalize_csrf(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None

    @field_validator(
        "cors_allowed_origins",
        "cors_allow_headers",
        "cors_expose_headers",
        mode="before",
    )
    @classmethod
    def _coerce_csv(cls, value: Iterable[str] | str | None) -> list[str] | None:
        if value is None or value == "":
            return None
        if isinstance(value, str):
            return _split_csv(value)
        return [str(item).strip() for item in value if str(item).strip()]

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        env = (self.ENV or "").lower()
        if env in {"prod", "production"}:
            if self.db_pass == "supersecret":
                raise ValueError("DB_PASS padrão não é permitido em produção")
            if self.db_user == "rota_user":
                raise ValueError("DB_USER padrão não é permitido em produção")
            if not self.CSRF_SECRET:
                raise ValueError("CSRF_SECRET é obrigatório em produção")
        return self

    @property
    def is_production(self) -> bool:
        return (self.ENV or "").lower() in {"prod", "production"}

    @property
    def url(self) -> str:
        return self.database_url or (
            f"{self.db_engine}://{self.db_user}:{self.db_pass}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def cors_origin_set(self) -> set[str]:
        return set(self.cors_allowed_origins_list())

    def cors_allowed_origins_list(self) -> list[str]:
        if isinstance(self.cors_allowed_origins, list):
            return self.cors_allowed_origins
        return _split_csv(self.cors_allowed_origins or "")

    def cors_allow_headers_list(self) -> list[str]:
        if isinstance(self.cors_allow_headers, list):
            return self.cors_allow_headers
        return _split_csv(self.cors_allow_headers or "")

    def cors_expose_headers_list(self) -> list[str]:
        if isinstance(self.cors_expose_headers, list):
            return self.cors_expose_headers
        return _split_csv(self.cors_expose_headers or "")

    def cors_allow_headers_string(self) -> str:
        return ",".join(self.cors_allow_headers_list())


settings = Settings()
