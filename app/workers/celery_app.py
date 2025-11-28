"""
Configuração do Celery
"""
from celery import Celery
from app.config import settings
import structlog

logger = structlog.get_logger(__name__)

# Cria instância do Celery
celery_app = Celery(
    "video_analysis",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

# Configurações
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    task_soft_time_limit=settings.CELERY_TASK_SOFT_TIME_LIMIT,
    task_track_started=True,
    task_send_sent_event=True,
    worker_send_task_events=True,
)

logger.info(
    "Celery app initialized",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)
