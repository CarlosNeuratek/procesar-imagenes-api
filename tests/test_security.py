"""Security primitives: bcrypt roundtrip + token expiry."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.auth.security import hash_password, verify_password
from app.auth.tokens import _utcnow_naive, issue, resolve


def test_bcrypt_hash_and_verify_roundtrip() -> None:
    h = hash_password("hello1234")
    assert h.startswith("$2")
    assert verify_password("hello1234", h)
    assert not verify_password("wrong", h)


def test_bcrypt_rounds_override() -> None:
    h = hash_password("x" * 8, rounds=4)
    assert h.startswith("$2b$04$")
    assert verify_password("x" * 8, h)


def test_token_expiry_returns_none(db) -> None:
    from app.auth.models import User

    user = User(
        email="sec@contadores",
        name="Sec",
        role="admin",
        password_hash=hash_password("any12345"),
    )
    db.add(user)
    db.commit()

    token = issue(user, db)
    assert resolve(token, db) is not None

    # Backdate the row past TTL.
    from app.auth.models import AuthToken

    row = db.query(AuthToken).filter_by(token=token).one()
    row.expires_at = _utcnow_naive() - timedelta(seconds=1)
    db.commit()

    assert resolve(token, db) is None