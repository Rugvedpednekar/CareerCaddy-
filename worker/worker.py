import traceback
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import BASE_DIR, DEFAULT_USER_ID, UPLOAD_DIR
from backend.database import SessionLocal, create_tables
from backend.models import Application, AutomationRun, Job, Resume, User, uid
from worker.browser import launch_browser, save_screenshot
from worker.portal_detector import detect_blocker, detect_portal
from worker.handlers import generic, greenhouse, lever

HANDLERS = {"greenhouse": greenhouse, "lever": lever, "generic": generic}

def asdict(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

def best_resume(db, resume_type):
    resume = db.query(Resume).filter(Resume.user_id == DEFAULT_USER_ID, Resume.resume_type == resume_type).order_by(Resume.created_at.desc()).first()
    return resume.file_path if resume else None

def run_once():
    create_tables()
    db = SessionLocal()
    pw = browser = None
    try:
        jobs = db.query(Job).filter(Job.user_id == DEFAULT_USER_ID, Job.status == "READY_TO_APPLY").limit(5).all()
        if not jobs:
            print("No READY_TO_APPLY jobs found.")
            return
        profile = db.query(User).filter(User.user_id == DEFAULT_USER_ID).first() or User(user_id=DEFAULT_USER_ID)
        pw, browser = launch_browser()
        for job in jobs:
            run = AutomationRun(run_id=uid("run"), user_id=DEFAULT_USER_ID, job_id=job.job_id, status="IN_PROGRESS", logs=[])
            db.add(run)
            app = db.query(Application).filter(Application.job_id == job.job_id, Application.user_id == DEFAULT_USER_ID).first()
            if not app:
                app = Application(application_id=uid("app"), user_id=DEFAULT_USER_ID, job_id=job.job_id, status="IN_PROGRESS", current_step="OPENING_PORTAL", resume_version=job.resume_version)
                db.add(app)
            job.status = "IN_PROGRESS"; app.status = "IN_PROGRESS"
            db.commit()
            context = browser.new_context()
            page = context.new_page()
            try:
                page.goto(job.apply_url, wait_until="domcontentloaded", timeout=45000)
                blocker = detect_blocker(page)
                if blocker:
                    app.status = blocker; job.status = blocker; app.blocker = blocker
                else:
                    portal = detect_portal(job.apply_url or job.portal or "")
                    handler = HANDLERS.get(portal, generic)
                    resume_path = best_resume(db, job.resume_version or "SWE")
                    result = handler.prepare_application(page, asdict(job), asdict(profile), resume_path)
                    screenshot_dir = UPLOAD_DIR if UPLOAD_DIR.is_absolute() else BASE_DIR / UPLOAD_DIR
                    screenshot_path = screenshot_dir / "screenshots" / DEFAULT_USER_ID / f"{app.application_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.png"
                    save_screenshot(page, screenshot_path)
                    app.status = "NEEDS_REVIEW"; app.current_step = "FORM_PREPARED"; app.screenshot_path = str(screenshot_path)
                    app.logs = result.get("logs", [])
                    app.blocker = result.get("blocker")
                    app.resume_path = resume_path
                    job.status = "NEEDS_REVIEW"
                    run.status = "NEEDS_REVIEW"; run.logs = app.logs; run.screenshot_path = str(screenshot_path)
                db.commit()
            except Exception as exc:
                app.status = "FAILED"; job.status = "FAILED"; app.blocker = str(exc)
                run.status = "FAILED"; run.error_message = traceback.format_exc()
                db.commit()
            finally:
                context.close()
    finally:
        if browser:
            browser.close()
        if pw:
            pw.stop()
        db.close()

if __name__ == "__main__":
    run_once()
