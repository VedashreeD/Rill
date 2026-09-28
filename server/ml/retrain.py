"""
Background retraining pipeline for Rill's visual embedding model.
Adapts class centroids based on real user-submitted tags from incident reports.
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, List

import torch
from bson import ObjectId
from safetensors.torch import load_file, save_file

from app.logging_config import get_logger

from .classes import CLASSES
from .inference import (
    CHECKPOINT_DIR,
    METADATA_PATH,
    WEIGHTS_PATH,
    extract_embedding,
)

logger = get_logger("rill.ml.retrain")


async def retrain_from_user_tags(db) -> dict:
    """
    Finds all reports with `userTag` in MongoDB, fetches their images,
    computes embeddings, updates the class centroids, saves the updated
    safetensors checkpoint, and refreshes condition scores for existing reports.
    """
    if not os.path.exists(WEIGHTS_PATH) or not os.path.exists(METADATA_PATH):
        logger.warning("cannot retrain: base model checkpoint does not exist yet")
        return {"status": "skipped", "reason": "no_checkpoint"}

    cursor = db.reports.find({"userTag": {"$in": CLASSES}, "imagePath": {"$ne": None}})
    tagged_reports = [r async for r in cursor]

    if not tagged_reports:
        logger.info("no user-tagged reports found to retrain on")
        return {"status": "skipped", "reason": "no_tagged_reports"}

    logger.info("starting background retraining with %d user-tagged reports…", len(tagged_reports))

    try:
        from motor.motor_asyncio import AsyncIOMotorGridFSBucket
        fs = AsyncIOMotorGridFSBucket(db)

        # 1. Collect embeddings grouped by user tag
        tagged_embeddings: Dict[str, List[torch.Tensor]] = {c: [] for c in CLASSES}
        report_embeddings: Dict[str, list[float]] = {}

        for report in tagged_reports:
            image_path = report.get("imagePath", "")
            image_bytes = None

            if "/api/reports/images/" in image_path:
                file_id_str = image_path.split("/")[-1]
                try:
                    grid_out = await fs.open_download_stream(ObjectId(file_id_str))
                    image_bytes = await grid_out.read()
                except Exception:
                    logger.warning("could not read image %s from GridFS", file_id_str)
                    continue
            else:
                from app.config import UPLOAD_DIR
                filename = os.path.basename(image_path)
                full_path = os.path.join(UPLOAD_DIR, filename)
                if os.path.exists(full_path):
                    with open(full_path, "rb") as f:
                        image_bytes = f.read()

            if not image_bytes:
                continue

            emb = extract_embedding(image_bytes)
            if emb is not None:
                tag = report["userTag"]
                tagged_embeddings[tag].append(torch.tensor(emb, dtype=torch.float32))
                report_embeddings[str(report["_id"])] = emb

        total_samples = sum(len(v) for v in tagged_embeddings.values())
        if total_samples == 0:
            logger.warning("could not extract embeddings for any tagged reports")
            return {"status": "failed", "reason": "no_valid_embeddings"}

        # 2. Load current model state & centroids
        tensors = load_file(WEIGHTS_PATH)
        centroids = {k[len("centroid."):]: v for k, v in tensors.items() if k.startswith("centroid.")}
        model_state = {k[len("model."):]: v for k, v in tensors.items() if k.startswith("model.")}

        with open(METADATA_PATH) as f:
            metadata = json.load(f)

        # 3. Update centroids with user tags
        # User tags represent real photos, so we weight them heavily relative to the synthetic baseline
        # Formula: c_new = normalize(c_base + sum(user_embeddings * weight))
        USER_WEIGHT = 3.0  # Gives real user feedback substantial pull towards true water photography

        updated_classes = []
        for class_name, user_embs in tagged_embeddings.items():
            if not user_embs:
                continue
            base_centroid = centroids.get(class_name)
            user_stack = torch.stack(user_embs)
            user_mean = torch.mean(user_stack, dim=0)

            if base_centroid is not None:
                # Blend synthetic baseline with real-world feedback
                combined = base_centroid + USER_WEIGHT * user_mean * len(user_embs)
            else:
                combined = user_mean

            centroids[class_name] = torch.nn.functional.normalize(combined, dim=0)
            updated_classes.append(class_name)

        # 4. Save updated checkpoint
        updated_tensors = {f"model.{k}": v.clone().contiguous() for k, v in model_state.items()}
        for class_name, centroid in centroids.items():
            updated_tensors[f"centroid.{class_name}"] = centroid.contiguous()

        save_file(updated_tensors, WEIGHTS_PATH)

        metadata["last_retrained_at"] = datetime.now(timezone.utc).isoformat()
        metadata["user_feedback_count"] = total_samples
        metadata["user_updated_classes"] = updated_classes

        with open(METADATA_PATH, "w") as f:
            json.dump(metadata, f, indent=2)

        # 5. Re-evaluate condition scores on reports in MongoDB
        # This updates the reports in place so the UI immediately shows the improved classification!
        all_reports_cursor = db.reports.find({"imagePath": {"$ne": None}})
        reclassified_count = 0
        async for r in all_reports_cursor:
            r_id = str(r["_id"])
            emb = report_embeddings.get(r_id)
            if not emb:
                image_path = r.get("imagePath", "")
                img_bytes = None
                if "/api/reports/images/" in image_path:
                    try:
                        g_out = await fs.open_download_stream(ObjectId(image_path.split("/")[-1]))
                        img_bytes = await g_out.read()
                    except Exception:
                        pass
                if img_bytes:
                    emb = extract_embedding(img_bytes)

            if emb:
                scores = []
                emb_t = torch.tensor(emb, dtype=torch.float32)
                for label, centroid in centroids.items():
                    sim = torch.nn.functional.cosine_similarity(
                        emb_t.unsqueeze(0), centroid.unsqueeze(0)
                    ).item()
                    scores.append({"label": label, "similarity": round(sim, 4)})
                scores.sort(key=lambda s: s["similarity"], reverse=True)
                new_condition = {
                    "label": scores[0]["label"],
                    "similarity": scores[0]["similarity"],
                    "scores": scores,
                }
                await db.reports.update_one(
                    {"_id": r["_id"]},
                    {"$set": {"condition": new_condition}},
                )
                reclassified_count += 1

        logger.info(
            "retraining complete: adapted %d centroids (%s) with %d samples; reclassified %d reports",
            len(updated_classes),
            updated_classes,
            total_samples,
            reclassified_count,
        )

        return {
            "status": "success",
            "samples": total_samples,
            "updatedClasses": updated_classes,
            "reclassifiedReports": reclassified_count,
        }

    except Exception:
        logger.error("background retraining failed", exc_info=True)
        return {"status": "error"}
