from worker.browser import safe_fill_by_label, safe_fill_by_placeholder, safe_upload_resume

def prepare_application(page, job, profile, resume_path) -> dict:
    logs = []
    fields = {
        "First Name": profile.get("first_name"),
        "Last Name": profile.get("last_name"),
        "Email": profile.get("email"),
        "Phone": profile.get("phone"),
        "LinkedIn": profile.get("linkedin"),
        "GitHub": profile.get("github"),
        "Portfolio": profile.get("portfolio"),
    }
    for label, value in fields.items():
        if safe_fill_by_label(page, label, value) or safe_fill_by_placeholder(page, label, value):
            logs.append(f"Filled {label}")
    if safe_upload_resume(page, resume_path):
        logs.append("Uploaded resume")
    logs.append("Stopped before final submit; user review required.")
    return {"status": "NEEDS_REVIEW", "logs": logs, "blocker": None}
