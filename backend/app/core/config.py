from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, model_validator
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
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_image_model: str = Field(default="gpt-image-1", alias="OPENAI_IMAGE_MODEL")
    slack_webhook_url: str = Field(default="", alias="SLACK_WEBHOOK_URL")
    aws_region: str = Field(default="", alias="AWS_REGION")
    sp_api_endpoint: str = Field(
        default="",
        validation_alias=AliasChoices("SP_API_ENDPOINT", "SPAPI_ENDPOINT"),
    )
    sp_api_token_url: str = Field(default="https://api.amazon.com/auth/o2/token", alias="SP_API_TOKEN_URL")
    admin_email: str = Field(default="admin@example.com", alias="ADMIN_EMAIL")
    admin_password: str = Field(default="change-me-admin", alias="ADMIN_PASSWORD")
    access_token_expire_minutes: int = Field(default=720, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    media_root: Path = Field(default=ROOT_DIR / "storage", alias="MEDIA_ROOT")
    media_url_prefix: str = Field(default="/media", alias="MEDIA_URL_PREFIX")
    aplus_upload_max_bytes: int = Field(default=8 * 1024 * 1024, alias="APLUS_UPLOAD_MAX_BYTES")

    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env",),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def apply_amazon_endpoint_defaults(self) -> "Settings":
        if self.aws_region:
            return self

        endpoint = self.sp_api_endpoint.lower()
        if "sellingpartnerapi-eu" in endpoint:
            self.aws_region = "eu-west-1"
        elif "sellingpartnerapi-fe" in endpoint:
            self.aws_region = "us-west-2"
        else:
            self.aws_region = "us-east-1"

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
