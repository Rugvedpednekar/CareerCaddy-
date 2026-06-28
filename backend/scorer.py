POSITIVE_TITLES = ["software engineer", "full stack", "fullstack", "backend", "frontend", "data engineer", "data analyst", "support engineer", "production support", "sre"]
TECH_SKILLS = ["python", "sql", "java", "javascript", "typescript", "react", "fastapi", "aws", "docker", "kubernetes", "postgresql"]
EARLY = ["new grad", "entry level", "junior", "0-2 years", "early career"]
SUPPORT = ["support", "ticket", "incident", "servicenow", "troubleshooting", "customer support", "production issue"]
NEGATIVE_TITLES = ["senior", "staff", "principal", "manager", "lead"]
CLEARANCE = ["u.s. citizen only", "security clearance required", "active clearance"]

def select_resume(title: str, description: str) -> str:
    text = f"{title} {description}".lower()
    if any(k in text for k in ["organizational psychology", "i/o psychology", "research assistant", "survey design", "spss"]):
        return "ORG_PSYCH"
    if any(k in text for k in ["human resources", "hr intern", "people operations", "talent acquisition", "employee experience"]):
        return "HR"
    if any(k in text for k in ["data analyst", "data engineer", " bi ", "analytics", "reporting"]):
        return "DATA_ANALYST"
    if any(k in text for k in ["support engineer", "sre", "production support", "incident", "troubleshooting"]):
        return "SUPPORT_ENGINEER"
    return "SWE"

def score_job(title: str, description: str) -> dict:
    score = 50
    positive, negative = [], []
    title_l = (title or "").lower()
    desc_l = (description or "").lower()
    if any(k in title_l for k in POSITIVE_TITLES):
        score += 15; positive.append("+15 relevant target title")
    found_skills = [s for s in TECH_SKILLS if s in desc_l]
    if found_skills:
        score += 10; positive.append(f"+10 skills match: {', '.join(found_skills[:8])}")
    if any(k in desc_l for k in EARLY):
        score += 10; positive.append("+10 early-career wording")
    if any(k in desc_l for k in SUPPORT):
        score += 10; positive.append("+10 support/incident fit")
    if any(k in title_l for k in NEGATIVE_TITLES):
        score -= 30; negative.append("-30 seniority/title mismatch")
    if "5+ years" in desc_l or "5 years" in desc_l:
        score -= 30; negative.append("-30 requires 5+ years")
    if any(k in desc_l for k in CLEARANCE):
        score -= 40; negative.append("-40 clearance/citizenship restriction")
    final = max(0, min(100, score))
    return {"base": 50, "positive": positive, "negative": negative, "final_score": final, "recommended_resume": select_resume(title, description)}
