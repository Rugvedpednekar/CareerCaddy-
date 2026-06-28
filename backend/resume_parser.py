import re
from pathlib import Path
from typing import Any


SKILLS = (
    "Python", "Java", "JavaScript", "TypeScript", "SQL", "React", "Node.js", "FastAPI",
    "Spring Boot", "AWS", "Docker", "Kubernetes", "PostgreSQL", "MySQL", "MongoDB", "Redis",
    "REST APIs", "Linux", "Git", "GitHub Actions", "CI/CD", "ServiceNow", "troubleshooting",
    "data pipelines", "ETL", "machine learning", "deep learning", "data analysis", "Excel", "SPSS",
    "research", "survey design", "organizational psychology", "HR", "talent acquisition",
    "employee engagement", "people operations",
)


def _read_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    if suffix == ".docx":
        from docx import Document
        return "\n".join(paragraph.text for paragraph in Document(str(path)).paragraphs)
    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="replace")
    raise ValueError("Only PDF, DOCX, and TXT resumes are supported")


def _section(lines: list[str], headings: tuple[str, ...], limit: int = 12) -> list[str]:
    lowered_headings = {heading.lower() for heading in headings}
    exact_indexes = [index for index, line in enumerate(lines) if line.lower().rstrip(":") in lowered_headings]
    indexes = exact_indexes or [index for index, line in enumerate(lines) if any(heading in line.lower() for heading in lowered_headings)]
    for index in indexes:
        values = []
        for candidate in lines[index + 1:index + 1 + limit]:
            if candidate.lower() in {"education", "experience", "work experience", "professional experience", "projects", "skills"}:
                break
            values.append(candidate)
        if values:
            return values
    return []


def parse_resume_file(file_path: str) -> dict[str, Any]:
    raw = _read_text(Path(file_path))
    lines = [re.sub(r"\s+", " ", line).strip() for line in raw.splitlines()]
    lines = [line for line in lines if line]
    text = " ".join(lines)
    email = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.IGNORECASE)
    phone = re.search(r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}", text)
    linkedin = re.search(r"https?://(?:www\.)?linkedin\.com/in/[\w\-/%]+", text, re.IGNORECASE)
    github = re.search(r"https?://(?:www\.)?github\.com/[\w\-]+", text, re.IGNORECASE)
    urls = re.findall(r"https?://[^\s|,]+", text, re.IGNORECASE)
    portfolio = next((url for url in urls if "linkedin.com" not in url.lower() and "github.com" not in url.lower()), None)
    location_match = re.search(r"\b([A-Z][A-Za-z .'-]{1,50},\s*[A-Z]{2})(?:\s+\d{5})?\b", " ".join(lines[:12]))
    location = location_match.group(1).strip() if location_match else None
    full_name = next((line for line in lines[:5] if re.fullmatch(r"[A-Za-z][A-Za-z .'-]{2,80}", line) and 2 <= len(line.split()) <= 5), None)
    graduation = re.search(r"(?:graduat(?:ion|ed)|expected)\s*[:\-]?\s*((?:(?:spring|summer|fall|winter|january|february|march|april|may|june|july|august|september|october|november|december)\s+)?(?:19|20)\d{2})", text, re.IGNORECASE)
    degree = re.search(r"\b((?:Bachelor(?:'s)?|Master(?:'s)?|B\.S\.|B\.A\.|M\.S\.|M\.A\.)[^|]{0,100})", text, re.IGNORECASE)
    lowered = text.lower()
    skills = [skill for skill in SKILLS if re.search(rf"(?<!\w){re.escape(skill.lower())}(?!\w)", lowered)]
    education = _section(lines, ("education", "university", "bachelor", "master"))
    experience = _section(lines, ("experience", "work experience", "professional experience"))
    projects = _section(lines, ("projects",))
    summary_lines = _section(lines, ("summary",), 5)
    return {
        "full_name": full_name,
        "email": email.group(0) if email else None,
        "phone": phone.group(0) if phone else None,
        "location": location,
        "linkedin": linkedin.group(0) if linkedin else None,
        "github": github.group(0) if github else None,
        "portfolio": portfolio,
        "education": education,
        "degree": degree.group(1).strip() if degree else None,
        "graduation_date": graduation.group(1).strip() if graduation else None,
        "skills": skills,
        "projects": projects,
        "experience": experience,
        "work_authorization": None,
        "summary": " ".join(summary_lines[:2]) or None,
        "raw_text": text,
    }
