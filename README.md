# CareerCaddy AI

CareerCaddy AI is a human-in-the-loop job application workspace. It helps users import jobs, score fit, select the right resume, prepare application forms, review generated answers, upload resumes, and track application status.

The production workflow supports two isolated accounts (`rugved` and `bebu`). Passwords are supplied only through environment variables, hashed with PBKDF2 before storage, and never committed or logged. All jobs, applications, resumes, profile data, dashboard statistics, exports, and worker runs are scoped to the authenticated user.

The app intentionally does not blind-submit applications. The Playwright worker can prepare a form and capture a screenshot, but it always stops before final submission and marks the application `NEEDS_REVIEW`. The user must manually review the application and click the UI control to mark it submitted.

## Architecture

- Frontend: plain HTML, Tailwind CDN, vanilla JavaScript, adapted from the attached Google Stitch dashboard export.
- Backend: FastAPI, SQLAlchemy, PostgreSQL-compatible models.
- Database: PostgreSQL on Railway for deployment. Local development can use PostgreSQL via `DATABASE_URL`; if omitted, the app falls back to a local SQLite file so the UI can still be exercised.
- Worker: Python Playwright browser automation for Greenhouse, Lever, and generic forms.
- Storage: local `uploads/` folder for MVP.
- AI: Gemini is optional. Missing `GEMINI_API_KEY` returns safe placeholder drafts.

## Local Setup

```bash
cd career-caddy-ai
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
playwright install
copy .env.example .env
uvicorn backend.main:app --reload
```

For PostgreSQL, set `DATABASE_URL` in `.env`:

```text
DATABASE_URL=postgresql://postgres:password@localhost:5432/careercaddy
```

Tables, additive schema upgrades, seeded user records, and upload folders are handled automatically when FastAPI starts. The authenticated `/api/init-db` endpoint remains available for debugging but is never required for local or Railway startup.

For local login, set `SESSION_SECRET_KEY`, `RUGVED_INITIAL_PASSWORD`, and `AKANSHA_INITIAL_PASSWORD` in `.env`. Existing password hashes are preserved on startup. In production, authentication is required for every application API except login and health checks.

The Job Tracker supports public job links, pasted job-posting text, and manual entry. Link and text imports extract structured details, score the role, and save it automatically. Pages that require login, present a CAPTCHA, block automated access, or do not expose enough required fields fall back to manual import.

## Run

```bash
uvicorn backend.main:app --reload
```

Pages:

- `http://localhost:8000/dashboard.html`
- `http://localhost:8000/jobs.html`
- `http://localhost:8000/review.html`
- `http://localhost:8000/applications.html`
- `http://localhost:8000/resumes.html`
- `http://localhost:8000/profile.html`
- `http://localhost:8000/settings.html`

Run the worker:

```bash
python worker/worker.py
```

## Demo Flow

1. Open the dashboard.
2. Import a job on the Job Tracker page.
3. Click Prepare and review or edit the generated application answers.
4. Click Start Automation to queue the application.
5. Run `python worker/worker.py`.
6. Review the prepared form and screenshot in the Review Queue.
7. Open the real application link, submit it manually, then mark it submitted in CareerCaddy.

## Railway Setup

1. Create a Railway project.
2. Add a PostgreSQL service.
3. Connect this GitHub repository.
4. Railway should inject `DATABASE_URL`.
5. Set `GEMINI_API_KEY` only if you want Gemini-generated screening drafts.
6. Set `SESSION_SECRET_KEY`, `RUGVED_INITIAL_PASSWORD`, and `AKANSHA_INITIAL_PASSWORD` as Railway variables. Never commit their values.
7. Set `APP_ENV=production`, `DEFAULT_USER_ID=rugved_pednekar`, and `UPLOAD_DIR=uploads`.
8. Deploy. Startup performs additive schema upgrades, creates upload folders, and seeds missing user records without dropping data or replacing existing password hashes.
7. The web process uses:

```text
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

The included `Procfile` also defines a worker process:

```text
worker: python worker/worker.py
```

Configure the worker service with the same `DATABASE_URL`, `SESSION_SECRET_KEY`, `UPLOAD_DIR`, and optional `GEMINI_API_KEY` as the web service. Set `APP_ENV=production`. The worker polls `READY_FOR_WORKER` applications for all users, fills safe known fields from that application owner only, captures a screenshot when possible, and always stops before final submission.

Uploads are stored locally for the MVP. Railway filesystem storage is ephemeral and not durable across redeploys, so replace local uploads with S3, Cloudinary, or another persistent object store before production use.

Railway sometimes provides PostgreSQL URLs beginning with `postgres://`; the app normalizes those to SQLAlchemy's expected `postgresql://` format automatically.

## Safety

CareerCaddy AI never clicks final submit. Automation only prepares forms, saves screenshots, and moves records to `NEEDS_REVIEW`.
