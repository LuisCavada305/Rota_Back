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
    CSRF_SECRET: str | None = Field(default=None, env="CSRF_SECRET")
    COOKIE_NAME: str = Field(default="rota_session", env="COOKIE_NAME")
    CSRF_COOKIE_NAME: str = Field(default="rota_csrf", env="CSRF_COOKIE_NAME")
    ENV: str = Field(default="dev", env="ENV")
    smtp_host: str | None = Field(default=None, env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_user: str | None = Field(default=None, env="SMTP_USER")
    smtp_password: str | None = Field(default=None, env="SMTP_PASSWORD")
    smtp_starttls: bool = Field(default=True, env="SMTP_STARTTLS")
    smtp_timeout: int = Field(default=20, env="SMTP_TIMEOUT")
    smtp_from_name: str = Field(default="Equipe Rota", env="SMTP_FROM_NAME")
    smtp_from_email: str | None = Field(default=None, env="SMTP_FROM_EMAIL")
    app_base_url: str | None = Field(default=None, env="APP_BASE_URL")
    password_reset_path: str = Field(default="/redefinir-senha", env="PASSWORD_RESET_PATH")
    rota_brand_color: str = Field(default="#0A3D8F", env="ROTA_BRAND_COLOR")

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
