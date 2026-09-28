import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from motor.motor_asyncio import AsyncIOMotorDatabase

from . import config
from .logging_config import get_logger

logger = get_logger("rill.db")

client: AsyncIOMotorClient | None = None
db: AsyncIOMotorDatabase | None = None


async def connect_db() -> None:
    global client, db

    if not config.MONGODB_URI:
        logger.error("MONGODB_URI is not set — copy .env.example to .env and fill it in")
        raise RuntimeError(
            "MONGODB_URI is not set. Copy .env.example to .env and fill it in."
        )

    logger.info("connecting to MongoDB…")
    try:
        client = AsyncIOMotorClient(config.MONGODB_URI, tlsCAFile=certifi.where())
        # Explicit db name — don't rely on the URI path containing one
        # (Atlas's own copy-paste connection string often omits it).
        db = client.get_database(config.MONGODB_DB_NAME)
        await client.admin.command("ping")
    except Exception:
        logger.error("failed to connect to MongoDB", exc_info=True)
        raise

    logger.info("connected to MongoDB (database=%s)", db.name)


def get_db() -> AsyncIOMotorDatabase:
    if db is None:
        logger.error("get_db() called before connect_db() ran")
        raise RuntimeError("Database not initialized — connect_db() hasn't run yet.")
    return db
