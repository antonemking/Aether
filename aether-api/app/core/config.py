from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Database
    database_url: str
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # API Security
    api_secret_key: str
    api_algorithm: str = "HS256"
    api_access_token_expire_minutes: int = 30

    # LLM APIs
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None

    # Environment
    environment: str = "development"

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
