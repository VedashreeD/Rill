"""
A procedurally-generated, labeled dataset of synthetic "stream condition"
images — used to train the visual similarity model since no real labeled
stream photos exist for this project. Every image is generated (not a
photo), consistent with the rest of Rill's fictional-world approach.

Six classes, each with a distinct base color and texture pattern, plus
per-sample random jitter so images within a class vary while staying
distinguishable from other classes — exactly the property triplet loss
needs (anchor/positive close, anchor/negative far).

Honest limitation: these classes are hand-designed to be visually
separable by construction. This proves the training pipeline works
end-to-end; it says nothing about how well the resulting embeddings would
generalize to real stream photography, which would need real labeled data.
"""

import os
import random
from typing import Optional

import numpy as np
from PIL import Image
from torch.utils.data import Dataset

from ml.architecture import get_transform
from ml.classes import CLASSES

_BASE_COLOR = {
    "clear": (80, 150, 160),
    "murky": (120, 100, 60),
    "flooded": (90, 85, 80),
    "whitewater": (150, 170, 175),
    "algae": (90, 140, 70),
    "debris": (110, 95, 75),
}

_NOISE_LEVEL = {
    "clear": 6,
    "murky": 16,
    "flooded": 20,
    "whitewater": 28,
    "algae": 18,
    "debris": 22,
}


def _add_streaks(arr: np.ndarray, rng: np.random.RandomState, count: int, color, alpha: float) -> None:
    """Horizontal-ish wavy streaks — used for whitewater / flood turbulence."""
    h, w, _ = arr.shape
    for _ in range(count):
        y0 = rng.randint(0, h)
        thickness = rng.randint(1, 3)
        amplitude = rng.randint(2, 8)
        phase = rng.uniform(0, 6.28)
        for x in range(0, w, 2):
            y = int(y0 + amplitude * np.sin(x / 12.0 + phase))
            if 0 <= y < h:
                y_end = min(h, y + thickness)
                arr[y:y_end, x] = (1 - alpha) * arr[y:y_end, x] + alpha * np.array(color)


def _add_blobs(arr: np.ndarray, rng: np.random.RandomState, count: int, color, alpha: float) -> None:
    """Irregular round patches — used for algae blooms / floating debris."""
    h, w, _ = arr.shape
    yy, xx = np.mgrid[0:h, 0:w]
    for _ in range(count):
        cy, cx = rng.randint(0, h), rng.randint(0, w)
        radius = rng.randint(8, 22)
        mask = (yy - cy) ** 2 + (xx - cx) ** 2 <= radius**2
        arr[mask] = (1 - alpha) * arr[mask] + alpha * np.array(color)


class SyntheticStreamDataset(Dataset):
    def __init__(
        self,
        samples_per_class: int = 150,
        seed: int = 0,
        save_dir: Optional[str] = None,
    ):
        """
        save_dir: if set, every generated image is saved to
        <save_dir>/<class_name>/<sample_idx>.png the first time it's
        generated — letting you actually look at exactly what the model
        is training on, not just trust that the generation code does what
        its docstring says. Deterministic given the same seed, so this
        reflects precisely the images used, not a separate approximate
        preview.
        """
        self.samples_per_class = samples_per_class
        self.index = [
            (class_idx, sample_idx)
            for class_idx in range(len(CLASSES))
            for sample_idx in range(samples_per_class)
        ]
        self.base_seed = seed
        self.transform = get_transform()
        self.save_dir = save_dir

        if self.save_dir:
            for class_name in CLASSES:
                os.makedirs(os.path.join(self.save_dir, class_name), exist_ok=True)

    def __len__(self) -> int:
        return len(self.index)

    def __getitem__(self, idx: int):
        class_idx, sample_idx = self.index[idx]
        class_name = CLASSES[class_idx]
        image = self._generate_image(class_name, seed=self.base_seed * 100_000 + idx)

        if self.save_dir:
            path = os.path.join(self.save_dir, class_name, f"{sample_idx:04d}.png")
            if not os.path.exists(path):
                image.save(path)

        tensor = self.transform(image)
        return tensor, class_idx

    def _generate_image(self, class_name: str, seed: int) -> Image.Image:
        rng = np.random.RandomState(seed)
        py_rng = random.Random(seed)

        size = 128
        base = _BASE_COLOR[class_name]
        jitter = tuple(int(np.clip(c + py_rng.randint(-15, 15), 0, 255)) for c in base)

        arr = np.full((size, size, 3), jitter, dtype=np.float64)
        noise = rng.normal(0, _NOISE_LEVEL[class_name], arr.shape)
        arr = arr + noise

        if class_name == "whitewater":
            _add_streaks(arr, rng, count=py_rng.randint(6, 10), color=(230, 235, 235), alpha=0.5)
        elif class_name == "flooded":
            _add_streaks(arr, rng, count=py_rng.randint(3, 6), color=(60, 55, 50), alpha=0.4)
        elif class_name == "algae":
            _add_blobs(arr, rng, count=py_rng.randint(4, 8), color=(60, 110, 40), alpha=0.6)
        elif class_name == "debris":
            _add_blobs(arr, rng, count=py_rng.randint(5, 9), color=(70, 55, 40), alpha=0.55)

        arr = np.clip(arr, 0, 255).astype(np.uint8)
        return Image.fromarray(arr, mode="RGB")
