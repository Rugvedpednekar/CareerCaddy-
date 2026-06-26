from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..config import DEFAULT_USER_ID
from ..database import get_db
from ..models import User
from ..schemas import ProfileIn

router = APIRouter(prefix="/api/profile", tags=["profile"])

@router.get("")
def get_profile(db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == DEFAULT_USER_ID).first()
    if not user:
        user = User(user_id=DEFAULT_USER_ID, first_name="Demo", last_name="User", email="demo@example.com", work_authorization="Yes", sponsorship_answer="I am eligible to work in the U.S. on OPT and may require sponsorship in the future.")
        db.add(user); db.commit(); db.refresh(user)
    return user

@router.post("")
def save_profile(payload: ProfileIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == DEFAULT_USER_ID).first()
    if not user:
        user = User(user_id=DEFAULT_USER_ID)
        db.add(user)
    for key, value in payload.model_dump().items():
        setattr(user, key, value)
    db.commit(); db.refresh(user)
    return user
