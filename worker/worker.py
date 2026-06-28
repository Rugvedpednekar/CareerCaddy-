import sys
import time
from datetime import datetime
from pathlib import Path

from sqlalchemy import func

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import BASE_DIR, UPLOAD_DIR
from backend.database import SessionLocal, create_tables, engine
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

def append_run_log(run, message):
    logs = list(run.logs or [])
    logs.append(message)
    run.logs = logs

def record_progress(db, app, run, current_step, *messages, status=None):
    app.current_step = current_step
    if status:
        app.status = status
        run.status = status
    for message in messages:
        append_log(app, message)
        append_run_log(run, message)
    db.commit()

def take_progress_screenshot(db, page, app, run, label):
    screenshot_dir = UPLOAD_DIR if UPLOAD_DIR.is_absolute() else BASE_DIR / UPLOAD_DIR
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
    screenshot_path = screenshot_dir / "screenshots" / app.user_id / f"{app.application_id}_{label}_{timestamp}.png"
    save_screenshot(page, screenshot_path)
    app.screenshot_path = str(screenshot_path)
    run.screenshot_path = str(screenshot_path)
    append_log(app, f"Screenshot captured: {label}.")
    append_run_log(run, f"Screenshot captured: {label} ({screenshot_path}).")
    db.commit()
    return screenshot_path

def log_queue_counts(db):
    rows = db.query(Application.status, func.count(Application.id)).group_by(Application.status).all()
    counts = {status: count for status, count in rows}
    print(
        "Queue status counts: "
        f"READY_FOR_WORKER={counts.get('READY_FOR_WORKER', 0)}, "
        f"IN_PROGRESS={counts.get('IN_PROGRESS', 0)}, "
        f"NEEDS_REVIEW={counts.get('NEEDS_REVIEW', 0)}, "
        f"FAILED={counts.get('FAILED', 0)}",
        flush=True,
    )

def run_once():
    create_tables()
    db = SessionLocal()
    pw = browser = None
    try:
        log_queue_counts(db)
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
            if job:
                job.status = "IN_PROGRESS"
            record_progress(
                db, app, run, "Worker picked up application",
                "Worker picked up application.",
                "Worker started preparing application.",
                status="IN_PROGRESS",
            )
            if not job or not job.apply_url:
                app.blocker = "Missing application URL"
                if job:
                    job.status = "NEEDS_REVIEW"
                record_progress(
                    db, app, run, "Prepared for review",
                    "Worker could not open the application because the job URL is missing.",
                    "Stopped before final submission.",
                    "Ready for user review.",
                    status="NEEDS_REVIEW",
                )
                continue
            context = None
            try:
                context = browser.new_context()
                page = context.new_page()
                record_progress(db, app, run, "Opening application page", "Opening application URL.")
                page.goto(job.apply_url, wait_until="domcontentloaded", timeout=45000)
                append_log(app, "Page loaded successfully.")
                append_run_log(run, "Page loaded successfully.")
                db.commit()
                take_progress_screenshot(db, page, app, run, "page_loaded")
                portal = detect_portal(job.apply_url or job.portal or "")
                portal_name = portal.replace("_", " ").title()
                record_progress(
                    db, app, run, "Checking blockers",
                    f"Detected portal: {portal_name}.",
                    "Checking for login/CAPTCHA/blockers.",
                )
                blocker = detect_blocker(page)
                if blocker:
                    app.blocker = "Login required" if blocker == "NEEDS_LOGIN" else "CAPTCHA requires user action"
                    job.status = "NEEDS_REVIEW"
                    take_progress_screenshot(db, page, app, run, "final_review_state")
                    record_progress(
                        db, app, run, "Prepared for review",
                        f"Worker stopped: {app.blocker}.",
                        "Stopped before final submission.",
                        "Ready for user review.",
                        status="NEEDS_REVIEW",
                    )
                else:
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
                    resume_log = f"Loaded resume path: {Path(resume_path).name}." if resume_path else "No resume path available."
                    record_progress(
                        db, app, run, "Filling known fields",
                        f"Loaded generated answers ({len(answers)} fields).",
                        resume_log,
                        "Filling safe known fields.",
                        "Uploading resume if supported.",
                    )
                    result = handler.prepare_application(page, asdict(job), automation_profile, resume_path)
                    for log in result.get("logs", []):
                        append_log(app, log)
                        append_run_log(run, log)
                    append_log(app, "Filled safe known fields where possible.")
                    append_run_log(run, "Filled safe known fields where possible.")
                    db.commit()
                    record_progress(db, app, run, "Saving screenshot", "Taking screenshot.")
                    take_progress_screenshot(db, page, app, run, "after_fields_filled")
                    take_progress_screenshot(db, page, app, run, "final_review_state")
                    app.blocker = result.get("blocker")
                    app.resume_path = resume_path
                    job.status = "NEEDS_REVIEW"
                    record_progress(
                        db, app, run, "Prepared for review",
                        "Stopped before final submission.",
                        "Ready for user review.",
                        status="NEEDS_REVIEW",
                    )
            except Exception as exc:
                message = f"{type(exc).__name__}: {str(exc)[:400]}"
                db.rollback()
                app.blocker = message
                if job:
                    job.status = "FAILED"
                run.error_message = message
                record_progress(
                    db, app, run, "Automation failed",
                    "Worker stopped because the application form could not be prepared.",
                    "Stopped before final submission.",
                    status="FAILED",
                )
            finally:
                if context:
                    context.close()
    finally:
        if browser:
            browser.close()
        if pw:
            pw.stop()
        db.close()

if __name__ == "__main__":
    create_tables()
    print("CareerCaddy worker started.", flush=True)
    print(f"Worker database host: {engine.url.host}", flush=True)
    print(f"Worker database name: {engine.url.database}", flush=True)

    while True:
        try:
            run_once()
        except Exception as exc:
            print(f"Worker loop error: {type(exc).__name__}: {str(exc)[:500]}", flush=True)
        time.sleep(15)
