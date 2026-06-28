import re

from agent.anti_detection import random_sleep, randomized_scroll
from agent.form_filler import FormFiller

from .base import PortalHandler


class WorkdayHandler(PortalHandler):
    portal_name = "Workday"

    def fill_application(self) -> dict[str, list[str]]:
        """Search the main document and frames; Playwright pierces open shadow roots."""
        result = {"standard_fields": [], "custom_questions": []}
        last_error = None
        scopes = [self.page, *[frame for frame in self.page.frames if frame != self.page.main_frame]]
        for scope in scopes:
            for _ in range(3):
                try:
                    scope.locator(
                        "section, div[data-automation-id]",
                        has_text=re.compile(r"application|experience|education|contact", re.I),
                    ).count()
                    randomized_scroll(self.page)
                    current = FormFiller(scope, self.profile, self.application, self.job).fill_all()
                    for key in result:
                        result[key].extend(value for value in current[key] if value not in result[key])
                    break
                except Exception as exc:
                    last_error = exc
                    random_sleep(1.0, 2.0)
            if result["standard_fields"] or result["custom_questions"]:
                return result
        if last_error:
            raise last_error
        return result
