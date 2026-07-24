"""
video_color_correction
=======================

Post-hoc color/intensity consistency correction for reconstructed video frames.

Public API:
    - VideoColorCorrectionPipeline : the main entry point teammates should use
    - CorrectionConfig, ColorSpace  : configuration
    - CorruptionRange               : wraps the classifier's output dicts

Everything else (scene detection backends, matching strategies, reference
selection) is an internal implementation detail and can be swapped without
changing the public API.
"""

from .config import ColorSpace, CorrectionConfig, HistogramMethod
from .corruption_range import CorruptionRange
from .orchestrator import VideoColorCorrectionPipeline
from .scene_average_correction import SceneAverageColorCorrector

__all__ = [
    "ColorSpace",
    "CorrectionConfig",
    "HistogramMethod",
    "CorruptionRange",
    "VideoColorCorrectionPipeline",
    "SceneAverageColorCorrector",
]
