# video_color_correction

Post-hoc color/intensity consistency correction for reconstructed video frames
(e.g. output from SeedVR2 / RVRT), given a corruption classifier's output.

## Why this exists
Independent per-frame/per-clip reconstruction models can introduce color,
saturation, or brightness drift relative to the surrounding clean frames.
This module corrects that **after generation**, without touching the
reconstruction model at all: it detects shot/scene boundaries, finds clean
reference frames within the same shot, and matches the reconstructed frame's
LAB-space statistics to those references.

## Install
```bash
pip install -r requirements.txt
```

## Quick start
```python
from video_color_correction import (
    VideoColorCorrectionPipeline, CorrectionConfig, ColorSpace, HistogramMethod
)

# frames: list[np.ndarray], full video, in order, corrupted frames already
#         replaced by the reconstruction model's output.
# corruption_output: whatever the classifier returns, e.g.
#   [{"start_frame": 40, "end_frame": 45, "type": "low_light"}, ...]

config = CorrectionConfig(
    color_space=ColorSpace.BGR,           # set to ColorSpace.RGB if your frames use RGB order
    histogram_method=HistogramMethod.MOMENT,  # or HistogramMethod.FULL for higher precision
    scene_detector_backend="pyscenedetect",   # or "histogram_diff" (no extra dependency)
    reference_window=3,
)

pipeline = VideoColorCorrectionPipeline(config)
result = pipeline.run(frames, corruption_output)

corrected_frames = result.frames             # same length/order as input
result.flagged_for_review                    # frame indices with no clean reference found
result.correction_log                        # per-frame debug info (num refs used, corruption type)
```

### Optional: region masks
If a spatial corruption mask happens to be available for some frames (e.g.
from the reconstruction model's inpainting mask), pass it in — only that
region will be corrected and used for reference statistics, leaving the rest
of the frame untouched:
```python
result = pipeline.run(frames, corruption_output, region_masks={40: mask_hw_bool, ...})
```
If you don't have masks (frame-level classifier only), omit `region_masks`
entirely and the whole frame is corrected/compared.

## Module layout
```
video_color_correction/
├── config.py                # ColorSpace, HistogramMethod, CorrectionConfig
├── corruption_range.py       # CorruptionRange — wraps the classifier's raw dicts
├── color_utils.py            # BGR/RGB <-> LAB conversion, single source of truth
├── scene_detection.py         # SceneDetector interface + PySceneDetect / histogram-diff backends
├── reference_selection.py    # ReferenceFrameSelector — picks clean, same-shot references
├── color_correction.py       # ColorCorrector — LAB matching (moment or full-histogram strategy)
└── orchestrator.py           # VideoColorCorrectionPipeline — the public entry point
```

Every module is independently swappable/testable:
- Change `CorrectionConfig.color_space` if a teammate's frames turn out to
  be in a different channel order — no other file needs to change.
- Change `CorrectionConfig.scene_detector_backend` to switch between
  PySceneDetect and the dependency-free histogram-diff fallback.
- Change `CorrectionConfig.histogram_method` to switch between fast
  moment-matching and precise full-histogram matching.

## Design notes
- **Frames are passed as in-memory numpy arrays, not video file paths.**
  Re-decoding a video at each pipeline stage risks frame-count mismatches
  and re-introduces compression artifacts between tools. Decode once,
  pass arrays.
- **Corrupted frames never influence scene-cut detection.** Visible
  corruption or reconstruction drift can look like a false cut, so cuts are
  only computed from clean frames; corrupted frames are then slotted into
  whichever shot their original index falls into.
- **Only same-shot frames are ever used as color references** — comparing
  across a scene cut would inject the wrong lighting/color profile.
