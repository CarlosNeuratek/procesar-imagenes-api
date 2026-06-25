"""Tests for /api/procesamiento/{start,stop,status} + claim collision."""
from __future__ import annotations

import threading


def test_start_running(client) -> None:
    r = client.post("/api/procesamiento/start?threads=2")
    assert r.status_code == 200
    assert r.json() == {"status": "running", "threads": 2}
    client.post("/api/procesamiento/stop")


def test_start_idempotent_same_n(client) -> None:
    client.post("/api/procesamiento/start?threads=2")
    r = client.post("/api/procesamiento/start?threads=2")
    assert r.status_code == 200
    assert r.json() == {"status": "already_running", "threads": 2}
    client.post("/api/procesamiento/stop")


def test_start_rejects_different_n(client) -> None:
    client.post("/api/procesamiento/start?threads=2")
    r = client.post("/api/procesamiento/start?threads=4")
    assert r.status_code == 409
    assert r.json()["detail"]["status"] == "running"
    assert r.json()["detail"]["threads"] == 2
    client.post("/api/procesamiento/stop")


def test_start_rejects_threads_above_cap(client) -> None:
    r = client.post("/api/procesamiento/start?threads=99")
    assert r.status_code == 422


def test_stop_idempotent(client) -> None:
    r = client.post("/api/procesamiento/stop")
    assert r.status_code == 200
    assert r.json() == {"status": "stopped"}


def test_status_idle(client) -> None:
    r = client.get("/api/procesamiento/status")
    assert r.status_code == 200
    body = r.json()
    assert body["running"] is False
    assert body["threads"] == 0
    assert body["queue_size"] == 0
    assert body["completed"] == 0
    assert body["error"] == 0


def test_claim_collision_free(db) -> None:
    """5 threads call claim_one_pending on 1 pending row; exactly 1 wins."""
    from datetime import datetime, timezone

    from app.procesamiento.models import ProcesamientoImagen
    from app.procesamiento.worker import claim_one_pending

    db.add(
        ProcesamientoImagen(
            ruta_archivo="/fotos/only.jpg",
            estado="Pendiente",
            fecha_creacion=datetime.now(timezone.utc),
        )
    )
    db.commit()

    results: list[int | None] = []
    lock = threading.Lock()

    def grab() -> None:
        from app.db import SessionLocal

        with SessionLocal() as s:
            row = claim_one_pending(s)
            with lock:
                results.append(row.id if row else None)

    threads = [threading.Thread(target=grab) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    non_null = sorted(r for r in results if r is not None)
    assert non_null == [1]
    assert len(results) - len(non_null) == 4