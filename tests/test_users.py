"""User management endpoints — admin-only GET/POST /users."""
from __future__ import annotations

ADMIN_EMAIL = "admin@contadores"
ADMIN_PASSWORD = "admin123"


def _admin_token(client) -> str:
    res = client.post(
        "/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert res.status_code == 200, res.text
    return res.json()["token"]


def _create_contador(client, admin_token: str) -> str:
    res = client.post(
        "/users",
        json={
            "email": "ana@contadores",
            "name": "Ana",
            "role": "contador",
            "password": "supersecret",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 201, res.text
    ana = res.json()
    return ana["id"]


def test_list_users_as_admin_returns_list(client) -> None:
    token = _admin_token(client)
    res = client.get("/users", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    body = res.json()
    assert isinstance(body, list)
    assert any(u["email"] == ADMIN_EMAIL for u in body)


def test_list_users_without_token_returns_401(client) -> None:
    res = client.get("/users")
    assert res.status_code == 401


def test_list_users_as_contador_returns_403(client) -> None:
    admin_token = _admin_token(client)
    _create_contador(client, admin_token)

    ana_login = client.post(
        "/auth/login", json={"email": "ana@contadores", "password": "supersecret"}
    )
    assert ana_login.status_code == 200, ana_login.text
    ana_token = ana_login.json()["token"]

    res = client.get("/users", headers={"Authorization": f"Bearer {ana_token}"})
    assert res.status_code == 403
    assert res.json()["detail"]


def test_create_user_as_admin_returns_201(client) -> None:
    admin_token = _admin_token(client)
    res = client.post(
        "/users",
        json={
            "email": "luis@contadores",
            "name": "Luis",
            "role": "contador",
            "password": "luispass1",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["email"] == "luis@contadores"
    assert body["name"] == "Luis"
    assert body["role"] == "contador"
    assert "id" in body
    assert "password" not in body
    assert "password_hash" not in body


def test_create_user_duplicate_email_returns_409(client) -> None:
    admin_token = _admin_token(client)
    payload = {
        "email": "dup@contadores",
        "name": "Dup",
        "role": "contador",
        "password": "duppass1",
    }
    first = client.post(
        "/users", json=payload, headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert first.status_code == 201, first.text

    second = client.post(
        "/users", json=payload, headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert second.status_code == 409
    assert second.json()["detail"]


def test_create_user_as_contador_returns_403(client) -> None:
    admin_token = _admin_token(client)
    _create_contador(client, admin_token)
    ana_login = client.post(
        "/auth/login", json={"email": "ana@contadores", "password": "supersecret"}
    )
    ana_token = ana_login.json()["token"]

    res = client.post(
        "/users",
        json={
            "email": "x@contadores",
            "name": "X",
            "role": "contador",
            "password": "xxxxxxxx",
        },
        headers={"Authorization": f"Bearer {ana_token}"},
    )
    assert res.status_code == 403
    assert res.json()["detail"]


def test_create_user_short_password_returns_422(client) -> None:
    admin_token = _admin_token(client)
    res = client.post(
        "/users",
        json={
            "email": "short@contadores",
            "name": "S",
            "role": "contador",
            "password": "short",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res.status_code == 422