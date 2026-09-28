"""
Shared logging setup for Rill's backend.

Produces lines like:
    [INFO] 23:04:11 rill.db: connected to MongoDB
    [WARN] 23:04:42 rill.auth: failed login attempt for username=alice
    [ERR ] 23:05:03 rill.signal: failed to process report 651f...: connection reset

Call configure_logging() once, as early as possible (before anything else
logs), then get_logger(name) anywhere you need a logger. Dotted names like
"rill.db", "rill.signal", "rill.auth" make it easy to grep logs by component.
"""

import logging
import sys

from . import config

# Relabel the standard levels so they match the requested [INFO]/[WARN]/[ERR] tags.
logging.addLevelName(logging.WARNING, "WARN")
logging.addLevelName(logging.ERROR, "ERR ")  # padded to line up with INFO/WARN

_FORMAT = "[%(levelname)s] %(asctime)s %(name)s: %(message)s"
_DATEFMT = "%H:%M:%S"

_configured = False


def configure_logging() -> None:
    global _configured
    if _configured:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATEFMT))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))

    # We log every request ourselves (see main.py's middleware), so silence
    # uvicorn's own per-request access log to avoid seeing each request twice.
    # uvicorn's startup/shutdown/error messages (uvicorn.error) are left alone.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
