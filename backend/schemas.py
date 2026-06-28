from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict

class JobIn(BaseModel):
    company: str
    title: str
    location: str | None = None
    apply_url: str | None = None
    portal: str | None = None
    source: str | None = None
    job_description: str | None = None

class JobUrlIn(BaseModel):
    url: str

class JobTextIn(BaseModel):
    job_text: str
    apply_url: str | None = None

class JobOut(JobIn):
    model_config = ConfigDict(from_attributes=True)
    job_id: str
    user_id: str
    job_summary: Optional[str] = None
    required_skills: Any = None
    missing_skills: Any = None
    fit_score: Optional[float] = None
    score_breakdown: Any = None
    resume_version: Optional[str] = None
    duplicate_hash: Optional[str] = None
    status: str
    date_found: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    application_id: str
    user_id: str
    job_id: str
    status: str
    current_step: Optional[str] = None
    resume_version: Optional[str] = None
    resume_path: Optional[str] = None
    screenshot_path: Optional[str] = None
    generated_answers: Any = None
    logs: Any = None
    blocker: Optional[str] = None
    review_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class ProfileIn(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin: str | None = None
    github: str | None = None
    portfolio: str | None = None
    school: str | None = None
    degree: str | None = None
    graduation_date: str | None = None
    work_authorization: str | None = None
    sponsorship_answer: str | None = None
    availability: str | None = None
    salary_expectation: str | None = None
    target_roles: list[str] | None = None

class BlockerIn(BaseModel):
    blocker: str = "FAILED"
    notes: str | None = None

class ReviewUpdateIn(BaseModel):
    generated_answers: dict[str, Any]
    notes: str | None = None

class AutomationStartIn(BaseModel):
    confirm_missing: bool = False
