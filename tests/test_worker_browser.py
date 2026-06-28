import unittest
from unittest.mock import MagicMock, patch

from worker.browser import launch_browser


class WorkerBrowserTests(unittest.TestCase):
    def test_launch_browser_uses_railway_safe_sync_chromium(self):
        playwright = MagicMock()
        browser = object()
        playwright.chromium.launch.return_value = browser

        with patch("worker.browser.sync_playwright") as sync_playwright:
            sync_playwright.return_value.start.return_value = playwright
            result = launch_browser()

        self.assertEqual(result, (playwright, browser))
        playwright.chromium.launch.assert_called_once_with(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        playwright.stop.assert_not_called()

    def test_launch_browser_stops_playwright_when_chromium_fails(self):
        playwright = MagicMock()
        playwright.chromium.launch.side_effect = RuntimeError("Chromium executable missing")

        with patch("worker.browser.sync_playwright") as sync_playwright:
            sync_playwright.return_value.start.return_value = playwright
            with self.assertRaisesRegex(RuntimeError, "Chromium executable missing"):
                launch_browser()

        playwright.stop.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
