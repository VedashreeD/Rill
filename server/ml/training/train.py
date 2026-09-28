"""
Trains Rill's visual model with triplet loss on the synthetic stream-
condition dataset, and saves it in a format ml/inference.py can load —
safetensors + a small JSON metadata sidecar, deliberately NOT pickle
(torch.save's default format is pickle-based under the hood despite the
.pt extension — safetensors is a standard, secure, non-pickle alternative
used by Hugging Face and others for exactly this reason).

Two things get trained/computed and saved together:
  1. The embedding model itself (triplet loss — see further down for why).
  2. Per-class centroid embeddings, computed by averaging this model's
     embeddings over each class after training. These are what let
     ml/inference.py's classify_condition() label a NEW image as
     clear/murky/flooded/whitewater/algae/debris — via nearest-centroid
     in embedding space, not a separately trained classifier head. This
     falls straight out of a triplet-trained embedding space (same-class
     images cluster near their centroid by construction of the loss), so
     it needs no extra training step.

Every image the dataset generates during this run is also saved to
ml/training/data/<class_name>/ — open them directly if you want to see
exactly what the model trained on, rather than trusting the generation
code's docstring.

Run from server/ (inside the venv, after `pip install -r ml/requirements.txt`).
Both of these work — direct execution and module execution:
    python ml/training/train.py
    python -m ml.training.train
    python -m ml.training.train --epochs 8 --samples-per-class 200

Why triplet loss at all: a plain classifier learns to separate the 6
synthetic classes, but doesn't directly optimize for "these two images are
visually similar" the way an embedding space needs to for Rill Overview's
"visually resembles" feature. Triplet loss does exactly that — for an
(anchor, positive, negative) triple, it pulls the anchor and positive (same
class) closer together and pushes the anchor and negative (different
class) further apart, in embedding space.
"""

import os
import sys

# Allows running this script directly (`python ml/training/train.py`), not
# just via `python -m ml.training.train`. Direct execution only puts this
# script's OWN folder on sys.path, not the server/ root two levels up — so
# without this, `from ml.architecture import ...` below fails with
# "ModuleNotFoundError: No module named 'ml'". This must run before any
# `ml.*` import.
_SERVER_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _SERVER_ROOT not in sys.path:
    sys.path.insert(0, _SERVER_ROOT)

try:
    import certifi
    import ssl
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())
except ImportError:
    pass

import argparse
import json
import random
import time
from datetime import datetime, timezone

from ml.architecture import EMBEDDING_DIM, build_model
from ml.classes import CLASSES
from ml.training.dataset import SyntheticStreamDataset

CHECKPOINT_DIR = os.path.join(os.path.dirname(__file__), "..", "checkpoints")
WEIGHTS_PATH = os.path.join(CHECKPOINT_DIR, "stream_embedding.safetensors")
METADATA_PATH = os.path.join(CHECKPOINT_DIR, "stream_embedding.json")

# Every training run saves exactly the images it used here, one folder per
# class — see SyntheticStreamDataset's save_dir for why this reflects the
# real dataset, not an approximate preview of it.
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def mine_triplets(images, labels):
    """
    For each sample in the batch (as an anchor), find another sample in the
    SAME batch with the same label (positive) and one with a different
    label (negative). Simple in-batch random mining — not hardest-negative
    mining, which would likely train faster/better but adds complexity this
    demo-scope pipeline doesn't need. Skips samples with no valid
    positive/negative in the batch (rare, given 6 classes and batch >= ~16).
    """
    import torch

    labels_list = labels.tolist()
    anchors, positives, negatives = [], [], []

    for i, anchor_label in enumerate(labels_list):
        pos_candidates = [j for j, l in enumerate(labels_list) if j != i and l == anchor_label]
        neg_candidates = [j for j, l in enumerate(labels_list) if l != anchor_label]
        if not pos_candidates or not neg_candidates:
            continue
        p = random.choice(pos_candidates)
        n = random.choice(neg_candidates)
        anchors.append(images[i])
        positives.append(images[p])
        negatives.append(images[n])

    if not anchors:
        return None, None, None
    return torch.stack(anchors), torch.stack(positives), torch.stack(negatives)


def compute_class_centroids(model, dataset):
    """
    Runs the (now-trained) model over the whole dataset in eval mode and
    averages the embeddings per class, giving one centroid per class —
    the reference point classify_condition() compares new images against.
    """
    import torch
    from torch.utils.data import DataLoader

    model.eval()
    sums = {c: None for c in CLASSES}
    counts = {c: 0 for c in CLASSES}

    with torch.no_grad():
        for images, labels in DataLoader(dataset, batch_size=64, shuffle=False):
            embeddings = model(images)
            for embedding, label_idx in zip(embeddings, labels.tolist()):
                class_name = CLASSES[label_idx]
                sums[class_name] = embedding.clone() if sums[class_name] is None else sums[class_name] + embedding
                counts[class_name] += 1

    centroids = {}
    for class_name in CLASSES:
        if counts[class_name] == 0:
            continue
        centroid = sums[class_name] / counts[class_name]
        centroids[class_name] = torch.nn.functional.normalize(centroid, dim=0)
    return centroids


def main(epochs: int, batch_size: int, samples_per_class: int, lr: float) -> None:
    import torch
    from safetensors.torch import save_file
    from torch import nn, optim
    from torch.utils.data import DataLoader

    print(f"[train] building synthetic dataset: {samples_per_class} samples x {len(CLASSES)} classes")
    dataset = SyntheticStreamDataset(samples_per_class=samples_per_class, save_dir=DATA_DIR)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, drop_last=True)

    print("[train] building model (ImageNet-pretrained backbone — needs internet on first run)")
    model = build_model(embedding_dim=EMBEDDING_DIM, pretrained=True)
    model.train()

    criterion = nn.TripletMarginLoss(margin=0.3)
    optimizer = optim.Adam(model.parameters(), lr=lr)

    for epoch in range(1, epochs + 1):
        start = time.time()
        total_loss = 0.0
        n_batches = 0

        for images, labels in loader:
            anchors, positives, negatives = mine_triplets(images, labels)
            if anchors is None:
                continue

            embed_a = model(anchors)
            embed_p = model(positives)
            embed_n = model(negatives)
            loss = criterion(embed_a, embed_p, embed_n)

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()
            n_batches += 1

        avg_loss = total_loss / max(n_batches, 1)
        elapsed = time.time() - start
        print(f"[train] epoch {epoch}/{epochs} — avg triplet loss: {avg_loss:.4f} ({elapsed:.1f}s)")

    print("[train] computing per-class centroids for condition classification…")
    centroids = compute_class_centroids(model, dataset)

    os.makedirs(CHECKPOINT_DIR, exist_ok=True)

    tensors = {f"model.{k}": v.clone().contiguous() for k, v in model.state_dict().items()}
    for class_name, centroid in centroids.items():
        tensors[f"centroid.{class_name}"] = centroid.contiguous()
    save_file(tensors, WEIGHTS_PATH)

    metadata = {
        "embedding_dim": EMBEDDING_DIM,
        "classes": CLASSES,
        "classes_with_centroids": list(centroids.keys()),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "epochs": epochs,
        "samples_per_class": samples_per_class,
    }
    with open(METADATA_PATH, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\n[train] saved weights to {os.path.abspath(WEIGHTS_PATH)}")
    print(f"[train] saved metadata to {os.path.abspath(METADATA_PATH)}")
    print(f"[train] saved the {len(dataset)} training images to {os.path.abspath(DATA_DIR)}"
          " (one folder per class) — open them directly to see exactly what was trained on.")
    print("[train] Rill Signal will pick this up automatically on the next report — no restart"
          " needed (the loader checks the checkpoint files themselves, not a one-time flag).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--samples-per-class", type=int, default=150)
    parser.add_argument("--lr", type=float, default=1e-4)
    args = parser.parse_args()

    main(
        epochs=args.epochs,
        batch_size=args.batch_size,
        samples_per_class=args.samples_per_class,
        lr=args.lr,
    )
