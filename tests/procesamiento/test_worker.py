"""Worker tests — process_one (mocked SDK) success + error paths."""
from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import patch

from app.procesamiento.models import ConfigPrompt, ProcesamientoImagen
from app.procesamiento.worker import process_one


def _seed_row(db, ruta: str, prompt: str | None = "describe") -> int:
    if prompt is not None:
        db.add(
            ConfigPrompt(
                id=1, prompt_texto=prompt, actualizado_en=datetime.now(timezone.utc)
            )
        )
    db.add(
        ProcesamientoImagen(
            ruta_archivo=ruta,
            estado="Procesando",
            fecha_creacion=datetime.now(timezone.utc),
        )
    )
    db.commit()
    return db.query(ProcesamientoImagen).filter_by(ruta_archivo=ruta).one().id


def test_worker_success_populates_result(db) -> None:
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tmp.write(b"\xff\xd8\xff\xe0fakejpeg")
    tmp.close()
    try:
        row_id = _seed_row(db, tmp.name, prompt="describe")

        with patch(
            "app.procesamiento.worker.gemini_client.generate",
            return_value="mocked gemini result",
        ):
            row = db.get(ProcesamientoImagen, row_id)
            process_one(row, db)

        updated = db.get(ProcesamientoImagen, row_id)
        assert updated.estado == "Completado"
        assert updated.resultado == "mocked gemini result"
        assert updated.tiempo_procesamiento > 0
        assert updated.error_mensaje is None
    finally:
        os.unlink(tmp.name)


def test_worker_error_populates_error_message(db) -> None:
    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.write(b"fakepng")
    tmp.close()
    try:
        row_id = _seed_row(db, tmp.name, prompt="describe")

        def boom(*_a, **_kw):
            raise RuntimeError("sdk is down")

        with patch(
            "app.procesamiento.worker.gemini_client.generate", side_effect=boom
        ):
            row = db.get(ProcesamientoImagen, row_id)
            process_one(row, db)

        updated = db.get(ProcesamientoImagen, row_id)
        assert updated.estado == "Error"
        assert "RuntimeError" in updated.error_mensaje
        assert "sdk is down" in updated.error_mensaje
        assert updated.tiempo_procesamiento > 0
        assert updated.resultado is None
    finally:
        os.unlink(tmp.name)


def test_worker_reads_fresh_prompt_each_iteration(db) -> None:
    """Worker must read the live config_prompt row, not a cached copy."""
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tmp.write(b"\xff\xd8fake")
    tmp.close()
    try:
        db.add(
            ConfigPrompt(
                id=1, prompt_texto="first", actualizado_en=datetime.now(timezone.utc)
            )
        )
        db.add(
            ProcesamientoImagen(
                ruta_archivo=tmp.name,
                estado="Procesando",
                fecha_creacion=datetime.now(timezone.utc),
            )
        )
        db.commit()
        seen: list[str] = []

        def fake_generate(prompt, *_a, **_kw):
            seen.append(prompt)
            return f"out:{prompt}"

        with patch(
            "app.procesamiento.worker.gemini_client.generate",
            side_effect=fake_generate,
        ):
            row = db.query(ProcesamientoImagen).filter_by(ruta_archivo=tmp.name).one()
            process_one(row, db)

        cfg = db.get(ConfigPrompt, 1)
        cfg.prompt_texto = "second"
        row = db.query(ProcesamientoImagen).filter_by(ruta_archivo=tmp.name).one()
        row.estado = "Procesando"
        row.resultado = None
        db.commit()

        with patch(
            "app.procesamiento.worker.gemini_client.generate",
            side_effect=fake_generate,
        ):
            process_one(row, db)

        assert seen == ["first", "second"]
    finally:
        os.unlink(tmp.name)