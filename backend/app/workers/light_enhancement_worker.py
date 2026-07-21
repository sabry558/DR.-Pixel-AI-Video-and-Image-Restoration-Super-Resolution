"""
DarkIR Video Enhancement Worker

Celery worker for video restoration using the DarkIR model.
Restores a frame segment and merges it back into the original video.
"""

import asyncio
import os
import shutil
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterator, List, Optional, Tuple

import cv2 as cv
import numpy as np
import torch
import torch.nn.functional as F
from torchvision.transforms import Resize

from app.services.light_rabbitmq_service import app
from app.repositories.job_repository import AsyncJobRepository, JobStatus
from app.workers.workers_schema.restore_schema import RestoreSchema


# =============================================================================
# DEVICE CONFIGURATION
# =============================================================================

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"DarkIR worker using device: {DEVICE}")


# =============================================================================
# PATH CONFIGURATION
# =============================================================================

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.append(str(REPO_ROOT))

DARKIR_ROOT = REPO_ROOT / "models" / "Darkir"
if str(DARKIR_ROOT) not in sys.path:
    sys.path.append(str(DARKIR_ROOT))

CONFIG_PATH = REPO_ROOT / "models" / "Darkir" / "options" / "inference_video" / "Baseline.yml"


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

class VideoCodec:
    """Supported video codecs for output writing."""
    MP4V = "mp4v"


class FramePadding:
    """Spatial padding requirements for model input."""
    MULTIPLE = 8


class ProgressInterval:
    """Frame intervals for progress reporting."""
    LOG_EVERY_N_FRAMES = 25


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
class ProcessingConfig:
    """Configuration for video frame processing."""
    resize_enabled: bool
    target_height: int = 720
    target_width: int = 1080


# =============================================================================
# EXCEPTIONS
# =============================================================================

class DarkIRError(Exception):
    """Base exception for DarkIR worker errors."""
    pass


class VideoOpenError(DarkIRError):
    """Raised when a video file cannot be opened."""
    pass


class VideoWriterError(DarkIRError):
    """Raised when a video writer cannot be initialized."""
    pass


class WeightsNotFoundError(DarkIRError):
    """Raised when model weights cannot be located."""
    pass


class JobNotFoundError(DarkIRError):
    """Raised when a job ID does not exist in the database."""
    pass


# =============================================================================
# MODEL MANAGEMENT
# =============================================================================

class ModelCache:
    """Singleton cache for the DarkIR model."""

    _instance: Optional[torch.nn.Module] = None

    @classmethod
    def get_or_load(cls) -> torch.nn.Module:
        """Retrieve cached model or build and load a fresh instance."""
        if cls._instance is None:
            cls._instance = _build_and_load_model()
        else:
            print("Reusing cached DarkIR model")
        return cls._instance

    @classmethod
    def clear(cls) -> None:
        """Clear the cached model to free memory."""
        cls._instance = None


def _build_and_load_model() -> torch.nn.Module:
    """Build model architecture and load pretrained weights."""
    from models.Darkir.archs.DarkIR import DarkIR
    from models.Darkir.options.options import parse

    opt = parse(str(CONFIG_PATH))
    network = opt["network"]

    model = DarkIR(
        img_channel=network["img_channels"],
        width=network["width"],
        middle_blk_num_enc=network["middle_blk_num_enc"],
        middle_blk_num_dec=network["middle_blk_num_dec"],
        enc_blk_nums=network["enc_blk_nums"],
        dec_blk_nums=network["dec_blk_nums"],
        dilations=network["dilations"],
        extra_depth_wise=network["extra_depth_wise"],
    )

    weights_path = _resolve_weights(opt)
    print(f"Loading DarkIR weights from: {weights_path}")

    checkpoint = torch.load(weights_path, map_location="cpu", weights_only=False)
    weights = checkpoint["params"]
    weights = _strip_module_prefix(weights)

    model.load_state_dict(weights)
    model = model.to(DEVICE)

    param_count = sum(p.numel() for p in model.parameters())
    print(f"Model loaded on {DEVICE}: {param_count:,} parameters")

    return model


def _strip_module_prefix(weights: dict) -> dict:
    """Remove 'module.' prefix from state dict keys."""
    if not all(key.startswith("module.") for key in weights.keys()):
        return weights

    return {key.removeprefix("module."): value for key, value in weights.items()}


def _resolve_weights(opt: dict) -> Path:
    """Locate DarkIR model weights."""
    configured = (REPO_ROOT / opt["save"]["path"]).resolve()
    if configured.exists():
        return configured

    candidates = [
        REPO_ROOT / "models" / "Darkir" / "model",
        REPO_ROOT / "models" / "darkir" / "model",
        REPO_ROOT / "models" / "Darkir" / "models",
        REPO_ROOT / "models" / "darkir" / "models",
    ]

    name = Path(opt["save"]["path"]).name

    for directory in candidates:
        direct = directory / name
        if direct.exists():
            return direct

        pt_files = sorted(directory.glob("*.pt"))
        if pt_files:
            return pt_files[0]

    raise WeightsNotFoundError(
        f"Weights not found. Searched: {configured}, {', '.join(str(c) for c in candidates)}"
    )


# =============================================================================
# FRAME CONVERSION
# =============================================================================

class FrameConverter:
    """Converts between OpenCV BGR frames and normalized PyTorch tensors."""

    @staticmethod
    def frame_to_tensor(frame: np.ndarray) -> torch.Tensor:
        """Convert BGR OpenCV frame [H, W, C] to normalized tensor [1, C, H, W]."""
        rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
        tensor = torch.from_numpy(rgb).permute(2, 0, 1).unsqueeze(0).float()
        return tensor / 255.0

    @staticmethod
    def tensor_to_frame(tensor: torch.Tensor) -> np.ndarray:
        """Convert tensor [1, C, H, W] back to BGR OpenCV frame [H, W, C]."""
        array = tensor.squeeze(0).permute(1, 2, 0).cpu().numpy()
        frame = (array * 255).astype(np.uint8)
        return cv.cvtColor(frame, cv.COLOR_RGB2BGR)

    @staticmethod
    def normalize(tensor: torch.Tensor) -> torch.Tensor:
        """Normalize tensor to [0, 1] range."""
        return (tensor - tensor.min()) / (tensor.max() - tensor.min())


# =============================================================================
# FRAME RESTORATION
# =============================================================================

class FrameRestorer:
    """Applies DarkIR inference to restore a single frame."""

    def __init__(self, model: torch.nn.Module, config: ProcessingConfig):
        self.model = model
        self.config = config
        self._downsample = (
            Resize((config.target_height, config.target_width))
            if config.resize_enabled
            else torch.nn.Identity()
        )

    def restore(self, frame: np.ndarray) -> np.ndarray:
        """Restore a single frame through the DarkIR model."""
        self.model.eval()

        with torch.inference_mode():
            tensor = FrameConverter.frame_to_tensor(frame)
            tensor = FrameConverter.normalize(tensor)
            tensor = tensor.to(DEVICE)

            original_height, original_width = tensor.shape[-2:]

            tensor = self._downsample(tensor)
            tensor = self._pad_tensor(tensor, FramePadding.MULTIPLE)

            output = self.model(tensor, side_loss=False)

            if self.config.resize_enabled:
                upsample = Resize((original_height, original_width))
                output = upsample(output)

            output = torch.clamp(output, 0.0, 1.0)
            output = output[:, :, :original_height, :original_width]

            return FrameConverter.tensor_to_frame(output)

    @staticmethod
    def _pad_tensor(tensor: torch.Tensor, multiple: int) -> torch.Tensor:
        """Pad spatial dimensions to be divisible by multiple."""
        _, _, height, width = tensor.shape
        pad_h = (multiple - height % multiple) % multiple
        pad_w = (multiple - width % multiple) % multiple

        if pad_h or pad_w:
            return F.pad(tensor, (0, pad_w, 0, pad_h), value=0)
        return tensor


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
        """Extract video metadata."""
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


class VideoWriter:
    """Context-managed video writer."""

    def __init__(self, path: Path, metadata: VideoMetadata, codec: str = VideoCodec.MP4V):
        self.path = path
        self.metadata = metadata
        self.codec = codec
        self._writer: Optional[cv.VideoWriter] = None

    def __enter__(self) -> "VideoWriter":
        fourcc = cv.VideoWriter_fourcc(*self.codec)
        self._writer = cv.VideoWriter(
            str(self.path),
            fourcc,
            self.metadata.fps,
            (self.metadata.width, self.metadata.height),
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

    def add_restored_frame(self, frame: np.ndarray) -> None:
        """Collect restored frames in order."""
        self.restored_frames.append(frame)

    def merge(self, output_path: Optional[Path] = None) -> Path:
        """
        Merge restored segment into original video.

        If output_path is None, overwrites the original video atomically.
        Returns the path to the final merged video.
        """
        if output_path is None:
            # Create a temporary path next to the original
            original = Path(self.video_path)
            temp_path = original.with_suffix(".temp.mp4")
            final_path = original
        else:
            temp_path = output_path
            final_path = output_path

        with VideoReader(self.video_path) as reader:
            meta = reader.metadata

            with VideoWriter(temp_path, meta) as writer:
                self._write_merged(reader, writer, meta)

        # If overwriting original, atomically replace
        if output_path is None:
            self._atomic_replace(temp_path, final_path)

        return final_path

    def _write_merged(self, reader: VideoReader, writer: VideoWriter, meta: VideoMetadata) -> None:
        """Write merged frames: restored for segment, original elsewhere."""
        restored_index = 0
        total_restored = len(self.restored_frames)

        for frame_idx, frame in enumerate(reader.iter_frames(0, meta.total_frames - 1)):
            # Check if this frame is in the restored segment
            if self.start_frame <= frame_idx <= self.end_frame and restored_index < total_restored:
                writer.write(self.restored_frames[restored_index])
                restored_index += 1
            else:
                writer.write(frame)

        print(f"Merged {restored_index} restored frames into video")

    @staticmethod
    def _atomic_replace(temp_path: Path, final_path: Path) -> None:
        """Atomically replace original with merged video."""
        # On Windows/WSL, shutil.move handles cross-device moves
        backup_path = final_path.with_suffix(final_path.suffix + ".backup")

        # Backup original (optional, remove if you don't want backups)
        if final_path.exists():
            shutil.copy2(str(final_path), str(backup_path))

        # Replace original with merged
        shutil.move(str(temp_path), str(final_path))

        # Clean up backup if successful
        if backup_path.exists():
            backup_path.unlink()

        print(f"Atomically replaced original with merged video: {final_path}")


# =============================================================================
# VIDEO PROCESSING ORCHESTRATION (with merger)
# =============================================================================

class VideoProcessor:
    """Orchestrates reading, restoring, and merging video frames."""

    def __init__(self, model: torch.nn.Module, config: ProcessingConfig):
        self.restorer = FrameRestorer(model, config)

    def process_and_merge(
        self,
        video_path: str,
        start_frame: int,
        end_frame: int,
        output_path: Optional[Path] = None,
    ) -> Path:
        """
        Restore a frame segment and merge it back into the original video.

        If output_path is None, overwrites the original video.
        Returns the path to the final merged video.
        """
        # Step 1: Restore the segment frames
        restored_path=build_output_path(video_path)
        if restored_path.exists():
            video_path=restored_path
            
        
        restored_frames = self._restore_segment(video_path, start_frame, end_frame)

        # Step 2: Merge restored frames back into original video
        merger = VideoMerger(video_path, start_frame, end_frame)
        for frame in restored_frames:
            merger.add_restored_frame(frame)

        return merger.merge(output_path)

    def _restore_segment(
        self,
        video_path: str,
        start_frame: int,
        end_frame: int,
    ) -> List[np.ndarray]:
        """Restore frames in the segment and return them as a list."""
        restored_frames: List[np.ndarray] = []

        with VideoReader(video_path) as reader:
            meta = reader.metadata
            print(
                f"Restoring segment: {video_path} "
                f"(frames {start_frame}..{end_frame}, total={meta.total_frames})"
            )

            count = 0
            for frame in reader.iter_frames(start_frame, end_frame):
                restored = self.restorer.restore(frame)
                restored_frames.append(restored)
                count += 1

                if count % ProgressInterval.LOG_EVERY_N_FRAMES == 0:
                    print(f"Restored {count} frames")

            print(f"Segment restoration complete: {count} frames")

        return restored_frames


# =============================================================================
# OUTPUT PATH & PAYLOAD
# =============================================================================

def build_output_path(source_path: str, job_id: Optional[int] = None) -> Path:
    source = Path(source_path)

    output_dir = source.parent.parent / "restored"
    output_dir.mkdir(parents=True, exist_ok=True)


    filename = source.name

    return output_dir / filename


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
# CONFIGURATION
# =============================================================================

def load_processing_config() -> ProcessingConfig:
    """Load resize setting from DarkIR config."""
    from models.Darkir.options.options import parse

    opt = parse(str(CONFIG_PATH))
    return ProcessingConfig(resize_enabled=bool(opt.get("Resize", False)))


# =============================================================================
# MAIN ASYNC WORKER
# =============================================================================

async def enhance_video(payload: RestoreSchema) -> None:
    """
    Main worker: restore segment and merge back into original video.
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

            config = load_processing_config()
            model = ModelCache.get_or_load()

            # Build output path (new merged video)
            output = build_output_path(job.source_path, payload.job_id)

            print(f"Output (merged video): {output}")

            processor = VideoProcessor(model, config)
            final_path = processor.process_and_merge(
                video_path=job.source_path,
                start_frame=payload.start_frame,
                end_frame=payload.end_frame,
                output_path=output,
            )

            print(f"Done: merged video saved to {final_path}")

            if payload.defect_num == payload.last_defect_num:
                await lifecycle.complete(str(final_path))

        except Exception:
            await lifecycle.fail()
            raise
        finally:
            await engine.dispose()


async def _fetch_job(repo: AsyncJobRepository, job_id: int):
    """Retrieve job or raise JobNotFoundError."""
    job = await repo.get_by_id(job_id)
    if job is None:
        raise JobNotFoundError(f"Job {job_id} not found")
    return job


# =============================================================================
# CELERY TASK ENTRY POINT
# =============================================================================

@app.task(queue="light_enhancement")
def route_light_enhancement(payload):
    """Celery task entry point. Wraps async worker in event loop."""
    normalized = normalize_payload(payload)
    asyncio.run(enhance_video(normalized))