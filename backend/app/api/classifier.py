from pathlib import Path

from app.services.file_service import FileService
from fastapi import APIRouter, Depends, HTTPException, status,UploadFile,File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import aiofiles
from app.repositories.job_repository import AsyncJobRepository,JobType

from app.core.security import verify_token
from app.core.config import get_settings
from app.api.dependencies import get_db
from backend.app.workers.video_classifier_worker import _report_video
settings = get_settings()
chunk_size = settings.UPLOAD_CHUNK_SIZE
bearer_scheme = HTTPBearer()

classifier_router = APIRouter(prefix="/classifier")


@classifier_router.post("/classify_video")

async def classify_video(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
                         db=Depends(get_db),
                         file: UploadFile = File(...)):
    user_id = verify_token(credentials.credentials)
    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only video files allowed")

    file_service = FileService(storage_dir=settings.STORAGE_DIR)
    file_path = await file_service.save_file(file, user_id=user_id, media_type="videos", chunk_size=chunk_size)

    job_repo = AsyncJobRepository(db)
    job=await job_repo.create_job(int(user_id), JobType.VIDEO_CLASSIFICATION, file_path, original_name=file.filename)
    _report_video.delay(job.id)
    return {"job_id": job.id}