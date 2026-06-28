from pathlib import Path

from .anti_detection import click_with_pacing, random_sleep


class ResumeUploader:
    def __init__(self, page):
        self.page = page

    def upload(self, resume_path: str | Path | None) -> bool:
        if not resume_path:
            return False
        path = Path(resume_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"Resume file does not exist: {path}")

        inputs = self.page.locator("input[type=file]")
        if inputs.count() == 0:
            triggers = self.page.get_by_text("Upload resume", exact=False).or_(
                self.page.get_by_text("Attach resume", exact=False)
            )
            if triggers.count():
                click_with_pacing(self.page, triggers.first)
                random_sleep(0.3, 0.8)
                inputs = self.page.locator("input[type=file]")
        if inputs.count() == 0:
            return False

        inputs.first.set_input_files(str(path))
        random_sleep(0.5, 1.2)
        confirmation = self.page.get_by_text(path.name, exact=False)
        return confirmation.count() > 0 or bool(inputs.first.input_value())
