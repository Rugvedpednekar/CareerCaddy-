import re

from agent.anti_detection import click_with_pacing, random_sleep

from .base import PortalHandler


class LinkedInHandler(PortalHandler):
    portal_name = "LinkedIn"

    def fill_application(self) -> dict[str, list[str]]:
        easy_apply = self._first(self.page.get_by_role("button", name=re.compile(r"easy apply", re.I)))
        if easy_apply:
            click_with_pacing(self.page, easy_apply)
            random_sleep(0.8, 1.5)

        combined = {"standard_fields": [], "custom_questions": []}
        for _ in range(10):
            current = super().fill_application()
            for key in combined:
                combined[key].extend(value for value in current[key] if value not in combined[key])
            self.upload_resume()
            if self.final_submit_button():
                break
            next_button = self._first(
                self.page.get_by_role("button", name=re.compile(r"^(next|continue|review)$", re.I))
            )
            if not next_button:
                break
            click_with_pacing(self.page, next_button)
            random_sleep(0.6, 1.4)
        return combined
