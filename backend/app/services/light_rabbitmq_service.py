from celery import Celery

from app.core.config import get_settings

settings = get_settings()

app = Celery(
    "light_worker",
    broker=settings.CELERY_BROKER_URL,
)
