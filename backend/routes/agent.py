import json
import queue
import threading

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from agent.orchestrator import AgentOrchestrator
from ..auth import get_current_user
from ..config import APP_ENV, IS_RAILWAY
from ..database import get_db
from ..models import Job, User


router = APIRouter(prefix="/api/agent", tags=["local-agent"])
TERMINAL_EVENTS = {"submitted", "aborted", "failed"}


@router.post("/run/{job_id}")
def run_agent(job_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if APP_ENV == "production" or IS_RAILWAY:
        raise HTTPException(409, "The headed application agent can only run on the user's local computer.")
    job = db.query(Job).filter(Job.job_id == job_id, Job.user_id == user.user_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    if not job.apply_url:
        raise HTTPException(409, "This job does not have an application URL.")

    events: queue.Queue[dict[str, str]] = queue.Queue()

    def publish(status: str, message: str) -> None:
        events.put({"status": status, "message": message})

    def execute() -> None:
        try:
            AgentOrchestrator().run(job_id, user.user_id, publish)
        except Exception as exc:
            publish("failed", f"Agent process failed: {type(exc).__name__}: {str(exc)[:300]}")

    threading.Thread(target=execute, name=f"careercaddy-agent-{job_id}", daemon=True).start()

    def stream():
        while True:
            event = events.get()
            yield f"event: status\ndata: {json.dumps(event)}\n\n"
            if event["status"] in TERMINAL_EVENTS:
                break

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
