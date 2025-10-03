# app/main.py
from __future__ import annotations

from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.exporter import export_to_excel

app = FastAPI(title="IBM_EXPORT_API_MAIN")


# ===== Models =====
class ExportRequest(BaseModel):
    tabla: str = Field(..., description="Nombre de la tabla en IBMi")
    archivo: str = Field(..., description="Nombre base del archivo (sin .xlsx)")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metadatos opcionales (logo_path, banner_cols_override, etc.)",
    )


# ===== Endpoints =====
@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "service": "IBM_EXPORT_API_MAIN"}


@app.post("/export")
def export_endpoint(req: ExportRequest) -> Dict[str, Any]:
    try:
        result = export_to_excel(
            tabla=req.tabla, archivo=req.archivo, metadata=req.metadata or {}
        )
        if not result.get("ok"):
            # export_to_excel ya retorna 'ok': False con 'error'
            raise HTTPException(
                status_code=500, detail=result.get("error", "Fallo al exportar")
            )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
