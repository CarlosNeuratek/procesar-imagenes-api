"""Opaque server-side tokens, kept in a process-local dict.

ponytail: in-memory token store; swap to Redis when sessions matter.
Opaque random strings, not JWT — no signature verification, just a lookup.
"""
from __future__ import annotations

import secrets

# token -> user dict
_STORE: dict[str, dict] = {}


def issue(user: dict) -> str:
    token = secrets.token_urlsafe(32)
    _STORE[token] = user
    return token


def resolve(token: str) -> dict | None:
    return _STORE.get(token)


def clear() -> None:
    """Test helper — wipe the store between cases."""
    _STORE.clear()