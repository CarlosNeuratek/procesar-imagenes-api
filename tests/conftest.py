"""Pytest fixtures: temp-file SQLite, admin bootstrap, per-test token truncate."""
from __future__ import annotations

import os
import tempfile
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# ponytail: temp-file SQLite per session, faster + isolates from dev DB.
# ponytail: in-memory would force a single connection (StaticPool); temp file
# allows the TestClient + middleware to share the same DB across requests.
_TEST_DB = os.path.join(tempfile.gettempdir(), "contadores-test.db")
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_TEST_DB}")
os.environ.setdefault("ADMIN_EMAIL", "admin@contadores")
os.environ.setdefault("ADMIN_PASSWORD", "admin123")


@pytest.fixture(scope="session")
def engine():
    from app.auth.models import AuthToken, User  # noqa: F401  (register tables)
    from app.db import Base

    eng = create_engine(
        os.environ["DATABASE_URL"],
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()
    if os.path.exists(_TEST_DB):
        os.unlink(_TEST_DB)


@pytest.fixture(autouse=True, scope="session")
def _bootstrap_admin(engine):
    """Seed admin once per session — survives across tests."""
    from app.auth.models import User
    from app.auth.security import hash_password
    from app.config import settings

    Session_ = sessionmaker(bind=engine)
    with Session_() as db:
        if not db.query(User).filter_by(email=settings.admin_email).first():
            db.add(
                User(
                    email=settings.admin_email,
                    name="Admin",
                    role="admin",
                    password_hash=hash_password(settings.admin_password),
                )
            )
            db.commit()


@pytest.fixture
def db(engine) -> Generator[Session, None, None]:
    """Function-scoped session; truncates auth_tokens + non-admin users per test."""
    from app.auth.models import User
    from app.config import settings

    Session_ = sessionmaker(bind=engine)
    s = Session_()
    s.execute(text("DELETE FROM auth_tokens"))
    s.execute(text("DELETE FROM users WHERE email != :email"), {"email": settings.admin_email})
    s.commit()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture(autouse=True)
def _restore_admin_state(engine) -> Generator[None, None, None]:
    """Restore admin password and clear rate-limit bucket after each test."""
    from app.auth.models import User
    from app.auth.rate_limit import _attempts
    from app.auth.security import hash_password, verify_password
    from app.config import settings

    yield
    _attempts.clear()
    Session_ = sessionmaker(bind=engine)
    with Session_() as s:
        admin = s.query(User).filter_by(email=settings.admin_email).first()
        if admin is not None and not verify_password(
            settings.admin_password, admin.password_hash
        ):
            admin.password_hash = hash_password(settings.admin_password)
            s.commit()


@pytest.fixture
def client(db) -> Generator[TestClient, None, None]:
    from app.db import get_db
    from app.main import app

    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()