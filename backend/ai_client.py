from .config import GEMINI_API_KEY

SAFE_AUTH = {
    "authorized_to_work": "Yes",
    "sponsorship_required": "Yes",
    "sponsorship_explanation": "I am eligible to work in the U.S. on OPT and may require sponsorship in the future.",
}

def generate_screening_answer(question: str, job: dict, profile: dict) -> str:
    q = question.lower()
    if "authorized" in q or "sponsorship" in q or "visa" in q:
        return SAFE_AUTH["sponsorship_explanation"] if "explain" in q else SAFE_AUTH["authorized_to_work"]
    if not GEMINI_API_KEY:
        return "Draft pending review: I am interested in this role because it aligns with my background and goals. Please review and tailor this answer before submission."
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = f"Answer under 120 words. Do not invent experience. Question: {question}\nJob: {job}\nProfile: {profile}"
        response = client.models.generate_content(model="gemini-1.5-flash", contents=prompt)
        return (response.text or "").strip()[:900]
    except Exception:
        return "Draft pending review: I can provide a concise, truthful response based on my profile and the role. Please verify before submission."
