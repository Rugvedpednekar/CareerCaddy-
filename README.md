# CareerCaddy AI

CareerCaddy AI is a human-in-the-loop job application workspace. It helps users import jobs, score fit, select the right resume, prepare application forms, review generated answers, upload resumes, and track application status.

The production workflow supports two isolated accounts (`rugved` and `bebu`). Passwords are supplied only through environment variables, hashed with PBKDF2 before storage, and never committed or logged. All jobs, applications, resumes, profile data, dashboard statistics, exports, and worker runs are scoped to the authenticated user.

The Railway Playwright worker intentionally does not submit applications. An optional local-only headed agent can use the user's persistent Chrome session and submit only after the user reviews a screenshot and types `YES` in the local terminal.

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

## Local Headed Application Agent

The local agent is separate from the Railway worker. It launches visible Chrome with an app-specific persistent user-data directory, so portal cookies survive between runs. The API rejects agent runs when `APP_ENV=production` or Railway environment variables are present.

Install Chrome and the Python dependencies, then configure `.env`:

```text
APP_ENV=development
CAREERCADDY_CHROME_USER_DATA_DIR=~/.careercaddy/chrome-profile
CAREERCADDY_BROWSER_CHANNEL=chrome
PORTAL_CREDENTIALS_FILE=~/.careercaddy/portal_credentials.enc
GMAIL_OAUTH_CLIENT_FILE=~/.careercaddy/gmail_credentials.json
GMAIL_OAUTH_TOKEN_FILE=~/.careercaddy/gmail_token.json
```

Generate a Fernet key once and place only the key in the local `.env` file:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Set it as `PORTAL_CREDENTIALS_KEY`, then save a portal login without putting the password in shell history or the database:

```bash
python -m agent.credential_store greenhouse
python -m agent.credential_store lever
python -m agent.credential_store workday
python -m agent.credential_store linkedin
```

The encrypted credential file and Fernet key must remain local. Do not commit either one. If a saved session is already logged in, credentials are not required.

### Gmail OTP OAuth

1. Create a Google Cloud project and enable the Gmail API.
2. Configure an OAuth consent screen for a Desktop app.
3. Download the OAuth client JSON to `~/.careercaddy/gmail_credentials.json` or the path in `GMAIL_OAUTH_CLIENT_FILE`.
4. Start an agent run. The first OTP request opens Google's local OAuth consent flow with the read-only Gmail scope.
5. The resulting refresh token is written to `GMAIL_OAUTH_TOKEN_FILE`; keep that file private and never commit it.

The OTP reader checks recent unread messages from the portal domain for subjects containing OTP, verification code, or confirm. It never logs codes and cannot modify email. If no code is found after five checks, the terminal asks for manual entry.

### Running the agent

Start FastAPI from a local interactive terminal:

```bash
uvicorn backend.main:app --reload
```

Open Job Tracker and click **🤖 Auto-Apply**. The page displays the streamed states `navigating`, `logging_in`, `otp_waiting`, `filling_fields`, `awaiting_confirmation`, `submitted`, or `failed`.

At the final gate, CareerCaddy saves and opens a screenshot while leaving the headed browser visible. The terminal accepts:

- `YES`: click the final Submit/Apply control.
- `NO`: abort without submitting.
- `EDIT`: leave the browser open for manual corrections and ask again.

You can also run the same pipeline directly:

```bash
python -m agent.orchestrator JOB_ID --user-id YOUR_USER_ID
```

Supported handlers are Greenhouse, Lever, Workday, LinkedIn Easy Apply, and a generic label-based fallback. Open-shadow-root fields are handled by Playwright locators. CAPTCHAs and human-verification challenges are never bypassed; they stop the run for manual action.

## Demo Flow

1. Open the dashboard.
2. Import a job on the Job Tracker page.
3. Click Prepare and review or edit the generated application answers.
4. Click Start Automation to queue the application.
5. Run `python worker/worker.py`.
6. Review the prepared form and screenshot in the Review Queue.
7. Open the real application link, submit it manually, then mark it submitted in CareerCaddy.

## Railway Setup

1. Create a Railway project. Railway uses the included official Playwright Docker image, which contains Chromium and its Linux system dependencies.
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

Set the Railway worker service start command to exactly:

```text
python worker/worker.py
```

Do not use `playwright install` as a Railway pre-deploy or start command. The Docker image and `playwright==1.60.0` package are version-matched, and the browser executable is already stored at `/ms-playwright` inside the runtime image rather than the disposable `/root/.cache/ms-playwright` build cache.

Uploads are stored locally for the MVP. Railway filesystem storage is ephemeral and not durable across redeploys, so replace local uploads with S3, Cloudinary, or another persistent object store before production use.

Railway sometimes provides PostgreSQL URLs beginning with `postgres://`; the app normalizes those to SQLAlchemy's expected `postgresql://` format automatically.

## Safety

- The Railway worker never clicks final submit; it only prepares forms and moves applications to `NEEDS_REVIEW`.
- The local headed agent can click final submit only after the confirmation gate receives the exact terminal response `YES`.
- CAPTCHAs, paywalls, access controls, and human-verification checks are never bypassed.
- Portal passwords are stored only in the encrypted local credential file, never in PostgreSQL or application logs.
- Gmail access uses the read-only scope, and OTP values are never logged or persisted.
