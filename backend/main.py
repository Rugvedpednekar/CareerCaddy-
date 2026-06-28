import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from .auth import get_current_user
from .config import AKANSHA_INITIAL_PASSWORD, APP_ENV, BASE_DIR, DEFAULT_USER_ID, FRONTEND_ORIGIN, RUGVED_INITIAL_PASSWORD, SESSION_SECRET_KEY, UPLOAD_DIR
from .database import create_tables, ensure_schema_upgrades
from .database import SessionLocal
from .models import User
from .routes import applications, auth, dashboard, export, jobs, profile, resumes
from .security import hash_password

logger = logging.getLogger("careercaddy.startup")

upload_path = UPLOAD_DIR if UPLOAD_DIR.is_absolute() else BASE_DIR / UPLOAD_DIR

USER_SEEDS = (
    {
        "user_id": "rugved_pednekar", "username": "rugved", "full_name": "Rugved Pednekar",
        "profile_type": "Software Engineering / Data Analyst / Support Engineer",
        "target_roles": ["Software Engineer", "Data Analyst", "Support Engineer", "Production Support Engineer", "Early Career / New Grad roles"],
        "password": RUGVED_INITIAL_PASSWORD,
    },
    {
        "user_id": "akansha_choudhary", "username": "bebu", "full_name": "Akansha Choudhary",
        "profile_type": "Organizational Psychology major",
        "target_roles": ["HR Intern", "People Operations Intern", "Organizational Psychology Intern", "Talent Acquisition Intern", "Human Resources Assistant", "Research Assistant", "Employee Experience Intern", "Industrial/Organizational Psychology roles"],
        "password": AKANSHA_INITIAL_PASSWORD,
    },
)

def ensure_upload_folders() -> None:
    for user_id in {DEFAULT_USER_ID, *(seed["user_id"] for seed in USER_SEEDS)}:
        (upload_path / "resumes" / user_id).mkdir(parents=True, exist_ok=True)
        (upload_path / "screenshots" / user_id).mkdir(parents=True, exist_ok=True)

def ensure_users() -> None:
    db = SessionLocal()
    try:
        for seed in USER_SEEDS:
            user = db.query(User).filter(User.user_id == seed["user_id"]).first()
            if not user:
                first_name, last_name = seed["full_name"].split(" ", 1)
                user = User(user_id=seed["user_id"], first_name=first_name, last_name=last_name)
                db.add(user)
            user.username = user.username or seed["username"]
            user.full_name = user.full_name or seed["full_name"]
            user.profile_type = user.profile_type or seed["profile_type"]
            user.target_roles = user.target_roles or seed["target_roles"]
            if not user.password_hash and seed["password"]:
                user.password_hash = hash_password(seed["password"])
        if APP_ENV != "production" and not db.query(User).filter(User.user_id == DEFAULT_USER_ID).first():
            db.add(User(user_id=DEFAULT_USER_ID, username="demo", full_name="Demo User", first_name="Demo", last_name="User", target_roles=[]))
        db.commit()
    finally:
        db.close()

def initialize_app_storage_and_database() -> None:
    create_tables()
    ensure_schema_upgrades()
    ensure_upload_folders()
    ensure_users()
    if APP_ENV == "production" and len(SESSION_SECRET_KEY) < 32:
        logger.warning("SESSION_SECRET_KEY must contain at least 32 characters; login is unavailable until configured.")
    logger.info("CareerCaddy AI startup complete: schema, upload folders, and user records are ready.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_app_storage_and_database()
    yield

app = FastAPI(title="CareerCaddy AI", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[FRONTEND_ORIGIN, "http://localhost:8000"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.include_router(auth.router)
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
def init_db(user: User = Depends(get_current_user)):
    initialize_app_storage_and_database()
    return {"status": "ok"}

@app.get("/")
def root():
    return RedirectResponse("/dashboard.html")

app.mount("/", StaticFiles(directory=BASE_DIR / "frontend", html=True), name="frontend")
