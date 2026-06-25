"""ThreadPoolExecutor worker pool for Gemini batch image processing.

ponytail: module-level executor is OK because the uvicorn process is
single-worker (`--workers 1`). Multiple processes would each hold their
own pool, breaking collision-free claim semantics.
"""
from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import gemini_client
from .models import ConfigPrompt, ProcesamientoImagen

logger = logging.getLogger(__name__)

MIME_BY_SUFFIX = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

_executor: Optional[ThreadPoolExecutor] = None
_stop_flag: threading.Event = threading.Event()
_state_lock: threading.Lock = threading.Lock()
_current_threads: int = 0


def claim_one_pending(db: Session) -> Optional[ProcesamientoImagen]:
    """Atomic claim: SELECT next Pendiente + flip to Procesando in one tx."""
    row = db.execute(
        select(ProcesamientoImagen)
        .where(ProcesamientoImagen.estado == "Pendiente")
        .order_by(ProcesamientoImagen.id)
        .limit(1)
    ).scalar_one_or_none()
    if row is None:
        return None
    row.estado = "Procesando"
    db.commit()
    return row


def _read_prompt(db: Session) -> str:
    cfg = db.get(ConfigPrompt, 1)
    return cfg.prompt_texto if cfg and cfg.prompt_texto else ""


def process_one(row: ProcesamientoImagen, db: Session) -> None:
    """Process a single claimed row. Updates row to Completado/Error in place."""
    started = time.monotonic()
    try:
        prompt = _read_prompt(db)
        path = Path(row.ruta_archivo)
        suffix = path.suffix.lower()
        mime = MIME_BY_SUFFIX.get(suffix, "application/octet-stream")
        text = gemini_client.generate(prompt, path.read_bytes(), mime)
        elapsed = time.monotonic() - started
        row.estado = "Completado"
        row.resultado = text
        row.tiempo_procesamiento = elapsed
        db.commit()
    except Exception as exc:
        elapsed = time.monotonic() - started
        row.estado = "Error"
        row.error_mensaje = f"{type(exc).__name__}: {exc}"
        row.tiempo_procesamiento = elapsed
        db.commit()
        logger.warning("worker error on id=%s: %s", row.id, exc)


def _worker_loop() -> None:
    """Single worker: claim + process until no pendings or stop_flag."""
    from ..db import SessionLocal

    while not _stop_flag.is_set():
        db = SessionLocal()
        try:
            row = claim_one_pending(db)
            if row is None:
                return
            process_one(row, db)
        finally:
            db.close()


def start(threads: int) -> dict:
    """Idempotent on same N (already_running); 409 if N differs."""
    global _executor, _current_threads
    with _state_lock:
        if _executor is not None:
            if _current_threads == threads:
                return {"status": "already_running", "threads": _current_threads}
            return {"status": "running", "threads": _current_threads}
        _stop_flag.clear()
        _executor = ThreadPoolExecutor(
            max_workers=threads, thread_name_prefix="gemini-worker"
        )
        _current_threads = threads
    for _ in range(threads):
        _executor.submit(_worker_loop)
    return {"status": "running", "threads": threads}


def stop() -> dict:
    global _executor, _current_threads
    with _state_lock:
        _stop_flag.set()
        if _executor is not None:
            _executor.shutdown(wait=True, cancel_futures=False)
            _executor = None
        _current_threads = 0
    return {"status": "stopped"}


def status(db: Session) -> dict:
    counts = {"Pendiente": 0, "Procesando": 0, "Completado": 0, "Error": 0}
    for estado, n in (
        db.query(ProcesamientoImagen.estado, ProcesamientoImagen.id)
        .all()
    ):
        counts[estado] = counts.get(estado, 0) + 1
    return {
        "running": _executor is not None,
        "threads": _current_threads,
        "queue_size": counts["Pendiente"],
        "completed": counts["Completado"],
        "error": counts["Error"],
        "procesando": counts["Procesando"],
    }