from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

DATA_MODE = os.getenv("DATA_MODE", "sample").lower()  # sample | csv | api
CONDUIT_CSV_PATH = os.getenv("CONDUIT_CSV_PATH", str(DATA_DIR / "sample_conduit.csv"))
CONDUIT_API_URL = os.getenv("CONDUIT_API_URL", "")
CONDUIT_API_TOKEN = os.getenv("CONDUIT_API_TOKEN", "")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
