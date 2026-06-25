"""HTTP layer for /auth/* endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from ..db import get_db
from . import service
from .schemas import LoginRequest, TokenResponse, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    return TokenResponse(**service.login(payload.email, payload.password, db))


@router.get("/me", response_model=UserPublic)
def me(
    request: Request,
    db: Session = Depends(get_db),
) -> UserPublic:
    auth = request.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    token = auth.split(" ", 1)[1].strip()
    user = service.me(token, db)
    return UserPublic(**user)