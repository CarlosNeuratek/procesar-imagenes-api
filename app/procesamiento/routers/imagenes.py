"""GET /api/imagenes + POST /api/imagenes/cargar (scan FOTOS_DIR)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...config import settings
from ...db import get_db
from ..models import ProcesamientoImagen
from ..schemas import Imagen, ImagenList, ScanResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/imagenes", tags=["procesamiento-imagenes"])

_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def _iter_candidate_files(root: Path):
    if not root.exists():
        return
    for entry in root.iterdir():
        if entry.is_file() and entry.suffix.lower() in _IMAGE_SUFFIXES:
            yield str(entry.resolve())


@router.get("", response_model=ImagenList)
def list_imagenes(db: Session = Depends(get_db)) -> ImagenList:
    rows = db.query(ProcesamientoImagen).order_by(ProcesamientoImagen.id.asc()).all()
    return ImagenList(
        imagenes=[
            Imagen(
                id=r.id,
                ruta_archivo=r.ruta_archivo,
                estado=r.estado,
                resultado=r.resultado,
                tiempo_procesamiento=r.tiempo_procesamiento,
                error_mensaje=r.error_mensaje,
                fecha_creacion=r.fecha_creacion.isoformat(),
            )
            for r in rows
        ]
    )


@router.post("/cargar", response_model=ScanResult)
def cargar(db: Session = Depends(get_db)) -> ScanResult:
    """Scan FOTOS_DIR; INSERT new pendings; UNIQUE constraint dedupes."""
    fotos = Path(settings.fotos_dir)
    candidates = list(_iter_candidate_files(fotos))
    scanned = len(candidates)
    inserted = 0
    skipped = 0
    now = datetime.now(timezone.utc)
    for ruta in candidates:
        row = ProcesamientoImagen(
            ruta_archivo=ruta, estado="Pendiente", fecha_creacion=now
        )
        db.add(row)
        try:
            db.commit()
            inserted += 1
        except IntegrityError:
            db.rollback()
            skipped += 1
    return ScanResult(scanned=scanned, inserted=inserted, skipped=skipped)