# contadores-api

FastAPI backend for the `contadores-ui` SPA. Real, DB-backed auth (bcrypt + opaque tokens in SQLite) with admin bootstrap, rate-limited login, admin-only `/users` surface, and an embedded Gemini batch image-processing slice (`/api/config`, `/api/imagenes`, `/api/procesamiento`).

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
uv run uvicorn app.main:app --workers 1 --port 8000
```

For local dev with autoreload:

```bash
uv run uvicorn app.main:app --reload --workers 1 --port 8000
```

**Single-worker constraint.** Rate limiting is in-process, so multiple workers would each hold an independent bucket. The default above uses `--workers 1` to match the rate-limit guarantee. For production with multiple workers behind a load balancer, swap the in-process limiter for Redis (out of scope for this slice).

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
| `FOTOS_DIR` | `/fotos` | Directory scanned by `POST /api/imagenes/cargar`. |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name. |
| `MAX_THREADS` | `1` | Soft cap for `/api/procesamiento/start`; hard cap is 16. |
| `STALE_PROCESSING_MINUTES` | `10` | Threshold for resetting orphaned `Procesando` rows on startup. |
| `GCP_PROJECT` | _(empty — derived from creds)_ | Vertex AI project ID. |
| `GCP_LOCATION` | `us-central1` | Vertex AI location. |
| `GOOGLE_APPLICATION_CREDENTIALS` | `contadores-api/credentials/google-credentials.json` | GCP service-account JSON. |

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

## Procesamiento (Gemini batch)

The same process serves a manual image-processing slice. Scan a directory of images, tweak the prompt, start a worker pool, poll the status, inspect results. No auth required on these endpoints (internal tooling).

### `GET /api/config/prompt`

Returns 200 with `{ id, prompt_texto, actualizado_en }`. If no prompt is set, both fields are `null`.

### `POST /api/config/prompt`

Body: `{ "prompt_texto": "..." }`. Upserts the single config row and returns 200 with the updated row.

### `POST /api/imagenes/cargar`

Scans `FOTOS_DIR` for files with extension `{.jpg, .jpeg, .png, .webp}` (case-insensitive) and INSERTs new pending rows. Duplicates are skipped via the `ruta_archivo` UNIQUE constraint.

Returns 200: `{ scanned, inserted, skipped }`.

### `GET /api/imagenes`

Returns 200: `{ imagenes: [...] }` ordered by `id ASC`. Each item: `{ id, ruta_archivo, estado, resultado, tiempo_procesamiento, error_mensaje, fecha_creacion }`.

### `POST /api/procesamiento/start?threads=N`

`threads` ∈ [1, 16], default 1.

- 200 `{ "status": "running", "threads": N }` — pool spawned.
- 200 `{ "status": "already_running", "threads": N }` — same N, no second pool.
- 409 `{ "detail": { "status": "running", "threads": <current> } }` — different N.
- 422 — Pydantic validation when `N` is outside [1, 16].

### `POST /api/procesamiento/stop`

Sets the stop flag; in-flight workers finish their current image and exit. Idempotent — safe to call when not running. Returns 200 `{ "status": "stopped" }`.

### `GET /api/procesamiento/status`

Returns 200: `{ running, threads, queue_size, completed, error, procesando }`. Counts derived from current table state.

### Manual smoke flow

```bash
# 1. Set prompt
curl -X POST http://localhost:8000/api/config/prompt \
  -H 'Content-Type: application/json' \
  -d '{"prompt_texto":"describe the meter reading"}'

# 2. Scan /fotos
curl -X POST http://localhost:8000/api/imagenes/cargar
# {"scanned":N,"inserted":N,"skipped":0}

# 3. Start worker pool
curl -X POST 'http://localhost:8000/api/procesamiento/start?threads=2'
# {"status":"running","threads":2}

# 4. Poll
curl http://localhost:8000/api/procesamiento/status

# 5. Stop
curl -X POST http://localhost:8000/api/procesamiento/stop
```

## Notes

- Tokens are opaque random strings (43 chars, 256 bits) stored in `auth_tokens` with a 24h TTL. `resolve` filters expired rows; pruning is deferred.
- Existing localStorage sessions from the mock slice are invalidated on first deploy — users re-login once.
- Forgot the admin password? Use the `reset-admin` CLI above.