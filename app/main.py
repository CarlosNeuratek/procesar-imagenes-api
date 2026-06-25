"""FastAPI application entry point."""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .auth.models import User
from .auth.rate_limit import LoginRateLimitMiddleware
from .auth.router import router as auth_router
from .auth.security import hash_password
from .config import settings
from .db import Base, SessionLocal, get_engine
from .procesamiento.models import ProcesamientoImagen
from .procesamiento.routers import (
    config as proc_config_router,
    imagenes as proc_imagenes_router,
    procesamiento as proc_procesamiento_router,
)
from .users.router import router as users_router

logger = logging.getLogger("contadores.api")


def _recover_orphaned_procesando() -> int:
    """Reset Procesando rows older than stale_processing_minutes to Pendiente."""
    threshold = datetime.now(timezone.utc) - timedelta(
        minutes=settings.stale_processing_minutes
    )
    with SessionLocal() as db:
        rows = (
            db.query(ProcesamientoImagen)
            .filter(
                ProcesamientoImagen.estado == "Procesando",
                ProcesamientoImagen.fecha_creacion < threshold,
            )
            .all()
        )
        for row in rows:
            row.estado = "Pendiente"
        db.commit()
        return len(rows)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=get_engine())
    with SessionLocal() as db:
        admin = db.execute(
            select(User).where(User.email == settings.admin_email)
        ).scalar_one_or_none()
        if admin is None:
            db.add(
                User(
                    email=settings.admin_email,
                    name="Admin",
                    role="admin",
                    password_hash=hash_password(settings.admin_password),
                )
            )
            db.commit()
            logger.info("admin bootstrapped: %s", settings.admin_email)
    recovered = _recover_orphaned_procesando()
    logger.info(
        "procesamiento ready: model=%s fotos=%s stale_min=%d recovered_orphans=%d",
        settings.gemini_model,
        settings.fotos_dir,
        settings.stale_processing_minutes,
        recovered,
    )
    yield


app = FastAPI(title="contadores-api", version="0.1.0", lifespan=lifespan)
app.add_middleware(LoginRateLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(proc_config_router.router)
app.include_router(proc_imagenes_router.router)
app.include_router(proc_procesamiento_router.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}