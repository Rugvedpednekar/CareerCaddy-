from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..config import DEFAULT_USER_ID
from ..database import get_db
from ..models import Job

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    base = db.query(Job).filter(Job.user_id == DEFAULT_USER_ID)
    total = base.count()
    avg = db.query(func.avg(Job.fit_score)).filter(Job.user_id == DEFAULT_USER_ID, Job.fit_score != None).scalar() or 0
    return {
        "total_found": total,
        "ready_to_apply": base.filter(Job.status == "READY_TO_APPLY").count(),
        "needs_review": base.filter(Job.status == "NEEDS_REVIEW").count(),
        "submitted": base.filter(Job.status == "SUBMITTED").count(),
        "failed_blocked": base.filter(Job.status.in_(["FAILED", "NEEDS_LOGIN", "NEEDS_CAPTCHA"])).count(),
        "average_fit_score": round(float(avg), 1),
    }
