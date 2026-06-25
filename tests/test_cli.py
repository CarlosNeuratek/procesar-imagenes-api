"""reset-admin CLI: updates hash, idempotent, fails clearly when admin missing."""
from __future__ import annotations

from sqlalchemy import text

from app.auth.cli import _reset_admin
from app.auth.security import verify_password


def test_reset_admin_updates_password_hash(db) -> None:
    rc = _reset_admin(["--password", "newpass123"])
    assert rc == 0
    db.commit()  # ensure we see CLI's writes via shared SQLite file
    h = db.execute(
        text("SELECT password_hash FROM users WHERE email='admin@contadores'")
    ).scalar_one()
    assert verify_password("newpass123", h)


def test_reset_admin_is_idempotent(db) -> None:
    rc1 = _reset_admin(["--password", "newpass123"])
    rc2 = _reset_admin(["--password", "newpass123"])
    db.commit()
    assert rc1 == 0
    assert rc2 == 0


def test_reset_admin_short_password_returns_2() -> None:
    rc = _reset_admin(["--password", "short"])
    assert rc == 2