"""DB-backed opaque token store.

ponytail: secrets.token_urlsafe(32) -> 43 chars, 256 bits entropy. No JWT
signing — opaque random strings persisted in SQLite with a TTL column.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import AuthToken, User

TOKEN_TTL = timedelta(hours=24)


def _utcnow_naive() -> datetime:
    """SQLite drops tz info — store and compare naive UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def issue(user: User, db: Session) -> str:
    token = secrets.token_urlsafe(32)
    db.add(
        AuthToken(
            token=token,
            user_id=user.id,
            expires_at=_utcnow_naive() + TOKEN_TTL,
        )
    )
    db.commit()
    return token


def resolve(token: str, db: Session) -> dict | None:
    row = db.execute(
        select(AuthToken).where(AuthToken.token == token)
    ).scalar_one_or_none()
    if row is None:
        return None
    if row.expires_at <= _utcnow_naive():
        return None
    user = row.user
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "role": user.role,
    }


def clear(db: Session) -> None:
    """Test helper — wipe tokens between cases."""
    db.execute(delete(AuthToken))
    db.commit()