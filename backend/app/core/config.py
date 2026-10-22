"""Application settings, read from the environment (or a local .env file)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    debug: bool = False
    database_url: str = "sqlite:///./portfolio.db"
    allowed_origins: list[str] = ["https://portfolio.ntshptl.in"]

    # Long random value; every admin route lives under /a/{admin_path_prefix}.
    admin_path_prefix: str = Field(min_length=16, pattern=r"^[A-Za-z0-9_-]+$")
    session_secret: str = Field(min_length=16)
    session_ttl_seconds: int = 2 * 60 * 60
    login_max_failures: int = 5  # per IP + username
    login_max_failures_per_account: int = 20  # per username, from any IP
    login_lockout_seconds: int = 15 * 60

    max_upload_bytes: int = 40 * 1024 * 1024
    max_request_body_bytes: int = 1_000_000  # JSON API calls; photos go straight to R2
    max_image_pixels: int = 100_000_000

    r2_endpoint: str = ""
    # Only if the browser must reach the store at a different address than the server does
    # (local Docker). Leave empty in production: R2 has one public endpoint.
    r2_presign_endpoint: str = ""
    r2_access_key: str = ""
    r2_secret_key: str = ""
    r2_public_bucket: str = ""
    r2_private_bucket: str = ""
    cdn_base_url: str

    unsplash_access_key: str = ""
    unsplash_user: str = "ntshptl"

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    contact_max_per_hour: int = 5  # per IP
    contact_max_per_hour_global: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
