"""Pydantic request/response shapes for the procesamiento routers."""
from __future__ import annotations

from pydantic import BaseModel, Field


class PromptIn(BaseModel):
    prompt_texto: str = Field(min_length=1)


class PromptOut(BaseModel):
    id: int
    prompt_texto: str | None
    actualizado_en: str | None


class Imagen(BaseModel):
    id: int
    ruta_archivo: str
    estado: str
    resultado: str | None
    tiempo_procesamiento: float | None
    error_mensaje: str | None
    fecha_creacion: str


class ImagenList(BaseModel):
    imagenes: list[Imagen]


class ScanResult(BaseModel):
    scanned: int
    inserted: int
    skipped: int


class StartResponse(BaseModel):
    status: str
    threads: int


class StopResponse(BaseModel):
    status: str


class StatusResponse(BaseModel):
    running: bool
    threads: int
    queue_size: int
    completed: int
    error: int
    procesando: int