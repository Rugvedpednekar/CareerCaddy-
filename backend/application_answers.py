import json
import re
from typing import Any

from .config import GEMINI_API_KEY


ANSWER_KEYS = (
    "full_name",
    "email",
    "phone",
    "location",
    "linkedin",
    "github",
    "portfolio",
    "work_authorization",
    "resume_version",
    "why_interested",
    "why_good_fit",
    "relevant_experience",
    "skills_match",
    "availability",
    "sponsorship_answer",
    "salary_expectation",
    "notes_for_review",
)


def _value(obj: Any, key: str, default: Any = "") -> Any:
    if obj is None:
        return default
    return getattr(obj, key, default) if not isinstance(obj, dict) else obj.get(key, default)


def _salary(job: Any) -> str | None:
    breakdown = _value(job, "score_breakdown", {}) or {}
    if not isinstance(breakdown, dict):
        return None
    metadata = breakdown.get("extraction_metadata") or {}
    return metadata.get("salary") if isinstance(metadata, dict) else None


def _strict_json(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    value = json.loads(cleaned)
    return value if isinstance(value, dict) else {}


def generate_application_answers(job: Any, profile: Any) -> dict[str, str]:
    first_name = (_value(profile, "first_name") or "").strip()
    last_name = (_value(profile, "last_name") or "").strip()
    full_name = " ".join(value for value in (first_name, last_name) if value)
    company = (_value(job, "company") or "the company").strip()
    title = (_value(job, "title") or "this role").strip()
    skills = _value(job, "required_skills", []) or []
    skills = [str(skill).strip() for skill in skills if str(skill).strip()][:8]
    skills_text = ", ".join(skills)
    resume_version = (_value(job, "resume_version") or "SWE").strip()
    sponsorship = (_value(profile, "sponsorship_answer") or "").strip()
    work_auth = (_value(profile, "work_authorization") or "").strip()
    salary = _salary(job)

    answers = {
        "full_name": full_name,
        "email": (_value(profile, "email") or "").strip(),
        "phone": (_value(profile, "phone") or "").strip(),
        "location": (_value(profile, "location") or "").strip(),
        "linkedin": (_value(profile, "linkedin") or "").strip(),
        "github": (_value(profile, "github") or "").strip(),
        "portfolio": (_value(profile, "portfolio") or "").strip(),
        "work_authorization": work_auth,
        "resume_version": resume_version,
        "why_interested": f"I am interested in the {title} opportunity at {company}. Please tailor this response to the role before submitting.",
        "why_good_fit": f"My {resume_version} resume is selected for review against this role's requirements. Please add only verified experience before submitting.",
        "relevant_experience": "Please fill manually.",
        "skills_match": f"Key skills to address: {skills_text}." if skills_text else "Please fill manually.",
        "availability": "Please fill manually.",
        "sponsorship_answer": sponsorship or work_auth or "Please verify manually.",
        "salary_expectation": f"Job range for review: {salary}." if salary else "Please fill manually.",
        "notes_for_review": "Please verify all answers before submitting.",
    }

    if GEMINI_API_KEY:
        try:
            from google import genai

            client = genai.Client(api_key=GEMINI_API_KEY)
            prompt = f"""Improve only the narrative application answers in this JSON. Return strict JSON only.
Do not invent personal data, experience, education, skills, dates, salary expectations, or authorization details. Keep answers concise and professional. Preserve empty or manual-review values when facts are unavailable. Never claim the application was submitted.
PROFILE: {json.dumps({key: _value(profile, key, None) for key in ('first_name','last_name','email','phone','location','linkedin','github','portfolio','graduation_date','work_authorization','sponsorship_answer')}, default=str)}
JOB: {json.dumps({key: _value(job, key, None) for key in ('company','title','location','job_description','job_summary','required_skills','fit_score','resume_version','score_breakdown')}, default=str)}
CURRENT ANSWERS: {json.dumps(answers)}"""
            response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
            improved = _strict_json(response.text or "")
            for key in ("why_interested", "why_good_fit", "relevant_experience", "skills_match"):
                value = improved.get(key)
                if isinstance(value, str) and value.strip():
                    answers[key] = value.strip()
        except Exception:
            pass

    return {key: str(answers.get(key) or "") for key in ANSWER_KEYS}
