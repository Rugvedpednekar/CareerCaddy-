import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import BASE_DIR, UPLOAD_DIR
from backend.database import SessionLocal, create_tables
from backend.models import Application, AutomationRun, Job, Resume, User, uid
from worker.browser import launch_browser, save_screenshot
from worker.portal_detector import detect_blocker, detect_portal
from worker.handlers import generic, greenhouse, lever

HANDLERS = {"greenhouse": greenhouse, "lever": lever, "generic": generic}

def asdict(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

def best_resume(db, user_id, resume_type):
    query = db.query(Resume).filter(Resume.user_id == user_id)
    resume = query.filter(Resume.resume_type == resume_type).order_by(Resume.created_at.desc()).first()
    resume = resume or query.filter(Resume.is_default.is_(True)).order_by(Resume.created_at.desc()).first()
    resume = resume or query.order_by(Resume.created_at.desc()).first()
    return resume.file_path if resume else None

def append_log(app, message):
    logs = list(app.logs or [])
    logs.append(message)
    app.logs = logs

def run_once():
    create_tables()
    db = SessionLocal()
    pw = browser = None
    try:
        applications = db.query(Application).filter(
            Application.status == "READY_FOR_WORKER",
        ).limit(5).all()
        if not applications:
            print("No READY_FOR_WORKER applications found.")
            return
        pw, browser = launch_browser()
        for app in applications:
            profile = db.query(User).filter(User.user_id == app.user_id).first() or User(user_id=app.user_id)
            job = db.query(Job).filter(Job.job_id == app.job_id, Job.user_id == app.user_id).first()
            run = AutomationRun(run_id=uid("run"), user_id=app.user_id, job_id=app.job_id, application_id=app.application_id, status="IN_PROGRESS", logs=[])
            db.add(run)
            app.status = "IN_PROGRESS"
            app.current_step = "Worker preparing form"
            append_log(app, "Worker started preparing application.")
            if job:
                job.status = "IN_PROGRESS"
            db.commit()
            if not job or not job.apply_url:
                app.status = "NEEDS_REVIEW"
                app.current_step = "Prepared for review"
                app.blocker = "Missing application URL"
                append_log(app, "Worker could not open the application because the job URL is missing.")
                run.status = "NEEDS_REVIEW"
                run.logs = list(app.logs or [])
                if job:
                    job.status = "NEEDS_REVIEW"
                db.commit()
                continue
            context = browser.new_context()
            page = context.new_page()
            try:
                page.goto(job.apply_url, wait_until="domcontentloaded", timeout=45000)
                append_log(app, "Opened application link.")
                blocker = detect_blocker(page)
                if blocker:
                    app.status = "NEEDS_REVIEW"
                    app.current_step = "Prepared for review"
                    app.blocker = "Login required" if blocker == "NEEDS_LOGIN" else "CAPTCHA requires user action"
                    append_log(app, f"Worker stopped: {app.blocker}.")
                    append_log(app, "Ready for user review.")
                    job.status = "NEEDS_REVIEW"
                    run.status = "NEEDS_REVIEW"
                    run.logs = list(app.logs or [])
                else:
                    portal = detect_portal(job.apply_url or job.portal or "")
                    handler = HANDLERS.get(portal, generic)
                    resume_path = best_resume(db, app.user_id, job.resume_version or "SWE")
                    automation_profile = asdict(profile)
                    answers = dict(app.generated_answers or {})
                    for key in ("email", "phone", "location", "linkedin", "github", "portfolio"):
                        automation_profile[key] = answers.get(key) or automation_profile.get(key)
                    full_name = answers.get("full_name", "")
                    if full_name and "Please fill" not in full_name:
                        parts = full_name.split(None, 1)
                        automation_profile["first_name"] = parts[0]
                        automation_profile["last_name"] = parts[1] if len(parts) > 1 else automation_profile.get("last_name")
                    result = handler.prepare_application(page, asdict(job), automation_profile, resume_path)
                    screenshot_dir = UPLOAD_DIR if UPLOAD_DIR.is_absolute() else BASE_DIR / UPLOAD_DIR
                    screenshot_path = screenshot_dir / "screenshots" / app.user_id / f"{app.application_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.png"
                    save_screenshot(page, screenshot_path)
                    for log in result.get("logs", []):
                        append_log(app, log)
                    append_log(app, "Filled safe known fields where possible.")
                    append_log(app, "Stopped before final submission.")
                    append_log(app, "Ready for user review.")
                    app.status = "NEEDS_REVIEW"; app.current_step = "Prepared for review"; app.screenshot_path = str(screenshot_path)
                    app.blocker = result.get("blocker")
                    app.resume_path = resume_path
                    job.status = "NEEDS_REVIEW"
                    run.status = "NEEDS_REVIEW"; run.logs = list(app.logs or []); run.screenshot_path = str(screenshot_path)
                db.commit()
            except Exception as exc:
                message = f"{type(exc).__name__}: {str(exc)[:400]}"
                app.status = "FAILED"; app.current_step = "Automation failed"; job.status = "FAILED"; app.blocker = message
                append_log(app, "Worker stopped because the application form could not be prepared.")
                run.status = "FAILED"; run.error_message = message; run.logs = list(app.logs or [])
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
