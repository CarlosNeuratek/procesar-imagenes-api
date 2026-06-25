"""Runtime configuration loaded from environment variables.

ponytail: stdlib os.getenv only. No pydantic-settings — one less dep for a
mock backend. Promote to pydantic-settings when env vars outgrow a dict.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    cors_origins: list[str] = None  # type: ignore[assignment]
    admin_email: str = os.getenv("ADMIN_EMAIL", "admin@contadores")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "admin123")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./contadores.db")
    bcrypt_rounds: int = int(os.getenv("BCRYPT_ROUNDS", "12"))

    def __post_init__(self) -> None:
        # Frozen dataclass + list default — build via object.__setattr__.
        object.__setattr__(
            self,
            "cors_origins",
            _split_csv(os.getenv("CORS_ORIGINS", "http://localhost:3000")),
        )


settings = Settings()