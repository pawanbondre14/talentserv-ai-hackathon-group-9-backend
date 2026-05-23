from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(raw: str) -> str:
    """Fix passwords that contain @ (common in Supabase URLs pasted without encoding)."""
    if "://" not in raw or raw.count("@") <= 1:
        return raw
    scheme, rest = raw.split("://", 1)
    creds, hostpart = rest.rsplit("@", 1)
    if ":" not in creds:
        return raw
    user, password = creds.split(":", 1)
    if "@" in password or "#" in password or " " in password:
        password = quote_plus(password, safe="")
    return f"{scheme}://{user}:{password}@{hostpart}"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "MeetingFeed AI"
    environment: str = "development"
    debug: bool = True
    api_prefix: str = "/api"

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    database_url: str = "postgresql://postgres:postgres@localhost:5432/postgres"

    clerk_issuer: str = ""
    clerk_jwks_url: str = ""
    skip_auth: bool = False
    dev_user_id: str = "dev_user_local"

    anthropic_api_key: str = ""
    openai_api_key: str = ""
    llm_provider: str = "anthropic"  # anthropic | openai
    anthropic_model: str = "claude-sonnet-4-20250514"
    openai_model: str = "gpt-4o-mini"
    min_transcript_words: int = 50
    max_transcript_chars: int = 120_000
    llm_mock: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def database_url_resolved(self) -> str:
        return normalize_database_url(self.database_url)


@lru_cache
def get_settings() -> Settings:
    return Settings()
