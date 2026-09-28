"""
Dev entrypoint: `python run.py`

Named run.py (not app.py) on purpose — the backend package is a directory
called app/, and a file named app.py sitting next to a package named app/
creates an ambiguous import ("import app" could mean either one). Keeping
this script's name distinct from the package avoids that entirely.

Equivalent to running:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 4000

Note: uvicorn.run() is called with the app passed as an import string
("app.main:app"), not the app object itself — reload=True requires that
(it re-imports the module in a subprocess on each change); passing the
object directly silently disables hot-reload.
"""

import uvicorn

from app.config import PORT

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # reachable from your phone on the same network too
        port=PORT,
        reload=True,
    )
