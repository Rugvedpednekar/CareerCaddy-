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
    full_name = (_value(profile, "full_name") or "").strip()
    if not full_name:
        first_name = (_value(profile, "first_name") or "").strip()
        last_name = (_value(profile, "last_name") or "").strip()
        full_name = " ".join(value for value in (first_name, last_name) if value)
    company = (_value(job, "company") or "the company").strip()
    title = (_value(job, "title") or "this role").strip()
    job_skills = [str(skill).strip() for skill in (_value(job, "required_skills", []) or []) if str(skill).strip()]
    candidate_skills = [str(skill).strip() for skill in (_value(profile, "skills", []) or []) if str(skill).strip()]
    matched_skills = [skill for skill in job_skills if skill.lower() in {value.lower() for value in candidate_skills}]
    skills_text = ", ".join(matched_skills[:8] or job_skills[:8])
    resume_version = (_value(job, "resume_version") or "SWE").strip()
    sponsorship = (_value(profile, "sponsorship_answer") or "").strip()
    work_auth = (_value(profile, "work_authorization") or "").strip()
    salary = _salary(job)
    experience = _value(profile, "experience", []) or []
    projects = _value(profile, "projects", []) or []
    relevant = " ".join(str(value) for value in (experience[:2] or projects[:2]))[:900]
    manual = "Please fill manually."

    answers = {
        "full_name": full_name or manual,
        "email": (_value(profile, "email") or manual).strip(),
        "phone": (_value(profile, "phone") or manual).strip(),
        "location": (_value(profile, "location") or manual).strip(),
        "linkedin": (_value(profile, "linkedin") or manual).strip(),
        "github": (_value(profile, "github") or manual).strip(),
        "portfolio": (_value(profile, "portfolio") or manual).strip(),
        "work_authorization": work_auth or manual,
        "resume_version": resume_version,
        "why_interested": f"I am interested in the {title} opportunity at {company}. Please tailor this response to the role before submitting.",
        "why_good_fit": f"My background includes {', '.join(matched_skills[:6])}, which aligns with this role's requirements." if matched_skills else manual,
        "relevant_experience": relevant or manual,
        "skills_match": f"Matching skills: {', '.join(matched_skills[:8])}." if matched_skills else (f"Job skills to verify: {skills_text}." if skills_text else manual),
        "availability": (_value(profile, "availability") or manual).strip(),
        "sponsorship_answer": sponsorship or work_auth or "Please verify manually.",
        "salary_expectation": (_value(profile, "salary_expectation") or (f"Job range for review: {salary}." if salary else manual)).strip(),
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


def generate_answer_package(job: Any, db, user_id: str) -> dict[str, Any]:
    from .candidate_context import build_candidate_context

    context = build_candidate_context(db, user_id, _value(job, "resume_version", None))
    candidate = context["candidate"]
    answers = generate_application_answers(job, candidate)
    sources = dict(context["sources"])
    resume_source = "resume_and_job_description" if context["resume_loaded"] else "manual_required"
    sources.update({
        "resume_version": "job_scoring",
        "why_interested": "resume_and_job_description" if context["resume_loaded"] else "profile_and_job_description",
        "why_good_fit": resume_source,
        "relevant_experience": "resume" if candidate.get("experience") or candidate.get("projects") else "manual_required",
        "skills_match": resume_source,
        "sponsorship_answer": sources.get("work_authorization", "manual_required"),
        "salary_expectation": context["sources"].get("salary_expectation", "job_description" if _salary(job) else "manual_required"),
        "notes_for_review": "system",
    })
    if context["resume"]:
        answers["resume_version"] = context["resume"].resume_type
        sources["resume_version"] = "resume"
    missing = sorted(set(context["missing_fields"] + [key for key, value in answers.items() if value in {"Please fill manually.", "Please verify manually."}]))
    return {"answers": answers, "sources": sources, "missing_fields": missing, "resume": context["resume"], "resume_loaded": context["resume_loaded"]}
