from datetime import datetime, timezone
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


def utcnow() -> datetime:
    """Timezone-naive UTC timestamp, consistent with the TIMESTAMP columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "SupportOps API"
    app_version: str = "1.1.0"
    debug: bool = False

    database_url: str = (
        "postgresql://supportops:password@localhost:5435/supportops"
    )
    sql_echo: bool = False

    default_page_size: int = 50
    max_page_size: int = 200

    cors_origins: str = "*"

    @property
    def cors_origin_list(self) -> list[str]:
        raw = self.cors_origins.strip()
        if raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()