import aiofiles
import uuid
from pathlib import Path
from app.repositories.job_repository import AsyncJobRepository, JobType
from fastapi import UploadFile
allowed = {".mp4", ".mov", ".avi", ".mkv"}

class FileService:
    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    async def save_file(self, file: UploadFile, user_id: int, media_type: str, chunk_size: int = 1024 * 1024):
        storage_dir = (
            self.storage_dir
            / str(user_id)
            / media_type
        )
        storage_dir.mkdir(parents=True, exist_ok=True)
        file_extension = Path(file.filename).suffix
        if file_extension not in allowed:
            raise ValueError("Unsupported video format")
        file_name = f"{uuid.uuid4()}{file_extension}"
        file_path = storage_dir / file_name
        async with aiofiles.open(file_path, "wb") as out_file:
            while chunk := await file.read(chunk_size):
                await out_file.write(chunk)

        await file.close()
        return str(file_path)
    



