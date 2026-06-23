from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CRAWLTOP_",
        extra="ignore",
    )

    app_name: str = "crawltop"
    data_dir: Path = Path("./data")
    db_path: Path = Path("./data/crawltop.db")
    log_level: str = "INFO"
    max_concurrency: int = Field(default=10, ge=1, le=100)
    user_agent: str = "crawltop/0.1 (+https://example.com/bot)"
    qdrant_mode: str = "disabled"
    qdrant_path: Path = Path("./data/qdrant")
    openai_api_key: str | None = None
    exa_api_key: str | None = None
    brave_api_key: str | None = None


def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
