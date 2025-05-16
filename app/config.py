import urllib.parse
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application configuration with environment variable mapping.
    All settings can be defined in .env file or as environment variables.
    """

    # Core settings
    PROJECT_NAME: str = Field(default="Elevate2AI", env="PROJECT_NAME")
    PROJECT_DESCRIPTION: str = Field(
        default="WhatsApp content generation service", env="PROJECT_DESCRIPTION"
    )
    ENVIRONMENT: Literal["dev", "prod"] = Field(default="dev", env="ENVIRONMENT")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    BASE_URL: str = Field(default="https://elevate2ai.example.com", env="BASE_URL")

    # Database
    DATABASE_PATH: str = Field(default="./app.db", env="DATABASE_PATH")
    SQL_ECHO: bool = Field(default=False, env="SQL_ECHO")

    # Security
    JWT_SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production", env="JWT_SECRET_KEY"
    )
    JWT_ALGORITHM: str = Field(default="HS256", env="JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS"
    )
    BACKEND_CORS_ORIGINS: str = Field(default="*", env="BACKEND_CORS_ORIGINS")
    SECURE_COOKIES: bool = Field(default=False, env="SECURE_COOKIES")
    TRUSTED_HOSTS: str = Field(default=["*"], env="TRUSTED_HOSTS")

    # External APIs
    # Image/Video services
    PEXELS_API_KEY: str = Field(..., env="PEXELS_API_KEY")
    UNSPLASH_API_KEY: str = Field(..., env="UNSPLASH_API_KEY")
    PIXABAY_API_KEY: str = Field(..., env="PIXABAY_API_KEY")
    SWITCHBOARD_API_KEY: str = Field(..., env="SWITCHBOARD_API_KEY")

    # OpenAI
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    OPENAI_TIMEOUT: float = Field(default=600.0, env="OPENAI_TIMEOUT")
    OPENAI_MAX_RETRIES: int = Field(default=2, env="OPENAI_MAX_RETRIES")

    # WhatsApp
    WHATSAPP_TOKEN: str = Field(..., env="WHATSAPP_TOKEN")
    WHATSAPP_PHONE_NUMBER_ID: str = Field(..., env="WHATSAPP_PHONE_NUMBER_ID")
    WHATSAPP_VERIFY_TOKEN: str = Field(..., env="WHATSAPP_VERIFY_TOKEN")

    # Admin
    ADMIN_WHATSAPP_NUMBER: str = Field(..., env="ADMIN_WHATSAPP_NUMBER")
    ADMIN_PASSWORD: str = Field(..., env="ADMIN_PASSWORD")

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_file_required = True


settings = Settings()

MEDIA_BASE_URL = urllib.parse.urljoin("https://", settings.BASE_URL)
