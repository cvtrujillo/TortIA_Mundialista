from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API Keys
    football_data_token: str = ""
    rapidapi_key: str = ""

    # AWS
    aws_region: str = "us-east-1"
    s3_bucket: str = "tortia-mundialista-artifacts"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 21600  # 6h

    # Model
    model_dir: str = "artifacts"
    ensemble_alpha: float = 0.55   # XGB weight in blend

    # App
    environment: str = "development"
    log_level: str = "INFO"
    allowed_origins: list[str] = ["http://localhost:5173", "https://cvtrujillo.github.io"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
