"""Re-export settings under the auth namespace so service.py can import it
without dragging the whole `app` package into import resolution order."""
from __future__ import annotations

from ..config import settings

__all__ = ["settings"]