import os
from pathlib import Path

from playwright.sync_api import BrowserContext, Page, Playwright, sync_playwright


class BrowserSession:
    """A visible persistent Chrome session owned by the local CareerCaddy agent."""

    def __init__(self, user_data_dir: str | Path | None = None, channel: str | None = None):
        configured_dir = user_data_dir or os.getenv("CAREERCADDY_CHROME_USER_DATA_DIR", "~/.careercaddy/chrome-profile")
        self.user_data_dir = Path(configured_dir).expanduser().resolve()
        self.channel = channel if channel is not None else os.getenv("CAREERCADDY_BROWSER_CHANNEL", "chrome")
        self.playwright: Playwright | None = None
        self.context: BrowserContext | None = None

    def start(self) -> "BrowserSession":
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.playwright = sync_playwright().start()
        launch_options = {
            "headless": False,
            "no_viewport": True,
            "args": ["--start-maximized"],
        }
        if self.channel:
            launch_options["channel"] = self.channel
        try:
            self.context = self.playwright.chromium.launch_persistent_context(
                str(self.user_data_dir),
                **launch_options,
            )
        except Exception:
            self.playwright.stop()
            self.playwright = None
            raise
        return self

    @property
    def page(self) -> Page:
        if not self.context:
            raise RuntimeError("Browser session has not been started")
        return self.context.pages[0] if self.context.pages else self.context.new_page()

    def close(self) -> None:
        try:
            if self.context:
                self.context.close()
        finally:
            self.context = None
            if self.playwright:
                self.playwright.stop()
                self.playwright = None

    def __enter__(self) -> "BrowserSession":
        return self.start()

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()
