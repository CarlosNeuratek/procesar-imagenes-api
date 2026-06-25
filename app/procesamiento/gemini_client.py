"""Lazy-init singleton wrapper over `google.genai.Client`.

ponytail: ADC (GOOGLE_APPLICATION_CREDENTIALS) is honored automatically by
the SDK; we only pass `vertexai=True`, project, location. Module-level
singleton because the worker is single-process — no need for a pool.
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

from google import genai
from google.genai import types

from ..config import settings

logger = logging.getLogger(__name__)

_client: Optional[genai.Client] = None
_client_lock = threading.Lock()


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = genai.Client(
                    vertexai=True,
                    project=settings.gcp_project or None,
                    location=settings.gcp_location,
                )
    return _client


def generate(prompt: str, image_bytes: bytes, mime_type: str) -> str:
    """Send prompt + image bytes to Gemini, return text or str(response) fallback."""
    part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    response = _get_client().models.generate_content(
        model=settings.gemini_model,
        contents=[prompt, part],
    )
    try:
        return response.text  # type: ignore[no-any-return]
    except (AttributeError, ValueError):
        return str(response)


def reset_client() -> None:
    """Test hook: drop the cached singleton so the next call rebuilds it."""
    global _client
    with _client_lock:
        _client = None