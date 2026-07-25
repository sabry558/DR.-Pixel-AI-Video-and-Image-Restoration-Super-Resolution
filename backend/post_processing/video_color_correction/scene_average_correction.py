"""
Scene-average color correction.

Use this when you DON'T have frame-level classifier output (no known list
of which frames are corrupted) — only a full reference video (e.g. the
pre-reconstruction original) and a full target video (e.g. SeedVR2/RVRT's
output) to compare against.

Since we don't know which specific frames drifted, we can't do frame-level
histogram matching against "clean neighbor frames" the way the classifier-
driven pipeline (orchestrator.py) does — there's no reliable notion of
"clean" without that metadata. Instead, this treats every frame in a scene
as needing correction, and shifts it toward that SCENE's average LAB level
from the reference video. Averaging must be done per-scene (not over the
whole video) or you'd blend together frames from different lighting/scenes,
which would corrupt frames that weren't actually mismatched.

Important caveat: this mode needs a full, frame-aligned reference video.
That's realistic for testing (you have both original.mp4 and
reconstructed.mp4), but NOT realistic in production, where you typically
only ever have the reconstructed output plus (maybe) classifier flags —
not the original. Treat this as a test/validation tool and a fallback for
"classifier gave us nothing," not the primary production path.
"""

from __future__ import annotations

import logging
from typing import List, Sequence

import numpy as np

from .color_utils import ColorSpaceConverter, validate_frame
from .config import ColorSpace
from .scene_detection import SceneDetector, Shot

logger = logging.getLogger(__name__)


class SceneAverageColorCorrector:
    """Shifts a target video's per-scene LAB mean to match a reference
    video's per-scene LAB mean. Mean-only (no std scaling) by design: with
    no frame-level ground truth about which frames actually drifted, we
    only trust the coarse average brightness/color level, not the spread —
    scaling std on top of that risks amplifying noise in reconstructed
    frames that didn't need correction at all.
    """

    def __init__(self, color_space: ColorSpace, scene_detector: SceneDetector):
        self.converter = ColorSpaceConverter(color_space)
        self.scene_detector = scene_detector

    def correct(
        self,
        reference_frames: Sequence[np.ndarray],
        target_frames: Sequence[np.ndarray],
    ) -> List[np.ndarray]:
        """
        Args:
            reference_frames: "ground truth" video (e.g. original), used
                only to compute each scene's target average — frame-aligned
                and same length as target_frames.
            target_frames: the video to correct (e.g. reconstructed output).

        Returns:
            Corrected copy of target_frames, same length/order.
        """
        if len(reference_frames) != len(target_frames):
            raise ValueError(
                f"reference_frames ({len(reference_frames)}) and target_frames "
                f"({len(target_frames)}) must be the same length — they need "
                "to be frame-aligned."
            )
        validate_frame(reference_frames[0])
        validate_frame(target_frames[0])

        indices = list(range(len(reference_frames)))
        # Scene boundaries are detected from the REFERENCE (original) video —
        # it's the one we trust to reflect true scene structure, since the
        # target video's own cuts could in principle be affected by whatever
        # caused frames to need reconstruction in the first place.
        shots = self.scene_detector.detect(list(reference_frames), indices)
        logger.info("Scene-average correction: %d shot(s) detected.", len(shots))

        corrected = list(target_frames)
        for shot in shots:
            scene_mean_lab = self._scene_mean_lab(reference_frames, shot)
            logger.info(
                "Shot [%d, %d): reference mean LAB = %s",
                shot.start_frame, shot.end_frame, scene_mean_lab.round(1).tolist(),
            )
            for i in range(shot.start_frame, shot.end_frame):
                corrected[i] = self._shift_frame_mean(target_frames[i], scene_mean_lab)

        return corrected

    def _scene_mean_lab(self, frames: Sequence[np.ndarray], shot: Shot) -> np.ndarray:
        """Average L, A, B across every reference frame in this shot."""
        sums = np.zeros(3, dtype=np.float64)
        count = 0
        for i in range(shot.start_frame, shot.end_frame):
            lab = self.converter.to_lab(frames[i])
            sums += lab.reshape(-1, 3).mean(axis=0)
            count += 1
        return sums / max(count, 1)

    def _shift_frame_mean(self, frame: np.ndarray, target_mean_lab: np.ndarray) -> np.ndarray:
        """Shifts this frame's LAB mean to target_mean_lab, per channel."""
        lab = self.converter.to_lab(frame).astype(np.float32)
        current_mean = lab.reshape(-1, 3).mean(axis=0)
        shift = target_mean_lab - current_mean
        shifted = np.clip(lab + shift, 0, 255).astype(np.uint8)
        return self.converter.from_lab(shifted)
