from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Application
    app_name: str = "Recipe Chat Assistant"
    debug: bool = False
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./local_dev.db"
    
    # Authentication
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    
    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    
    # LLM Integration
    google_api_key: str
    google_openai_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    
    # Email (optional for MVP)
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    
    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()