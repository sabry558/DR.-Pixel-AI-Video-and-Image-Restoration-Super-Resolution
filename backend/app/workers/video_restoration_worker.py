"""
SeedVR2 Video Enhancement Worker

Celery worker for video super-resolution/restoration using SeedVR2-3B.
Restores a frame segment and merges it back into the original video.

Mirrors the architecture of the DarkIR worker (model caching, job lifecycle,
segment-restore-then-merge), but SeedVR2 is NOT a drop-in replacement for a
plain per-frame CNN like DarkIR. Read the "IMPORTANT SEEDVR-SPECIFIC
ASSUMPTIONS" block below before running this in production — several of
these are inferred from SeedVR's reference inference script rather than a
documented public API, since SeedVR wasn't designed to be imported as a
library.

IMPORTANT SEEDVR-SPECIFIC ASSUMPTIONS (verify these against your repo):
  1. `configure_runner()` and `generation_loop()` (imported from SeedVR's own
     `projects/inference_seedvr2_3b.py`) use paths relative to the CURRENT
     WORKING DIRECTORY (e.g. './configs_3b/main.yaml', './ckpts/...'), not
     paths relative to that file's own location. This worker chdirs into
     the SeedVR repo root at import time to satisfy that. If you customized
     the repo layout, these relative paths may not resolve.
  2. `generation_loop()`'s text-embedding step loads two hardcoded files,
     `pos_emb.pt` and `neg_emb.pt`, from the current working directory. You
     must have these precomputed and placed at the SeedVR repo root — this
     worker does not compute them. If they're named/located differently in
     your setup, patch `_ensure_text_embeddings()` below.
  3. SeedVR2 is a super-resolution model: its output resolution is
     `res_h x res_w` (default 720x1280), which will usually NOT match your
     source video's resolution. Unlike DarkIR (which restores in-place at
     the original resolution), this worker resizes SeedVR's output back
     down/up to the original frame size so it can merge into the source
     video like DarkIR does. If you actually want the higher-resolution
     output preserved, save the restored segment directly instead of
     merging it back in place — merging defeats the purpose of upscaling.
  4. `configure_runner()` calls `init_torch()` / sequence-parallel setup,
     which is written assuming a `torchrun`-style distributed launch. This
     worker sets RANK/WORLD_SIZE/LOCAL_RANK/MASTER_ADDR/MASTER_PORT env
     vars for a single-process "distributed" group of size 1 so it can run
     inside a normal Celery worker process without `torchrun`. This is a
     common workaround but is NOT something we've traced through SeedVR's
     actual `common/distributed/__init__.py` — verify it initializes
     cleanly in your environment before relying on it.
  5. Multi-GPU (`sp_size > 1`) is NOT supported by this worker as written;
     it assumes one GPU per worker process (`sp_size=1`), matching SeedVR's
     own guidance that 1 GPU handles up to ~720p, and 4 GPUs are needed for
     1080p/2K (see SeedVR's README).
  6. The segment assigned to a task (`start_frame`..`end_frame`) is further
     split into short sub-chunks (`SeedVRConfig.chunk_seconds`, default
     1.5s) before being fed to the model, one `generation_loop()` call
     covering all sub-chunks. This bounds GPU memory use regardless of how
     long the assigned segment is, mirroring the ffmpeg-based chunking used
     in the standalone (non-worker) SeedVR2 inference pipeline.
"""

import asyncio
import os
import shutil
import socket
import sys
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional

import cv2 as cv
import numpy as np
import torch

from app.services.light_rabbitmq_service import app
from app.repositories.job_repository import AsyncJobRepository, JobStatus
from app.workers.workers_schema.restore_schema import RestoreSchema
from redis import Redis
redis_client = Redis(
    host="redis",      
    port=6379,
    db=0,
    decode_responses=True,
)
# =============================================================================
# DEVICE CONFIGURATION
# =============================================================================

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"SeedVR2 worker using device: {DEVICE}")

if DEVICE.type != "cuda":
    print("WARNING: SeedVR2 is only practical on a CUDA GPU. CPU inference "
          "will be extremely slow if it runs at all.")


# =============================================================================
# PATH CONFIGURATION
# =============================================================================

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

# Where your cloned SeedVR repo lives, e.g. <REPO_ROOT>/models/SeedVR
SEEDVR_ROOT = REPO_ROOT / "models" / "SeedVR"
if str(SEEDVR_ROOT) not in sys.path:
    sys.path.append(str(SEEDVR_ROOT))

CHECKPOINT_PATH = SEEDVR_ROOT / "ckpts" / "seedvr2_ema_3b.pth"
POS_EMB_PATH = SEEDVR_ROOT / "pos_emb.pt"
NEG_EMB_PATH = SEEDVR_ROOT / "neg_emb.pt"

# configure_runner()/generation_loop() use paths relative to cwd — see
# assumption #1 in the module docstring. We chdir once, at import time.
_ORIGINAL_CWD = os.getcwd()
os.chdir(SEEDVR_ROOT)


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

class ProgressInterval:
    """Frame intervals for progress reporting."""
    LOG_EVERY_N_FRAMES = 25


class SeedVRDefaults:
    """Default SeedVR2 generation parameters (see SeedVR's README)."""
    RES_H = 720
    RES_W = 1280
    SAMPLE_STEPS = 1
    SEED = 666
    SP_SIZE = 1  # single GPU; see assumption #5


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
class SeedVRConfig:
    """Configuration for a SeedVR2 generation pass."""
    res_h: int = SeedVRDefaults.RES_H
    res_w: int = SeedVRDefaults.RES_W
    sample_steps: int = SeedVRDefaults.SAMPLE_STEPS
    seed: int = SeedVRDefaults.SEED
    sp_size: int = SeedVRDefaults.SP_SIZE
    resize_output_to_source: bool = True  # see assumption #3
    chunk_seconds: float = 1.5  # sub-chunk length fed to the model per pass;
                                 # keeps GPU memory bounded on long segments


# =============================================================================
# EXCEPTIONS
# =============================================================================

class SeedVRWorkerError(Exception):
    """Base exception for SeedVR2 worker errors."""
    pass


class VideoOpenError(SeedVRWorkerError):
    """Raised when a video file cannot be opened."""
    pass


class VideoWriterError(SeedVRWorkerError):
    """Raised when a video writer cannot be initialized."""
    pass


class CheckpointNotFoundError(SeedVRWorkerError):
    """Raised when the SeedVR2 checkpoint cannot be located."""
    pass


class TextEmbeddingsNotFoundError(SeedVRWorkerError):
    """Raised when pos_emb.pt / neg_emb.pt are missing (see assumption #2)."""
    pass


class GenerationOutputMissingError(SeedVRWorkerError):
    """Raised when SeedVR2 didn't produce an output file for a segment."""
    pass


class JobNotFoundError(SeedVRWorkerError):
    """Raised when a job ID does not exist in the database."""
    pass


# =============================================================================
# DISTRIBUTED ENV SETUP (single-process, no torchrun — see assumption #4)
# =============================================================================

def _free_tcp_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


def _ensure_single_process_distributed_env() -> None:
    """Sets the env vars torchrun would normally set, for a single-process
    'distributed' group of world size 1. Only sets them if absent, so this
    is a no-op if you DO launch this worker under torchrun."""
    defaults = {
        "RANK": "0",
        "LOCAL_RANK": "0",
        "WORLD_SIZE": "1",
        "MASTER_ADDR": "127.0.0.1",
        "MASTER_PORT": str(_free_tcp_port()),
    }
    for key, value in defaults.items():
        os.environ.setdefault(key, value)


# =============================================================================
# MODEL MANAGEMENT
# =============================================================================

class RunnerCache:
    """Singleton cache for the SeedVR2 runner (DiT + VAE). Loading takes
    ~20+ seconds, so this avoids reloading it on every Celery task."""

    _instance = None  # type: ignore[assignment]

    @classmethod
    def get_or_load(cls, sp_size: int = SeedVRDefaults.SP_SIZE):
        if cls._instance is None:
            cls._instance = _build_and_load_runner(sp_size)
        else:
            print("Reusing cached SeedVR2 runner")
        return cls._instance

    @classmethod
    def clear(cls) -> None:
        cls._instance = None


def _build_and_load_runner(sp_size: int):
    """Loads the SeedVR2 DiT + VAE via SeedVR's own configure_runner()."""
    if not CHECKPOINT_PATH.exists():
        raise CheckpointNotFoundError(f"Checkpoint not found: {CHECKPOINT_PATH}")
    if not (POS_EMB_PATH.exists() and NEG_EMB_PATH.exists()):
        raise TextEmbeddingsNotFoundError(
            f"Expected pos_emb.pt and neg_emb.pt at {SEEDVR_ROOT} — see "
            "assumption #2 in the module docstring."
        )

    _ensure_single_process_distributed_env()

    # Imported here (not at module top) so the chdir into SEEDVR_ROOT above
    # has already happened, matching how SeedVR's own script expects to run.
    from projects.inference_seedvr2_3b import configure_runner

    print(f"Loading SeedVR2 runner (sp_size={sp_size})... this takes a while.")
    runner = configure_runner(sp_size)
    print("SeedVR2 runner loaded.")
    return runner


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
# SEGMENT RESTORATION (SeedVR2 equivalent of DarkIR's FrameRestorer)
# =============================================================================

class SegmentRestorer:
    """Runs SeedVR2 on a short video segment and returns restored frames.

    Unlike DarkIR's per-frame tensor call, SeedVR2 only exposes a
    file-in/file-out batch API (generation_loop), so this writes the
    segment to temp sub-chunk clips, calls SeedVR2's own generation loop
    once across all of them, and reads the restored clips back in order.

    The segment is split into short sub-chunks (config.chunk_seconds each,
    default 1.5s) before being handed to the model. This mirrors the
    ffmpeg-based chunking used in the standalone inference pipeline this
    worker was adapted from — SeedVR2 can exhaust GPU memory if fed long
    clips in one pass, so bounding each pass to a short chunk keeps memory
    usage predictable regardless of how long the requested segment is.
    generation_loop() already iterates every file in its input directory
    one at a time, so handing it N short chunk files in a single call
    still only ever processes one chunk's worth of frames on the GPU at
    once."""

    def __init__(self, runner, config: SeedVRConfig, work_dir: Path):
        self.runner = runner
        self.config = config
        self.work_dir = work_dir

    def restore(self, video_path: str, start_frame: int, end_frame: int,
                source_meta: VideoMetadata) -> List[np.ndarray]:
        from projects.inference_seedvr2_3b import generation_loop

        clip_in_dir = self.work_dir / "clip_in"
        clip_out_dir = self.work_dir / "clip_out"
        clip_in_dir.mkdir(parents=True, exist_ok=True)
        clip_out_dir.mkdir(parents=True, exist_ok=True)
        for f in list(clip_in_dir.glob("*.mp4")) + list(clip_out_dir.glob("*.mp4")):
            f.unlink()

        # 1. Read the full segment into memory, then split it into short
        #    sub-chunks so no single model pass has to hold more than
        #    ~chunk_seconds worth of frames.
        with VideoReader(video_path) as reader:
            segment_frames = list(reader.iter_frames(start_frame, end_frame))
        if not segment_frames:
            raise GenerationOutputMissingError(
                f"No frames extracted for segment {start_frame}..{end_frame}"
            )

        frames_per_chunk = max(1, round(self.config.chunk_seconds * source_meta.fps))
        chunk_names = []
        for i in range(0, len(segment_frames), frames_per_chunk):
            chunk_frames = segment_frames[i:i + frames_per_chunk]
            chunk_name = f"chunk_{i // frames_per_chunk:04d}.mp4"
            chunk_path = clip_in_dir / chunk_name
            with VideoWriter(chunk_path, source_meta.fps, source_meta.width, source_meta.height) as writer:
                for frame in chunk_frames:
                    writer.write(frame)
            chunk_names.append(chunk_name)

        print(
            f"Segment split into {len(chunk_names)} sub-chunk(s) of up to "
            f"{frames_per_chunk} frames ({self.config.chunk_seconds}s each) -> {clip_in_dir}"
        )

        # 2. Run SeedVR2's own generation loop once across all sub-chunks.
        #    It processes each file in the directory in turn, so GPU memory
        #    use stays bounded to one sub-chunk at a time regardless of how
        #    many sub-chunks there are.
        generation_loop(
            self.runner,
            video_path=str(clip_in_dir),
            output_dir=str(clip_out_dir),
            batch_size=1,
            sample_steps=self.config.sample_steps,
            seed=self.config.seed,
            res_h=self.config.res_h,
            res_w=self.config.res_w,
            sp_size=self.config.sp_size,
        )

        # 3. Read the restored sub-chunks back IN ORDER and concatenate
        #    them to reconstruct the full segment.
        restored_frames: List[np.ndarray] = []
        for chunk_name in chunk_names:
            chunk_out_path = clip_out_dir / chunk_name
            if not chunk_out_path.exists():
                raise GenerationOutputMissingError(
                    f"SeedVR2 did not produce an output file at {chunk_out_path}"
                )
            with VideoReader(str(chunk_out_path)) as reader:
                restored_frames.extend(reader.read_all())

        # 4. SeedVR2 outputs at res_h x res_w, which usually != the source
        #    resolution (see assumption #3). Resize back to match if we're
        #    merging into the original video.
        if self.config.resize_output_to_source:
            restored_frames = [
                cv.resize(f, (source_meta.width, source_meta.height), interpolation=cv.INTER_LANCZOS4)
                for f in restored_frames
            ]

        return restored_frames


# =============================================================================
# VIDEO MERGER — merges restored segment back into original video
# =============================================================================

class VideoMerger:
    """
    Merges a restored frame segment back into the original video.

    Strategy:
    1. Read original video frames
    2. For frames in [start, end] range, use restored frames
    3. For all other frames, use original frames
    4. Write merged result to a new video file
    5. Atomically replace original with merged result
    """

    def __init__(self, video_path: str, start_frame: int, end_frame: int):
        self.video_path = video_path
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.restored_frames: List[np.ndarray] = []

    def add_restored_frames(self, frames: List[np.ndarray]) -> None:
        self.restored_frames.extend(frames)

    def merge(self, output_path: Optional[Path] = None) -> Path:
        if output_path is None:
            original = Path(self.video_path)
            temp_path = original.with_suffix(".temp.mp4")
            final_path = original
        else:
            temp_path = output_path
            final_path = output_path

        with VideoReader(self.video_path) as reader:
            meta = reader.metadata
            with VideoWriter(temp_path, meta.fps, meta.width, meta.height) as writer:
                self._write_merged(reader, writer, meta)

        if output_path is None:
            self._atomic_replace(temp_path, final_path)

        return final_path

    def _write_merged(self, reader: VideoReader, writer: VideoWriter, meta: VideoMetadata) -> None:
        restored_index = 0
        total_restored = len(self.restored_frames)

        for frame_idx, frame in enumerate(reader.iter_frames(0, meta.total_frames - 1)):
            if self.start_frame <= frame_idx <= self.end_frame and restored_index < total_restored:
                writer.write(self.restored_frames[restored_index])
                restored_index += 1
            else:
                writer.write(frame)

        print(f"Merged {restored_index} restored frames into video")

    @staticmethod
    def _atomic_replace(temp_path: Path, final_path: Path) -> None:
        backup_path = final_path.with_suffix(final_path.suffix + ".backup")

        if final_path.exists():
            shutil.copy2(str(final_path), str(backup_path))

        shutil.move(str(temp_path), str(final_path))

        if backup_path.exists():
            backup_path.unlink()

        print(f"Atomically replaced original with merged video: {final_path}")


# =============================================================================
# VIDEO PROCESSING ORCHESTRATION (with merger)
# =============================================================================

class VideoProcessor:
    """Orchestrates reading, restoring, and merging video frames."""

    def __init__(self, runner, config: SeedVRConfig, work_dir: Path):
        self.restorer = SegmentRestorer(runner, config, work_dir)

    def process_and_merge(
        self,
        video_path: str,
        start_frame: int,
        end_frame: int,
        output_path: Optional[Path] = None,
    ) -> Path:
        restored_path = build_output_path(video_path)
        if restored_path.exists():
            video_path = str(restored_path)

        with VideoReader(video_path) as reader:
            source_meta = reader.metadata

        print(
            f"Restoring segment: {video_path} "
            f"(frames {start_frame}..{end_frame}, total={source_meta.total_frames})"
        )
        restored_frames = self.restorer.restore(video_path, start_frame, end_frame, source_meta)
        print(f"Segment restoration complete: {len(restored_frames)} frames")

        merger = VideoMerger(video_path, start_frame, end_frame)
        merger.add_restored_frames(restored_frames)

        return merger.merge(output_path)


# =============================================================================
# OUTPUT PATH & PAYLOAD
# =============================================================================

def build_output_path(source_path: str, job_id: Optional[int] = None) -> Path:
    source = Path(source_path)
    output_dir = source.parent.parent / "restored"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / source.name


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
    Main worker: restore segment with SeedVR2 and merge back into the
    original video.
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

            config = SeedVRConfig() 
            runner = RunnerCache.get_or_load(sp_size=config.sp_size)

            output = build_output_path(job.source_path, payload.job_id)
            print(f"Output (merged video): {output}")

            work_dir = SEEDVR_ROOT / "_worker_tmp" / f"job_{payload.job_id}"
            work_dir.mkdir(parents=True, exist_ok=True)
            try:
                processor = VideoProcessor(runner, config, work_dir)
                final_path = processor.process_and_merge(
                    video_path=job.source_path,
                    start_frame=payload.start_frame,
                    end_frame=payload.end_frame,
                    output_path=output,
                )
            finally:
                shutil.rmtree(work_dir, ignore_errors=True)

            print(f"Done: merged video saved to {final_path}")

            redis_client.decr(f"{payload.job_id}")
            if redis_client.get(f"{payload.job_id}") == "0":
                redis_client.delete(f"{payload.job_id}")

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
def video_restoration_worker(payload):
    """Celery task entry point. Wraps async worker in event loop."""
    normalized = normalize_payload(payload)
    asyncio.run(enhance_video(normalized))