import json

from fastapi import Depends, Header, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import ALLOW_DEV_UNAUTHENTICATED, DEFAULT_USER_ID, SESSION_SECRET_KEY
from .database import get_db
from .models import User
from .security import decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_user_id: str | None = Header(None, alias="X-User-Id"),
    query_user_id: str | None = Query(None, alias="user_id"),
    db: Session = Depends(get_db),
) -> User:
    if credentials:
        if len(SESSION_SECRET_KEY) < 32:
            raise HTTPException(500, "SESSION_SECRET_KEY is not configured")
        try:
            claims = decode_access_token(credentials.credentials, SESSION_SECRET_KEY)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            raise HTTPException(401, "Invalid or expired session") from exc
        user_id = claims.get("sub")
        if (x_user_id and x_user_id != user_id) or (query_user_id and query_user_id != user_id):
            raise HTTPException(403, "User identity does not match authenticated session")
    elif ALLOW_DEV_UNAUTHENTICATED:
        user_id = DEFAULT_USER_ID
    else:
        raise HTTPException(401, "Authentication required")
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(401, "Authenticated user not found")
    return user
