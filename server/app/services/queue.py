"""
Rill Signal — classification + visual aggregation queue (hackathon MVP).

Reports are marked "queued" on creation by Rill Report; this worker polls
MongoDB and moves them through processing. Three independent jobs happen
here:

1. Severity classification — currently a PLACEHOLDER (random tier). This is
   the seam where the real Nemotron + LangGraph classification call plugs
   in later.

2. Visual embedding + spatial-temporal aggregation — a REAL, working
   pipeline (see ml/inference.py and ml/aggregation.py), run only when a
   report has an image.

3. Condition classification (clear/murky/flooded/whitewater/algae/debris)
   — also real, via nearest-centroid against the trained model's class
   centroids (see ml/inference.py's classify_condition).

Both 2 and 3 degrade gracefully: if torch/torchvision aren't installed, or
no trained model exists yet, these steps are skipped with a warning and
everything else (severity classification, the report itself) still works.
"""

import asyncio
import random

from ..db import get_db
from ..logging_config import get_logger

logger = get_logger("rill.signal")

POLL_INTERVAL_SECONDS = 3
FAKE_TIERS = ["green", "watch", "caution", "emergency"]


async def _run_visual_pipeline(db, report: dict) -> tuple[list[dict], dict | None]:
    """
    Returns (visual_matches, condition):
      visual_matches: list of {segmentCode, similarity} for the most
        visually similar OTHER locations, or [] if unavailable.
      condition: {label, similarity} — the predicted condition class, or
        None if unavailable.
    Never raises — failures here must not affect severity classification.
    """
    image_path = report.get("imagePath")
    if not image_path:
        return [], None

    try:
        # Imported lazily so the queue worker (and the whole app) starts
        # fine even if the ml/ dependencies aren't installed.
        import os

        from ml.aggregation import find_similar_locations, update_location_profile
        from ml.inference import classify_condition, extract_embedding

        from ..config import UPLOAD_DIR

        image_bytes = None
        if "/api/reports/images/" in image_path:
            from bson import ObjectId
            from motor.motor_asyncio import AsyncIOMotorGridFSBucket

            file_id_str = image_path.split("/")[-1]
            fs = AsyncIOMotorGridFSBucket(db)
            grid_out = await fs.open_download_stream(ObjectId(file_id_str))
            image_bytes = await grid_out.read()
        else:
            filename = os.path.basename(image_path)
            full_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.exists(full_path):
                with open(full_path, "rb") as f:
                    image_bytes = f.read()

        if not image_bytes:
            return [], None

        embedding = extract_embedding(image_bytes)
        if embedding is None:
            return [], None  # ml/inference.py already logged why

        segment_code = report["segmentCode"]
        await update_location_profile(db, segment_code, embedding)
        matches = await find_similar_locations(db, embedding, exclude_segment=segment_code)
        condition = classify_condition(embedding)
        return matches, condition
    except Exception:
        logger.warning("visual pipeline failed for report %s", report["_id"], exc_info=True)
        return [], None


async def process_report(db, report: dict) -> None:
    logger.info(
        "processing report %s (segment=%s)", report["_id"], report.get("segmentCode")
    )
    await db.reports.update_one({"_id": report["_id"]}, {"$set": {"status": "processing"}})

    # --- Placeholder severity classification logic ---
    # Replace this block with a call to the real classification service.
    # Keeping it deterministic-but-varied here so the dashboard has
    # something meaningful to show during early development.
    tier = random.choice(FAKE_TIERS)
    confidence = round(random.uniform(0.5, 1.0), 2)

    visual_matches, condition = await _run_visual_pipeline(db, report)

    await db.reports.update_one(
        {"_id": report["_id"]},
        {
            "$set": {
                "status": "classified",
                "classification": {
                    "tier": tier,
                    "confidence": confidence,
                    "reasoning": (
                        f"[placeholder] auto-assigned for demo purposes based on "
                        f"segment {report.get('segmentCode')}"
                    ),
                },
                "visualMatches": visual_matches,
                "condition": condition,
            }
        },
    )
    logger.info(
        "classified report %s as %s (confidence=%.2f, condition=%s, visual matches=%s)",
        report["_id"],
        tier,
        confidence,
        condition["label"] if condition else None,
        len(visual_matches),
    )


async def _tick(db) -> None:
    report = await db.reports.find_one({"status": "queued"}, sort=[("createdAt", 1)])
    if not report:
        return

    try:
        await process_report(db, report)
    except Exception:
        logger.error("failed to process report %s", report["_id"], exc_info=True)
        await db.reports.update_one({"_id": report["_id"]}, {"$set": {"status": "failed"}})


async def run_queue_worker() -> None:
    db = get_db()
    logger.info("worker started (polling every %ss)", POLL_INTERVAL_SECONDS)
    while True:
        try:
            await _tick(db)
        except Exception:
            # Defensive: a bug here must never silently kill the worker —
            # log it and keep polling rather than let the background task die.
            logger.error("unexpected error in queue tick", exc_info=True)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
