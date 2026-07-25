"""
Video Merge Worker

Celery worker that merges restored video segments (from DarkIR and SeedVR2)
back into the original video file. Triggered when all segment restoration
tasks have finished.
"""

import asyncio
import re
import shutil
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import cv2 as cv
import numpy as np

from app.services.light_rabbitmq_service import app
from app.repositories.job_repository import AsyncJobRepository, JobStatus
from redis import Redis
import sys

from post_processing.video_color_correction.orchestrator import VideoColorCorrectionPipeline

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))


# =============================================================================
# DATABASE URL
# =============================================================================

def _get_database_url() -> str:
    from app.core.config import get_settings

    settings = get_settings()
    url = settings.database_url
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


# =============================================================================
# DATA CLASSES & EXCEPTIONS
# =============================================================================

@dataclass(frozen=True)
class VideoMetadata:
    fps: float
    width: int
    height: int
    total_frames: int


@dataclass
class SegmentInfo:
    start_frame: int
    end_frame: int
    path: Path
    capture: Optional[cv.VideoCapture] = field(default=None, compare=False)


class MergeWorkerError(Exception):
    pass


class VideoOpenError(MergeWorkerError):
    pass


class VideoWriterError(MergeWorkerError):
    pass


class JobNotFoundError(MergeWorkerError):
    pass


# =============================================================================
# VIDEO I/O
# =============================================================================

class VideoReader:
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

    def read_next(self) -> Optional[np.ndarray]:
        success, frame = self._capture.read()
        return frame if success else None


class VideoWriter:
    def __init__(self, path: Path, meta: VideoMetadata, codec: str = "mp4v"):
        self.path = path
        self.meta = meta
        self.codec = codec
        self._writer = None

    def __enter__(self) -> "VideoWriter":
        fourcc = cv.VideoWriter_fourcc(*self.codec)
        self._writer = cv.VideoWriter(
            str(self.path),
            fourcc,
            self.meta.fps,
            (self.meta.width, self.meta.height),
        )
        if not self._writer.isOpened():
            raise VideoWriterError(f"Cannot open writer: {self.path}")
        return self

    def __exit__(self, *args) -> None:
        if self._writer is not None:
            self._writer.release()

    def write(self, frame: np.ndarray) -> None:
        self._writer.write(frame)


# =============================================================================
# SEGMENT DISCOVERY
# =============================================================================

SEGMENT_RE = re.compile(r"^(\d+)_(\d+)_(.+)$")

OUTPUT_DIRS = ["light_enhanced_videos", "restored_videos"]


def discover_segments(source_path: str) -> List[SegmentInfo]:
    """
    Scan output directories for restored segments belonging to this source.
    Filenames are expected to match:  {start}_{end}_{original_filename}
    """
    source = Path(source_path)
    segments: List[SegmentInfo] = []

    for dir_name in OUTPUT_DIRS:
        directory = source.parent.parent / dir_name
        if not directory.exists():
            continue
        for file_path in directory.iterdir():
            match = SEGMENT_RE.match(file_path.name)
            if not match:
                continue
            start_str, end_str, filename = match.groups()
            if filename != source.name:
                continue
            segments.append(SegmentInfo(
                start_frame=int(start_str),
                end_frame=int(end_str),
                path=file_path,
            ))

    segments.sort(key=lambda s: s.start_frame)
    return segments


# =============================================================================
# MERGE LOGIC
# =============================================================================

class VideoMerger:
    def __init__(self, source_path: str, segments: List[SegmentInfo], output_path: Path):
        self.source_path = source_path
        self.segments = segments
        self.output_path = output_path

    def merge(self) -> Path:
        with VideoReader(self.source_path) as reader:
            meta = reader.metadata

            # Open all segment videos
            for seg in self.segments:
                seg.capture = cv.VideoCapture(str(seg.path))
                if not seg.capture.isOpened():
                    raise VideoOpenError(f"Cannot open segment: {seg.path}")

            try:
                with VideoWriter(self.output_path, meta) as writer:
                    frame_idx = 0
                    seg_idx = 0
                    written_restored = 0
                    written_original = 0

                    while True:
                        original = reader.read_next()
                        if original is None:
                            break

                        restored: Optional[np.ndarray] = None

                        # Advance past segments we've already left behind
                        while seg_idx < len(self.segments) and frame_idx > self.segments[seg_idx].end_frame:
                            self.segments[seg_idx].capture.release()
                            self.segments[seg_idx].capture = None
                            seg_idx += 1

                        # Check if current frame falls inside the active segment
                        if seg_idx < len(self.segments):
                            seg = self.segments[seg_idx]
                            if seg.start_frame <= frame_idx <= seg.end_frame:
                                success, seg_frame = seg.capture.read()
                                if success:
                                    restored = seg_frame
                                else:
                                    print(f"Warning: segment {seg.path} ran out of frames at {frame_idx}")

                        # Safety: resize restored frame if resolution somehow mismatches
                        if restored is not None:
                            if (restored.shape[1], restored.shape[0]) != (meta.width, meta.height):
                                restored = cv.resize(
                                    restored,
                                    (meta.width, meta.height),
                                    interpolation=cv.INTER_LANCZOS4,
                                )
                            writer.write(restored)
                            written_restored += 1
                        else:
                            writer.write(original)
                            written_original += 1

                        frame_idx += 1
                        if frame_idx % 100 == 0:
                            print(f"Merged {frame_idx}/{meta.total_frames} frames")

                print(
                    f"Merge complete: {frame_idx} total frames "
                    f"({written_restored} restored, {written_original} original) -> {self.output_path}"
                )

            finally:
                for seg in self.segments:
                    if seg.capture is not None:
                        seg.capture.release()

        return self.output_path


# =============================================================================
# OUTPUT PATH
# =============================================================================

def build_output_path(source_path: str) -> Path:
    source = Path(source_path)
    output_dir = source.parent.parent / "finalized_videos"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / source.name


# =============================================================================
# JOB LIFECYCLE
# =============================================================================

class JobLifecycle:
    def __init__(self, repo: AsyncJobRepository, job_id: int):
        self.repo = repo
        self.job_id = job_id

    async def complete(self, output_path: str) -> None:
        await self.repo.complete_job(self.job_id, output_path)

    async def fail(self) -> None:
        with suppress(Exception):
            await self.repo.fail_job(self.job_id)


# =============================================================================
# MAIN ASYNC WORKER
# =============================================================================

async def merge_video(job_id: int, source_path: str) -> None:
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker

    database_url = _get_database_url()
    engine = create_async_engine(database_url, echo=False, future=True)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        repo = AsyncJobRepository(session)
        lifecycle = JobLifecycle(repo, job_id)

        try:
            job = await repo.get_by_id(job_id)
            if job is None:
                raise JobNotFoundError(f"Job {job_id} not found")

            segments = discover_segments(source_path)
            corruption_ranges=[]
            for seg in segments:
                corruption_ranges.append({"start_frame": seg.start_frame, "end_frame": seg.end_frame})

            if not segments:
                # Nothing was restored — promote the original to final
                print(f"No restored segments found for job {job_id}; promoting original")
                output = build_output_path(source_path)
                shutil.copy2(source_path, output)
                await lifecycle.complete(str(output))
                return

            print(f"Found {len(segments)} restored segments for job {job_id}:")
            for seg in segments:
                print(f"  [{seg.start_frame:>5}..{seg.end_frame:<5}] {seg.path.name}")

            output = build_output_path(source_path)
            merger = VideoMerger(source_path, segments, output)
            final_path = merger.merge()

            frames = []
            with VideoReader(str(final_path)) as reader:
                meta = reader.metadata        # ← ADD THIS
                while True:
                    frame = reader.read_next()
                    if frame is None:
                        break
                    frames.append(frame)

            pipeline = VideoColorCorrectionPipeline()
            result = pipeline.run(frames, corruption_ranges)

            temp_path = final_path.with_suffix(".tmp.mp4")
            with VideoWriter(temp_path, meta, codec="mp4v") as writer:
                for frame in result.frames:
                    writer.write(frame)

            temp_path.replace(final_path)
            print(f"Overwrote {final_path} with color-corrected version "
                f"({len(result.correction_log)} corrected, "
                f"{len(result.flagged_for_review)} flagged)")            


            await lifecycle.complete(str(final_path))
            print(f"Job {job_id} marked complete: {final_path}")

        except Exception:
            await lifecycle.fail()
            raise
        finally:
            await engine.dispose()


# =============================================================================
# CELERY TASK ENTRY POINT
# =============================================================================

@app.task(queue="merge_and_color_correction")
def route_merge_video(job_id: int, source_path: str):
    """Celery task entry point. Merges restored segments into the original."""
    asyncio.run(merge_video(job_id, source_path))