"""Bot configuration from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    telegram_bot_token: str = Field(default="")
    backend_url: str = Field(default="http://backend:8000")
    request_timeout: float = Field(default=60.0)
    dashboard_client_url: str = Field(default="http://localhost:5173")


@lru_cache
def get_settings() -> BotSettings:
    return BotSettings()
