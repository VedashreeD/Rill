"""
Spatial-temporal visual aggregation for Rill.

"Spatial": each of the 10 world locations (see app/world.py) gets its own
running visual profile — a single centroid embedding representing "what
images from this place tend to look like."

"Temporal": each new image updates its location's centroid via an
exponential moving average (EMA), so recent images influence the profile
more than older ones — the profile drifts with the place's visual history
instead of being a static one-time snapshot. This is a standard, legitimate
technique for online (streaming) centroid estimation — not a learned
temporal model (no ConvLSTM / 3D-CNN here), stated plainly so the scope is
clear.

Similarity across locations (used to answer "which place does this image
visually resemble most") is plain cosine similarity between an image's
embedding and every location's current centroid.

Profiles are persisted in the `location_profiles` collection, one document
per segment code: { segmentCode, embedding: [128 floats], sampleCount, updatedAt }
"""

from datetime import datetime, timezone
from typing import Optional

from app.logging_config import get_logger

logger = get_logger("rill.ml.aggregation")

EMA_ALPHA = 0.3  # weight given to each new image; higher = faster drift


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _normalize(vec: list[float]) -> list[float]:
    norm = sum(x * x for x in vec) ** 0.5
    if norm == 0:
        return vec
    return [x / norm for x in vec]


async def update_location_profile(db, segment_code: str, embedding: list[float]) -> None:
    """
    Folds a new image's embedding into its location's running centroid
    (spatial = keyed by segment_code, temporal = EMA-weighted by recency).
    """
    existing = await db.location_profiles.find_one({"segmentCode": segment_code})

    if existing is None:
        new_centroid = embedding
        sample_count = 1
    else:
        old_centroid = existing["embedding"]
        new_centroid = _normalize(
            [
                EMA_ALPHA * new + (1 - EMA_ALPHA) * old
                for new, old in zip(embedding, old_centroid)
            ]
        )
        sample_count = existing.get("sampleCount", 0) + 1

    await db.location_profiles.update_one(
        {"segmentCode": segment_code},
        {
            "$set": {
                "segmentCode": segment_code,
                "embedding": new_centroid,
                "sampleCount": sample_count,
                "updatedAt": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )
    logger.info(
        "updated visual profile: segment=%s sampleCount=%s", segment_code, sample_count
    )


async def find_similar_locations(
    db, embedding: list[float], exclude_segment: Optional[str] = None, top_n: int = 3
) -> list[dict]:
    """
    Ranks every location's current centroid by cosine similarity to the
    given embedding. This is what answers "which places does this image
    visually resemble" — independent of which place the report was actually
    (currently randomly) assigned to.
    """
    profiles = [p async for p in db.location_profiles.find({})]

    ranked = []
    for profile in profiles:
        if exclude_segment and profile["segmentCode"] == exclude_segment:
            continue
        similarity = _cosine_similarity(embedding, profile["embedding"])
        ranked.append({"segmentCode": profile["segmentCode"], "similarity": round(similarity, 4)})

    ranked.sort(key=lambda r: r["similarity"], reverse=True)
    return ranked[:top_n]
