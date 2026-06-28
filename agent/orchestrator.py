import argparse
from datetime import datetime
from pathlib import Path
from typing import Callable

from backend.candidate_context import build_candidate_context
from backend.config import BASE_DIR, DEFAULT_USER_ID, UPLOAD_DIR
from backend.database import SessionLocal
from backend.models import Application, AutomationRun, Job, User, uid

from .browser_session import BrowserSession
from .confirmation_gate import ConfirmationGate
from .credential_store import get_portal_credentials
from .otp_handler import OTPHandler
from .portal_handlers import build_handler, portal_domain
from .portal_handlers.base import ManualActionRequired


ProgressCallback = Callable[[str, str], None]


def _append_log(record, message: str) -> None:
    logs = list(record.logs or [])
    logs.append(message)
    record.logs = logs


class AgentOrchestrator:
    def __init__(
        self,
        session_factory=SessionLocal,
        browser_session_factory=BrowserSession,
        otp_handler_factory=OTPHandler,
        confirmation_gate_factory=ConfirmationGate,
    ):
        self.session_factory = session_factory
        self.browser_session_factory = browser_session_factory
        self.otp_handler_factory = otp_handler_factory
        self.confirmation_gate_factory = confirmation_gate_factory

    def run(self, job_id: str, user_id: str, progress_callback: ProgressCallback | None = None) -> str:
        emit = progress_callback or (lambda status, message: None)
        db = self.session_factory()
        browser_session = None
        application = run = job = None

        def record(status: str, message: str, db_status: str | None = None) -> None:
            if application is not None:
                application.current_step = message[:120]
                if db_status:
                    application.status = db_status
                _append_log(application, message)
            if run is not None:
                if db_status:
                    run.status = db_status
                _append_log(run, message)
            db.commit()
            emit(status, message)

        try:
            job = db.query(Job).filter(Job.job_id == job_id, Job.user_id == user_id).first()
            if not job:
                raise ValueError("Job not found for the authenticated user")
            if not job.apply_url:
                raise ValueError("Job does not have an application URL")
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                raise ValueError("User profile not found")

            application = db.query(Application).filter(
                Application.job_id == job_id,
                Application.user_id == user_id,
            ).first()
            if not application:
                application = Application(
                    application_id=uid("app"),
                    user_id=user_id,
                    job_id=job_id,
                    status="IN_PROGRESS",
                    current_step="Starting local agent",
                    logs=[],
                )
                db.add(application)

            candidate = build_candidate_context(db, user_id, job.resume_version)
            profile = dict(candidate["candidate"])
            profile.update({
                "first_name": user.first_name,
                "last_name": user.last_name,
                "full_name": user.full_name or " ".join(filter(None, [user.first_name, user.last_name])),
                "email": user.email or profile.get("email"),
                "phone": user.phone or profile.get("phone"),
                "address": user.location or profile.get("location"),
                "location": user.location or profile.get("location"),
                "linkedin": user.linkedin or profile.get("linkedin"),
                "github": user.github or profile.get("github"),
                "portfolio": user.portfolio or profile.get("portfolio"),
                "school": user.school,
                "degree": user.degree or profile.get("degree"),
                "work_authorization": user.work_authorization or profile.get("work_authorization"),
                "visa_type": user.sponsorship_answer,
                "sponsorship_answer": user.sponsorship_answer,
            })
            resume = candidate.get("resume")
            resume_path = resume.file_path if resume else application.resume_path
            application.resume_path = resume_path
            application.resume_version = resume.resume_type if resume else job.resume_version

            run = AutomationRun(
                run_id=uid("agent"),
                user_id=user_id,
                job_id=job_id,
                application_id=application.application_id,
                status="IN_PROGRESS",
                logs=[],
            )
            db.add(run)
            job.status = "IN_PROGRESS"
            record("navigating", "Starting visible local browser session.", "IN_PROGRESS")

            browser_session = self.browser_session_factory().start()
            page = browser_session.page
            portal, handler = build_handler(
                job.portal,
                job.apply_url,
                page=page,
                profile=profile,
                application=application,
                job=job,
                credentials=get_portal_credentials(portal_key_for_credentials(job.portal, job.apply_url)),
                resume_path=resume_path,
                progress=lambda status, message: record(status, message),
            )
            record("navigating", f"Navigating to {handler.portal_name} application page.")
            handler.navigate(job.apply_url)

            record("logging_in", "Checking saved portal session and login state.")
            handler.login()
            handler.check_for_challenge()

            if handler.otp_input():
                record("otp_waiting", "Waiting for a portal verification code from Gmail.")
                code = self.otp_handler_factory().wait_for_code(portal_domain(job.apply_url))
                if not code:
                    raise ManualActionRequired("OTP was not provided")
                handler.fill_otp(code)
                record("logging_in", "Verification code accepted; continuing application.")

            record("filling_fields", "Filling standard profile fields and tailored application answers.")
            result = handler.fill_application()
            record(
                "filling_fields",
                f"Filled {len(result['standard_fields'])} standard fields and {len(result['custom_questions'])} custom answers.",
            )
            uploaded = handler.upload_resume()
            record("filling_fields", "Resume uploaded successfully." if uploaded else "No supported resume upload field was found.")

            screenshot_root = UPLOAD_DIR if UPLOAD_DIR.is_absolute() else BASE_DIR / UPLOAD_DIR
            screenshot_path = screenshot_root / "agent_screenshots" / user_id / (
                f"{application.application_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.png"
            )
            application.screenshot_path = str(screenshot_path)
            run.screenshot_path = str(screenshot_path)
            record("awaiting_confirmation", "Application is ready. Waiting for explicit YES in the local terminal.", "AWAITING_CONFIRMATION")
            gate = self.confirmation_gate_factory(log_fn=lambda message: record("awaiting_confirmation", message))
            decision = gate.confirm(page, screenshot_path)
            if decision != "YES":
                application.blocker = "User aborted before submission"
                job.status = "READY_TO_APPLY"
                record("aborted", "Application aborted by user; nothing was submitted.", "ABORTED")
                return "ABORTED"

            record("awaiting_confirmation", "Explicit confirmation received; clicking the final submit control.")
            handler.submit()
            job.status = "SUBMITTED"
            application.blocker = None
            record("submitted", "Application submitted after explicit user confirmation.", "SUBMITTED")
            return "SUBMITTED"
        except ManualActionRequired as exc:
            if application is not None:
                application.blocker = str(exc)
            if job is not None:
                job.status = "NEEDS_REVIEW"
            record("failed", f"Manual action required: {exc}", "NEEDS_REVIEW")
            return "NEEDS_REVIEW"
        except Exception as exc:
            db.rollback()
            message = f"{type(exc).__name__}: {str(exc)[:400]}"
            if application is not None:
                application.blocker = message
            if run is not None:
                run.error_message = message
            if job is not None:
                job.status = "FAILED"
            record("failed", f"Local agent failed: {message}", "FAILED")
            return "FAILED"
        finally:
            if browser_session:
                browser_session.close()
            db.close()


def portal_key_for_credentials(portal: str | None, url: str) -> str:
    from .portal_handlers import portal_key

    return portal_key(portal, url)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local CareerCaddy application agent")
    parser.add_argument("job_id")
    parser.add_argument("--user-id", default=DEFAULT_USER_ID)
    args = parser.parse_args()
    AgentOrchestrator().run(args.job_id, args.user_id, lambda status, message: print(f"[{status}] {message}", flush=True))


if __name__ == "__main__":
    main()
