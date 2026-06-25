"""Runtime configuration loaded from environment variables.

ponytail: stdlib os.getenv only. No pydantic-settings — one less dep for a
mock backend. Promote to pydantic-settings when env vars outgrow a dict.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


# ponytail: default creds path lives next to the app; env wins.
_DEFAULT_GOOGLE_CREDS = (
    "/Users/carlos/Documents/GitHub/teyma/contadores/"
    "contadores-api/credentials/google-credentials.json"
)


@dataclass(frozen=True)
class Settings:
    api_host: str = os.getenv("API_HOST", "127.0.0.1")
    api_port: int = int(os.getenv("API_PORT", "8000"))
    cors_origins: list[str] = None  # type: ignore[assignment]
    admin_email: str = os.getenv("ADMIN_EMAIL", "admin@contadores")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "admin123")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./contadores.db")
    bcrypt_rounds: int = max(4, min(15, int(os.getenv("BCRYPT_ROUNDS", "12"))))

    # procesar-imagenes-api slice — Gemini batch processing
    fotos_dir: str = os.getenv("FOTOS_DIR", "/fotos")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    max_threads: int = max(1, min(16, int(os.getenv("MAX_THREADS", "1"))))
    stale_processing_minutes: int = max(
        1, int(os.getenv("STALE_PROCESSING_MINUTES", "10"))
    )
    gcp_project: str = os.getenv("GCP_PROJECT", "")
    gcp_location: str = os.getenv("GCP_LOCATION", "us-central1")
    google_application_credentials: str = os.getenv(
        "GOOGLE_APPLICATION_CREDENTIALS", _DEFAULT_GOOGLE_CREDS
    )

    def __post_init__(self) -> None:
        # Frozen dataclass + list default — build via object.__setattr__.
        object.__setattr__(
            self,
            "cors_origins",
            _split_csv(os.getenv("CORS_ORIGINS", "http://localhost:3000")),
        )


settings = Settings()