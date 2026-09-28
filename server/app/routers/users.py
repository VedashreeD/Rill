from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from ..db import get_db
from ..deps import get_current_user_id
from ..models import AlertSettings, UserMe

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserMe)
async def get_me(user_id: str = Depends(get_current_user_id)) -> UserMe:
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(404, "user not found")

    return UserMe(
        id=str(user["_id"]),
        username=user["username"],
        alertSettings=AlertSettings(**user.get("alertSettings", {})),
    )


@router.put("/me/alert-settings", response_model=AlertSettings)
async def update_alert_settings(
    body: AlertSettings, user_id: str = Depends(get_current_user_id)
) -> AlertSettings:
    db = get_db()
    await db.users.update_one(
        {"_id": ObjectId(user_id)}, {"$set": {"alertSettings": body.model_dump()}}
    )
    return body
