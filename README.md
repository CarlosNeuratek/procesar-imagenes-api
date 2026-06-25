# contadores-api

Mock FastAPI backend for the `contadores-ui` SPA. Replaces the hardcoded login with a real local server.

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

## Run

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Or, with the venv active:

```bash
uvicorn app.main:app --reload --port 8000
```

Server starts on `http://localhost:8000`. Interactive docs at `/docs`.

## Test

```bash
uv run pytest
```

## Endpoints

### `POST /auth/login`

Request:

```json
{ "email": "admin@contadores", "password": "admin123" }
```

Response 200:

```json
{ "token": "<opaque>", "user": { "id": "u-admin-001", "email": "admin@contadores", "name": "Admin", "role": "admin" } }
```

Response 401: `{ "detail": "Invalid credentials" }`.

### `GET /auth/me`

Header: `Authorization: Bearer <token>`.
Returns the same `user` shape. 401 if the header is missing or the token is unknown.

## Notes

This is the **mock slice**. The token is an opaque random string kept in a process-local dict (lost on restart). Real DB, real JWT, password hashing, and refresh tokens come in later slices.