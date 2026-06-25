"""POST /auth/login rate limit: 5 failed attempts/min/IP, 6th -> 429."""
from __future__ import annotations

from app.auth.rate_limit import _attempts

ADMIN_EMAIL = "admin@contadores"


def test_sixth_failed_login_returns_429(client) -> None:
    _attempts.clear()
    for i in range(5):
        r = client.post(
            "/auth/login",
            json={"email": ADMIN_EMAIL, "password": f"wrong-{i}"},
        )
        assert r.status_code == 401, (i, r.status_code, r.text)
    r = client.post(
        "/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong-6"}
    )
    assert r.status_code == 429, r.text
    assert int(r.headers["Retry-After"]) >= 1


def test_successful_login_does_not_consume_slot(client) -> None:
    _attempts.clear()
    # 4 failed + 1 successful + 1 failed should still be under the limit
    for i in range(4):
        r = client.post(
            "/auth/login",
            json={"email": ADMIN_EMAIL, "password": f"wrong-{i}"},
        )
        assert r.status_code == 401
    r_ok = client.post(
        "/auth/login", json={"email": ADMIN_EMAIL, "password": "admin123"}
    )
    assert r_ok.status_code == 200
    r_fail = client.post(
        "/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong-5"}
    )
    assert r_fail.status_code == 401
    # Now bucket has 5 entries (the 200 didn't consume); next should 429
    r_block = client.post(
        "/auth/login", json={"email": ADMIN_EMAIL, "password": "wrong-6"}
    )
    assert r_block.status_code == 429