from kombu import Queue
from celery import Celery
from app.core.config import get_settings

settings = get_settings()

app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    include=[
        "app.workers.classifier_worker",
        # add other worker modules here as you create them, e.g.:
        # "app.workers.restoration_worker",
        # "app.workers.super_resolution_worker",
    ],
)

app.conf.task_queues = (
    Queue("video_classifier"),
    Queue("image_classifier"),
    Queue("restoration"),
    Queue("super_resolution"),
)