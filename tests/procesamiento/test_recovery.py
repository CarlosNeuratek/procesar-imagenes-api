"""Lifespan recovery: stale Procesando rows reset to Pendiente on startup."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.main import _recover_orphaned_procesando
from app.procesamiento.models import ProcesamientoImagen


def test_orphan_reset_returns_count_and_flips_state(db) -> None:
    stale = datetime.now(timezone.utc) - timedelta(minutes=30)
    db.add(
        ProcesamientoImagen(
            ruta_archivo="/fotos/old.jpg",
            estado="Procesando",
            fecha_creacion=stale,
        )
    )
    # fresh row (must NOT be reset)
    db.add(
        ProcesamientoImagen(
            ruta_archivo="/fotos/fresh.jpg",
            estado="Procesando",
            fecha_creacion=datetime.now(timezone.utc),
        )
    )
    db.commit()

    assert _recover_orphaned_procesando() == 1

    refreshed = (
        db.query(ProcesamientoImagen)
        .order_by(ProcesamientoImagen.ruta_archivo)
        .all()
    )
    by_path = {r.ruta_archivo: r.estado for r in refreshed}
    assert by_path["/fotos/old.jpg"] == "Pendiente"
    assert by_path["/fotos/fresh.jpg"] == "Procesando"


def test_orphan_reset_no_op_when_nothing_stale(db) -> None:
    db.add(
        ProcesamientoImagen(
            ruta_archivo="/fotos/recent.jpg",
            estado="Procesando",
            fecha_creacion=datetime.now(timezone.utc),
        )
    )
    db.commit()
    assert _recover_orphaned_procesando() == 0
    row = db.query(ProcesamientoImagen).one()
    assert row.estado == "Procesando"