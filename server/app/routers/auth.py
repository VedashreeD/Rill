from fastapi import APIRouter, HTTPException

from ..db import get_db
from ..logging_config import get_logger
from ..models import AuthResponse, LoginRequest, RegisterRequest, UserPublic
from ..security import create_access_token, hash_password, verify_password

logger = get_logger("rill.auth")
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(body: RegisterRequest) -> AuthResponse:
    db = get_db()
    username = body.username.strip().lower()

    if not username or not body.password:
        raise HTTPException(400, "username and password are required")
    if len(body.password) < 6:
        raise HTTPException(400, "password must be at least 6 characters")

    existing = await db.users.find_one({"username": username})
    if existing:
        raise HTTPException(409, "that username is taken")

    doc = {
        "username": username,
        "passwordHash": hash_password(body.password),
        "alertSettings": {
            "channels": ["push"],
            "radiusMeters": 2000,
            "minTier": "caution",
            "homeSegmentCode": None,
        },
    }
    result = await db.users.insert_one(doc)
    user_id = str(result.inserted_id)
    token = create_access_token(user_id, username)
    logger.info("user registered: username=%s id=%s", username, user_id)
    return AuthResponse(token=token, user=UserPublic(id=user_id, username=username))


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest) -> AuthResponse:
    db = get_db()
    username = body.username.strip().lower()

    user = await db.users.find_one({"username": username})
    if not user or not verify_password(body.password, user["passwordHash"]):
        logger.warning("failed login attempt: username=%s", username)
        raise HTTPException(401, "invalid username or password")

    user_id = str(user["_id"])
    token = create_access_token(user_id, username)
    logger.info("user logged in: username=%s id=%s", username, user_id)
    return AuthResponse(token=token, user=UserPublic(id=user_id, username=username))
