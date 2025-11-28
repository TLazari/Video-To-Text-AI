"""
Configurações da aplicação
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Configurações da aplicação"""

    # App
    APP_NAME: str = "Video Analysis API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # OpenRouter
    OPENROUTER_API_KEY: str = ""  # Deve ser configurado via .env
    OPENROUTER_MODEL: str = "nvidia/nemotron-nano-12b-v2-vl:free"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENROUTER_TIMEOUT: int = 120

    # Video Processing
    MAX_VIDEO_SIZE_MB: int = 500
    SUPPORTED_FORMATS: list = ["mp4", "avi", "mov", "mkv", "webm"]
    MAX_FRAMES_TO_EXTRACT: int = 10

    # Redis
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_URL: Optional[str] = None

    # Celery
    CELERY_BROKER_URL: Optional[str] = None  # Será construído a partir de Redis
    CELERY_RESULT_BACKEND: Optional[str] = None  # Será construído a partir de Redis
    CELERY_TASK_TIME_LIMIT: int = 600  # 10 minutos
    CELERY_TASK_SOFT_TIME_LIMIT: int = 540  # 9 minutos

    # API
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list = ["*"]

    # Job Management
    JOB_RESULT_TTL: int = 86400  # 24 horas
    JOB_CHECK_INTERVAL: int = 5  # segundos

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    def __init__(self, **data):
        super().__init__(**data)

        # Constrói URLs do Redis se não fornecidas
        if not self.REDIS_URL:
            password_part = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
            self.REDIS_URL = f"redis://{password_part}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

        # Constrói URLs do Celery
        if not self.CELERY_BROKER_URL:
            self.CELERY_BROKER_URL = self.REDIS_URL

        if not self.CELERY_RESULT_BACKEND:
            self.CELERY_RESULT_BACKEND = self.REDIS_URL


# Instância global
settings = Settings()
