from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from sqlalchemy.orm import Session
from ..application_answers import generate_answer_package
from ..auth import get_current_user
from ..config import BASE_DIR, UPLOAD_DIR
from ..database import get_db
from ..models import Application, AutomationRun, Job, User, uid
from ..schemas import AutomationStartIn, BlockerIn, ReviewUpdateIn

router = APIRouter(prefix="/api/applications", tags=["applications"])

def model_dict(obj):
    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}

def get_application_record(application_id: str, db: Session, user_id: str) -> Application:
    app = db.query(Application).filter(Application.application_id == application_id, Application.user_id == user_id).first()
    if not app:
        raise HTTPException(404, "Application not found")
    return app

def append_logs(app: Application, messages: list[str]) -> None:
    logs = list(app.logs or [])
    logs.extend(message for message in messages if message not in logs)
    app.logs = logs

@router.post("/{job_id}/prepare")
def prepare(job_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    job = db.query(Job).filter(Job.job_id == job_id, Job.user_id == user.user_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    app = db.query(Application).filter(Application.job_id == job_id, Application.user_id == user.user_id).first()
    if not app:
        app = Application(
            application_id=uid("app"),
            user_id=user.user_id,
            job_id=job_id,
            status="NEEDS_REVIEW",
            current_step="Prepared for review",
            resume_version=job.resume_version,
        )
        db.add(app)
    elif app.status != "SUBMITTED":
        app.status = "NEEDS_REVIEW"
        app.current_step = "Prepared for review"
        app.resume_version = app.resume_version or job.resume_version
    package = generate_answer_package(job, db, user.user_id)
    generated = package["answers"]
    existing_answers = dict(app.generated_answers or {})
    app.generated_answers = {**generated, **{key: value for key, value in existing_answers.items() if value not in (None, "")}}
    app.generated_answer_sources = package["sources"]
    app.missing_fields = package["missing_fields"]
    if package["resume"]:
        app.resume_path = package["resume"].file_path
        app.resume_version = package["resume"].resume_type
    append_logs(app, [
        "Application prepared for review.",
        *( ["Loaded candidate data from uploaded resume."] if package["resume_loaded"] else [] ),
        "Used profile fallback for missing resume fields.",
        "Generated review-ready answers.",
        "Waiting for user review before final submission.",
    ])
    job.status = "NEEDS_REVIEW"
    db.commit()
    db.refresh(app)
    return app

@router.get("")
def list_applications(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = db.query(Application).filter(Application.user_id == user.user_id)
    if status:
        q = q.filter(Application.status == status)
    apps = q.order_by(Application.updated_at.desc()).all()
    jobs = {j.job_id: j for j in db.query(Job).filter(Job.job_id.in_([a.job_id for a in apps] or ["none"])).all()}
    return [{**model_dict(a), "job": jobs.get(a.job_id)} for a in apps]

@router.get("/{application_id}")
def get_application(application_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    app = get_application_record(application_id, db, user.user_id)
    job = db.query(Job).filter(Job.job_id == app.job_id, Job.user_id == user.user_id).first()
    return {**model_dict(app), "job": job}

@router.get("/{application_id}/automation-status")
def get_automation_status(application_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    app = get_application_record(application_id, db, user.user_id)
    runs = db.query(AutomationRun).filter(
        AutomationRun.application_id == application_id,
        AutomationRun.user_id == user.user_id,
    ).order_by(AutomationRun.created_at.desc()).all()
    return {
        "application_id": app.application_id,
        "status": app.status,
        "current_step": app.current_step,
        "logs": app.logs or [],
        "blocker": app.blocker,
        "screenshot_path": app.screenshot_path,
        "automation_runs": [
            {
                "run_id": run.run_id,
                "status": run.status,
                "logs": run.logs or [],
                "screenshot_path": run.screenshot_path,
                "error_message": run.error_message,
                "created_at": run.created_at,
                "updated_at": run.updated_at,
            }
            for run in runs
        ],
    }

@router.get("/{application_id}/screenshot")
def get_screenshot(application_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    app = get_application_record(application_id, db, user.user_id)
    if not app.screenshot_path:
        raise HTTPException(404, "Screenshot not found")
    path = Path(app.screenshot_path).resolve()
    root = (UPLOAD_DIR if UPLOAD_DIR.is_absolute() else BASE_DIR / UPLOAD_DIR).resolve()
    allowed = (root / "screenshots" / user.user_id).resolve()
    if not path.is_relative_to(allowed) or not path.exists():
        raise HTTPException(404, "Screenshot not found")
    return FileResponse(path, media_type="image/png")

@router.patch("/{application_id}/review")
def save_review(application_id: str, payload: ReviewUpdateIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    app = get_application_record(application_id, db, user.user_id)
    app.generated_answers = payload.generated_answers
    append_logs(app, ["Review changes saved."])
    if payload.notes and payload.notes.strip():
        append_logs(app, [f"Review note: {payload.notes.strip()[:500]}"])
    db.commit(); db.refresh(app)
    return app

@router.post("/{application_id}/regenerate-answers")
def regenerate_answers(application_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    app = get_application_record(application_id, db, user.user_id)
    job = db.query(Job).filter(Job.job_id == app.job_id, Job.user_id == user.user_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    package = generate_answer_package(job, db, user.user_id)
    app.generated_answers = package["answers"]
    app.generated_answer_sources = package["sources"]
    app.missing_fields = package["missing_fields"]
    if package["resume"]:
        app.resume_path = package["resume"].file_path
        app.resume_version = package["resume"].resume_type
    append_logs(app, ["Generated answers regenerated from resume and profile."])
    db.commit(); db.refresh(app)
    return app

@router.post("/{application_id}/start-automation")
def start_automation(application_id: str, payload: AutomationStartIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    app = get_application_record(application_id, db, user.user_id)
    if app.status == "SUBMITTED":
        raise HTTPException(409, "Submitted applications cannot be queued for automation.")
    important_missing = [field for field in (app.missing_fields or []) if field in {"full_name", "email", "phone", "work_authorization"}]
    if important_missing and not payload.confirm_missing:
        return {"queued": False, "requires_confirmation": True, "missing_fields": important_missing, "application": app}
    app.status = "READY_FOR_WORKER"
    app.current_step = "Queued for automation"
    app.blocker = None
    append_logs(app, ["Queued for automation.", "Application queued for worker automation."])
    job = db.query(Job).filter(Job.job_id == app.job_id, Job.user_id == user.user_id).first()
    if job: job.status = "READY_TO_APPLY"
    db.commit(); db.refresh(app)
    return {"queued": True, "requires_confirmation": False, "missing_fields": important_missing, "application": app}

@router.post("/{application_id}/mark-review")
def mark_review(application_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    app = get_application_record(application_id, db, user.user_id)
    app.status = "NEEDS_REVIEW"; app.current_step = "Prepared for review"
    job = db.query(Job).filter(Job.job_id == app.job_id, Job.user_id == user.user_id).first()
    if job: job.status = "NEEDS_REVIEW"
    db.commit(); db.refresh(app)
    return app

@router.post("/{application_id}/mark-submitted")
def mark_submitted(application_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    app = get_application_record(application_id, db, user.user_id)
    app.status = "SUBMITTED"; app.current_step = "User confirmed manual submission"
    job = db.query(Job).filter(Job.job_id == app.job_id, Job.user_id == user.user_id).first()
    if job: job.status = "SUBMITTED"
    db.commit(); db.refresh(app)
    return app

@router.post("/{application_id}/skip")
def skip(application_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    app = get_application_record(application_id, db, user.user_id)
    app.status = "SKIPPED"
    job = db.query(Job).filter(Job.job_id == app.job_id, Job.user_id == user.user_id).first()
    if job: job.status = "SKIPPED"
    db.commit(); db.refresh(app)
    return app

@router.post("/{application_id}/mark-blocked")
def mark_blocked(application_id: str, payload: BlockerIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    app = get_application_record(application_id, db, user.user_id)
    blocker = payload.blocker.upper()
    app.status = blocker if blocker in {"NEEDS_LOGIN", "NEEDS_CAPTCHA"} else "BLOCKED"
    app.current_step = "Blocked by user"
    app.blocker = payload.notes or payload.blocker
    append_logs(app, ["Marked blocked by user."])
    job = db.query(Job).filter(Job.job_id == app.job_id, Job.user_id == user.user_id).first()
    if job: job.status = app.status
    db.commit(); db.refresh(app)
    return app
