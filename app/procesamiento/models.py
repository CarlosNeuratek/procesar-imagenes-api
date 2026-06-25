"""SQLAlchemy 2.x mapped classes for the Gemini image-processing slice.

Reuses the existing `Base` from `app/db.py` so `Base.metadata.create_all()`
in the existing lifespan picks up the new tables automatically.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ConfigPrompt(Base):
    __tablename__ = "config_prompt"

    # ponytail: single-row table (id=1). Use upsert at the router layer.
    id: Mapped[int] = mapped_column(primary_key=True)
    prompt_texto: Mapped[str | None] = mapped_column(Text, nullable=True)
    actualizado_en: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ProcesamientoImagen(Base):
    __tablename__ = "procesamiento_imagenes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    ruta_archivo: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    resultado: Mapped[str | None] = mapped_column(Text, nullable=True)
    tiempo_procesamiento: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_mensaje: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha_creacion: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, nullable=False
    )

    __table_args__ = (
        CheckConstraint(
            "estado IN ('Pendiente','Procesando','Completado','Error')",
            name="ck_procesamiento_estado",
        ),
    )