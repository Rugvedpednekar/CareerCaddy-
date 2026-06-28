from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from ..auth import get_current_user
from ..candidate_context import parse_and_store_resume
from ..database import get_db
from ..file_storage import save_upload, storage_root
from ..models import Resume, User, uid

router = APIRouter(prefix="/api/resumes", tags=["resumes"])

@router.post("/upload")
def upload_resume(resume_type: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if Path(file.filename or "").suffix.lower() not in {".pdf", ".docx", ".txt"}:
        raise HTTPException(400, "Only PDF, DOCX, and TXT resumes are supported")
    path = save_upload(file, "resumes", user.user_id)
    resume = Resume(resume_id=uid("resume"), user_id=user.user_id, resume_type=resume_type.strip().upper()[:80], file_name=Path(file.filename or "resume").name, file_path=str(path), parse_status="Needs parsing")
    db.add(resume); db.commit(); db.refresh(resume)
    parse_and_store_resume(db, resume)
    return resume

@router.get("")
def list_resumes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Resume).filter(Resume.user_id == user.user_id).order_by(Resume.created_at.desc()).all()

@router.post("/{resume_id}/parse")
def parse_resume(resume_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resume = db.query(Resume).filter(Resume.resume_id == resume_id, Resume.user_id == user.user_id).first()
    if not resume:
        raise HTTPException(404, "Resume not found")
    parsed = parse_and_store_resume(db, resume)
    return {"resume": resume, "parsed_resume_data": parsed}

@router.post("/{resume_id}/set-default")
def set_default(resume_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resume = db.query(Resume).filter(Resume.resume_id == resume_id, Resume.user_id == user.user_id).first()
    if not resume:
        raise HTTPException(404, "Resume not found")
    db.query(Resume).filter(Resume.user_id == user.user_id).update({Resume.is_default: False})
    resume.is_default = True
    db.commit(); db.refresh(resume)
    return resume

@router.delete("/{resume_id}")
def delete_resume(resume_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    resume = db.query(Resume).filter(Resume.resume_id == resume_id, Resume.user_id == user.user_id).first()
    if not resume:
        raise HTTPException(404, "Resume not found")
    try:
        path = Path(resume.file_path).resolve()
        allowed = (storage_root() / "resumes" / user.user_id).resolve()
        if path.is_relative_to(allowed) and path.exists():
            path.unlink()
    except OSError:
        pass
    db.delete(resume); db.commit()
    return {"deleted": True}
