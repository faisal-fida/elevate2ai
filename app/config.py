from typing import List, Literal
from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Project Configuration
    PROJECT_NAME: str = Field(default="", env="PROJECT_NAME")
    PROJECT_DESCRIPTION: str = Field(default="", env="PROJECT_DESCRIPTION")
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    ENVIRONMENT: Literal["dev", "prod"] = Field(default="dev", env="ENVIRONMENT")

    # Database Configuration
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./app.db", env="DATABASE_URL"
    )
    SQL_ECHO: bool = Field(default=False, env="SQL_ECHO")

    # JWT Configuration
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

    # Image Management Configuration
    PEXELS_API_KEY: str = Field(..., env="PEXELS_API_KEY")
    UNSPLASH_API_KEY: str = Field(..., env="UNSPLASH_API_KEY")
    PIXABAY_API_KEY: str = Field(..., env="PIXABAY_API_KEY")
    SWITCHBOARD_API_KEY: str = Field(..., env="SWITCHBOARD_API_KEY")

    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(..., env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini", env="OPENAI_MODEL")
    OPENAI_TIMEOUT: float = Field(default=600.0, env="OPENAI_TIMEOUT")
    OPENAI_MAX_RETRIES: int = Field(default=2, env="OPENAI_MAX_RETRIES")

    # WhatsApp Configuration
    WHATSAPP_TOKEN: str = Field(..., env="WHATSAPP_TOKEN")
    WHATSAPP_PHONE_NUMBER_ID: str = Field(..., env="WHATSAPP_PHONE_NUMBER_ID")
    WHATSAPP_VERIFY_TOKEN: str = Field(..., env="WHATSAPP_VERIFY_TOKEN")

    # Admin User Configuration
    ADMIN_WHATSAPP_NUMBER: str = Field(..., env="ADMIN_WHATSAPP_NUMBER")
    ADMIN_PASSWORD: str = Field(..., env="ADMIN_PASSWORD")

    # Security Configuration
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = Field(
        default=["http://localhost:3000"], env="BACKEND_CORS_ORIGINS"
    )
    SECURE_COOKIES: bool = Field(default=False, env="SECURE_COOKIES")
    TRUSTED_HOSTS: List[str] = Field(default=["*"], env="TRUSTED_HOSTS")

    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_file_required = True


settings = Settings()
