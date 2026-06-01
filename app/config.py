from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Gateway configuration, sourced from environment / .env."""

    model_config = SettingsConfigDict(
        env_prefix="ONE_API_", env_file=".env", extra="ignore"
    )

    store: str = "memory"  # "memory" | "redis"
    default_balance: int = 100
    redis_url: str = "redis://localhost:6379/0"

    # Per-call cost for each billable endpoint, in credits.
    # Dollar costs are divided by $0.001/credit for display purposes.
    costs: dict[str, int] = {
        "/v1/enrich": 10,   # legacy mock
        "/v1/scrape": 5,    # legacy mock
        "/v1/jina": 2,      # $0.002 per scrape
        "/v1/firecrawl": 5, # $0.005 per scrape
        "/v1/weather": 1,   # $0.001 per call
        "/v1/search": 10,   # $0.010 per search
    }


class OpenAISettings(BaseSettings):
    """Reads OPENAI_API_KEY from .env (no prefix)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"


settings = Settings()
openai_settings = OpenAISettings()
