import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
# Explicit, so the app never depends on the URI itself containing a database
# name — Atlas's own "Connect > Drivers" copy button often gives you a URI
# with nothing between the host and the "?", which breaks anything relying
# on the URI path alone.
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "rill")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

CLIENT_ORIGIN = os.getenv("CLIENT_ORIGIN", "http://localhost:5173")
CLIENT_BASE_URL = os.getenv("CLIENT_BASE_URL", "http://localhost:5173")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "uploads")

# Optional — only used by run.py (the `python run.py` entrypoint).
PORT = int(os.getenv("PORT", "4000"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
