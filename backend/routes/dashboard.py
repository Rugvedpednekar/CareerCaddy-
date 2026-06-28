from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..auth import get_current_user
from ..database import get_db
from ..models import Application, Job, Resume, User

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/stats")
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    base = db.query(Job).filter(Job.user_id == user.user_id)
    total = base.count()
    avg = db.query(func.avg(Job.fit_score)).filter(Job.user_id == user.user_id, Job.fit_score != None).scalar() or 0
    applications = db.query(Application).filter(Application.user_id == user.user_id)
    profile_fields = [user.full_name or " ".join(value for value in (user.first_name, user.last_name) if value), user.email, user.phone, user.location, user.linkedin, user.github or user.portfolio, user.work_authorization, user.availability, user.salary_expectation, user.target_roles]
    completeness = round(sum(bool(value) for value in profile_fields) / len(profile_fields) * 100)
    return {
        "total_found": total,
        "scored": base.filter(Job.status == "SCORED").count(),
        "ready_to_apply": base.filter(Job.status == "READY_TO_APPLY").count(),
        "needs_review": base.filter(Job.status == "NEEDS_REVIEW").count(),
        "submitted": base.filter(Job.status == "SUBMITTED").count(),
        "failed_blocked": base.filter(Job.status.in_(["FAILED", "NEEDS_LOGIN", "NEEDS_CAPTCHA"])).count(),
        "average_fit_score": round(float(avg), 1),
        "applications_in_review": applications.filter(Application.status == "NEEDS_REVIEW").count(),
        "submitted_applications": applications.filter(Application.status == "SUBMITTED").count(),
        "failed_applications": applications.filter(Application.status.in_(["FAILED", "BLOCKED", "NEEDS_LOGIN", "NEEDS_CAPTCHA"])).count(),
        "resumes_uploaded": db.query(Resume).filter(Resume.user_id == user.user_id).count(),
        "profile_completeness": completeness,
    }
