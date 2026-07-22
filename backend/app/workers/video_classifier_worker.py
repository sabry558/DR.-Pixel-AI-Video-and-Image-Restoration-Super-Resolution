from app.services.video_corruption.video_corruption_reporter import VideoCorruptionReporter
from app.services.rabbitmq_service import app
from app.repositories.job_repository import AsyncJobRepository, JobStatus
from app.db.session import SessionLocal
from app.core.config import get_settings
import asyncio
from app.db.session import engine  
from app.workers.light_enhancement_worker import route_light_enhancement
from app.workers.video_restoration_worker import _route_video_restoration
settings = get_settings()

reporter = VideoCorruptionReporter(
    classifier_path=str(settings.CLASSIFIER_MODEL_PATH),
    sample_rate=10,
    thresholds_per_class={"blur": 0.99, "noise": 0.58},
    majority_window_size=25,
    batch_size=32,
    device="cpu"
)

DETECTOR_QUEUE_BY_DEFECT = {
    "blur": "video_restoration",
    "noise": "video_restoration",
    "low_light": "light_enhancement",
}


@app.task(queue="video_classifier")
def _report_video(job_id):                

    asyncio.run(_report_video_impl(job_id))



def _dispatch_defect(defect_payload):
    defect_type = str(defect_payload["defect_type"]).lower()
    queue_name = DETECTOR_QUEUE_BY_DEFECT.get(defect_type)

    if queue_name == "light_enhancement":
        return route_light_enhancement.delay(defect_payload)

    if queue_name == "video_restoration":
        return _route_video_restoration.delay(defect_payload)

    raise ValueError(f"Unsupported defect type: {defect_type}")


async def _report_video_impl(job_id):
    async with SessionLocal() as session:
        job_repo = AsyncJobRepository(session)

        try:
            job = await job_repo.get_by_id(job_id)
            if job is None:
                raise ValueError(f"Job {job_id} not found")

            await job_repo.update_job_status(job_id, JobStatus.RUNNING)

            results = reporter.classify_video(job.source_path)
            total_defects = len(results)

            for defect_num, result in enumerate(results, start=1):
                _dispatch_defect({
                    "job_id": job_id,
                    "start_frame": int(result["start_frame"]),
                    "end_frame": int(result["end_frame"]),
                    "defect_num": defect_num,
                    "last_defect_num": total_defects,
                    "defect_type": result["class"],
                })

                


        except Exception as e:
            await job_repo.update_job_status(job_id, JobStatus.FAILED)
            raise
        finally:
            await engine.dispose()


