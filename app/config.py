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
    costs: dict[str, int] = {
        "/v1/enrich": 10,
        "/v1/scrape": 5,
    }


settings = Settings()
