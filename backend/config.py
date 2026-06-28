import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
APP_ENV = os.getenv("APP_ENV", "development")
WORKER_HEADLESS = os.getenv("WORKER_HEADLESS", "true").lower() != "false"
IS_RAILWAY = bool(os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"))
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "demo_user")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "")
RUGVED_INITIAL_PASSWORD = os.getenv("RUGVED_INITIAL_PASSWORD", "")
AKANSHA_INITIAL_PASSWORD = os.getenv("AKANSHA_INITIAL_PASSWORD", "")
ALLOW_DEV_UNAUTHENTICATED = os.getenv("ALLOW_DEV_UNAUTHENTICATED", "true" if APP_ENV != "production" else "false").lower() == "true"
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:8000")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))

def get_database_url() -> str:
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        return f"sqlite:///{BASE_DIR / 'career_caddy_dev.db'}"
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url
