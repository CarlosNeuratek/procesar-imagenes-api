"""Auth business logic — DB-backed bcrypt + opaque tokens."""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import tokens
from .models import User
from .security import verify_password


def _user_public(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
    }


def authenticate(email: str, password: str, db: Session) -> User | None:
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def login(email: str, password: str, db: Session) -> dict:
    user = authenticate(email, password, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = tokens.issue(user, db)
    return {"token": token, "user": _user_public(user)}


def me(token: str, db: Session) -> dict:
    user = tokens.resolve(token, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return user