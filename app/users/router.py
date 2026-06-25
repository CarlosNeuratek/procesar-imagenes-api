"""User management endpoints — admin-only."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth.models import User
from ..auth.schemas import Role, UserCreate, UserPublic
from ..auth.security import hash_password, require_admin
from ..db import get_db

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserPublic])
def list_users(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
) -> list[UserPublic]:
    users = db.execute(select(User).limit(limit).offset(offset)).scalars().all()
    return [
        UserPublic(id=u.id, email=u.email, name=u.name, role=u.role) for u in users
    ]


@router.post("", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    _admin: dict = Depends(require_admin),
) -> UserPublic:
    user = User(
        email=payload.email,
        name=payload.name,
        role=payload.role.value if isinstance(payload.role, Role) else payload.role,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )
    return UserPublic(id=user.id, email=user.email, name=user.name, role=user.role)