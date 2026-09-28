from bson import ObjectId
from fastapi import APIRouter, Depends

from ..db import get_db
from ..deps import get_current_user_id
from ..models import AlertRecord

router = APIRouter(prefix="/api/users/me/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertRecord])
async def list_my_alerts(user_id: str = Depends(get_current_user_id)) -> list[AlertRecord]:
    """
    Past alerts sent to the current user. Empty for now — nothing writes
    to the `alerts` collection yet, since Rill Alert (the actual dispatch
    system) isn't built. This endpoint exists so the UI's alert history is
    honestly wired up now (correctly shows "no alerts yet") and ready to
    receive real records the moment dispatch exists.
    """
    db = get_db()
    cursor = db.alerts.find({"userId": ObjectId(user_id)}).sort("sentAt", -1).limit(100)
    docs = [d async for d in cursor]
    return [
        AlertRecord(
            id=str(d["_id"]),
            tier=d["tier"],
            segmentCode=d["segmentCode"],
            message=d["message"],
            sentAt=d["sentAt"],
        )
        for d in docs
    ]
