from sqlalchemy.orm import Session

from .models import Resume, User
from .resume_parser import parse_resume_file


PERSONAL_FIELDS = ("full_name", "email", "phone", "location", "linkedin", "github", "portfolio", "work_authorization", "graduation_date")


def select_resume(db: Session, user_id: str, resume_version: str | None = None) -> Resume | None:
    query = db.query(Resume).filter(Resume.user_id == user_id)
    if resume_version:
        matching = query.filter(Resume.resume_type == resume_version).order_by(Resume.created_at.desc()).first()
        if matching:
            return matching
    default = query.filter(Resume.is_default.is_(True)).order_by(Resume.created_at.desc()).first()
    return default or query.order_by(Resume.created_at.desc()).first()


def parse_and_store_resume(db: Session, resume: Resume) -> dict:
    try:
        resume.parsed_resume_data = parse_resume_file(resume.file_path)
        resume.parse_status = "Parsed"
    except Exception:
        resume.parsed_resume_data = {}
        resume.parse_status = "Failed"
    db.commit()
    db.refresh(resume)
    return dict(resume.parsed_resume_data or {})


def build_candidate_context(db: Session, user_id: str, resume_version: str | None = None) -> dict:
    profile = db.query(User).filter(User.user_id == user_id).first()
    resume = select_resume(db, user_id, resume_version)
    parsed = dict(resume.parsed_resume_data or {}) if resume else {}
    if resume and (not parsed or resume.parse_status != "Parsed"):
        parsed = parse_and_store_resume(db, resume)
    profile_values = {
        "full_name": (profile.full_name or " ".join(value for value in (profile.first_name, profile.last_name) if value)).strip() if profile else "",
        "email": profile.email if profile else None, "phone": profile.phone if profile else None,
        "location": profile.location if profile else None, "linkedin": profile.linkedin if profile else None,
        "github": profile.github if profile else None, "portfolio": profile.portfolio if profile else None,
        "work_authorization": profile.work_authorization if profile else None,
        "graduation_date": profile.graduation_date if profile else None,
        "availability": profile.availability if profile else None,
        "salary_expectation": profile.salary_expectation if profile else None,
        "sponsorship_answer": profile.sponsorship_answer if profile else None,
        "target_roles": profile.target_roles if profile else [],
    }
    candidate, sources = {}, {}
    for field in PERSONAL_FIELDS:
        if parsed.get(field):
            candidate[field], sources[field] = parsed[field], "resume"
        elif profile_values.get(field):
            candidate[field], sources[field] = profile_values[field], "profile"
        else:
            candidate[field], sources[field] = "Please fill manually.", "manual_required"
    for field in ("availability", "salary_expectation", "sponsorship_answer", "target_roles"):
        value = profile_values.get(field)
        candidate[field] = value or ("Please fill manually." if field != "target_roles" else [])
        sources[field] = "profile" if value else "manual_required"
    for field in ("skills", "experience", "projects", "education", "summary", "degree"):
        candidate[field] = parsed.get(field) or ([] if field in {"skills", "experience", "projects", "education"} else None)
    missing = [field for field in PERSONAL_FIELDS if sources[field] == "manual_required"]
    return {"candidate": candidate, "sources": sources, "missing_fields": missing, "resume": resume, "resume_loaded": bool(resume and parsed)}
