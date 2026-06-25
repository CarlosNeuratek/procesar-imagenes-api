"""GET / POST /api/config/prompt — single-row prompt upsert."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...db import get_db
from ..models import ConfigPrompt
from ..schemas import PromptIn, PromptOut

router = APIRouter(prefix="/api/config", tags=["procesamiento-config"])


@router.get("/prompt", response_model=PromptOut)
def get_prompt(db: Session = Depends(get_db)) -> PromptOut:
    row = db.get(ConfigPrompt, 1)
    if row is None:
        return PromptOut(id=1, prompt_texto=None, actualizado_en=None)
    return PromptOut(
        id=1,
        prompt_texto=row.prompt_texto,
        actualizado_en=row.actualizado_en.isoformat() if row.actualizado_en else None,
    )


@router.post("/prompt", response_model=PromptOut)
def upsert_prompt(payload: PromptIn, db: Session = Depends(get_db)) -> PromptOut:
    from datetime import datetime, timezone

    row = db.get(ConfigPrompt, 1)
    ts = datetime.now(timezone.utc)
    if row is None:
        row = ConfigPrompt(id=1, prompt_texto=payload.prompt_texto, actualizado_en=ts)
        db.add(row)
    else:
        row.prompt_texto = payload.prompt_texto
        row.actualizado_en = ts
    db.commit()
    db.refresh(row)
    return PromptOut(
        id=1,
        prompt_texto=row.prompt_texto,
        actualizado_en=row.actualizado_en.isoformat() if row.actualizado_en else None,
    )