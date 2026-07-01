"""Application settings loaded from environment variables / .env."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration. Values come from the environment or a .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core
    app_name: str = "NutriBot"
    environment: str = Field(default="development")

    # Database (async driver: postgresql+asyncpg://...)
    database_url: str = Field(
        default="postgresql+asyncpg://nutribot:nutribot@db:5432/nutribot"
    )

    # DeepSeek (OpenAI-compatible API)
    deepseek_api_key: str = Field(default="")
    deepseek_base_url: str = Field(default="https://api.deepseek.com")
    deepseek_model: str = Field(default="deepseek-chat")

    # How many past messages to include as context per DeepSeek call.
    chat_history_limit: int = Field(default=20)

    # RAG / embeddings
    embeddings_url: str = Field(default="http://embeddings:80")
    rag_top_k: int = Field(default=4)
    # Minimum cosine similarity (0..1) for a chunk to be injected as context.
    rag_min_similarity: float = Field(default=0.4)
    rag_chunk_size: int = Field(default=800)
    rag_chunk_overlap: int = Field(default=100)

    # Open Food Facts
    off_base_url: str = Field(default="https://world.openfoodfacts.org")
    # Full-text search uses the dedicated Search-a-licious service (the legacy
    # cgi/search.pl endpoint is frequently rate-limited / returns 503).
    off_search_url: str = Field(default="https://search.openfoodfacts.org")
    # OFF asks clients to identify themselves with a descriptive User-Agent.
    off_user_agent: str = Field(
        default="NutriBot/0.1 (personal project; https://t.me/nutribot_beni_bot)"
    )
    off_search_limit: int = Field(default=5)
    off_cache_ttl_days: int = Field(default=30)

    # Auth / JWT
    jwt_secret: str = Field(default="change-me-in-production")
    jwt_algorithm: str = Field(default="HS256")
    access_token_minutes: int = Field(default=30)
    refresh_token_days: int = Field(default=30)
    login_code_minutes: int = Field(default=10)
    # Public URL of the client dashboard (shown by the bot on /login).
    dashboard_client_url: str = Field(default="http://localhost:5173")
    # Comma-separated list of allowed CORS origins for the dashboards.
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:5174"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        origins = {o.strip() for o in self.cors_origins.split(",") if o.strip()}
        origins.add(self.dashboard_client_url)
        return sorted(origins)

    # DeepSeek pricing (USD per 1M tokens) for cost metrics. Adjust to the
    # current published prices for your model.
    deepseek_price_input_per_mtok: float = Field(default=0.27)
    deepseek_price_output_per_mtok: float = Field(default=1.10)


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
