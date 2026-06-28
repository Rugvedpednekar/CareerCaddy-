from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..auth import get_current_user
from ..database import get_db
from ..models import User
from ..schemas import ProfileIn

router = APIRouter(prefix="/api/profile", tags=["profile"])

@router.get("")
def get_profile(user: User = Depends(get_current_user)):
    return user

@router.post("")
def save_profile(payload: ProfileIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    for key, value in payload.model_dump().items():
        setattr(user, key, value)
    user.full_name = " ".join(value for value in (user.first_name, user.last_name) if value).strip() or user.full_name
    db.commit(); db.refresh(user)
    return user
