"""
Rill's live visual inference — loads the TRAINED StreamEmbeddingNet
checkpoint (see ml/training/train.py) and uses it to turn an uploaded
photo into (a) a 128-dim embedding for cross-location similarity, and
(b) a predicted condition class (clear/murky/flooded/whitewater/algae/
debris) via nearest-centroid classification against the class centroids
saved alongside the model.

Until ml/training/train.py has been run at least once, there's no
checkpoint to load, and every function here returns None (with a warning
explaining why) instead of falling back to an untrained model — see
ml/status.py for the proactive startup-time version of this same check.

Loaded via safetensors, not pickle — see ml/requirements.txt for why.

Caching note: the loaded model is cached by the checkpoint files' mtime,
not just "loaded once" — so if a report comes in before you've trained a
model, and you train one afterward, the very next report picks up the new
checkpoint automatically. No server restart needed.
"""

import io
import os
from typing import Optional

from app.logging_config import get_logger

from .architecture import build_model, get_transform

logger = get_logger("rill.ml.inference")

CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), "checkpoints")
WEIGHTS_PATH = os.path.join(CHECKPOINT_DIR, "stream_embedding.safetensors")
METADATA_PATH = os.path.join(CHECKPOINT_DIR, "stream_embedding.json")

_cached_bundle: Optional[dict] = None
_cached_mtime: Optional[float] = None
_warned_missing_torch = False
_warned_missing_checkpoint = False


def _checkpoint_exists() -> bool:
    return os.path.exists(WEIGHTS_PATH) and os.path.exists(METADATA_PATH)


def _checkpoint_mtime() -> float:
    return max(os.path.getmtime(WEIGHTS_PATH), os.path.getmtime(METADATA_PATH))


def _load_model() -> Optional[dict]:
    global _cached_bundle, _cached_mtime, _warned_missing_torch, _warned_missing_checkpoint

    try:
        import torch
    except ImportError:
        if not _warned_missing_torch:
            logger.warning(
                "torch/torchvision not installed — visual similarity and condition "
                "classification are disabled. Install with: pip install -r ml/requirements.txt"
            )
            _warned_missing_torch = True
        return None

    if not _checkpoint_exists():
        if not _warned_missing_checkpoint:
            logger.warning(
                "no trained model found in %s — run `python -m ml.training.train` first. "
                "Visual similarity and condition classification are disabled until then.",
                CHECKPOINT_DIR,
            )
            _warned_missing_checkpoint = True
        return None
    _warned_missing_checkpoint = False  # in case it existed, was removed, now exists again

    mtime = _checkpoint_mtime()
    if _cached_bundle is not None and _cached_mtime == mtime:
        return _cached_bundle  # unchanged since last load — reuse it

    try:
        import json

        from safetensors.torch import load_file

        with open(METADATA_PATH) as f:
            metadata = json.load(f)

        tensors = load_file(WEIGHTS_PATH)
        model_state = {k[len("model."):]: v for k, v in tensors.items() if k.startswith("model.")}
        centroids = {k[len("centroid."):]: v for k, v in tensors.items() if k.startswith("centroid.")}

        model = build_model(embedding_dim=metadata["embedding_dim"], pretrained=False)
        model.load_state_dict(model_state)
        model.eval()

        _cached_bundle = {
            "model": model,
            "preprocess": get_transform(),
            "torch": torch,
            "centroids": centroids,
            "classes": metadata["classes"],
        }
        _cached_mtime = mtime
        logger.info(
            "loaded trained visual model (classes=%s, centroids=%s)",
            metadata["classes"],
            list(centroids.keys()),
        )
        return _cached_bundle
    except Exception:
        logger.warning("failed to load trained model checkpoint", exc_info=True)
        return None


def _embed_image(image_bytes: bytes, bundle: dict):
    from PIL import Image

    torch = bundle["torch"]
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    tensor = bundle["preprocess"](image).unsqueeze(0)

    with torch.no_grad():
        embedding = bundle["model"](tensor)  # already L2-normalized, shape (1, EMBEDDING_DIM)
    return embedding.squeeze(0)


def extract_embedding(image_bytes: bytes) -> Optional[list[float]]:
    """
    Returns an L2-normalized embedding for the given image as a plain
    list[float], or None if no trained model is available yet / the image
    can't be decoded.
    """
    bundle = _load_model()
    if bundle is None:
        return None
    try:
        return _embed_image(image_bytes, bundle).tolist()
    except Exception:
        logger.warning("failed to extract embedding for an uploaded image", exc_info=True)
        return None


def classify_condition(embedding: list[float]) -> Optional[dict]:
    """
    Labels an embedding against ALL 6 trained condition classes
    (clear/murky/flooded/whitewater/algae/debris) via cosine similarity to
    each class's centroid — falls straight out of the triplet-trained
    embedding space, no separate classifier head needed.

    Returns the full ranked breakdown, not just the winner:
    {"label": str, "similarity": float, "scores": [{"label": str, "similarity": float}, ...]}
    (scores sorted descending, "label"/"similarity" at the top level mirror
    scores[0] for convenient access), or None if no trained model / no
    centroids are available.

    Why the full breakdown, not just the top label: a confident call
    (0.95 vs 0.20) and a close call (0.61 vs 0.58) are very different
    signals even when they produce the same winning label — that margin is
    exactly what a downstream reasoning step (or a human moderator) would
    need to decide how much to trust this classification, not just what it
    said.
    """
    bundle = _load_model()
    if bundle is None or not bundle["centroids"]:
        return None

    try:
        torch = bundle["torch"]
        emb_tensor = torch.tensor(embedding, dtype=torch.float32)

        scores = []
        for label, centroid in bundle["centroids"].items():
            similarity = torch.nn.functional.cosine_similarity(
                emb_tensor.unsqueeze(0), centroid.unsqueeze(0)
            ).item()
            scores.append({"label": label, "similarity": round(similarity, 4)})

        scores.sort(key=lambda s: s["similarity"], reverse=True)
        best = scores[0]

        return {"label": best["label"], "similarity": best["similarity"], "scores": scores}
    except Exception:
        logger.warning("failed to classify condition for an embedding", exc_info=True)
        return None
