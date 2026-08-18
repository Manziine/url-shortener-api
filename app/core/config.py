from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/urlshortener"
    REDIS_URL: str = "redis://localhost:6379"
    BASE_URL: str = "http://localhost:8000"
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"


settings = Settings()
