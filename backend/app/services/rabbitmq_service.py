from kombu import Queue
from celery import Celery
from app.core.config import get_settings

settings = get_settings()

app = Celery(
    "worker",
    broker=settings.CELERY_BROKER_URL,
    include=[
        "app.workers.video_classifier_worker",
        "app.workers.light_enhancement_worker",
        "app.workers.video_restoration_worker",
        "app.workers.fal_video_restoration_worker",
        "app.workers.merge_and_color_correction_worker",
    ],
)

app.conf.task_queues = (
    Queue("video_classifier"),
    Queue("image_classifier"),
    Queue("video_restoration"),
    Queue("light_enhacement"),
    Queue("image_restoration"),
    Queue("merge_and_color_correction"),

)