"""Tests for /api/config/prompt (GET empty, POST upsert, GET roundtrip)."""
from __future__ import annotations


def test_get_prompt_empty(client) -> None:
    r = client.get("/api/config/prompt")
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == 1
    assert body["prompt_texto"] is None
    assert body["actualizado_en"] is None


def test_post_then_get_roundtrip(client) -> None:
    r = client.post("/api/config/prompt", json={"prompt_texto": "describe image"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["prompt_texto"] == "describe image"
    assert body["actualizado_en"] is not None

    r2 = client.get("/api/config/prompt")
    assert r2.status_code == 200
    assert r2.json()["prompt_texto"] == "describe image"


def test_post_updates_timestamp(client) -> None:
    r1 = client.post("/api/config/prompt", json={"prompt_texto": "first"})
    ts1 = r1.json()["actualizado_en"]
    r2 = client.post("/api/config/prompt", json={"prompt_texto": "second"})
    ts2 = r2.json()["actualizado_en"]
    assert ts2 >= ts1
    assert r2.json()["prompt_texto"] == "second"