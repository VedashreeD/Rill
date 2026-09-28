from fastapi import APIRouter

from ml.status import get_status

router = APIRouter(prefix="/api/ml", tags=["ml"])


@router.get("/status")
async def ml_status() -> dict:
    """
    Public (no auth) — lets the frontend show a "train the model first"
    banner instead of a silently-empty condition filter when no trained
    model is available yet.
    """
    return get_status()
