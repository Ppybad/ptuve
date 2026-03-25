from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    downloader_type: Literal["ytdlp"] = "ytdlp"
    downloads_dir: str = "/downloads"
    database_url: str = "postgresql://postgres:postgres@db:5432/ptuve"
    redis_url: str = "redis://redis:6379/0"
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=False, extra="ignore")

settings = Settings()
