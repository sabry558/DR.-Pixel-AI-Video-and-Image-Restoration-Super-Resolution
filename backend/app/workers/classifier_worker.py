from pathlib import Path

from app.services.video_corruption.video_corruption_reporter import VideoCorruptionReporter
from app.services.rabbitmq_service import app
from app.repositories.job_repository import AsyncJobRepository, JobStatus
from app.db.session import SessionLocal
from app.models.database.user import User
from app.models.database.refresh_token import RefreshToken
from app.core.config import get_settings
import asyncio
from app.db.session import engine  

settings = get_settings()

reporter = VideoCorruptionReporter(
    classifier_path=str(settings.CLASSIFIER_MODEL_PATH),
    sample_rate=10,
    thresholds_per_class={"blur": 0.99, "noise": 0.58},
    majority_window_size=25,
    batch_size=32,
    device="cpu"
)


@app.task(queue="video_classifier")
def _report_video(job_id):
    asyncio.run(_report_video_impl(job_id))


async def _report_video_impl(job_id):
    async with SessionLocal() as session:
        job_repo = AsyncJobRepository(session)

        try:
            job = await job_repo.get_by_id(job_id)
            await job_repo.update_job_status(job_id, JobStatus.RUNNING)

            result = reporter.classify_video(job.source_path)

            await job_repo.update_job_status(job_id, JobStatus.COMPLETED)

        except Exception as e:
            await job_repo.update_job_status(job_id, JobStatus.FAILED)
            raise
        finally:
            await engine.dispose()