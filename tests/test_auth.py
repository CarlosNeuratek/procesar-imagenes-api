"""End-to-end tests for /auth/* endpoints."""
from __future__ import annotations

ADMIN_EMAIL = "admin@contadores"
ADMIN_PASSWORD = "admin123"


def test_login_success_returns_token_and_user(client) -> None:
    res = client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert res.status_code == 200, res.text
    body = res.json()
    assert isinstance(body["token"], str) and body["token"]
    assert body["user"]["email"] == ADMIN_EMAIL
    assert body["user"]["role"] == "admin"


def test_login_wrong_password_returns_401(client) -> None:
    res = client.post("/auth/login", json={"email": ADMIN_EMAIL, "password": "nope"})
    assert res.status_code == 401
    assert res.json()["detail"]


def test_login_unknown_email_returns_401(client) -> None:
    res = client.post("/auth/login", json={"email": "ghost@contadores", "password": "x"})
    assert res.status_code == 401


def test_me_with_valid_token_returns_user(client) -> None:
    login = client.post(
        "/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    ).json()
    res = client.get("/auth/me", headers={"Authorization": f"Bearer {login['token']}"})
    assert res.status_code == 200
    assert res.json()["email"] == ADMIN_EMAIL


def test_me_without_header_returns_401(client) -> None:
    res = client.get("/auth/me")
    assert res.status_code == 401


def test_me_with_garbage_token_returns_401(client) -> None:
    res = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert res.status_code == 401


def test_cors_preflight_from_localhost_3000(client) -> None:
    res = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert res.status_code in (200, 204)
    assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"