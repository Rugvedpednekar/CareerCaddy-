import os
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from ..config import DEFAULT_USER_ID
from ..database import get_db
from ..file_storage import save_upload
from ..models import Resume, uid

router = APIRouter(prefix="/api/resumes", tags=["resumes"])

@router.post("/upload")
def upload_resume(resume_type: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)):
    if resume_type not in {"SWE", "DATA_ANALYST", "SUPPORT_ENGINEER"}:
        raise HTTPException(400, "Unsupported resume_type")
    path = save_upload(file, "resumes", DEFAULT_USER_ID)
    resume = Resume(resume_id=uid("resume"), user_id=DEFAULT_USER_ID, resume_type=resume_type, file_name=file.filename, file_path=str(path))
    db.add(resume); db.commit(); db.refresh(resume)
    return resume

@router.get("")
def list_resumes(db: Session = Depends(get_db)):
    return db.query(Resume).filter(Resume.user_id == DEFAULT_USER_ID).order_by(Resume.created_at.desc()).all()

@router.delete("/{resume_id}")
def delete_resume(resume_id: str, db: Session = Depends(get_db)):
    resume = db.query(Resume).filter(Resume.resume_id == resume_id, Resume.user_id == DEFAULT_USER_ID).first()
    if not resume:
        raise HTTPException(404, "Resume not found")
    try:
        if resume.file_path and os.path.exists(resume.file_path):
            os.remove(resume.file_path)
    except OSError:
        pass
    db.delete(resume); db.commit()
    return {"deleted": True}
