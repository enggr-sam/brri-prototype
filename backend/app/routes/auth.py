"""Register and log in with a mobile number + password."""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import AuthToken, User
from app.schemas.auth import AuthRequest, AuthResponse, UserOut
from app.utils.security import hash_password, new_token, normalize_mobile, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_out(user: User) -> UserOut:
    return UserOut(id=user.id, mobile=user.mobile, created_at=user.created_at)


def _issue_token(db: Session, user: User) -> str:
    token = new_token()
    db.add(AuthToken(token=token, user_id=user.id))
    db.commit()
    return token


@router.post("/register", response_model=AuthResponse)
def register(body: AuthRequest, db: Session = Depends(get_db)) -> AuthResponse:
    mobile = normalize_mobile(body.mobile)
    if len(body.password) < 4:
        raise HTTPException(status_code=400, detail="পাসওয়ার্ড কমপক্ষে ৪ অক্ষর হতে হবে।")
    exists = db.scalar(select(User).where(User.mobile == mobile))
    if exists:
        raise HTTPException(
            status_code=409,
            detail="এই মোবাইল নম্বর দিয়ে আগেই একাউন্ট আছে। লগইন করুন।",
        )
    user = User(mobile=mobile, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return AuthResponse(token=_issue_token(db, user), user=_user_out(user))


@router.post("/login", response_model=AuthResponse)
def login(body: AuthRequest, db: Session = Depends(get_db)) -> AuthResponse:
    mobile = normalize_mobile(body.mobile)
    user = db.scalar(select(User).where(User.mobile == mobile))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="মোবাইল নম্বর বা পাসওয়ার্ড ভুল।")
    return AuthResponse(token=_issue_token(db, user), user=_user_out(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(user)


@router.post("/logout")
def logout(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> dict:
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        row = db.get(AuthToken, token)
        if row is not None:
            db.delete(row)
            db.commit()
    return {"ok": True}
