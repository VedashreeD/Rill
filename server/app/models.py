from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class UserPublic(BaseModel):
    id: str
    username: str


class AuthResponse(BaseModel):
    token: str
    user: UserPublic


class AlertSettings(BaseModel):
    channels: List[str] = ["push"]
    radiusMeters: int = 2000
    minTier: str = "caution"
    homeSegmentCode: Optional[str] = None  # a code from the world catalog, e.g. "SEG-03"


class UserMe(BaseModel):
    id: str
    username: str
    alertSettings: AlertSettings


class AlertRecord(BaseModel):
    """
    A record of an alert that was sent to a user. Nothing writes to this
    collection yet — Rill Alert (the actual dispatch system) isn't built.
    This model + its endpoint exist so the UI's alert history is honestly
    wired up now (correctly showing "no alerts yet") and ready to receive
    real records the moment dispatch exists, without a schema change.
    """

    id: str
    tier: str
    segmentCode: str
    message: str
    sentAt: datetime


class Classification(BaseModel):
    tier: Optional[str] = None
    confidence: Optional[float] = None
    reasoning: Optional[str] = None


class VisualMatch(BaseModel):
    segmentCode: str
    similarity: float


class ConditionScore(BaseModel):
    label: str
    similarity: float


class Condition(BaseModel):
    label: str
    similarity: float
    scores: List[ConditionScore] = []


class ReportOut(BaseModel):
    id: str
    reporter: str
    segmentCode: str
    description: str
    imagePath: Optional[str] = None
    status: str
    classification: Classification
    visualMatches: List[VisualMatch] = []
    condition: Optional[Condition] = None
    userTag: Optional[str] = None
    createdAt: datetime


class WorldLocationOut(BaseModel):
    code: str
    name: str
    description: str
    illustration: str
    lat: float
    lng: float
    reportCount: int
    imageCount: int
    currentTier: Optional[str] = None
    lastReportAt: Optional[datetime] = None
    latestImagePath: Optional[str] = None
