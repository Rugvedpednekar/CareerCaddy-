import hashlib
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from ..config import DEFAULT_USER_ID
from ..database import get_db
from ..models import Job, uid
from ..schemas import JobIn
from ..scorer import score_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

def duplicate_hash(job: JobIn) -> str:
    raw = "|".join([(job.company or "").strip().lower(), (job.title or "").strip().lower(), (job.location or "").strip().lower(), (job.apply_url or "").strip().lower()])
    return hashlib.sha256(raw.encode()).hexdigest()

@router.post("/import")
def import_jobs(payload: JobIn | list[JobIn], db: Session = Depends(get_db)):
    items = payload if isinstance(payload, list) else [payload]
    results = []
    for item in items:
        dh = duplicate_hash(item)
        existing = db.query(Job).filter(Job.user_id == DEFAULT_USER_ID, Job.duplicate_hash == dh).first()
        if existing:
            existing.status = "DUPLICATE" if existing.status == "FOUND" else existing.status
            db.commit(); db.refresh(existing)
            results.append(existing)
            continue
        job = Job(job_id=uid("job"), user_id=DEFAULT_USER_ID, duplicate_hash=dh, status="FOUND", **item.model_dump())
        db.add(job)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            job = db.query(Job).filter(Job.user_id == DEFAULT_USER_ID, Job.duplicate_hash == dh).first()
        db.refresh(job)
        results.append(job)
    return results if isinstance(payload, list) else results[0]

@router.get("")
def list_jobs(status: str | None = None, portal: str | None = None, min_score: float | None = Query(None), search: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Job).filter(Job.user_id == DEFAULT_USER_ID)
    if status:
        q = q.filter(Job.status == status)
    if portal:
        q = q.filter(Job.portal == portal)
    if min_score is not None:
        q = q.filter(Job.fit_score >= min_score)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(Job.company.ilike(like), Job.title.ilike(like), Job.location.ilike(like)))
    return q.order_by(Job.created_at.desc()).all()

@router.get("/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.job_id == job_id, Job.user_id == DEFAULT_USER_ID).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return job

@router.post("/{job_id}/score")
def score(job_id: str, db: Session = Depends(get_db)):
    job = get_job(job_id, db)
    breakdown = score_job(job.title, job.job_description or "")
    job.fit_score = breakdown["final_score"]
    job.score_breakdown = breakdown
    job.resume_version = breakdown["recommended_resume"]
    job.status = "SCORED"
    db.commit(); db.refresh(job)
    return job

@router.post("/{job_id}/ready")
def ready(job_id: str, db: Session = Depends(get_db)):
    job = get_job(job_id, db)
    job.status = "READY_TO_APPLY"
    db.commit(); db.refresh(job)
    return job

@router.post("/{job_id}/skip")
def skip(job_id: str, db: Session = Depends(get_db)):
    job = get_job(job_id, db)
    job.status = "SKIPPED"
    db.commit(); db.refresh(job)
    return job

@router.delete("/{job_id}")
def delete(job_id: str, db: Session = Depends(get_db)):
    job = get_job(job_id, db)
    db.delete(job); db.commit()
    return {"deleted": True}
