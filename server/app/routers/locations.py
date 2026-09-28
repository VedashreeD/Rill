from fastapi import APIRouter

from ..db import get_db
from ..models import WorldLocationOut
from ..world import WORLD_LOCATIONS

router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.get("", response_model=list[WorldLocationOut])
async def list_locations() -> list[WorldLocationOut]:
    """
    The fixed world catalog, each entry enriched with live stats computed
    from the reports collection: total reports, total images, the most
    recent classified tier, and when it was last reported on.
    Public (no auth) — it's static reference data plus non-sensitive counts.
    """
    db = get_db()
    results: list[WorldLocationOut] = []

    for loc in WORLD_LOCATIONS:
        reports = [
            r
            async for r in db.reports.find({"segmentCode": loc["code"]}).sort("createdAt", -1)
        ]
        report_count = len(reports)
        image_count = sum(1 for r in reports if r.get("imagePath"))
        current_tier = None
        last_report_at = None
        for r in reports:
            tier = (r.get("classification") or {}).get("tier")
            if tier:
                current_tier = tier
                break
        if reports:
            last_report_at = reports[0]["createdAt"]

        results.append(
            WorldLocationOut(
                code=loc["code"],
                name=loc["name"],
                description=loc["description"],
                illustration=loc["illustration"],
                lat=loc["lat"],
                lng=loc["lng"],
                reportCount=report_count,
                imageCount=image_count,
                currentTier=current_tier,
                lastReportAt=last_report_at,
            )
        )

    return results
