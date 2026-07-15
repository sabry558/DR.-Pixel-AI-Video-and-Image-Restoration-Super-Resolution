"""
VideoColorCorrectionPipeline: the single public entry point teammates call.

Design notes for the team:
    - Frames are passed as in-memory lists of numpy arrays (decoded once,
      upfront), NOT as video file paths. Re-decoding at each pipeline stage
      risks introducing new compression artifacts and frame-count mismatches
      between tools (ffmpeg vs OpenCV vs decord, etc). Decode once, pass
      arrays between modules.
    - Corrupted frames are EXCLUDED from scene-cut detection (visible
      corruption or reconstruction drift can look like a false cut), then
      slotted into whichever shot their original index falls into.
    - Only the color_space flag in CorrectionConfig needs to change if a
      teammate's module produces frames in a different channel order.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Sequence

import numpy as np

from .color_correction import ColorCorrector
from .config import CorrectionConfig
from .corruption_range import CorruptionRange, flatten_to_index_set
from .reference_selection import ReferenceFrameSelector
from .scene_detection import Shot, build_scene_detector

logger = logging.getLogger(__name__)


class CorrectionResult:
    """Result of running the pipeline: corrected frames plus bookkeeping
    about anything that couldn't be corrected, so callers/QA can inspect it
    rather than have failures silently swallowed.
    """

    def __init__(self, frames: List[np.ndarray]):
        self.frames = frames
        self.flagged_for_review: List[int] = []  # frame indices with no reference
        self.correction_log: Dict[int, dict] = {}  # per-frame debug info

    def flag(self, frame_idx: int, reason: str) -> None:
        self.flagged_for_review.append(frame_idx)
        logger.warning("Frame %d flagged for manual review: %s", frame_idx, reason)

    def log_correction(self, frame_idx: int, num_references: int, corruption_type: str) -> None:
        self.correction_log[frame_idx] = {
            "num_references": num_references,
            "corruption_type": corruption_type,
        }


class VideoColorCorrectionPipeline:
    """Composes scene detection, reference selection, and color correction
    into a single callable pipeline.

    Usage:
        config = CorrectionConfig(color_space=ColorSpace.BGR)
        pipeline = VideoColorCorrectionPipeline(config)
        result = pipeline.run(frames, corruption_dicts)
        corrected_frames = result.frames
    """

    def __init__(self, config: Optional[CorrectionConfig] = None):
        self.config = config or CorrectionConfig()
        logging.basicConfig(level=self.config.log_level)

        self.scene_detector = build_scene_detector(
            self.config.scene_detector_backend,
            self.config.scene_detection_threshold,
            self.config.color_space,
            self.config.assumed_fps,
        )
        self.color_corrector = ColorCorrector(
            self.config.color_space, self.config.histogram_method
        )

    def run(
        self,
        frames: Sequence[np.ndarray],
        corruption_ranges: Sequence[dict] | Sequence[CorruptionRange],
        region_masks: Optional[Dict[int, np.ndarray]] = None,
    ) -> CorrectionResult:
        """
        Args:
            frames: ALL frames of the video, in order, with corrupted
                frames already replaced by the reconstruction model's
                (SeedVR2/RVRT) output. Color order must match
                self.config.color_space.
            corruption_ranges: Raw output from the corruption classifier —
                either the raw list of dicts, or already-parsed
                CorruptionRange objects.
            region_masks: Optional {frame_idx: boolean H x W mask}. Only
                needed if a spatial corruption mask is available; omit
                entirely (or leave an index out) to correct the whole frame.

        Returns:
            CorrectionResult with `.frames` (corrected, same order/length as
            input) and bookkeeping about anything flagged for review.
        """
        parsed_ranges = self._parse_ranges(corruption_ranges)
        corrupted_indices = flatten_to_index_set(parsed_ranges)

        shots = self._detect_shots(frames, corrupted_indices)
        selector = ReferenceFrameSelector(
            shots=shots,
            corrupted_indices=corrupted_indices,
            window=self.config.reference_window,
        )

        result = CorrectionResult(frames=list(frames))

        for corruption_range in parsed_ranges:
            for frame_idx in corruption_range.indices():
                self._correct_single_frame(
                    frame_idx=frame_idx,
                    corruption_type=corruption_range.corruption_type,
                    frames=frames,
                    selector=selector,
                    region_masks=region_masks,
                    result=result,
                )

        logger.info(
            "Pipeline finished: %d frame(s) corrected, %d flagged for review.",
            len(result.correction_log), len(result.flagged_for_review),
        )
        return result

    def _parse_ranges(
        self, corruption_ranges: Sequence[dict] | Sequence[CorruptionRange]
    ) -> List[CorruptionRange]:
        if corruption_ranges and isinstance(corruption_ranges[0], dict):
            return CorruptionRange.from_dict_list(list(corruption_ranges))
        return list(corruption_ranges)  # already CorruptionRange objects

    def _detect_shots(
        self, frames: Sequence[np.ndarray], corrupted_indices: set
    ) -> List[Shot]:
        clean_indices = [i for i in range(len(frames)) if i not in corrupted_indices]
        clean_frames = [frames[i] for i in clean_indices]
        return self.scene_detector.detect(clean_frames, clean_indices)

    def _correct_single_frame(
        self,
        frame_idx: int,
        corruption_type: str,
        frames: Sequence[np.ndarray],
        selector: ReferenceFrameSelector,
        region_masks: Optional[Dict[int, np.ndarray]],
        result: CorrectionResult,
    ) -> None:
        reference_frames = selector.get_reference_frames(frame_idx, frames)

        if len(reference_frames) < self.config.min_references_required:
            result.flag(
                frame_idx,
                reason=f"only {len(reference_frames)} clean reference(s) found "
                        f"in shot (need {self.config.min_references_required}).",
            )
            return

        mask = region_masks.get(frame_idx) if region_masks else None

        result.frames[frame_idx] = self.color_corrector.correct(
            frame=frames[frame_idx],
            reference_frames=reference_frames,
            region_mask=mask,
        )
        result.log_correction(frame_idx, len(reference_frames), corruption_type)
