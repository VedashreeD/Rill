import asyncio
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import CLIENT_ORIGIN, UPLOAD_DIR
from .db import connect_db
from .logging_config import configure_logging, get_logger
from .routers import alerts, auth, locations, ml_status, reports, users
from .services.queue import run_queue_worker

configure_logging()  # must run before anything else logs
logger = get_logger("rill.server")

os.makedirs(UPLOAD_DIR, exist_ok=True)

_queue_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _queue_task
    logger.info("starting up…")

    from ml.status import log_startup_status

    log_startup_status(logger)  # always logs — see ml/status.py for why this matters

    await connect_db()
    _queue_task = asyncio.create_task(run_queue_worker())
    logger.info("Rill Signal queue worker launched")
    yield
    logger.info("shutting down…")
    if _queue_task:
        _queue_task.cancel()
        try:
            await _queue_task
        except asyncio.CancelledError:
            pass
    logger.info("shutdown complete")


app = FastAPI(title="Rill API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[CLIENT_ORIGIN] if CLIENT_ORIGIN != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Logs every request with its outcome:
      [INFO]  2xx/3xx responses
      [WARN]  4xx responses (client errors — bad input, auth failures, etc.)
      [ERR ]  5xx responses, and any unhandled exception (with full traceback)
    """
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.error(
            "%s %s -> unhandled exception after %.1fms",
            request.method,
            request.url.path,
            duration_ms,
            exc_info=True,
        )
        raise

    duration_ms = (time.perf_counter() - start) * 1000
    line = "%s %s -> %s (%.1fms)"
    args = (request.method, request.url.path, response.status_code, duration_ms)

    if response.status_code >= 500:
        logger.error(line, *args)
    elif response.status_code >= 400:
        logger.warning(line, *args)
    else:
        logger.info(line, *args)

    return response


app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/health")
async def health() -> dict:
    return {"ok": True}


app.include_router(auth.router)
app.include_router(alerts.router)
app.include_router(locations.router)
app.include_router(ml_status.router)
app.include_router(reports.router)
app.include_router(users.router)
