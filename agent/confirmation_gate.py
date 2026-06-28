import os
import platform
import subprocess
from pathlib import Path
from typing import Callable


class ConfirmationGate:
    def __init__(self, input_fn: Callable[[str], str] = input, log_fn: Callable[[str], None] | None = None):
        self.input_fn = input_fn
        self.log_fn = log_fn or (lambda message: None)

    def _open_screenshot(self, path: Path) -> None:
        system = platform.system()
        if system == "Windows":
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif system == "Darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def confirm(self, page, screenshot_path: str | Path) -> str:
        path = Path(screenshot_path).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            page.screenshot(path=str(path), full_page=True)
            self._open_screenshot(path)
            decision = self.input_fn(
                "Review the screenshot and visible browser. Type YES to submit, NO to abort, or EDIT for manual corrections: "
            ).strip().upper()
            if decision == "YES":
                self.log_fn("User confirmed final submission.")
                return "YES"
            if decision == "NO":
                self.log_fn("User aborted final submission.")
                return "NO"
            if decision == "EDIT":
                self.log_fn("User requested manual corrections before confirmation.")
                self.input_fn("Make corrections in the browser, then press Enter to review again: ")
                continue
            print("Please type YES, NO, or EDIT.")
