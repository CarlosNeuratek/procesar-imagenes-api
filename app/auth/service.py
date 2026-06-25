"""Auth business logic. Hardcoded user for the mock slice."""
from __future__ import annotations

from . import tokens
from .config_compat import settings  # local import avoids cycle on import-time


def _hardcoded_user() -> dict:
    return {
        "id": "u-admin-001",
        "email": settings.admin_email,
        "name": "Admin",
        "role": "admin",
    }


def authenticate(email: str, password: str) -> dict | None:
    if email == settings.admin_email and password == settings.admin_password:
        return _hardcoded_user()
    return None


def login(email: str, password: str) -> dict | None:
    user = authenticate(email, password)
    if user is None:
        return None
    return {"token": tokens.issue(user), "user": user}


def me(token: str) -> dict | None:
    return tokens.resolve(token)