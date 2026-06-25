"""POST /api/procesamiento/{start,stop} + GET /api/procesamiento/status.

End-to-end implementation lives in T9 (this file owns the HTTP contract;
the worker module owns the pool + claim logic).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ...db import get_db
from ..schemas import StartResponse, StatusResponse, StopResponse
from .. import worker

router = APIRouter(prefix="/api/procesamiento", tags=["procesamiento-pool"])


@router.post("/start", response_model=StartResponse)
def start(threads: int = Query(default=1, ge=1, le=16)) -> StartResponse:
    result = worker.start(threads)
    if result["status"] == "running" and result["threads"] != threads:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=result)
    return StartResponse(**result)


@router.post("/stop", response_model=StopResponse)
def stop() -> StopResponse:
    return StopResponse(**worker.stop())


@router.get("/status", response_model=StatusResponse)
def get_status(db: Session = Depends(get_db)) -> StatusResponse:
    return StatusResponse(**worker.status(db))