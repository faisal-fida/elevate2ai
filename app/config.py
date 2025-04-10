from typing import List, Literal
from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings
import logging
from pathlib import Path


class Settings(BaseSettings):
    ENVIRONMENT: Literal["development", "production"] = "development"
    PROJECT_NAME: str = "FastAPI Supabase Template"
    PROJECT_DESCRIPTION: str = "Production-ready FastAPI template with Supabase integration"
    LOG_LEVEL: str = "INFO"
    
    # Test Configuration
    TEST_AUTH_TOKEN: str = "test_token"
    TEST_ADMIN_AUTH_TOKEN: str = "test_admin_token"

    # Database configuration
    SUPABASE_URL: str = Field(..., env="SUPABASE_URL")
    SUPABASE_KEY: str = Field(..., env="SUPABASE_KEY")
    SUPABASE_JWT_SECRET: str = Field(..., env="SUPABASE_JWT_SECRET")
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    # Security
    SECURE_COOKIES: bool = False
    TRUSTED_HOSTS: List[str] = ["localhost"]

    # Logging
    LOG_DIR: Path = Path("logs")
    LOG_FORMAT: str = "%(levelname)s:     %(message)s"

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"

    def configure_logging(self) -> None:
        self.LOG_DIR.mkdir(exist_ok=True)
        logging.basicConfig(
            level=self.LOG_LEVEL,
            format=self.LOG_FORMAT,
            handlers=[logging.StreamHandler(), logging.FileHandler(self.LOG_DIR / "app.log")],
        )


settings = Settings()
settings.configure_logging()
