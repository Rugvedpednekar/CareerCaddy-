from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import SESSION_SECRET_KEY
from ..database import get_db
from ..models import User
from ..security import create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


def public_user(user: User) -> dict:
    return {
        "user_id": user.user_id,
        "username": user.username,
        "full_name": user.full_name or " ".join(value for value in (user.first_name, user.last_name) if value),
        "profile_type": user.profile_type,
        "target_roles": user.target_roles or [],
    }


@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username.strip().lower()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Invalid username or password")
    if len(SESSION_SECRET_KEY) < 32:
        raise HTTPException(503, "Login is not configured")
    return {
        "access_token": create_access_token(user.user_id, user.username or "", SESSION_SECRET_KEY),
        "token_type": "bearer",
        "user": public_user(user),
    }


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return public_user(user)


@router.post("/logout")
def logout(user: User = Depends(get_current_user)):
    return {"success": True}
