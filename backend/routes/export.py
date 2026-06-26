from io import BytesIO
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy.orm import Session
from ..config import DEFAULT_USER_ID
from ..database import get_db
from ..models import Application, Job

router = APIRouter(prefix="/api/export", tags=["export"])

@router.get("/excel")
def export_excel(db: Session = Depends(get_db)):
    wb = Workbook()
    ws = wb.active
    ws.title = "Jobs"
    ws.append(["Company", "Title", "Location", "Portal", "Fit Score", "Resume", "Status", "Apply URL"])
    for job in db.query(Job).filter(Job.user_id == DEFAULT_USER_ID).order_by(Job.created_at.desc()).all():
        ws.append([job.company, job.title, job.location, job.portal, job.fit_score, job.resume_version, job.status, job.apply_url])
    ws2 = wb.create_sheet("Applications")
    ws2.append(["Application ID", "Job ID", "Status", "Current Step", "Resume", "Blocker", "Updated"])
    for app in db.query(Application).filter(Application.user_id == DEFAULT_USER_ID).order_by(Application.updated_at.desc()).all():
        ws2.append([app.application_id, app.job_id, app.status, app.current_step, app.resume_version, app.blocker, app.updated_at.isoformat() if app.updated_at else ""])
    stream = BytesIO()
    wb.save(stream); stream.seek(0)
    return StreamingResponse(stream, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=careercaddy_export.xlsx"})
