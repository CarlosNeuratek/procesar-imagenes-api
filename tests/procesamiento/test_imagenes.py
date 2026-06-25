"""Tests for /api/imagenes scan + listing."""
from __future__ import annotations

from app.config import settings


def _override_fotos_dir(value: str) -> None:
    """Frozen dataclass — poke through the door."""
    object.__setattr__(settings, "fotos_dir", value)


def test_get_imagenes_empty(client) -> None:
    r = client.get("/api/imagenes")
    assert r.status_code == 200
    assert r.json() == {"imagenes": []}


def test_scan_inserts_pending(tmp_path, client) -> None:
    fotos = tmp_path / "fotos"
    fotos.mkdir()
    for name in ("a.jpg", "b.png", "c.webp"):
        (fotos / name).write_bytes(b"fake-bytes")
    # non-image files must be ignored
    (fotos / "ignore.txt").write_text("not an image")

    _override_fotos_dir(str(fotos))

    r = client.post("/api/imagenes/cargar")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scanned"] == 3
    assert body["inserted"] == 3
    assert body["skipped"] == 0


def test_scan_dedupes(tmp_path, client) -> None:
    fotos = tmp_path / "fotos"
    fotos.mkdir()
    (fotos / "a.jpg").write_bytes(b"fake")
    _override_fotos_dir(str(fotos))

    r1 = client.post("/api/imagenes/cargar")
    assert r1.json() == {"scanned": 1, "inserted": 1, "skipped": 0}
    r2 = client.post("/api/imagenes/cargar")
    assert r2.json() == {"scanned": 1, "inserted": 0, "skipped": 1}


def test_scan_missing_dir(tmp_path, client) -> None:
    _override_fotos_dir(str(tmp_path / "does_not_exist"))
    r = client.post("/api/imagenes/cargar")
    assert r.status_code == 200
    assert r.json() == {"scanned": 0, "inserted": 0, "skipped": 0}


def test_get_imagenes_returns_rows(tmp_path, client) -> None:
    fotos = tmp_path / "fotos"
    fotos.mkdir()
    for name in ("a.jpg", "b.png"):
        (fotos / name).write_bytes(b"fake")
    _override_fotos_dir(str(fotos))

    client.post("/api/imagenes/cargar")
    r = client.get("/api/imagenes")
    assert r.status_code == 200
    rows = r.json()["imagenes"]
    assert len(rows) == 2
    assert {row["estado"] for row in rows} == {"Pendiente"}
    assert rows[0]["id"] < rows[1]["id"]