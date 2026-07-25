"""
Reference-frame selection.

Given a corrupted frame index, this answers: "which clean frames, from the
same shot, within the configured window, can I use as a color/intensity
reference?"

This is deliberately kept separate from both scene_detection.py and
color_correction.py — it's the piece most likely to change if the
corruption classifier's output format changes, and neither of the other two
modules need to know anything about it.
"""

from __future__ import annotations

import logging
from typing import List, Sequence

import numpy as np

from .scene_detection import Shot

logger = logging.getLogger(__name__)


class ReferenceFrameSelector:
    """Selects clean, same-shot reference frames for a given corrupted index."""

    def __init__(self, shots: Sequence[Shot], corrupted_indices: set, window: int):
        """
        Args:
            shots: Shot boundaries covering the full video (original indices).
            corrupted_indices: Set of ALL corrupted frame indices in the video
                (flattened across every CorruptionRange). Used to make sure a
                reference frame is never itself corrupted.
            window: Max distance (in frames) to look before/after the target
                frame for a reference, within the same shot.
        """
        self.shots = shots
        self.corrupted_indices = corrupted_indices
        self.window = window

    def _find_shot(self, frame_idx: int) -> Shot:
        for shot in self.shots:
            if frame_idx in shot:
                return shot
        raise ValueError(
            f"Frame index {frame_idx} does not fall inside any detected shot. "
            "This usually means shot boundaries don't cover the full video "
            "range — check the scene detector output."
        )

    def get_reference_indices(self, frame_idx: int) -> List[int]:
        """Indices of clean, same-shot frames within `window` of frame_idx,
        closest first.
        """
        shot = self._find_shot(frame_idx)
        candidates = [
            i for i in range(shot.start_frame, shot.end_frame)
            if i != frame_idx
            and i not in self.corrupted_indices
            and abs(i - frame_idx) <= self.window
        ]
        candidates.sort(key=lambda i: abs(i - frame_idx))
        return candidates

    def get_reference_frames(
        self, frame_idx: int, all_frames: Sequence[np.ndarray]
    ) -> List[np.ndarray]:
        """Convenience wrapper: same as get_reference_indices but returns the
        actual frame arrays instead of indices.
        """
        indices = self.get_reference_indices(frame_idx)
        if not indices:
            logger.warning(
                "No clean reference frames found for frame %d within window=%d "
                "of its shot.", frame_idx, self.window
            )
        return [all_frames[i] for i in indices]
