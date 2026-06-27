from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..application_answers import generate_application_answers
from ..config import DEFAULT_USER_ID
from ..database import get_db
from ..models import Application, Job, User, uid
from ..schemas import BlockerIn, ReviewUpdateIn

router = APIRouter(prefix="/api/applications", tags=["applications"])

def model_dict(obj):
    return {column.name: getattr(obj, column.name) for column in obj.__table__.columns}

def get_application_record(application_id: str, db: Session) -> Application:
    app = db.query(Application).filter(Application.application_id == application_id, Application.user_id == DEFAULT_USER_ID).first()
    if not app:
        raise HTTPException(404, "Application not found")
    return app

def append_logs(app: Application, messages: list[str]) -> None:
    logs = list(app.logs or [])
    logs.extend(message for message in messages if message not in logs)
    app.logs = logs

@router.post("/{job_id}/prepare")
def prepare(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.job_id == job_id, Job.user_id == DEFAULT_USER_ID).first()
    if not job:
        raise HTTPException(404, "Job not found")
    app = db.query(Application).filter(Application.job_id == job_id, Application.user_id == DEFAULT_USER_ID).first()
    if not app:
        app = Application(
            application_id=uid("app"),
            user_id=DEFAULT_USER_ID,
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
    profile = db.query(User).filter(User.user_id == DEFAULT_USER_ID).first()
    generated = generate_application_answers(job, profile)
    existing_answers = dict(app.generated_answers or {})
    app.generated_answers = {**generated, **{key: value for key, value in existing_answers.items() if value not in (None, "")}}
    append_logs(app, [
        "Application prepared for review.",
        "Generated basic application answers.",
        "Waiting for user review before final submission.",
    ])
    job.status = "NEEDS_REVIEW"
    db.commit()
    db.refresh(app)
    return app

@router.get("")
def list_applications(status: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Application).filter(Application.user_id == DEFAULT_USER_ID)
    if status:
        q = q.filter(Application.status == status)
    apps = q.order_by(Application.updated_at.desc()).all()
    jobs = {j.job_id: j for j in db.query(Job).filter(Job.job_id.in_([a.job_id for a in apps] or ["none"])).all()}
    return [{**model_dict(a), "job": jobs.get(a.job_id)} for a in apps]

@router.get("/{application_id}")
def get_application(application_id: str, db: Session = Depends(get_db)):
    app = get_application_record(application_id, db)
    job = db.query(Job).filter(Job.job_id == app.job_id).first()
    return {**model_dict(app), "job": job}

@router.patch("/{application_id}/review")
def save_review(application_id: str, payload: ReviewUpdateIn, db: Session = Depends(get_db)):
    app = get_application_record(application_id, db)
    app.generated_answers = payload.generated_answers
    append_logs(app, ["Review changes saved."])
    if payload.notes and payload.notes.strip():
        append_logs(app, [f"Review note: {payload.notes.strip()[:500]}"])
    db.commit(); db.refresh(app)
    return app

@router.post("/{application_id}/start-automation")
def start_automation(application_id: str, db: Session = Depends(get_db)):
    app = get_application_record(application_id, db)
    if app.status == "SUBMITTED":
        raise HTTPException(409, "Submitted applications cannot be queued for automation.")
    app.status = "READY_FOR_WORKER"
    app.current_step = "Queued for automation"
    app.blocker = None
    append_logs(app, ["Application queued for worker automation."])
    job = db.query(Job).filter(Job.job_id == app.job_id).first()
    if job: job.status = "READY_TO_APPLY"
    db.commit(); db.refresh(app)
    return app

@router.post("/{application_id}/mark-review")
def mark_review(application_id: str, db: Session = Depends(get_db)):
    app = get_application_record(application_id, db)
    app.status = "NEEDS_REVIEW"; app.current_step = "Prepared for review"
    job = db.query(Job).filter(Job.job_id == app.job_id).first()
    if job: job.status = "NEEDS_REVIEW"
    db.commit(); db.refresh(app)
    return app

@router.post("/{application_id}/mark-submitted")
def mark_submitted(application_id: str, db: Session = Depends(get_db)):
    app = get_application_record(application_id, db)
    app.status = "SUBMITTED"; app.current_step = "User confirmed manual submission"
    job = db.query(Job).filter(Job.job_id == app.job_id).first()
    if job: job.status = "SUBMITTED"
    db.commit(); db.refresh(app)
    return app

@router.post("/{application_id}/skip")
def skip(application_id: str, db: Session = Depends(get_db)):
    app = get_application_record(application_id, db)
    app.status = "SKIPPED"
    job = db.query(Job).filter(Job.job_id == app.job_id).first()
    if job: job.status = "SKIPPED"
    db.commit(); db.refresh(app)
    return app

@router.post("/{application_id}/mark-blocked")
def mark_blocked(application_id: str, payload: BlockerIn, db: Session = Depends(get_db)):
    app = get_application_record(application_id, db)
    blocker = payload.blocker.upper()
    app.status = blocker if blocker in {"NEEDS_LOGIN", "NEEDS_CAPTCHA"} else "FAILED"
    app.blocker = payload.notes or payload.blocker
    job = db.query(Job).filter(Job.job_id == app.job_id).first()
    if job: job.status = app.status
    db.commit(); db.refresh(app)
    return app
