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

    # Pydantic v2: configurações via model_config
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
