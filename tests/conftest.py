"""Pytest fixtures: a fresh FastAPI TestClient per test, plus a token-store reset."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.auth import tokens
from app.main import app


@pytest.fixture
def client() -> TestClient:
    tokens.clear()
    return TestClient(app)