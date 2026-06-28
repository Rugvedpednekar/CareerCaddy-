from pathlib import Path
from playwright.sync_api import sync_playwright
from backend.config import APP_ENV, IS_RAILWAY, WORKER_HEADLESS

def launch_browser():
    pw = sync_playwright().start()
    headless = APP_ENV == "production" or IS_RAILWAY or WORKER_HEADLESS
    browser = pw.chromium.launch(headless=headless, slow_mo=0 if headless else 250)
    return pw, browser

def save_screenshot(page, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(path), full_page=True)

def safe_fill_by_label(page, label, value):
    if not value:
        return False
    try:
        page.get_by_label(label, exact=False).first.fill(value, timeout=1500)
        return True
    except Exception:
        return False

def safe_fill_by_placeholder(page, placeholder, value):
    if not value:
        return False
    try:
        page.get_by_placeholder(placeholder, exact=False).first.fill(value, timeout=1500)
        return True
    except Exception:
        return False

def safe_upload_resume(page, resume_path):
    if not resume_path:
        return False
    try:
        page.locator("input[type=file]").first.set_input_files(resume_path, timeout=1500)
        return True
    except Exception:
        return False
