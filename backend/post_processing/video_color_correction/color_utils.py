"""
Color-space conversion helpers.

This is the ONLY file in the package that should call cv2.cvtColor with a
hardcoded BGR2LAB / RGB2LAB constant. Every other module asks a
ColorSpaceConverter to do the conversion for it, passing the ColorSpace flag
from CorrectionConfig. If frames ever arrive in an unexpected channel order,
fixing this one file fixes the whole pipeline.
"""

from __future__ import annotations

import logging

import cv2
import numpy as np

from .config import ColorSpace

logger = logging.getLogger(__name__)


class ColorSpaceConverter:
    """Converts frames to/from LAB, aware of whether input is BGR or RGB."""

    def __init__(self, color_space: ColorSpace):
        self.color_space = color_space
        self._to_lab_code = (
            cv2.COLOR_BGR2LAB if color_space == ColorSpace.BGR else cv2.COLOR_RGB2LAB
        )
        self._from_lab_code = (
            cv2.COLOR_LAB2BGR if color_space == ColorSpace.BGR else cv2.COLOR_LAB2RGB
        )

    def to_lab(self, frame: np.ndarray) -> np.ndarray:
        """Convert a uint8 frame in self.color_space order to LAB (uint8)."""
        return cv2.cvtColor(frame, self._to_lab_code)

    def from_lab(self, lab_frame: np.ndarray) -> np.ndarray:
        """Convert a LAB (uint8) frame back to self.color_space order."""
        return cv2.cvtColor(lab_frame, self._from_lab_code)


def validate_frame(frame: np.ndarray) -> None:
    """Basic sanity check, catches the most common integration bugs early."""
    if frame is None:
        raise ValueError("Frame is None.")
    if frame.dtype != np.uint8:
        raise ValueError(
            f"Expected uint8 frame, got dtype={frame.dtype}. "
            "Convert frames to uint8 (0-255) before passing them in."
        )
    if frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError(
            f"Expected an HxWx3 frame, got shape={frame.shape}."
        )
