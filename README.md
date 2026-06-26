# CareerCaddy AI

CareerCaddy AI is a human-in-the-loop job application workspace. It helps users import jobs, score fit, select the right resume, prepare application forms, review generated answers, upload resumes, and track application status.

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

Tables, the default `demo_user`, and upload folders are created automatically when the FastAPI app starts. The `/api/init-db` endpoint remains available as an optional debug endpoint, but it is not required for local or Railway startup.

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
3. Score the job.
4. Mark it ready.
5. Run `python worker/worker.py`.
6. Review the prepared application in the Review Queue.
7. Mark submitted manually only after reviewing the real application.

## Railway Setup

1. Create a Railway project.
2. Add a PostgreSQL service.
3. Connect this GitHub repository.
4. Railway should inject `DATABASE_URL`.
5. Set `GEMINI_API_KEY` only if you want Gemini-generated screening drafts.
6. Deploy. On startup, CareerCaddy AI automatically creates database tables, upload folders, and the `demo_user` profile.
7. The web process uses:

```text
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

The included `Procfile` also defines a worker process:

```text
worker: python worker/worker.py
```

Uploads are stored locally for the MVP. Railway filesystem storage is ephemeral and not durable across redeploys, so replace local uploads with S3, Cloudinary, or another persistent object store before production use.

Railway sometimes provides PostgreSQL URLs beginning with `postgres://`; the app normalizes those to SQLAlchemy's expected `postgresql://` format automatically.

## Safety

CareerCaddy AI never clicks final submit. Automation only prepares forms, saves screenshots, and moves records to `NEEDS_REVIEW`.
