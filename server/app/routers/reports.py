import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from pydantic import BaseModel
from starlette.responses import StreamingResponse

from ml.classes import CLASSES

from ..config import UPLOAD_DIR
from ..db import get_db
from ..deps import get_current_user_id
from ..logging_config import get_logger
from ..models import Classification, Condition, ReportOut, VisualMatch
from ..world import WORLD_BY_CODE

logger = get_logger("rill.reports")
router = APIRouter(prefix="/api/reports", tags=["reports"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8MB
TIER_ORDER = ["green", "watch", "caution", "emergency"]


def report_doc_to_out(doc: dict) -> ReportOut:
    cls = doc.get("classification") or {}
    matches = doc.get("visualMatches") or []
    condition = doc.get("condition")
    return ReportOut(
        id=str(doc["_id"]),
        reporter=str(doc["reporter"]),
        segmentCode=doc.get("segmentCode", "UNKNOWN"),
        description=doc.get("description", ""),
        imagePath=doc.get("imagePath"),
        status=doc.get("status", "queued"),
        classification=Classification(**cls),
        visualMatches=[VisualMatch(**m) for m in matches],
        condition=Condition(**condition) if condition else None,
        userTag=doc.get("userTag"),
        createdAt=doc["createdAt"],
    )


@router.post("", response_model=ReportOut, status_code=201)
async def create_report(
    description: str = Form(""),
    segmentCode: str = Form(...),
    image: Optional[UploadFile] = File(None),
    user_id: str = Depends(get_current_user_id),
) -> ReportOut:
    """
    No GPS/location permission from the client, ever — location comes
    entirely from segmentCode, which is how a per-location QR code
    identifies where a scan happened: each of the 10 printed QR codes
    encodes a link like /report?segment=SEG-03, and the frontend passes
    that code straight through here.

    segmentCode is REQUIRED and must match a real location — there is no
    fallback. A report with a missing or unrecognized segment code is
    rejected outright (400), not silently reassigned to a random location.
    Deliberate: a fallback that substitutes fabricated location data is
    exactly the kind of thing that's tolerable in a demo and dangerous in
    a real deployment, so it doesn't exist here at all, not even as an
    option — this is production-shaped behavior, not just a stricter demo
    setting.
    """
    if segmentCode not in WORLD_BY_CODE:
        raise HTTPException(
            400,
            "unrecognized location — this report page must be opened via a valid "
            "Rill Report QR code",
        )

    if not description and not image:
        raise HTTPException(400, "provide a description, a photo, or both")

    db = get_db()
    image_path = None
    if image is not None:
        if image.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(400, "only image uploads are allowed")

        contents = await image.read()
        if len(contents) > MAX_IMAGE_BYTES:
            raise HTTPException(400, "image must be under 8MB")

        fs = AsyncIOMotorGridFSBucket(db)
        ext = os.path.splitext(image.filename or "")[1] or ".jpg"
        filename = f"{int(datetime.now().timestamp() * 1000)}-{uuid.uuid4().hex}{ext}"
        file_id = await fs.upload_from_stream(
            filename,
            contents,
            metadata={"contentType": image.content_type},
        )
        image_path = f"/api/reports/images/{file_id}"

    assigned_location = WORLD_BY_CODE[segmentCode]
    doc = {
        "reporter": ObjectId(user_id),
        "segmentCode": assigned_location["code"],
        "description": description,
        "imagePath": image_path,
        "status": "queued",
        "classification": {"tier": None, "confidence": None, "reasoning": None},
        "visualMatches": [],
        "condition": None,
        "createdAt": datetime.now(timezone.utc),
    }
    result = await db.reports.insert_one(doc)
    doc["_id"] = result.inserted_id
    logger.info(
        "report created: id=%s segment=%s (%s) reporter=%s has_image=%s",
        result.inserted_id,
        assigned_location["code"],
        assigned_location["name"],
        user_id,
        image_path is not None,
    )
    return report_doc_to_out(doc)


@router.get("", response_model=list[ReportOut])
async def list_reports(
    segmentCode: Optional[str] = None,
    minTier: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
) -> list[ReportOut]:
    db = get_db()
    query: dict = {}
    if segmentCode:
        query["segmentCode"] = segmentCode

    cursor = db.reports.find(query).sort("createdAt", -1).limit(200)
    docs = [d async for d in cursor]

    results: list[ReportOut] = []
    for d in docs:
        if minTier and minTier in TIER_ORDER:
            tier = (d.get("classification") or {}).get("tier")
            if not tier or TIER_ORDER.index(tier) < TIER_ORDER.index(minTier):
                continue
        results.append(report_doc_to_out(d))

    return results


@router.get("/images/{file_id}")
async def get_report_image(file_id: str):
    try:
        oid = ObjectId(file_id)
    except Exception:
        raise HTTPException(404, "Invalid image id")

    db = get_db()
    fs = AsyncIOMotorGridFSBucket(db)
    try:
        grid_out = await fs.open_download_stream(oid)
    except Exception:
        raise HTTPException(404, "Image not found")

    content_type = (grid_out.metadata or {}).get("contentType", "image/jpeg")

    async def stream_gridfs():
        while True:
            chunk = await grid_out.readchunk()
            if not chunk:
                break
            yield chunk

    return StreamingResponse(
        stream_gridfs(),
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


class TagReportRequest(BaseModel):
    tag: str


@router.post("/{report_id}/tag", response_model=ReportOut)
async def tag_report(
    report_id: str,
    body: TagReportRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
) -> ReportOut:
    if body.tag not in CLASSES:
        raise HTTPException(
            400,
            f"Invalid tag '{body.tag}'. Must be one of: {', '.join(CLASSES)}",
        )

    try:
        oid = ObjectId(report_id)
    except Exception:
        raise HTTPException(404, "Invalid report ID")

    db = get_db()
    report = await db.reports.find_one({"_id": oid})
    if not report:
        raise HTTPException(404, "Report not found")

    await db.reports.update_one(
        {"_id": oid},
        {"$set": {"userTag": body.tag, "userTaggedAt": datetime.now(timezone.utc)}},
    )
    report["userTag"] = body.tag

    # Trigger background retraining using the user's feedback
    from ml.retrain import retrain_from_user_tags

    background_tasks.add_task(retrain_from_user_tags, db)

    logger.info(
        "report %s tagged as '%s' by user %s — retraining triggered",
        report_id,
        body.tag,
        user_id,
    )
    return report_doc_to_out(report)

