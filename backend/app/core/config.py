from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Amazon Seller Ops"
    app_version: str = "0.1.0"
    app_env: str = Field(default="development", alias="APP_ENV")
    secret_key: str = Field(default="change-me-change-me-change-me-1234", alias="SECRET_KEY")
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/amazon_seller_ops",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    lwa_client_id: str = Field(default="", alias="LWA_CLIENT_ID")
    lwa_client_secret: str = Field(default="", alias="LWA_CLIENT_SECRET")
    aws_access_key_id: str = Field(default="", alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(default="", alias="AWS_SECRET_ACCESS_KEY")
    lwa_refresh_token: str = Field(default="", alias="LWA_REFRESH_TOKEN")
    marketplace_id: str = Field(default="", alias="MARKETPLACE_ID")
    seller_id: str = Field(default="", alias="SELLER_ID")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    slack_webhook_url: str = Field(default="", alias="SLACK_WEBHOOK_URL")
    admin_email: str = Field(default="admin@example.com", alias="ADMIN_EMAIL")
    admin_password: str = Field(default="change-me-admin", alias="ADMIN_PASSWORD")
    access_token_expire_minutes: int = Field(default=720, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env",),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
