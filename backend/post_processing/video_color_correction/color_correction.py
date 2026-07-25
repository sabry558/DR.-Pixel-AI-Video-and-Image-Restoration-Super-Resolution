"""
Color/intensity correction via LAB-space statistic matching.

Two interchangeable strategies (Strategy pattern), selected via
CorrectionConfig.histogram_method:
    - MomentMatcher : matches per-channel mean/std (fast, Reinhard-style)
    - FullHistogramMatcher : matches full per-channel CDF (slower, precise)

ColorCorrector is the class other modules actually call; it delegates the
math to whichever strategy the config selects, and optionally restricts the
computation to a region_mask.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Sequence

import numpy as np

from .color_utils import ColorSpaceConverter, validate_frame
from .config import ColorSpace, HistogramMethod

logger = logging.getLogger(__name__)


class HistogramMatchingStrategy(ABC):
    """Common interface for per-channel LAB statistic matching strategies."""

    @abstractmethod
    def match_channel(
        self,
        target_channel: np.ndarray,
        reference_channel: np.ndarray,
        target_mask: Optional[np.ndarray] = None,
        reference_mask: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """Returns a corrected copy of target_channel, matched to
        reference_channel's statistics. If masks are given, only pixels
        where the mask is True are used to compute statistics (but the
        whole channel is still returned, transformed).
        """
        raise NotImplementedError


class MomentMatcher(HistogramMatchingStrategy):
    """Matches mean and standard deviation only (fast, robust to noise).
    Equivalent to Reinhard-style color transfer applied per frame.
    """

    def match_channel(
        self,
        target_channel: np.ndarray,
        reference_channel: np.ndarray,
        target_mask: Optional[np.ndarray] = None,
        reference_mask: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        target_pixels = target_channel[target_mask] if target_mask is not None else target_channel
        reference_pixels = (
            reference_channel[reference_mask] if reference_mask is not None else reference_channel
        )

        target_mean, target_std = target_pixels.mean(), target_pixels.std()
        ref_mean, ref_std = reference_pixels.mean(), reference_pixels.std()

        if target_std < 1e-6:
            logger.debug("Target channel has near-zero std; skipping scale, only shifting mean.")
            corrected = target_channel.astype(np.float32) - target_mean + ref_mean
        else:
            corrected = (
                (target_channel.astype(np.float32) - target_mean) / target_std
            ) * ref_std + ref_mean

        return np.clip(corrected, 0, 255).astype(np.uint8)


class FullHistogramMatcher(HistogramMatchingStrategy):
    """Matches the full cumulative distribution (histogram specification).
    Handles cases moment matching misses, e.g. clipped highlights/shadows or
    non-linear tone shifts, at higher compute cost.
    """

    def match_channel(
        self,
        target_channel: np.ndarray,
        reference_channel: np.ndarray,
        target_mask: Optional[np.ndarray] = None,
        reference_mask: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        target_pixels = target_channel[target_mask] if target_mask is not None else target_channel.ravel()
        reference_pixels = (
            reference_channel[reference_mask] if reference_mask is not None else reference_channel.ravel()
        )

        # Build CDFs over the 0-255 uint8 range.
        target_hist, _ = np.histogram(target_pixels, bins=256, range=(0, 256))
        ref_hist, _ = np.histogram(reference_pixels, bins=256, range=(0, 256))

        target_cdf = np.cumsum(target_hist).astype(np.float64)
        target_cdf /= target_cdf[-1] if target_cdf[-1] > 0 else 1

        ref_cdf = np.cumsum(ref_hist).astype(np.float64)
        ref_cdf /= ref_cdf[-1] if ref_cdf[-1] > 0 else 1

        # For each possible source value, find the reference value whose CDF
        # is closest -> builds a 256-entry lookup table.
        lookup_table = np.searchsorted(ref_cdf, target_cdf).clip(0, 255).astype(np.uint8)

        return lookup_table[target_channel]


def build_histogram_matcher(method: HistogramMethod) -> HistogramMatchingStrategy:
    """Factory: turns a config enum into a strategy instance.

    Centralizing this means CorrectionConfig.histogram_method is the only
    thing that needs to change to swap matching strategy.
    """
    if method == HistogramMethod.MOMENT:
        return MomentMatcher()
    if method == HistogramMethod.FULL:
        return FullHistogramMatcher()
    raise ValueError(f"Unknown histogram_method: {method!r}")


class ColorCorrector:
    """Corrects a reconstructed frame's color/intensity to match clean,
    same-shot reference frames, using LAB space and a pluggable matching
    strategy.
    """

    def __init__(self, color_space: ColorSpace, histogram_method: HistogramMethod):
        self.converter = ColorSpaceConverter(color_space)
        self.strategy = build_histogram_matcher(histogram_method)

    def correct(
        self,
        frame: np.ndarray,
        reference_frames: Sequence[np.ndarray],
        region_mask: Optional[np.ndarray] = None,
    ) -> np.ndarray:
        """
        Args:
            frame: The reconstructed frame to correct, in the pipeline's
                configured color_space, uint8.
            reference_frames: One or more clean, same-shot frames to match
                statistics against. If more than one is given, their pixels
                are pooled together for a more stable reference distribution.
            region_mask: Optional boolean mask (H x W) restricting which
                pixels are corrected AND which pixels are used to compute
                reference statistics. If None, the whole frame is used
                (appropriate when corruption covers most/all of the frame,
                or when no spatial mask is available).

        Returns:
            Corrected frame, same shape/dtype/color_space as the input.
        """
        validate_frame(frame)
        for ref in reference_frames:
            validate_frame(ref)

        if not reference_frames:
            logger.warning("No reference frames provided; returning frame unchanged.")
            return frame

        target_lab = self.converter.to_lab(frame)
        reference_labs = [self.converter.to_lab(ref) for ref in reference_frames]

        # Pool all reference frames' pixels together per channel for a more
        # stable statistic than any single neighbor would give.
        pooled_reference_lab = np.concatenate(
            [ref.reshape(-1, 3) for ref in reference_labs], axis=0
        )

        corrected_lab = np.empty_like(target_lab)
        for channel_idx in range(3):
            target_channel = target_lab[:, :, channel_idx]
            reference_channel = pooled_reference_lab[:, channel_idx]

            corrected_lab[:, :, channel_idx] = self.strategy.match_channel(
                target_channel=target_channel,
                reference_channel=reference_channel,
                target_mask=region_mask,
                reference_mask=None,  # already pooled/flattened above
            )

        corrected_frame = self.converter.from_lab(corrected_lab)

        if region_mask is not None:
            # Only replace pixels inside the mask; leave the rest of the
            # frame untouched (it was never corrupted, don't overcorrect it).
            output = frame.copy()
            output[region_mask] = corrected_frame[region_mask]
            return output

        return corrected_frame
