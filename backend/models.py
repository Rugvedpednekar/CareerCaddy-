import uuid
from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from .database import Base

JSONType = JSON().with_variant(JSONB, "postgresql")

def uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"

class TimestampMixin:
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class User(Base, TimestampMixin):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(80), unique=True, index=True, nullable=False)
    first_name = Column(String(120))
    last_name = Column(String(120))
    email = Column(String(255))
    phone = Column(String(80))
    location = Column(String(255))
    linkedin = Column(String(255))
    github = Column(String(255))
    portfolio = Column(String(255))
    school = Column(String(255))
    degree = Column(String(255))
    graduation_date = Column(String(80))
    work_authorization = Column(String(255))
    sponsorship_answer = Column(Text)

class Job(Base, TimestampMixin):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True)
    job_id = Column(String(80), unique=True, index=True, nullable=False, default=lambda: uid("job"))
    user_id = Column(String(80), index=True, nullable=False)
    company = Column(String(255), nullable=False)
    title = Column(String(255), nullable=False)
    location = Column(String(255))
    apply_url = Column(Text)
    portal = Column(String(80))
    source = Column(String(120))
    job_description = Column(Text)
    job_summary = Column(Text)
    required_skills = Column(JSONType, default=list)
    missing_skills = Column(JSONType, default=list)
    fit_score = Column(Float)
    score_breakdown = Column(JSONType, default=dict)
    resume_version = Column(String(80))
    duplicate_hash = Column(String(128), index=True)
    status = Column(String(40), default="FOUND", index=True)
    date_found = Column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("user_id", "duplicate_hash", name="uq_user_job_duplicate"),)

class Application(Base, TimestampMixin):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True)
    application_id = Column(String(80), unique=True, index=True, nullable=False, default=lambda: uid("app"))
    user_id = Column(String(80), index=True, nullable=False)
    job_id = Column(String(80), ForeignKey("jobs.job_id"), index=True, nullable=False)
    status = Column(String(40), default="CREATED", index=True)
    current_step = Column(String(120))
    resume_version = Column(String(80))
    resume_path = Column(Text)
    screenshot_path = Column(Text)
    generated_answers = Column(JSONType, default=dict)
    logs = Column(JSONType, default=list)
    blocker = Column(String(255))
    review_url = Column(Text)

class Resume(Base, TimestampMixin):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True)
    resume_id = Column(String(80), unique=True, index=True, nullable=False, default=lambda: uid("resume"))
    user_id = Column(String(80), index=True, nullable=False)
    resume_type = Column(String(80), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=False)
    is_default = Column(Boolean, default=False)

class AutomationRun(Base, TimestampMixin):
    __tablename__ = "automation_runs"
    id = Column(Integer, primary_key=True)
    run_id = Column(String(80), unique=True, index=True, nullable=False, default=lambda: uid("run"))
    user_id = Column(String(80), index=True, nullable=False)
    job_id = Column(String(80), index=True)
    application_id = Column(String(80), index=True)
    status = Column(String(40), default="IN_PROGRESS")
    logs = Column(JSONType, default=list)
    screenshot_path = Column(Text)
    error_message = Column(Text)
