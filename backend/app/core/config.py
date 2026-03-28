from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Amazon Seller Ops"
    app_version: str = "0.1.0"
    app_env: str = Field(default="development", alias="APP_ENV")
    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

