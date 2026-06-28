import json
import ipaddress
import re
from html import unescape
from typing import Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from .config import GEMINI_API_KEY


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
MAX_PAGE_CHARS = 1_500_000
TITLE_TERMS = (
    "software engineer", "data analyst", "support engineer", "backend engineer",
    "full stack engineer", "fullstack engineer", "data engineer", "machine learning engineer",
    "new grad", "intern", "associate", "developer", "analyst", "platform engineer",
    "sre", "production support",
)
SKILL_TERMS = (
    "Python", "Java", "JavaScript", "TypeScript", "SQL", "React", "Node.js", "FastAPI",
    "Spring Boot", "AWS", "Docker", "Kubernetes", "PostgreSQL", "MySQL", "MongoDB",
    "Redis", "REST APIs", "Linux", "Git", "GitHub Actions", "CI/CD", "ServiceNow",
    "troubleshooting", "data pipelines", "ETL", "machine learning", "distributed systems",
    "microservices",
    "deep learning", "data analysis", "Excel", "SPSS", "research", "survey design",
    "organizational psychology", "HR", "talent acquisition", "employee engagement", "people operations",
)


class JobExtractionError(ValueError):
    pass


def normalize_whitespace(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", unescape(str(value))).strip()
    return text or None


def clean_description(value: Any) -> str | None:
    if not value:
        return None
    return normalize_whitespace(BeautifulSoup(str(value), "lxml").get_text(" ", strip=True))


def detect_portal(url: str) -> str:
    lowered = url.lower()
    checks = (
        ("greenhouse", ("greenhouse.io", "boards.greenhouse.io")),
        ("lever", ("lever.co", "jobs.lever.co")),
        ("ashby", ("ashbyhq.com",)),
        ("workday", ("myworkdayjobs.com", "workday")),
        ("linkedin", ("linkedin.com/jobs",)),
        ("indeed", ("indeed.com",)),
    )
    return next((name for name, needles in checks if any(needle in lowered for needle in needles)), "generic")


def validate_url(url: str) -> str:
    value = (url or "").strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise JobExtractionError("Enter a valid job URL beginning with http:// or https://.")
    hostname = (parsed.hostname or "").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise JobExtractionError("Local and private network URLs cannot be imported.")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise JobExtractionError("Local and private network URLs cannot be imported.")
    return value


def _job_postings(value: Any):
    if isinstance(value, list):
        for item in value:
            yield from _job_postings(item)
    elif isinstance(value, dict):
        kind = value.get("@type")
        kinds = kind if isinstance(kind, list) else [kind]
        if "JobPosting" in kinds:
            yield value
        for key, item in value.items():
            if key != "@context":
                yield from _job_postings(item)


def _location(value: Any) -> str | None:
    if isinstance(value, list):
        locations = [item for item in (_location(v) for v in value) if item]
        return "; ".join(dict.fromkeys(locations)) or None
    if isinstance(value, str):
        return normalize_whitespace(value)
    if not isinstance(value, dict):
        return None
    address = value.get("address", value)
    if isinstance(address, str):
        return normalize_whitespace(address)
    if not isinstance(address, dict):
        return normalize_whitespace(value.get("name"))
    parts = [address.get(key) for key in ("streetAddress", "addressLocality", "addressRegion", "postalCode", "addressCountry")]
    return ", ".join(str(part).strip() for part in parts if part) or normalize_whitespace(value.get("name"))


def _salary(value: Any) -> str | None:
    if not value:
        return None
    if isinstance(value, str):
        return normalize_whitespace(value)
    if not isinstance(value, dict):
        return normalize_whitespace(value)
    currency = value.get("currency") or ""
    amount = value.get("value", value)
    if isinstance(amount, dict):
        minimum = amount.get("minValue")
        maximum = amount.get("maxValue")
        exact = amount.get("value")
        unit = amount.get("unitText") or ""
        if minimum is not None or maximum is not None:
            bounds = " - ".join(str(v) for v in (minimum, maximum) if v is not None)
            return normalize_whitespace(f"{currency} {bounds} {unit}")
        if exact is not None:
            return normalize_whitespace(f"{currency} {exact} {unit}")
    return normalize_whitespace(json.dumps(value, ensure_ascii=True))


def _meta(soup: BeautifulSoup, *names: str) -> str | None:
    for name in names:
        tag = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return normalize_whitespace(tag["content"])
    return None


def _strict_json(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    value = json.loads(cleaned)
    if not isinstance(value, dict):
        raise ValueError("AI response was not a JSON object")
    return value


def structure_job_with_ai(raw_text: str, url: str, portal: str) -> dict[str, Any]:
    if not GEMINI_API_KEY or not raw_text:
        return {}
    from google import genai

    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""Extract a job posting from the page text below. Return strict JSON only with exactly these keys:
{{"company":null,"title":null,"location":null,"job_description":null,"job_summary":null,"required_skills":[],"employment_type":null,"salary":null,"date_posted":null}}
Do not invent missing details. Use null when unknown. Extract skills only when explicitly present. The summary must be 2-4 grounded sentences. Keep the description grounded in the fetched text.
URL: {url}
Portal: {portal}
PAGE TEXT:
{raw_text[:50000]}"""
    response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
    return _strict_json(response.text or "")


def structure_job_text_with_ai(job_text: str, apply_url: str | None = None) -> dict[str, Any]:
    if not GEMINI_API_KEY:
        return {}
    from google import genai

    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""Extract a job posting from pasted text. Return strict JSON only with exactly these keys:
{{"company":null,"title":null,"location":null,"job_description":null,"job_summary":null,"required_skills":[],"employment_type":null,"salary":null,"date_posted":null}}
Do not invent details. Use null when unknown. Extract only information present in the text. required_skills must be a list. The summary must be 2-4 grounded sentences.
Optional URL: {apply_url or ''}
PASTED TEXT:
{job_text[:50000]}"""
    response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
    return _strict_json(response.text or "")


def _first_matching_line(lines: list[str], pattern: str) -> str | None:
    regex = re.compile(pattern, re.IGNORECASE)
    for line in lines:
        match = regex.search(line)
        if match:
            return normalize_whitespace(match.group(1))
    return None


def _text_summary(text: str) -> str | None:
    chunks = [normalize_whitespace(value) for value in re.split(r"\n+|(?<=[.!?])\s+", text)]
    metadata = re.compile(r"^(company|job title|title|role|position|location|salary|employment type|date posted|posted)\s*[:\-]", re.IGNORECASE)
    useful = [value for value in chunks if value and 45 <= len(value) <= 320 and not metadata.search(value)]
    return " ".join(useful[:4]) or None


def extract_job_from_text(job_text: str, apply_url: str | None = None) -> dict[str, Any]:
    raw = (job_text or "").strip()
    if not raw:
        raise JobExtractionError("Paste the full job posting text before extracting details.")
    if len(raw) < 100:
        raise JobExtractionError("Job posting text must contain at least 100 characters.")
    url = validate_url(apply_url) if apply_url and apply_url.strip() else None
    lines = [normalize_whitespace(line) for line in raw.splitlines()]
    lines = [line for line in lines if line]
    cleaned = normalize_whitespace(raw) or ""

    title = _first_matching_line(lines, r"^(?:job\s+title|title|role|position)\s*[:\-]\s*(.+)$")
    if not title:
        title = next((line for line in lines if len(line) <= 140 and any(term in line.lower() for term in TITLE_TERMS)), None)
    company = _first_matching_line(lines, r"^company\s*[:\-]\s*(.+)$")
    if not company:
        company = _first_matching_line(lines, r"^(?:about|at)\s+([A-Z][A-Za-z0-9&.'\- ]{1,80})(?:\s|$)")
    if not company and title in lines:
        title_index = lines.index(title)
        if title_index > 0:
            candidate = lines[title_index - 1]
            if len(candidate) <= 80 and not any(term in candidate.lower() for term in TITLE_TERMS):
                company = candidate

    location = _first_matching_line(lines, r"^location\s*[:\-]\s*(.+)$")
    if not location:
        location = next((line for line in lines if re.fullmatch(r"(?:[A-Za-z .'-]+,\s*[A-Z]{2}|Remote|United States)", line, re.IGNORECASE)), None)
    salary_match = re.search(r"\$\s?\d{2,3}(?:,\d{3})+(?:\.\d+)?\s*(?:-|to|–)\s*\$?\s?\d{2,3}(?:,\d{3})+(?:\.\d+)?", cleaned, re.IGNORECASE)
    employment_match = re.search(r"\b(full[- ]time|part[- ]time|internship|contract|temporary)\b", cleaned, re.IGNORECASE)
    date_match = re.search(r"(?:date posted|posted)\s*[:\-]\s*([^|;]{4,40})", cleaned, re.IGNORECASE)
    lowered = cleaned.lower()
    skills = [skill for skill in SKILL_TERMS if re.search(rf"(?<!\w){re.escape(skill.lower())}(?!\w)", lowered)]

    data: dict[str, Any] = {
        "company": company,
        "title": title,
        "location": location,
        "apply_url": url,
        "portal": detect_portal(url or ""),
        "source": "Text Paste",
        "job_description": cleaned[:50000],
        "job_summary": _text_summary(raw),
        "required_skills": skills,
        "employment_type": normalize_whitespace(employment_match.group(1)) if employment_match else None,
        "salary": normalize_whitespace(salary_match.group(0)) if salary_match else None,
        "date_posted": normalize_whitespace(date_match.group(1)) if date_match else None,
    }
    warnings: list[str] = []
    if GEMINI_API_KEY:
        try:
            ai_data = structure_job_text_with_ai(cleaned, url)
            for key in ("company", "title", "location", "employment_type", "salary", "date_posted"):
                if ai_data.get(key) and not data.get(key):
                    data[key] = normalize_whitespace(ai_data[key])
            if ai_data.get("job_description"):
                data["job_description"] = clean_description(ai_data["job_description"])
            if ai_data.get("job_summary"):
                data["job_summary"] = normalize_whitespace(ai_data["job_summary"])
            ai_skills = ai_data.get("required_skills")
            if isinstance(ai_skills, list):
                data["required_skills"] = [value for value in (normalize_whitespace(skill) for skill in ai_skills) if value]
        except Exception:
            warnings.append("AI cleanup was unavailable; standard text extraction was used.")
    for field in ("company", "title", "location"):
        if not data.get(field):
            warnings.append(f"Could not determine {field} from the pasted text.")
    data["extraction_warnings"] = warnings
    return data


def extract_job_from_url(url: str) -> dict[str, Any]:
    url = validate_url(url)
    portal = detect_portal(url)
    try:
        response = httpx.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
            follow_redirects=True,
            timeout=20.0,
        )
        if response.status_code in {401, 403, 429}:
            raise JobExtractionError("This job page is blocked or requires login. Please use manual import.")
        response.raise_for_status()
    except JobExtractionError:
        raise
    except httpx.HTTPError as exc:
        raise JobExtractionError("Could not fetch this job page. Please use manual import.") from exc

    html = response.text[:MAX_PAGE_CHARS]
    soup = BeautifulSoup(html, "lxml")
    posting = None
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            posting = next(_job_postings(json.loads(script.string or script.get_text())), None)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue
        if posting:
            break

    body_text = normalize_whitespace(soup.get_text(" ", strip=True)) or ""
    data: dict[str, Any] = {
        "company": None,
        "title": None,
        "location": None,
        "apply_url": url,
        "portal": portal,
        "source": "URL Import",
        "job_description": None,
        "job_summary": None,
        "required_skills": [],
        "employment_type": None,
        "salary": None,
        "date_posted": None,
    }
    if posting:
        organization = posting.get("hiringOrganization") or {}
        data.update(
            company=normalize_whitespace(organization.get("name") if isinstance(organization, dict) else organization),
            title=normalize_whitespace(posting.get("title")),
            location=_location(posting.get("jobLocation") or posting.get("applicantLocationRequirements")),
            job_description=clean_description(posting.get("description")),
            date_posted=normalize_whitespace(posting.get("datePosted")),
            employment_type=normalize_whitespace(posting.get("employmentType")),
            salary=_salary(posting.get("baseSalary")),
        )

    data["title"] = data["title"] or _meta(soup, "og:title", "twitter:title") or normalize_whitespace(soup.title.string if soup.title else None)
    site_name = _meta(soup, "og:site_name")
    platform_names = {"linkedin", "indeed", "greenhouse", "lever", "ashby", "workday"}
    if site_name and site_name.lower() not in platform_names:
        data["company"] = data["company"] or site_name
    fallback_description = _meta(soup, "og:description", "twitter:description")
    data["job_description"] = data["job_description"] or fallback_description or body_text[:30000] or None
    data["job_summary"] = fallback_description

    warnings: list[str] = []
    if GEMINI_API_KEY:
        try:
            ai_data = structure_job_with_ai(body_text, url, portal)
            for key in ("company", "title", "location", "job_description", "employment_type", "salary", "date_posted"):
                if ai_data.get(key) and not data.get(key):
                    data[key] = clean_description(ai_data[key]) if key == "job_description" else normalize_whitespace(ai_data[key])
            if ai_data.get("job_summary"):
                data["job_summary"] = normalize_whitespace(ai_data["job_summary"])
            skills = ai_data.get("required_skills")
            if isinstance(skills, list):
                data["required_skills"] = [value for value in (normalize_whitespace(skill) for skill in skills) if value]
        except Exception:
            warnings.append("AI cleanup was unavailable; standard page extraction was used.")

    for field in ("company", "title", "location", "job_description"):
        if not data.get(field):
            warnings.append(f"Could not determine {field.replace('_', ' ')} from the page.")
    data["extraction_warnings"] = warnings
    return data
