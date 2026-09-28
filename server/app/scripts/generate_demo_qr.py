"""
Generates 10 demo QR codes for the hackathon walkthrough — one per
Cindervale Watershed location, each encoding a link straight to Rill
Report with that location's segment code pre-filled
(e.g. /report?segment=SEG-03), so scanning a specific physical QR code
logs the report against that specific location.

A report submitted with no segment code (or an unrecognized one) still
works — the server falls back to randomly assigning one of the 10
locations. That fallback exists for testing the generic /report link
directly; the QR codes themselves are what makes location assignment
meaningful rather than random.

Run from server/ (inside the venv, after `pip install -r requirements.txt`).
Both of these work — direct execution and module execution:
    python app/scripts/generate_demo_qr.py
    python -m app.scripts.generate_demo_qr
"""

import os
import sys

# Allows running this script directly, not just via -m — see the matching
# comment in ml/training/train.py for why this is needed.
_SERVER_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _SERVER_ROOT not in sys.path:
    sys.path.insert(0, _SERVER_ROOT)

import qrcode

from app.config import CLIENT_BASE_URL
from app.world import WORLD_LOCATIONS

OUT_DIR = "demo-qr-codes"


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    for loc in WORLD_LOCATIONS:
        url = f"{CLIENT_BASE_URL}/report?segment={loc['code']}"
        path = os.path.join(OUT_DIR, f"{loc['code']}.png")
        img = qrcode.make(url)
        img.save(path)
        print(f"generated {path} -> {url}  ({loc['name']})")
    print(f"\nDone. {len(WORLD_LOCATIONS)} demo QR codes in {OUT_DIR}/")


if __name__ == "__main__":
    main()
