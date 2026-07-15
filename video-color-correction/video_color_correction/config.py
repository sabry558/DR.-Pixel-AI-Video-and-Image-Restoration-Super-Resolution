"""
Central configuration for the color correction pipeline.

Keeping every tunable in one dataclass means there is exactly one place to
look when something needs to change (e.g. the pipeline is fed RGB frames
instead of BGR, or the reference-frame window needs to grow).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ColorSpace(str, Enum):
    """Input/output color channel order of the frames the pipeline receives.

    This is the single flag that controls channel-order handling everywhere.
    If a teammate's module ever produces frames in a different order than
    expected, this is the only place that needs to change.
    """
    BGR = "bgr"   # OpenCV's default
    RGB = "rgb"


class HistogramMethod(str, Enum):
    """Which statistic-matching strategy ColorCorrector should use."""
    MOMENT = "moment"        # fast: match mean/std per channel (Reinhard-style)
    FULL = "full"             # slower, more precise: full CDF histogram matching


@dataclass
class CorrectionConfig:
    """All tunable parameters for the pipeline, in one place.

    Attributes:
        color_space: Channel order of frames going in/out (see ColorSpace).
        reference_window: How many frames before/after a corrupted frame to
            search for clean references, within the same shot.
        histogram_method: Which ColorCorrector strategy to use.
        scene_detector_backend: "pyscenedetect" or "histogram_diff".
        scene_detection_threshold: Threshold passed to whichever scene
            detector backend is selected. Meaning depends on backend.
        assumed_fps: Only used by the PySceneDetect backend, which requires
            a frame rate to build internal timecodes. Frame arrays carry no
            fps metadata, so this is a stand-in; it only affects the
            detector's internal min-scene-length/flash-filter timing, not
            which pixels get compared. Pass the real fps if known.
        min_references_required: If fewer than this many clean reference
            frames are found for a corrupted frame, it is flagged for manual
            review instead of corrected.
        log_level: Standard logging level (e.g. logging.INFO) for all
            loggers created by this package.
    """
    color_space: ColorSpace = ColorSpace.BGR
    reference_window: int = 3
    histogram_method: HistogramMethod = HistogramMethod.MOMENT
    scene_detector_backend: str = "pyscenedetect"
    scene_detection_threshold: float = 27.0
    assumed_fps: float = 30.0
    min_references_required: int = 1
    log_level: int = 20  # logging.INFO, kept as int to avoid importing logging here
