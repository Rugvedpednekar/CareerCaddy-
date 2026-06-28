import re
from typing import Callable

from agent.anti_detection import click_with_pacing, random_sleep, type_with_delay
from agent.form_filler import FormFiller
from agent.resume_uploader import ResumeUploader


class ManualActionRequired(RuntimeError):
    pass


class PortalHandler:
    portal_name = "Generic"

    def __init__(
        self,
        page,
        profile: dict,
        application,
        job,
        credentials: dict[str, str] | None = None,
        resume_path: str | None = None,
        progress: Callable[[str, str], None] | None = None,
        input_fn: Callable[[str], str] = input,
    ):
        self.page = page
        self.profile = profile
        self.application = application
        self.job = job
        self.credentials = credentials or {}
        self.resume_path = resume_path
        self.progress = progress or (lambda status, message: None)
        self.input_fn = input_fn

    def navigate(self, url: str) -> None:
        self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
        self.check_for_challenge()

    def check_for_challenge(self) -> None:
        body = self.page.locator("body")
        text = body.inner_text(timeout=5000).lower() if body.count() else ""
        if "captcha" in text or "verify you are human" in text:
            raise ManualActionRequired("CAPTCHA or human verification requires manual action")

    def _first(self, *locators):
        for locator in locators:
            try:
                if locator.count() and locator.first.is_visible():
                    return locator.first
            except Exception:
                continue
        return None

    def login(self) -> None:
        password = self._first(
            self.page.get_by_label("Password", exact=False),
            self.page.locator("input[type=password]"),
        )
        if not password:
            return
        username = self._first(
            self.page.get_by_label("Email", exact=False),
            self.page.get_by_label("Username", exact=False),
            self.page.locator("input[type=email]"),
        )
        portal_username = self.credentials.get("username", "")
        portal_password = self.credentials.get("password", "")
        if username and portal_username and portal_password:
            type_with_delay(username, portal_username)
            type_with_delay(password, portal_password)
            button = self._first(
                self.page.get_by_role("button", name=re.compile(r"^(sign in|log in|continue)$", re.I)),
                self.page.locator("button[type=submit]"),
            )
            if button:
                click_with_pacing(self.page, button)
                random_sleep(1.0, 2.0)
            return

        sso = self._first(self.page.get_by_role("button", name=re.compile(r"sso|single sign|continue with", re.I)))
        if sso:
            click_with_pacing(self.page, sso)
        self.progress("logging_in", "Complete portal login in the visible browser, then return to the terminal.")
        self.input_fn("Complete login in the visible browser, then press Enter to continue: ")

    def otp_input(self):
        return self._first(
            self.page.get_by_label(re.compile(r"otp|verification code|security code", re.I)),
            self.page.locator("input[autocomplete=one-time-code]"),
            self.page.locator('input[name*="otp" i], input[name*="code" i]'),
        )

    def fill_otp(self, code: str) -> None:
        field = self.otp_input()
        if not field:
            return
        type_with_delay(field, code)
        button = self._first(
            self.page.get_by_role("button", name=re.compile(r"verify|continue|confirm", re.I)),
            self.page.locator("button[type=submit]"),
        )
        if button:
            click_with_pacing(self.page, button)
            random_sleep(0.8, 1.8)

    def fill_application(self) -> dict[str, list[str]]:
        return FormFiller(self.page, self.profile, self.application, self.job).fill_all()

    def upload_resume(self) -> bool:
        return ResumeUploader(self.page).upload(self.resume_path)

    def final_submit_button(self):
        return self._first(
            self.page.get_by_role("button", name=re.compile(r"^(submit application|submit|apply)$", re.I)),
            self.page.locator("button[type=submit]", has_text=re.compile(r"submit|apply", re.I)),
        )

    def submit(self) -> None:
        button = self.final_submit_button()
        if not button:
            raise RuntimeError("Final Submit/Apply button was not found")
        click_with_pacing(self.page, button)
        random_sleep(1.0, 2.0)
