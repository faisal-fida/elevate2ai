from typing import List, Literal
from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENVIRONMENT: Literal["development", "production"] = "development"
    PROJECT_NAME: str = "FastAPI"
    PROJECT_DESCRIPTION: str = "Production-ready FastAPI"
    LOG_LEVEL: str = "INFO"

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
