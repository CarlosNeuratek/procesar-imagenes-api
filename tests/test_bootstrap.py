"""Admin bootstrap idempotency — lifespan called twice creates exactly one row."""
from __future__ import annotations

import asyncio

from sqlalchemy import text

from app.auth.models import User
from app.config import settings


def test_lifespan_runs_twice_keeps_one_admin(db) -> None:
    from app.main import app

    # Wipe admin rows so we can observe the bootstrap effect
    db.execute(text("DELETE FROM users"))
    db.commit()

    async def run():
        async with app.router.lifespan_context(app):
            pass
        async with app.router.lifespan_context(app):
            pass

    asyncio.run(run())

    count = db.query(User).filter_by(email=settings.admin_email).count()
    assert count == 1


def test_admin_can_login_after_bootstrap(db, client) -> None:
    from app.main import app

    db.execute(text("DELETE FROM users"))
    db.commit()

    async def run():
        async with app.router.lifespan_context(app):
            pass

    asyncio.run(run())

    res = client.post(
        "/auth/login",
        json={"email": settings.admin_email, "password": settings.admin_password},
    )
    assert res.status_code == 200, res.text
    assert res.json()["user"]["role"] == "admin"