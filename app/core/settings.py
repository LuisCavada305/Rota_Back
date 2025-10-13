# app/core/settings.py
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    db_engine: str = Field(default="postgresql+psycopg", env="DB_ENGINE")
    db_host: str = Field(default="localhost", env="DB_HOST")
    db_port: int = Field(default=5432, env="DB_PORT")
    db_name: str = Field(default="rota", env="DB_NAME")
    db_user: str = Field(default="rota_user", env="DB_USER")
    db_pass: str = Field(default="supersecret", env="DB_PASS")
    database_url: str | None = Field(default=None, env="DATABASE_URL")
    API_ORIGIN: str = Field(default="http://localhost:5173", env="API_ORIGIN")
    JWT_SECRET: str = Field(env="JWT_SECRET")
    COOKIE_NAME: str = Field(default="rota_session", env="COOKIE_NAME")
    CSRF_COOKIE_NAME: str = Field(default="rota_csrf", env="CSRF_COOKIE_NAME")
    ENV: str = Field(default="dev", env="ENV")
    EMAIL_BACKEND: str = Field(default="console", env="EMAIL_BACKEND")
    SMTP_HOST: str = Field(default="localhost", env="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, env="SMTP_PORT")
    SMTP_USERNAME: str | None = Field(default=None, env="SMTP_USERNAME")
    SMTP_PASSWORD: str | None = Field(default=None, env="SMTP_PASSWORD")
    SMTP_USE_TLS: bool = Field(default=True, env="SMTP_USE_TLS")
    SMTP_USE_SSL: bool = Field(default=False, env="SMTP_USE_SSL")
    SMTP_TIMEOUT: float = Field(default=10.0, env="SMTP_TIMEOUT")
    DEFAULT_FROM_EMAIL: str = Field(
        default="no-reply@example.com", env="DEFAULT_FROM_EMAIL"
    )
    FRONTEND_ORIGIN: str = Field(
        default="http://localhost:5173", env="FRONTEND_ORIGIN"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",              # troque para ".env.docker" se rodar no compose
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def url(self) -> str:
        return self.database_url or (
            f"{self.db_engine}://{self.db_user}:{self.db_pass}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

settings = Settings()
