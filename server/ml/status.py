"""
Cheap, torch-free checks for whether the visual model stack is usable —
used both for the startup log warning (see app/main.py's lifespan) and
the GET /api/ml/status endpoint the frontend uses to show a "train the
model first" banner.

Deliberately avoids importing torch: importing ml.inference itself is safe
(its heavy imports are all deferred inside functions), so checking path
existence here never pays — or requires — the torch import cost just to
answer "is it trained yet?".
"""

import importlib.util
import os

from .classes import CLASSES
from .inference import METADATA_PATH, WEIGHTS_PATH

TRAIN_INSTRUCTIONS = "pip install -r ml/requirements.txt && python -m ml.training.train"


def torch_installed() -> bool:
    return importlib.util.find_spec("torch") is not None


def model_trained() -> bool:
    return os.path.exists(WEIGHTS_PATH) and os.path.exists(METADATA_PATH)


def get_status() -> dict:
    return {
        "torchInstalled": torch_installed(),
        "trained": model_trained(),
        "classes": CLASSES,
        "instructions": TRAIN_INSTRUCTIONS,
    }


def log_startup_status(logger) -> None:
    """
    Called once at server startup (app/main.py's lifespan) so this is
    always visible in the logs regardless of whether anyone ever submits
    an image report — the previous version of this check only fired
    lazily, the first time an image was actually processed, which meant
    it was easy to never see it at all.
    """
    if not torch_installed():
        logger.warning(
            "ML stack not installed — visual similarity & condition classification "
            "disabled. To enable: %s",
            TRAIN_INSTRUCTIONS,
        )
        return

    if not model_trained():
        logger.warning(
            "ML stack installed but no trained model found in ml/checkpoints/ — visual "
            "similarity & condition classification disabled until you train one. Run: "
            "python -m ml.training.train"
        )
        return

    logger.info("trained visual model found (classes=%s) — ready", CLASSES)
