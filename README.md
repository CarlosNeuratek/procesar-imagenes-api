# contadores-api

FastAPI backend for the `contadores-ui` SPA. Real, DB-backed auth (bcrypt + opaque tokens in SQLite) with admin bootstrap, rate-limited login, and an admin-only `/users` surface.

## Requirements

- Python 3.11+
- [`uv`](https://github.com/astral-sh/uv) (recommended) or `pip` + `venv`

## Install

```bash
uv sync --extra dev
```

With pip + venv:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

New deps: `sqlalchemy>=2.0`, `bcrypt>=4.0`.

## Run

```bash
uv run uvicorn app.main:app --reload --port 8000
```

**Run with a single worker.** Rate limiting is in-process, so multiple workers would each hold an independent bucket. Use `--workers 1` in production:

```bash
uvicorn app.main:app --workers 1 --host 0.0.0.0 --port 8000
```

Server starts on `http://localhost:8000`. Interactive docs at `/docs`.

## Test

```bash
uv run pytest
```

## Environment

| Var | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./contadores.db` | SQLite path. Use `sqlite:////abs/path.db` for absolute. |
| `BCRYPT_ROUNDS` | `12` | Cost factor. Lower for faster tests, raise for prod. |
| `ADMIN_EMAIL` | `admin@contadores` | Email used by bootstrap and `reset-admin`. |
| `ADMIN_PASSWORD` | `admin123` | Initial password; rotate after first login. |
| `CORS_ORIGINS` | `http://localhost:3000` | Comma-separated allowlist. |
| `API_HOST` / `API_PORT` | `127.0.0.1` / `8000` | Bind settings. |

The lifespan creates tables via `Base.metadata.create_all()` and bootstraps the admin user if missing (idempotent across restarts).

## CLI: reset admin password

Recovery path when the admin password is lost:

```bash
uv run python -m app.auth.cli reset-admin --password newpass123
```

Resolution order: `--password` flag → `ADMIN_PASSWORD` env var → `getpass` prompt.

## Endpoints

### `POST /auth/login`

Request:

```json
{ "email": "admin@contadores", "password": "admin123" }
```

Response 200:

```json
{ "token": "<opaque>", "user": { "id": "...", "email": "admin@contadores", "name": "Admin", "role": "admin" } }
```

- 401: `{ "detail": "Invalid credentials" }`
- 429: rate-limited (5 failed attempts/min/IP). Includes `Retry-After` header.

### `GET /auth/me`

Header: `Authorization: Bearer <token>`.
Returns the same `user` shape. 401 if the header is missing or the token is unknown/expired.

### `GET /users` (admin only)

Headers: `Authorization: Bearer <admin-token>`.
Query: `limit` (default 50, max 200), `offset` (default 0).
Returns `list[UserPublic]`. 401 if no token, 403 if not admin.

### `POST /users` (admin only)

Headers: `Authorization: Bearer <admin-token>`.
Body: `{ "email", "name", "role": "admin" | "contador", "password" (min 8) }`.
Returns 201 with `{ id, email, name, role }`. 409 on duplicate email.

## Notes

- Tokens are opaque random strings (43 chars, 256 bits) stored in `auth_tokens` with a 24h TTL. `resolve` filters expired rows; pruning is deferred.
- Existing localStorage sessions from the mock slice are invalidated on first deploy — users re-login once.
- Forgot the admin password? Use the `reset-admin` CLI above.