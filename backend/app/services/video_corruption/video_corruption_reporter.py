"""
video_corruption_reporter.py
=============================
VideoCorruptionReporter samples frames from a video, classifies each sampled
frame with a MobileNetV3-style classifier, smooths the raw per-frame
predictions with a majority-vote window (to filter out false positives), and
collapses the result into contiguous "corruption regions".

Example
-------
reporter = VideoCorruptionReporter(
    classifier_path="best_model.pth",
    sample_rate=10,
    thresholds_per_class={"blur": 0.7, "noise": 0.6},
    majority_window_size=5,
    batch_size=32,
)
regions = reporter.classify_video("input.mp4")
# -> [{"start_frame": 100, "end_frame": 150, "class": "blur"}, ...]

Dependencies
------------
pip install torch torchvision pillow opencv-python
"""

from collections import Counter
from typing import Dict, List, Optional

import cv2
import torch
import torch.nn as nn
from PIL import Image
from torchvision import models, transforms
import os

class VideoCorruptionReporter:
    """
    Detects and reports contiguous corrupted regions (e.g. blur, noise) in a
    video using a pretrained frame classifier.

    "no_corrupt" frames/regions are never reported — only actual corruption
    regions are returned by `classify_video`.
    """

    NO_CORRUPT_LABEL = "uncorrupted"
    DEFAULT_THRESHOLD = 0.5

    def __init__(
        self,
        classifier_path: str,
        sample_rate: int,
        thresholds_per_class: Dict[str, float],
        majority_window_size: int,
        batch_size: int,
        device: Optional[str] = None,
    ):
        """
        Parameters
        ----------
        classifier_path : path to the .pth checkpoint (same format expected
            by the original inference.py: contains "cfg" with "num_classes",
            "img_size", and "classes" (an ordered list of class names, where
            list index == model output index), plus "model_state").
            `classes_mapping` (output index -> class name) is derived
            directly from the checkpoint's "classes" list, so it always
            matches the model — no need to pass or hardcode it separately.
        sample_rate : sample one frame every N frames.
        thresholds_per_class : confidence threshold per corruption class
            name (lowercase-insensitive). Classes not listed default to
            DEFAULT_THRESHOLD (0.5). Not applicable to "no_corrupt".
        majority_window_size : size of the centered majority-vote smoothing
            window applied to the per-frame labels. 1 (or less) disables
            smoothing.
        batch_size : number of frames classified per forward pass.
        device : "cuda" / "cpu". Auto-detected if not given.
        """
        self.classifier_path = classifier_path
        self.sample_rate = sample_rate
        self.thresholds_per_class = {k.lower(): v for k, v in thresholds_per_class.items()}
        self.majority_window_size = majority_window_size
        self.batch_size = batch_size

        self.device = torch.device(
            device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        )

        self.model, self.classes_mapping, self.img_size = self._load_model()
        self.transform = transforms.Compose([
            transforms.Resize((self.img_size, self.img_size)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])

    # ─────────────────────────────────────────────
    # Model loading
    # ─────────────────────────────────────────────

    def _build_model(self, num_classes: int) -> nn.Module:
        model = models.mobilenet_v3_large(weights=None)
        in_features = model.classifier[-1].in_features
        model.classifier[-1] = nn.Linear(in_features, num_classes)
        return model

    def _load_model(self):
        """
        Loads the model AND derives the index -> class name mapping straight
        from the checkpoint's cfg["classes"] list, so it's always in sync
        with the model's actual output size (avoids KeyError on argmax
        indices that a hand-written classes_mapping doesn't account for).
        """
        ckpt = torch.load(self.classifier_path, map_location=self.device)
        cfg = ckpt["cfg"]
        model = self._build_model(cfg["num_classes"])
        model.load_state_dict(ckpt["model_state"])
        model.to(self.device).eval()
        img_size = cfg["img_size"]
        classes_mapping = {i: c for i, c in enumerate(cfg["classes"])}
        return model, classes_mapping, img_size

    # ─────────────────────────────────────────────
    # Frame extraction
    # ─────────────────────────────────────────────

    def _extract_frames(self, video_path: str):
        """Yield (frame_idx, PIL.Image) for every `sample_rate`-th frame."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Cannot open video: {video_path}")

        frame_idx = 0
        while True:
            ret, bgr = cap.read()
            if not ret:
                break
            if frame_idx % self.sample_rate == 0:
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                yield frame_idx, Image.fromarray(rgb)
            frame_idx += 1
        cap.release()

    # ─────────────────────────────────────────────
    # Batched inference
    # ─────────────────────────────────────────────

    def _run_inference(self, video_path: str) -> List[dict]:
        """
        Runs the classifier over sampled frames in batches.
        Returns a list of dicts: {"frame_idx", "pred_class", "probs"}
        ordered by increasing frame_idx.
        """
        results = []
        buf_idxs, buf_imgs = [], []

        def flush():
            if not buf_imgs:
                return
            batch = torch.stack([self.transform(img) for img in buf_imgs]).to(self.device)
            with torch.no_grad():
                logits = self.model(batch)
                probs = torch.softmax(logits, dim=1).cpu().numpy()
            for fi, p in zip(buf_idxs, probs):
                pred_class = self.classes_mapping[int(p.argmax())]
                results.append({"frame_idx": fi, "pred_class": pred_class, "probs": p})
            buf_idxs.clear()
            buf_imgs.clear()

        for frame_idx, img in self._extract_frames(video_path):
            buf_idxs.append(frame_idx)
            buf_imgs.append(img)
            if len(buf_imgs) >= self.batch_size:
                flush()
        flush()  # leftover partial batch

        return results

    # ─────────────────────────────────────────────
    # Threshold-based label resolution (raw, per-frame)
    # ─────────────────────────────────────────────

    def _resolve_label(self, frame_result: dict) -> str:
        """
        Decides the *effective* label of a single frame from its raw
        prediction:
        - If the raw predicted class is already "no_corrupt", keep it.
        - If the predicted class is a corruption class, only keep it if its
          confidence clears that class's threshold. Otherwise fall back to
          "no_corrupt" (a low-confidence corruption call is treated as
          classifier noise, not a real corruption).
        """
        cls = frame_result["pred_class"].lower()
        if cls == self.NO_CORRUPT_LABEL:
            return self.NO_CORRUPT_LABEL

        threshold = self.thresholds_per_class.get(cls, self.DEFAULT_THRESHOLD)
        class_idx = next(
            (idx for idx, name in self.classes_mapping.items() if name.lower() == cls),
            None,
        )
        confidence = float(frame_result["probs"][class_idx]) if class_idx is not None else 0.0

        return frame_result["pred_class"] if confidence >= threshold else self.NO_CORRUPT_LABEL

    def _resolve_labels(self, results: List[dict]) -> List[str]:
        """Vectorized wrapper over `_resolve_label` for a full results list."""
        return [self._resolve_label(r) for r in results]

    # ─────────────────────────────────────────────
    # Majority-vote smoothing
    # ─────────────────────────────────────────────

    def _smooth_labels(self, labels: List[str]) -> List[str]:
        """
        For each position i, replaces the label with the majority label
        found within the centered window [i - half, i + half], to filter out
        sporadic false positives/negatives from the classifier.
        A `majority_window_size` of 1 (or less) disables smoothing.
        """
        window = self.majority_window_size
        if window <= 1:
            return list(labels)

        n = len(labels)
        half = window // 2
        smoothed = []
        for i in range(n):
            lo = max(0, i - half)
            hi = min(n, i + half + 1)
            majority_label = Counter(labels[lo:hi]).most_common(1)[0][0]
            smoothed.append(majority_label)
        return smoothed

    # ─────────────────────────────────────────────
    # Region building
    # ─────────────────────────────────────────────

    def _labels_to_regions(self, frame_indices: List[int], labels: List[str]) -> List[dict]:
        """
        Collapses a per-frame label sequence into contiguous regions of the
        same class, skipping "no_corrupt" regions entirely.

        Returns
        -------
        [{"start_frame": int, "end_frame": int, "class": str}, ...]
        `start_frame`/`end_frame` are the first/last *sampled* frame indices
        belonging to that region (inclusive).
        """
        regions = []
        n = len(labels)
        i = 0
        while i < n:
            current_label = labels[i]
            start_idx = i
            while i < n and labels[i] == current_label:
                i += 1
            end_idx = i - 1

            if current_label != self.NO_CORRUPT_LABEL:
                regions.append({
                    "start_frame": frame_indices[start_idx],
                    "end_frame": frame_indices[end_idx],
                    "class": current_label,
                })
        return regions

    # ─────────────────────────────────────────────
    # Public entry point
    # ─────────────────────────────────────────────

    def classify_video(self, video_path: str) -> List[dict]:
        """
        Runs the full pipeline on a video and returns the corrupted regions:

            [{"start_frame": 100, "end_frame": 150, "class": "blur"},
             {"start_frame": 230, "end_frame": 450, "class": "noise"}, ...]

        Pipeline
        --------
        1. `_run_inference`     -> sample frames every `sample_rate` frames
                                    and batch-classify them.
        2. `_resolve_labels`    -> apply per-class confidence thresholds to
                                    get a raw effective label per frame.
        3. `_smooth_labels`     -> majority-vote smoothing over the label
                                    sequence to remove sporadic false
                                    positives.
        4. `_labels_to_regions` -> collapse consecutive equal labels into
                                    regions, dropping "no_corrupt".
        """
        raw_results = self._run_inference(video_path)
        if not raw_results:
            return []

        frame_indices = [r["frame_idx"] for r in raw_results]

        raw_labels = self._resolve_labels(raw_results)
        smoothed_labels = self._smooth_labels(raw_labels)

        return self._labels_to_regions(frame_indices, smoothed_labels)    

if __name__ == "__main__":
    
    #EXAMPLE USAGE
    pth_path = os.getenv("CLASSIFIER_PATH")

    reporter = VideoCorruptionReporter(
        classifier_path=pth_path,
        sample_rate=10,
        thresholds_per_class={"blur": 0.99, "noise": 0.58},
        majority_window_size=25,
        batch_size=32,
        device="cpu"
        )


    report = reporter.classify_video("./output.mp4")

    print(report)

