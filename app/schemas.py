# app/schemas.py — igual, con metadata opcional
from __future__ import annotations
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class ExportRequest(BaseModel):
    tabla: str = Field(..., min_length=1, max_length=30)
    archivo: str = Field(..., min_length=1, max_length=60)
    metadata: Optional[Dict[str, Any]] = None


class ExportResponse(BaseModel):
    ok: bool
    table: str
    rows: int
    cols: int
    uploaded_to: dict
    local_copy: Optional[str] = None
    elapsed_ms: int