# app/schemas.py
from typing import Optional
from pydantic import BaseModel, Field


# ------- Request -------
class ExportRequest(BaseModel):
    # Validación directa por longitud (1..30) compatible v1/v2
    tabla: str = Field(..., min_length=1, max_length=30)
    archivo: str = Field(..., min_length=1, max_length=30)


# ------- Response -------
class UploadedTo(BaseModel):
    host: str
    dir: str
    filename: str
    tls: bool
    port: int


class ExportResponse(BaseModel):
    ok: bool
    table: str
    rows: int
    cols: int
    elapsed_ms: int
    # Compatibilidad: si alguna ruta aún devuelve 'path'
    path: Optional[str] = None
    # Nuevos campos para subida por (F)TPS
    local_copy: Optional[str] = None
    uploaded_to: Optional[UploadedTo] = None
