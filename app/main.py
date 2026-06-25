"""FastAPI application entry point."""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .auth.models import User
from .auth.rate_limit import LoginRateLimitMiddleware
from .auth.router import router as auth_router
from .auth.security import hash_password
from .config import settings
from .db import Base, SessionLocal, get_engine

logger = logging.getLogger("contadores.api")


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


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    return {"status": "ok"}