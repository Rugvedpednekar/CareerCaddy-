from typing import Any

from backend.ai_client import generate_screening_answer

from .anti_detection import random_sleep, type_with_delay


STANDARD_QUESTION_TERMS = {
    "name", "email", "phone", "location", "address", "linkedin", "github", "portfolio",
    "resume", "authorization", "visa", "sponsor", "school", "degree", "experience",
}


def _object_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if hasattr(value, "__table__"):
        return {column.name: getattr(value, column.name) for column in value.__table__.columns}
    return dict(vars(value)) if value is not None else {}


def answer_custom_question(question: str, profile: dict, job: Any) -> str:
    return generate_screening_answer(question, _object_dict(job), profile)


class FormFiller:
    FIELD_LABELS = {
        "full_name": ("Full name", "Name"),
        "first_name": ("First name", "Given name"),
        "last_name": ("Last name", "Family name"),
        "email": ("Email", "Email address"),
        "phone": ("Phone", "Phone number", "Mobile"),
        "address": ("Address", "Street address"),
        "location": ("Location", "City"),
        "linkedin": ("LinkedIn", "LinkedIn URL"),
        "github": ("GitHub", "GitHub URL"),
        "portfolio": ("Portfolio", "Website"),
        "years_experience": ("Years of experience", "Experience"),
        "school": ("School", "University"),
        "degree": ("Degree",),
    }

    def __init__(self, page, profile: dict, application: Any, job: Any):
        self.page = page
        self.profile = profile
        self.application = application
        self.job = job

    def _value(self, key: str) -> str:
        answers = _object_dict(self.application).get("generated_answers") or {}
        value = self.profile.get(key) or answers.get(key)
        return "" if value in (None, "Please fill manually.", "Please verify manually.") else str(value)

    def _fill_label(self, label: str, value: str) -> bool:
        if not value:
            return False
        for locator in (
            self.page.get_by_label(label, exact=False),
            self.page.get_by_placeholder(label, exact=False),
        ):
            if locator.count():
                try:
                    type_with_delay(locator.first, value)
                    return True
                except Exception:
                    continue
        return False

    def fill_standard_fields(self) -> list[str]:
        filled = []
        for key, labels in self.FIELD_LABELS.items():
            value = self._value(key)
            for label in labels:
                if self._fill_label(label, value):
                    filled.append(key)
                    break
        self._fill_work_authorization_selects()
        return filled

    def _fill_work_authorization_selects(self) -> None:
        authorization = str(self.profile.get("work_authorization") or "")
        sponsorship = str(self.profile.get("sponsorship_answer") or self.profile.get("visa_type") or "")
        for select in self.page.locator("select").all():
            label = " ".join(filter(None, [select.get_attribute("name"), select.get_attribute("aria-label")])).lower()
            value = sponsorship if "sponsor" in label or "visa" in label else authorization
            if value and any(term in label for term in ("author", "sponsor", "visa")):
                try:
                    select.select_option(label=value)
                except Exception:
                    pass

    def fill_custom_questions(self) -> list[str]:
        answered = []
        for field in self.page.locator("textarea").all():
            try:
                if field.input_value().strip():
                    continue
                question = field.get_attribute("aria-label") or field.get_attribute("placeholder") or field.evaluate(
                    "el => el.closest('label')?.innerText || el.parentElement?.innerText || ''"
                )
                question = " ".join(str(question or "").split())[:500]
                if not question or any(term in question.lower() for term in STANDARD_QUESTION_TERMS):
                    continue
                answer = answer_custom_question(question, self.profile, self.job)
                if answer:
                    type_with_delay(field, answer)
                    random_sleep(0.2, 0.7)
                    answered.append(question)
            except Exception:
                continue
        return answered

    def fill_all(self) -> dict[str, list[str]]:
        return {
            "standard_fields": self.fill_standard_fields(),
            "custom_questions": self.fill_custom_questions(),
        }
