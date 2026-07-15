"""
test_manual.py
==============

Manual/exploratory test for the video_color_correction pipeline, using two
REAL videos you already have:

    - original.mp4      : the clean/original video
    - reconstructed.mp4  : the same video after SeedVR2/RVRT reconstruction
                            (visibly different saturation/intensity)

Since we do the splicing ourselves, we already know exactly which frame
indices are "corrupted" — no classifier needed for this test. The script:

    1. Reads both videos into frame arrays (OpenCV -> BGR).
    2. Picks a random contiguous range of frame indices.
    3. Builds a test video = original frames, EXCEPT that range is replaced
       with the reconstructed video's frames at the same indices (so we've
       manually created the exact problem: a video that's fine except for
       a color-shifted patch, mimicking what the real pipeline will see).
    4. Builds the corruption_ranges dict ourselves (we know the indices).
    5. Runs VideoColorCorrectionPipeline on it.
    6. Reports before/after LAB stats and writes a corrected output video
       so you can eyeball it.

Usage:
    python test_manual.py --original path/to/original.mp4 \
                           --reconstructed path/to/reconstructed.mp4 \
                           --num-frames 10 \
                           --output corrected_test_output.mp4
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import List, Tuple

import cv2
import matplotlib
matplotlib.use("Agg")  # no display needed, just save PNGs
import matplotlib.pyplot as plt
import numpy as np

from video_color_correction import (
    ColorSpace,
    CorrectionConfig,
    HistogramMethod,
    VideoColorCorrectionPipeline,
)

logger = logging.getLogger("test_manual")


def read_video_frames(path: str) -> Tuple[List[np.ndarray], float]:
    """Reads every frame of a video into a list of BGR uint8 arrays."""
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Could not open video: {path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frames = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frames.append(frame)
    cap.release()

    if not frames:
        raise ValueError(f"No frames read from {path} — check the file/path.")
    return frames, fps


def write_video(path: str, frames: List[np.ndarray], fps: float) -> None:
    h, w = frames[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, fps, (w, h))
    if not writer.isOpened():
        raise RuntimeError(f"Could not open VideoWriter for {path} — check codec support.")

    for i, f in enumerate(frames):
        if f.shape[:2] != (h, w):
            raise ValueError(
                f"Frame {i} has shape {f.shape[:2]}, expected {(h, w)}. "
                "All frames must share the same resolution before writing."
            )
        writer.write(f)
    writer.release()


def lab_means(frame: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    return lab.reshape(-1, 3).mean(axis=0)  # [L, A, B]


def plot_lab_over_range(
    original_frames: List[np.ndarray],
    before_frames: List[np.ndarray],
    after_frames: List[np.ndarray],
    start_idx: int,
    end_idx: int,
    output_path: str,
    context: int = 5,
) -> None:
    """Line chart of mean L, A, B per frame across [start-context, end+context],
    for original vs spliced(before) vs corrected(after). Makes the
    correction's effect immediately visible without scrubbing video.
    """
    lo = max(0, start_idx - context)
    hi = min(len(original_frames), end_idx + context + 1)
    indices = list(range(lo, hi))

    orig_lab = np.array([lab_means(original_frames[i]) for i in indices])
    before_lab = np.array([lab_means(before_frames[i]) for i in indices])
    after_lab = np.array([lab_means(after_frames[i]) for i in indices])

    channel_names = ["L (lightness)", "A (green-red)", "B (blue-yellow)"]
    fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)

    for c in range(3):
        ax = axes[c]
        ax.plot(indices, orig_lab[:, c], label="original", color="black", linewidth=2)
        ax.plot(indices, before_lab[:, c], label="spliced (before fix)", color="red",
                 linestyle="--", marker="o", markersize=3)
        ax.plot(indices, after_lab[:, c], label="corrected (after fix)", color="green",
                 marker="o", markersize=3)
        ax.axvspan(start_idx, end_idx, color="yellow", alpha=0.15, label="spliced range" if c == 0 else None)
        ax.set_ylabel(channel_names[c])
        ax.grid(True, alpha=0.3)

    axes[0].legend(loc="upper right", fontsize=8)
    axes[-1].set_xlabel("frame index")
    fig.suptitle(f"LAB channel means — frames [{lo}, {hi - 1}] (spliced range: [{start_idx}, {end_idx}])")
    fig.tight_layout()
    fig.savefig(output_path, dpi=130)
    plt.close(fig)
    logger.info("LAB comparison plot saved to: %s", output_path)


def save_side_by_side_frames(
    original_frames: List[np.ndarray],
    before_frames: List[np.ndarray],
    after_frames: List[np.ndarray],
    frame_indices: List[int],
    output_dir: str,
) -> None:
    """For each requested frame index, saves ONE image showing three panels
    side by side: original | spliced (before fix) | corrected (after fix),
    for both the raw BGR frame and its LAB channels stacked below it.
    """
    os.makedirs(output_dir, exist_ok=True)
    label_h = 24

    def label_panel(img: np.ndarray, text: str) -> np.ndarray:
        panel = np.zeros((img.shape[0] + label_h, img.shape[1], 3), dtype=np.uint8)
        panel[label_h:, :, :] = img
        cv2.putText(panel, text, (4, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
        return panel

    for idx in frame_indices:
        orig = label_panel(original_frames[idx], "original")
        before = label_panel(before_frames[idx], "spliced (before)")
        after = label_panel(after_frames[idx], "corrected (after)")
        combined_bgr = np.hstack([orig, before, after])

        # Same three panels, but visualizing the L channel only (grayscale),
        # to make brightness/intensity differences even more obvious.
        def l_channel_bgr(img: np.ndarray) -> np.ndarray:
            l = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)[:, :, 0]
            return cv2.cvtColor(l, cv2.COLOR_GRAY2BGR)

        orig_l = label_panel(l_channel_bgr(original_frames[idx]), "original (L)")
        before_l = label_panel(l_channel_bgr(before_frames[idx]), "spliced (L)")
        after_l = label_panel(l_channel_bgr(after_frames[idx]), "corrected (L)")
        combined_l = np.hstack([orig_l, before_l, after_l])

        combined = np.vstack([combined_bgr, combined_l])
        out_path = os.path.join(output_dir, f"frame_{idx:05d}_comparison.png")
        cv2.imwrite(out_path, combined)

    logger.info("Saved %d side-by-side comparison image(s) to: %s", len(frame_indices), output_dir)


def splice_reconstructed_into_original(
    original_frames: List[np.ndarray],
    reconstructed_frames: List[np.ndarray],
    num_frames: int,
    seed: int,
) -> Tuple[List[np.ndarray], int, int]:
    """Builds a test frame array: original frames, with a random contiguous
    range replaced by the reconstructed video's frames at the same indices.

    Returns (spliced_frames, start_idx, end_idx_inclusive).
    """
    n = min(len(original_frames), len(reconstructed_frames))
    if n <= num_frames:
        raise ValueError(
            f"Videos too short ({n} usable frames) for num_frames={num_frames}."
        )

    rng = np.random.default_rng(seed)
    start_idx = int(rng.integers(0, n - num_frames))
    end_idx = start_idx + num_frames - 1

    spliced = list(original_frames[:n])  # truncate to shorter video's length
    for i in range(start_idx, end_idx + 1):
        spliced[i] = reconstructed_frames[i]

    return spliced, start_idx, end_idx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", required=True, help="Path to original.mp4")
    parser.add_argument("--reconstructed", required=True, help="Path to reconstructed.mp4 (SeedVR2/RVRT output)")
    parser.add_argument("--num-frames", type=int, default=10, help="How many consecutive frames to splice in as 'corrupted'")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for picking which frames to splice")
    parser.add_argument("--output", default="corrected_test_output.mp4", help="Where to save the corrected video")
    parser.add_argument("--backend", default="pyscenedetect", choices=["pyscenedetect", "histogram_diff"])
    parser.add_argument("--method", default="moment", choices=["moment", "full"])
    parser.add_argument("--corruption-type", default="color_shift", help="Label to tag the manually-known range with")
    parser.add_argument("--lab-plot", default="lab_comparison.png", help="Where to save the LAB channel comparison chart")
    parser.add_argument("--frames-dir", default="frame_comparisons", help="Directory to save side-by-side comparison images")
    parser.add_argument("--sample-frames", type=int, default=4, help="How many frames from the spliced range to save as side-by-side images")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    logger.info("Reading original video: %s", args.original)
    original_frames, fps = read_video_frames(args.original)
    logger.info("Reading reconstructed video: %s", args.reconstructed)
    reconstructed_frames, _ = read_video_frames(args.reconstructed)

    logger.info(
        "Original frames: %d, Reconstructed frames: %d, fps: %.2f",
        len(original_frames), len(reconstructed_frames), fps,
    )

    orig_h, orig_w = original_frames[0].shape[:2]
    recon_h, recon_w = reconstructed_frames[0].shape[:2]
    logger.info("Original resolution: %dx%d, Reconstructed resolution: %dx%d",
                orig_w, orig_h, recon_w, recon_h)

    if (orig_h, orig_w) != (recon_h, recon_w):
        logger.warning(
            "Resolution mismatch! Resizing reconstructed frames from %dx%d to %dx%d "
            "to match the original. This is a common side effect of restoration "
            "models that upscale/pad/crop — worth flagging to whoever runs "
            "SeedVR2/RVRT, since this resize is a quality-affecting step happening "
            "silently here.",
            recon_w, recon_h, orig_w, orig_h,
        )
        reconstructed_frames = [
            cv2.resize(f, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
            for f in reconstructed_frames
        ]

    spliced_frames, start_idx, end_idx = splice_reconstructed_into_original(
        original_frames, reconstructed_frames, args.num_frames, args.seed
    )
    logger.info("Spliced reconstructed frames into indices [%d, %d] of the original.", start_idx, end_idx)

    # We did the splicing ourselves, so we already know the corruption range —
    # build the classifier-shaped dict manually instead of running a real classifier.
    corruption_ranges = [
        {"start_frame": start_idx, "end_frame": end_idx, "type": args.corruption_type}
    ]

    config = CorrectionConfig(
        color_space=ColorSpace.BGR,  # OpenCV decodes as BGR
        histogram_method=HistogramMethod.MOMENT if args.method == "moment" else HistogramMethod.FULL,
        scene_detector_backend=args.backend,
        assumed_fps=fps,
    )
    pipeline = VideoColorCorrectionPipeline(config)
    result = pipeline.run(spliced_frames, corruption_ranges)

    print("\n=== RESULTS ===")
    print(f"Spliced (simulated corrupted) range: frames [{start_idx}, {end_idx}]")
    print(f"Flagged for review (no reference found): {result.flagged_for_review}")
    print(f"Correction log: {result.correction_log}\n")

    print(f"{'idx':>5} | {'original L,A,B':>22} | {'spliced(before) L,A,B':>26} | {'corrected(after) L,A,B':>26}")
    for i in range(max(0, start_idx - 2), min(len(spliced_frames), end_idx + 3)):
        orig_lab = lab_means(original_frames[i])
        before_lab = lab_means(spliced_frames[i])
        after_lab = lab_means(result.frames[i])
        marker = " <-- spliced" if start_idx <= i <= end_idx else ""
        print(
            f"{i:>5} | {orig_lab.round(1)!s:>22} | {before_lab.round(1)!s:>26} | "
            f"{after_lab.round(1)!s:>26}{marker}"
        )

    write_video(args.output, result.frames, fps)
    print(f"\nCorrected video written to: {args.output}")
    print("Open it alongside the original to eyeball whether the spliced range still stands out.")

    plot_lab_over_range(
        original_frames=original_frames,
        before_frames=spliced_frames,
        after_frames=result.frames,
        start_idx=start_idx,
        end_idx=end_idx,
        output_path=args.lab_plot,
    )
    print(f"LAB comparison chart written to: {args.lab_plot}")

    n_samples = min(args.sample_frames, end_idx - start_idx + 1)
    sample_indices = list(np.linspace(start_idx, end_idx, num=n_samples, dtype=int))
    sample_indices = sorted(set(int(i) for i in sample_indices))
    save_side_by_side_frames(
        original_frames=original_frames,
        before_frames=spliced_frames,
        after_frames=result.frames,
        frame_indices=sample_indices,
        output_dir=args.frames_dir,
    )
    print(f"Side-by-side comparison images written to: {args.frames_dir}/")


if __name__ == "__main__":
    main()
