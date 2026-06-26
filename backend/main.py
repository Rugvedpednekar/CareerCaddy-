import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from .config import BASE_DIR, DEFAULT_USER_ID, FRONTEND_ORIGIN, UPLOAD_DIR
from .database import create_tables
from .database import SessionLocal
from .models import User
from .routes import applications, dashboard, export, jobs, profile, resumes

logger = logging.getLogger("careercaddy.startup")

upload_path = UPLOAD_DIR if UPLOAD_DIR.is_absolute() else BASE_DIR / UPLOAD_DIR

def ensure_upload_folders() -> None:
    (upload_path / "resumes" / DEFAULT_USER_ID).mkdir(parents=True, exist_ok=True)
    (upload_path / "screenshots" / DEFAULT_USER_ID).mkdir(parents=True, exist_ok=True)

def ensure_demo_user() -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.user_id == DEFAULT_USER_ID).first()
        if not user:
            db.add(
                User(
                    user_id=DEFAULT_USER_ID,
                    first_name="Demo",
                    last_name="User",
                    email="demo@example.com",
                    work_authorization="Yes",
                    sponsorship_answer="I am eligible to work in the U.S. on OPT and may require sponsorship in the future.",
                )
            )
            db.commit()
    finally:
        db.close()

def initialize_app_storage_and_database() -> None:
    create_tables()
    ensure_upload_folders()
    ensure_demo_user()
    logger.info("CareerCaddy AI startup complete: database tables, upload folders, and demo_user are ready.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_app_storage_and_database()
    yield

app = FastAPI(title="CareerCaddy AI", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[FRONTEND_ORIGIN, "http://localhost:8000"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(dashboard.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(resumes.router)
app.include_router(profile.router)
app.include_router(export.router)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/init-db")
def init_db():
    initialize_app_storage_and_database()
    return {"status": "ok"}

@app.get("/")
def root():
    return RedirectResponse("/dashboard.html")

ensure_upload_folders()
app.mount("/uploads", StaticFiles(directory=upload_path), name="uploads")
app.mount("/", StaticFiles(directory=BASE_DIR / "frontend", html=True), name="frontend")
