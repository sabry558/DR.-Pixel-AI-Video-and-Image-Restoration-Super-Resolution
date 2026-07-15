"""
Scene/shot boundary detection.

Corrupted frames must never be allowed to influence WHERE a cut is detected
(visible corruption or reconstruction drift can look like a false cut), so
every backend here receives only the CLEAN frames plus a mapping back to
their original indices in the full video, and returns shot boundaries in
terms of the ORIGINAL indices.

Two backends are provided behind a common interface (Strategy pattern) so
the detection method can be swapped without touching anything downstream:
    - PySceneDetectBackend    : wraps the PySceneDetect library (default)
    - HistogramDiffBackend    : pure OpenCV/numpy fallback, no extra dependency
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Sequence

import cv2
import numpy as np

from .config import ColorSpace

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Shot:
    """A contiguous shot, expressed in ORIGINAL (full-video) frame indices."""
    start_frame: int  # inclusive
    end_frame: int    # exclusive

    def __contains__(self, frame_idx: int) -> bool:
        return self.start_frame <= frame_idx < self.end_frame


class SceneDetector(ABC):
    """Common interface every scene-detection backend must implement."""

    @abstractmethod
    def detect(
        self,
        clean_frames: Sequence[np.ndarray],
        original_indices: Sequence[int],
    ) -> List[Shot]:
        """
        Args:
            clean_frames: Frames with corrupted ones already removed, in
                original video order.
            original_indices: original_indices[i] is the full-video index of
                clean_frames[i]. Same length as clean_frames.

        Returns:
            List of Shot objects covering the *original* index space. Gaps
            left by removed corrupted frames are bridged (a shot's range is
            extended across any corrupted frames it contains), so every
            original frame index — corrupted or not — falls inside exactly
            one Shot.
        """
        raise NotImplementedError

    @staticmethod
    def _bridge_gaps(
        cut_original_indices: List[int], total_frame_count: int
    ) -> List[Shot]:
        """Turn a sorted list of cut points (original indices) into Shots
        that cover the full [0, total_frame_count) range, so corrupted
        frames (which were excluded from detection) still fall inside a
        shot.
        """
        boundaries = sorted(set([0, *cut_original_indices, total_frame_count]))
        return [
            Shot(start_frame=boundaries[i], end_frame=boundaries[i + 1])
            for i in range(len(boundaries) - 1)
        ]


class PySceneDetectBackend(SceneDetector):
    """Wraps PySceneDetect's ContentDetector.

    Requires the `scenedetect` package (pip install scenedetect).
    """

    def __init__(
        self,
        threshold: float = 27.0,
        color_space: ColorSpace = ColorSpace.BGR,
        assumed_fps: float = 30.0,
    ):
        self.threshold = threshold
        # PySceneDetect's ContentDetector assumes BGR internally (OpenCV
        # convention) regardless of what the rest of this pipeline is
        # configured for, so we track input color space here to convert
        # just before handing frames to it.
        self.color_space = color_space
        # PySceneDetect's frame-driven API requires a FrameTimecode (which
        # needs an fps) rather than a plain frame index. We operate on
        # in-memory arrays with no fps metadata attached, so this is an
        # assumed value used only to build valid timecodes for the
        # detector's internal flash-filter/min-scene-length logic — it does
        # not affect which pixels are compared for the cut decision itself.
        # Pass the real fps here if it's known/available in your pipeline.
        self.assumed_fps = assumed_fps

    def detect(
        self,
        clean_frames: Sequence[np.ndarray],
        original_indices: Sequence[int],
    ) -> List[Shot]:
        try:
            from scenedetect import ContentDetector
            from scenedetect.common import FrameTimecode
        except ImportError as e:
            raise ImportError(
                "PySceneDetectBackend requires the 'scenedetect' package. "
                "Install it with: pip install scenedetect"
            ) from e

        if len(clean_frames) == 0:
            logger.warning("No clean frames provided to scene detector.")
            return []

        # PySceneDetect is built around decoding a video file directly; since
        # we operate on in-memory arrays (by design, see module docstring in
        # orchestrator.py) we drive its ContentDetector frame-by-frame
        # ourselves instead of using its video-file API.
        detector = ContentDetector(threshold=self.threshold)
        cut_original_indices: List[int] = []

        needs_bgr_conversion = self.color_space == ColorSpace.RGB

        def make_timecode(local_frame_num: int) -> "FrameTimecode":
            return FrameTimecode(timecode=local_frame_num, fps=self.assumed_fps)

        for i, frame in enumerate(clean_frames):
            bgr_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) if needs_bgr_conversion else frame
            cuts = detector.process_frame(make_timecode(i), bgr_frame)
            for cut_timecode in cuts:
                cut_original_indices.append(original_indices[cut_timecode.frame_num])
        cuts = detector.post_process(make_timecode(len(clean_frames)))
        for cut_timecode in cuts:
            local_i = min(cut_timecode.frame_num, len(original_indices) - 1)
            cut_original_indices.append(original_indices[local_i])

        total = max(original_indices) + 1 if original_indices else 0
        shots = self._bridge_gaps(cut_original_indices, total)
        logger.info("PySceneDetect found %d shot(s).", len(shots))
        return shots


class HistogramDiffBackend(SceneDetector):
    """Pure OpenCV/numpy fallback: flags a cut wherever consecutive clean
    frames' color histograms differ by more than `threshold` (Bhattacharyya
    distance). No extra dependency beyond opencv-python.
    """

    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold  # Bhattacharyya distance in [0, 1]

    def _histogram(self, frame: np.ndarray) -> np.ndarray:
        hist = cv2.calcHist([frame], [0, 1, 2], None, [8, 8, 8],
                             [0, 256, 0, 256, 0, 256])
        cv2.normalize(hist, hist)
        return hist

    def detect(
        self,
        clean_frames: Sequence[np.ndarray],
        original_indices: Sequence[int],
    ) -> List[Shot]:
        if len(clean_frames) == 0:
            logger.warning("No clean frames provided to scene detector.")
            return []

        cut_original_indices: List[int] = []
        prev_hist = self._histogram(clean_frames[0])
        for i in range(1, len(clean_frames)):
            curr_hist = self._histogram(clean_frames[i])
            distance = cv2.compareHist(prev_hist, curr_hist, cv2.HISTCMP_BHATTACHARYYA)
            if distance > self.threshold:
                cut_original_indices.append(original_indices[i])
            prev_hist = curr_hist

        total = max(original_indices) + 1 if original_indices else 0
        shots = self._bridge_gaps(cut_original_indices, total)
        logger.info("HistogramDiffBackend found %d shot(s).", len(shots))
        return shots


def build_scene_detector(
    backend_name: str,
    threshold: float,
    color_space: ColorSpace = ColorSpace.BGR,
    assumed_fps: float = 30.0,
) -> SceneDetector:
    """Factory: turns a config string into a SceneDetector instance.

    Centralizing this means CorrectionConfig.scene_detector_backend is the
    only thing that needs to change to swap detection strategy.
    """
    if backend_name == "pyscenedetect":
        return PySceneDetectBackend(
            threshold=threshold, color_space=color_space, assumed_fps=assumed_fps
        )
    if backend_name == "histogram_diff":
        # Histogram-diff backend works directly on whatever channel order it
        # is given since it's just comparing color-histogram distances, not
        # displaying/decoding frames, so no conversion is needed here.
        return HistogramDiffBackend(threshold=threshold)
    raise ValueError(f"Unknown scene_detector_backend: {backend_name!r}")
