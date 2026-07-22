"""
DarkIR Video Enhancement Worker

Celery worker for video restoration using the DarkIR model.
Adapts the standalone inference script for async job-queue processing.
"""

import asyncio
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterator, Optional

import cv2 as cv
import numpy as np
import torch
import torch.nn.functional as F
from torchvision.transforms import Resize

from app.services.light_rabbitmq_service import app
from app.db.session import SessionLocal
from app.repositories.job_repository import AsyncJobRepository, JobStatus
from app.workers.workers_schema.restore_schema import RestoreSchema


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
    """
    Singleton cache for the DarkIR model.

    Safe for Celery prefork pools (one cache per worker process).
    Not thread-safe — use with prefork or solo pool only.
    """

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

    # The original script prefixes keys with "module."
    weights = {f"module.{key}": value for key, value in weights.items()}
    model.load_state_dict(weights)

    param_count = sum(p.numel() for p in model.parameters())
    print(f"Model loaded: {param_count:,} parameters")

    return model


def _resolve_weights(opt: dict) -> Path:
    """
    Locate DarkIR model weights.

    Checks configured path first, then searches common model directories.
    """
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
# FRAME CONVERSION (adapted from inference script)
# =============================================================================

class FrameConverter:
    """
    Converts between OpenCV BGR frames and normalized PyTorch tensors.

    Mirrors the original inference script's array_to_tensor / tensor_to_array.
    """

    @staticmethod
    def frame_to_tensor(frame: np.ndarray) -> torch.Tensor:
        """
        Convert BGR OpenCV frame [H, W, C] to normalized tensor [1, C, H, W].
        """
        rgb = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
        tensor = torch.from_numpy(rgb).permute(2, 0, 1).unsqueeze(0).float()
        return tensor / 255.0

    @staticmethod
    def tensor_to_frame(tensor: torch.Tensor) -> np.ndarray:
        """
        Convert tensor [1, C, H, W] back to BGR OpenCV frame [H, W, C].
        """
        array = tensor.squeeze(0).permute(1, 2, 0).cpu().numpy()
        frame = (array * 255).astype(np.uint8)
        return cv.cvtColor(frame, cv.COLOR_RGB2BGR)

    @staticmethod
    def normalize(tensor: torch.Tensor) -> torch.Tensor:
        """Normalize tensor to [0, 1] range (min-max normalization)."""
        return (tensor - tensor.min()) / (tensor.max() - tensor.min())


# =============================================================================
# FRAME RESTORATION (adapted from inference script)
# =============================================================================

class FrameRestorer:
    """
    Applies DarkIR inference to restore a single frame.

    Mirrors the original script's apply_model logic:
    - Optional resize to 720x1080 before inference
    - Pad to multiple of 8
    - Run model with side_loss=False
    - Upsample back to original size
    - Clamp and crop padding
    """

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

            original_height, original_width = tensor.shape[-2:]

            # Downsample if configured
            tensor = self._downsample(tensor)

            # Pad to multiple of 8
            tensor = self._pad_tensor(tensor, FramePadding.MULTIPLE)

            # Model inference (side_loss=False as in original)
            output = self.model(tensor, side_loss=False)

            # Upsample back to original size if resized
            if self.config.resize_enabled:
                upsample = Resize((original_height, original_width))
                output = upsample(output)

            # Clamp and crop padding
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
# VIDEO PROCESSING ORCHESTRATION
# =============================================================================

class VideoProcessor:
    """Orchestrates reading, restoring, and writing video frames."""

    def __init__(self, model: torch.nn.Module, config: ProcessingConfig):
        self.restorer = FrameRestorer(model, config)

    def process(
        self,
        video_path: str,
        output_path: Path,
        start_frame: int,
        end_frame: int,
    ) -> int:
        """
        Process a video segment and write restored output.

        Returns number of frames processed.
        """
        with VideoReader(video_path) as reader:
            meta = reader.metadata
            self._log_start(video_path, start_frame, end_frame, meta)

            with VideoWriter(output_path, meta) as writer:
                return self._process_segment(reader, writer, start_frame, end_frame)

    def _process_segment(
        self,
        reader: VideoReader,
        writer: VideoWriter,
        start: int,
        end: int,
    ) -> int:
        """Iterate frames, restore each, write to output."""
        count = 0

        for frame in reader.iter_frames(start, end):
            restored = self.restorer.restore(frame)
            writer.write(restored)
            count += 1

            if count % ProgressInterval.LOG_EVERY_N_FRAMES == 0:
                print(f"Processed {count} frames")

        print(f"Finished: {count} frames written")
        return count

    @staticmethod
    def _log_start(path: str, start: int, end: int, meta: VideoMetadata) -> None:
        print(
            f"Starting DarkIR: {path} "
            f"(frames {start}..{end}, total={meta.total_frames}, "
            f"size={meta.width}x{meta.height}, fps={meta.fps})"
        )


# =============================================================================
# OUTPUT PATH & PAYLOAD
# =============================================================================

def build_output_path(source_path: str, job_id: Optional[int] = None) -> Path:
    """Generate unique output path, optionally including job_id."""
    source = Path(source_path)
    suffix = f"_restored_{job_id}" if job_id else "_restored"
    return source.with_name(f"{source.stem}{suffix}{source.suffix}")


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
    Main worker: load model, process video frames, update job status.
    """
    async with SessionLocal() as session:
        repo = AsyncJobRepository(session)
        lifecycle = JobLifecycle(repo, payload.job_id)

        try:
            job = await _fetch_job(repo, payload.job_id)
            await lifecycle.start()

            config = load_processing_config()
            model = ModelCache.get_or_load()
            output = build_output_path(job.source_path, payload.job_id)

            print(f"Output: {output}")

            processor = VideoProcessor(model, config)
            processor.process(
                video_path=job.source_path,
                output_path=output,
                start_frame=payload.start_frame,
                end_frame=payload.end_frame,
            )

            print(f"Done: {output}")

            if payload.defect_num == payload.last_defect_num:
                await lifecycle.complete(str(output))

        except Exception:
            await lifecycle.fail()
            raise


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