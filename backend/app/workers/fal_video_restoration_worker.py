"""
SeedVR2 (via fal.ai) Video Enhancement Worker

Celery worker for video super-resolution/restoration using SeedVR2, hosted
on fal.ai (model: fal-ai/seedvr/upscale/video). Restores a frame segment
and writes only the restored frames to a new video file.

Mirrors the architecture of the DarkIR worker (client caching, job
lifecycle, segment-restore-then-write), with two deliberate differences
from that worker and from the local-GPU SeedVR2 worker built alongside it:

  1. There is no local model to load — "restoration" is a fully async
     network call to fal.ai's hosted SeedVR2 endpoint. FalClientCache below
     plays the same architectural role as DarkIR's ModelCache, but caches
     an `fal_client.AsyncClient` instance rather than GPU weights.
  2. The segment assigned to a task is sent to fal.ai as ONE whole clip,
     not split into sub-chunks. This is different from the local-GPU
     SeedVR2 worker (which chunks to bound GPU memory) — fal.ai handles
     its own batching/memory management server-side, and chunking here
     would only add upload/download round-trips for no benefit.

IMPORTANT — resolution caveat:
SeedVR2 is a super-resolution model, so fal.ai's restored clip will
usually be at a different resolution than your source segment. This
worker resizes the restored frames back down/up to the source resolution
before writing to the output file. If you want the higher-resolution
output preserved instead, set `resize_output_to_source=False` in
SeedVRFalConfig.

Setup:
    pip install fal-client httpx aiofiles
    export FAL_KEY="your-fal-api-key"
"""

import asyncio
import os
import shutil
import sys
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional

import aiofiles
import cv2 as cv
import fal_client
import httpx
import numpy as np

from app.services.light_rabbitmq_service import app
from app.repositories.job_repository import AsyncJobRepository, JobStatus
from app.workers.workers_schema.restore_schema import RestoreSchema
from app.core.config import get_settings
from redis import Redis
from app.workers.merge_and_color_correction_worker import route_merge_video

# =============================================================================
# PATH CONFIGURATION
# =============================================================================
redis_client = Redis(
    host="localhost",
    port=6379,
    decode_responses=True,
)
REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))


# =============================================================================
# DATABASE URL (matches your Settings class exactly)
# =============================================================================

def _get_database_url() -> str:
    """
    Resolve the async database URL from your Settings class.
    Your Settings.database_url returns 'postgresql://...'
    We need 'postgresql+asyncpg://...' for async SQLAlchemy.
    """
    from app.core.config import get_settings

    settings = get_settings()
    url = settings.database_url

    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return url


# =============================================================================
# CONSTANTS
# =============================================================================

FAL_MODEL_ID = "fal-ai/seedvr/upscale/video"


class SeedVRFalDefaults:
    """Default SeedVR2 (fal.ai) generation parameters — see
    https://fal.ai/models/fal-ai/seedvr/upscale/video/api"""
    UPSCALE_MODE = "factor"       # "factor" or "target"
    UPSCALE_FACTOR = 2.0
    TARGET_RESOLUTION = "1080p"   # 720p, 1080p, 1440p, 2160p
    NOISE_SCALE = 0.1
    OUTPUT_FORMAT = "X264 (.mp4)"
    OUTPUT_QUALITY = "high"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass(frozen=True)
class VideoMetadata:
    """Extracted metadata from a video file."""
    fps: float
    width: int
    height: int
    total_frames: int


@dataclass(frozen=True)
class SeedVRFalConfig:
    """Configuration for a SeedVR2-via-fal.ai generation pass."""
    upscale_mode: str = SeedVRFalDefaults.UPSCALE_MODE
    upscale_factor: float = SeedVRFalDefaults.UPSCALE_FACTOR
    target_resolution: str = SeedVRFalDefaults.TARGET_RESOLUTION
    noise_scale: float = SeedVRFalDefaults.NOISE_SCALE
    seed: Optional[int] = None
    resize_output_to_source: bool = True  # see module docstring


# =============================================================================
# EXCEPTIONS
# =============================================================================

class SeedVRWorkerError(Exception):
    """Base exception for SeedVR2-via-fal worker errors."""
    pass


class VideoOpenError(SeedVRWorkerError):
    """Raised when a video file cannot be opened."""
    pass


class VideoWriterError(SeedVRWorkerError):
    """Raised when a video writer cannot be initialized."""
    pass


class FalKeyMissingError(SeedVRWorkerError):
    """Raised when the FAL_KEY environment variable isn't set."""
    pass


class FalRequestError(SeedVRWorkerError):
    """Raised when the fal.ai request fails or returns an unexpected shape."""
    pass


class JobNotFoundError(SeedVRWorkerError):
    """Raised when a job ID does not exist in the database."""
    pass


# =============================================================================
# CLIENT MANAGEMENT (fal.ai equivalent of DarkIR's ModelCache)
# =============================================================================
settings = get_settings()
fal_key = settings.FAL_API_KEY

class FalClientCache:
    """Singleton cache for the fal.ai async client. There's no GPU weight
    loading here (fal.ai hosts the model), but we still cache the client
    instance rather than constructing a new one per task."""

    _instance: Optional["fal_client.AsyncClient"] = None

    @classmethod
    def get_or_create(cls) -> "fal_client.AsyncClient":
        if cls._instance is None:
            cls._instance = fal_client.AsyncClient(key=fal_key)
            print("Created fal.ai AsyncClient")
        else:
            print("Reusing cached fal.ai AsyncClient")
        return cls._instance

    @classmethod
    def clear(cls) -> None:
        cls._instance = None


# =============================================================================
# VIDEO I/O
# =============================================================================

class VideoReader:
    """Context-managed video reader with frame iteration."""

    def __init__(self, path: str):
        self.path = path
        self._capture: Optional[cv.VideoCapture] = None

    def __enter__(self) -> "VideoReader":
        self._capture = cv.VideoCapture(self.path)
        if not self._capture.isOpened():
            raise VideoOpenError(f"Cannot open video: {self.path}")
        return self

    def __exit__(self, *args) -> None:
        if self._capture is not None:
            self._capture.release()

    @property
    def metadata(self) -> VideoMetadata:
        return VideoMetadata(
            fps=self._capture.get(cv.CAP_PROP_FPS) or 25.0,
            width=int(self._capture.get(cv.CAP_PROP_FRAME_WIDTH)),
            height=int(self._capture.get(cv.CAP_PROP_FRAME_HEIGHT)),
            total_frames=int(self._capture.get(cv.CAP_PROP_FRAME_COUNT) or 0),
        )

    def iter_frames(self, start: int, end: int) -> Iterator[np.ndarray]:
        """Yield frames from start to end (inclusive)."""
        self._capture.set(cv.CAP_PROP_POS_FRAMES, start)
        current = start
        while current <= end:
            success, frame = self._capture.read()
            if not success:
                break
            yield frame
            current += 1

    def read_all(self) -> List[np.ndarray]:
        frames = []
        while True:
            success, frame = self._capture.read()
            if not success:
                break
            frames.append(frame)
        return frames


class VideoWriter:
    """Context-managed video writer."""

    def __init__(self, path: Path, fps: float, width: int, height: int, codec: str = "mp4v"):
        self.path = path
        self.fps = fps
        self.width = width
        self.height = height
        self.codec = codec
        self._writer: Optional[cv.VideoWriter] = None

    def __enter__(self) -> "VideoWriter":
        fourcc = cv.VideoWriter_fourcc(*self.codec)
        self._writer = cv.VideoWriter(str(self.path), fourcc, self.fps, (self.width, self.height))
        if not self._writer.isOpened():
            raise VideoWriterError(f"Cannot open writer: {self.path}")
        return self

    def __exit__(self, *args) -> None:
        if self._writer is not None:
            self._writer.release()

    def write(self, frame: np.ndarray) -> None:
        self._writer.write(frame)


# =============================================================================
# SEGMENT RESTORATION (fal.ai SeedVR2 — sent as ONE clip, no chunking)
# =============================================================================

def _on_queue_update(update) -> None:
    if isinstance(update, fal_client.InProgress):
        for log in update.logs:
            print(f"[fal] {log['message']}")


class SegmentRestorer:
    """Runs SeedVR2 (via fal.ai) on a video segment and returns restored
    frames. The ENTIRE segment is uploaded and processed as a single clip
    in a single async request — no sub-chunking."""

    def __init__(self, client: "fal_client.AsyncClient", config: SeedVRFalConfig, work_dir: Path):
        self.client = client
        self.config = config
        self.work_dir = work_dir

    async def restore(self, video_path: str, start_frame: int, end_frame: int,
                       source_meta: VideoMetadata) -> List[np.ndarray]:
        self.work_dir.mkdir(parents=True, exist_ok=True)
        clip_in_path = self.work_dir / "segment_in.mp4"
        clip_out_path = self.work_dir / "segment_out.mp4"

        # 1. Extract the WHOLE segment into one clip file (no chunking).
        with VideoReader(video_path) as reader:
            with VideoWriter(clip_in_path, source_meta.fps, source_meta.width, source_meta.height) as writer:
                count = 0
                for frame in reader.iter_frames(start_frame, end_frame):
                    writer.write(frame)
                    count += 1
        if count == 0:
            raise FalRequestError(f"No frames extracted for segment {start_frame}..{end_frame}")
        print(f"Extracted segment: {count} frames -> {clip_in_path}")

        # 2. Upload the whole clip once.
        print(f"Uploading segment to fal.ai ...")
        video_url = await self.client.upload_file(clip_in_path)
        print(f"Uploaded -> {video_url}")

        # 3. Call SeedVR2 on fal.ai with that URL — ONE request for the
        #    whole segment, not one per sub-chunk.
        arguments = {
            "video_url": video_url,
            "upscale_mode": self.config.upscale_mode,
            "output_format": SeedVRFalDefaults.OUTPUT_FORMAT,
            "output_quality": SeedVRFalDefaults.OUTPUT_QUALITY,
            "noise_scale": self.config.noise_scale,
        }
        if self.config.upscale_mode == "factor":
            arguments["upscale_factor"] = self.config.upscale_factor
        else:
            arguments["target_resolution"] = self.config.target_resolution
        if self.config.seed is not None:
            arguments["seed"] = self.config.seed

        print(f"Submitting to {FAL_MODEL_ID} ...")
        try:
            result = await self.client.subscribe(
                FAL_MODEL_ID,
                arguments=arguments,
                with_logs=True,
                on_queue_update=_on_queue_update,
            )
            restored_url = result["video"]["url"]
        except (KeyError, TypeError) as e:
            raise FalRequestError(f"Unexpected response shape from fal.ai: {e}") from e
        except Exception as e:
            raise FalRequestError(f"fal.ai request failed: {e}") from e

        print(f"Restored video URL: {restored_url}")

        # 4. Download the restored clip, async.
        async with httpx.AsyncClient() as http_client:
            async with http_client.stream("GET", restored_url) as response:
                response.raise_for_status()
                async with aiofiles.open(clip_out_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        await f.write(chunk)

        # 5. Read the restored clip back.
        with VideoReader(str(clip_out_path)) as reader:
            restored_frames = reader.read_all()

        # 6. SeedVR2 upscales, so the output resolution usually != source.
        #    Resize back to match if configured.
        if self.config.resize_output_to_source:
            restored_frames = [
                cv.resize(f, (source_meta.width, source_meta.height), interpolation=cv.INTER_LANCZOS4)
                for f in restored_frames
            ]

        return restored_frames


# =============================================================================
# VIDEO PROCESSING ORCHESTRATION (writes only restored frames)
# =============================================================================

class VideoProcessor:
    """Orchestrates reading, restoring (via fal.ai), and writing video frames."""

    def __init__(self, client: "fal_client.AsyncClient", config: SeedVRFalConfig, work_dir: Path):
        self.restorer = SegmentRestorer(client, config, work_dir)

    async def process_segment(
        self,
        video_path: str,
        start_frame: int,
        end_frame: int,
        output_path: Path,
    ) -> Path:
        """
        Restore a frame segment via fal.ai and write ONLY the restored
        frames to a new video file.

        Returns the path to the output video containing only the restored segment.
        """
        with VideoReader(video_path) as reader:
            source_meta = reader.metadata

        print(
            f"Restoring segment: {video_path} "
            f"(frames {start_frame}..{end_frame}, total={source_meta.total_frames})"
        )

        restored_frames = await self.restorer.restore(
            video_path, start_frame, end_frame, source_meta
        )
        print(f"Segment restoration complete: {len(restored_frames)} frames")

        # Write only the restored frames to the output file
        with VideoWriter(output_path, source_meta.fps, source_meta.width, source_meta.height) as writer:
            for frame in restored_frames:
                writer.write(frame)

        print(f"Wrote {len(restored_frames)} restored frames to {output_path}")
        return output_path


# =============================================================================
# OUTPUT PATH & PAYLOAD
# =============================================================================

def build_output_path(source_path: str, job_id: Optional[int] = None, start_frame: int = None, end_frame: int = None) -> Path:
    source = Path(source_path)
    output_dir = source.parent.parent / "restored_videos"
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = source.name
    return output_dir / f"{start_frame}_{end_frame}_{filename}"


def normalize_payload(payload) -> RestoreSchema:
    """Ensure payload is a validated RestoreSchema instance."""
    if isinstance(payload, RestoreSchema):
        return payload
    return RestoreSchema.model_validate(payload)


# =============================================================================
# JOB LIFECYCLE
# =============================================================================

class JobLifecycle:
    """Manages database job status transitions."""

    def __init__(self, repo: AsyncJobRepository, job_id: int):
        self.repo = repo
        self.job_id = job_id

    async def start(self) -> None:
        await self.repo.update_job_status(self.job_id, JobStatus.RUNNING)

    async def complete(self, output_path: str) -> None:
        await self.repo.complete_job(self.job_id, output_path)

    async def fail(self) -> None:
        with suppress(Exception):
            await self.repo.fail_job(self.job_id)


# =============================================================================
# MAIN ASYNC WORKER
# =============================================================================

async def enhance_video(payload: RestoreSchema) -> None:
    """
    Main worker: restore segment via fal.ai SeedVR2 (whole segment, one
    request, no chunking) and write only restored frames to a new video file.
    """
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    database_url = _get_database_url()
    engine = create_async_engine(database_url, echo=False, future=True)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        repo = AsyncJobRepository(session)
        lifecycle = JobLifecycle(repo, payload.job_id)

        try:
            job = await _fetch_job(repo, payload.job_id)
            await lifecycle.start()

            config = SeedVRFalConfig()  # override fields here from payload if you add them
            client = FalClientCache.get_or_create()

            output = build_output_path(job.source_path, payload.job_id,payload.start_frame, payload.end_frame)
            print(f"Output (restored segment): {output}")

            work_dir = REPO_ROOT / "_worker_tmp" / f"job_{payload.job_id}"
            try:
                processor = VideoProcessor(client, config, work_dir)
                final_path = await processor.process_segment(
                    video_path=job.source_path,
                    start_frame=payload.start_frame,
                    end_frame=payload.end_frame,
                    output_path=output,
                )
            finally:
                shutil.rmtree(work_dir, ignore_errors=True)

            print(f"Done: restored segment saved to {final_path}")

            remaining = redis_client.decr(f"{payload.job_id}")
            if int(remaining) <= 0:
                redis_client.delete(f"{payload.job_id}")
                print(f"All segments restored for job {remaining}, merging...")
                route_merge_video.delay(payload.job_id, job.source_path)


        except Exception:
            await lifecycle.fail()
            raise
        finally:
            await engine.dispose()


async def _fetch_job(repo: AsyncJobRepository, job_id: int):
    job = await repo.get_by_id(job_id)
    if job is None:
        raise JobNotFoundError(f"Job {job_id} not found")
    return job


# =============================================================================
# CELERY TASK ENTRY POINT
# =============================================================================

@app.task(queue="video_restoration")
def route_seedvr_fal_enhancement(payload):
    """Celery task entry point. Wraps async worker in event loop."""
    normalized = normalize_payload(payload)
    asyncio.run(enhance_video(normalized))