"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import AuthToken, User


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="আগে লগইন করুন।")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="আগে লগইন করুন।")
    row = db.scalar(select(AuthToken).where(AuthToken.token == token))
    if row is None:
        raise HTTPException(status_code=401, detail="সেশন শেষ। আবার লগইন করুন।")
    user = db.get(User, row.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="সেশন শেষ। আবার লগইন করুন।")
    return user
