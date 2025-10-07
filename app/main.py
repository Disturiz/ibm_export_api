# app/main.py
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd

from app.exporter import export, export_to_excel  # usa las dos rutas correctas

app = FastAPI(title="IBM i Export API", version="1.0.0")


class ExportRequest(BaseModel):
    tabla: str
    archivo: str
    metadata: Optional[Dict[str, Any]] = None


class DemoRequest(BaseModel):
    archivo: str
    metadata: Optional[Dict[str, Any]] = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/export")
def export_endpoint(req: ExportRequest):
    """
    Extrae del IBMi (tabla) y genera el Excel + FTP (sin extensión en remoto).
    """
    try:
        return export(req.tabla, req.archivo, req.metadata or {})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/export_demo")
def export_demo(req: DemoRequest):
    """
    Genera un Excel de prueba con datos dummy y aplica el diseño.
    """
    try:
        df = pd.DataFrame(
            [
                {
                    "Fecha": "2025-09-30",
                    "Descripción": "Abono",
                    "Débito": 0.00,
                    "Crédito": 150.00,
                    "Saldo": 150.00,
                },
                {
                    "Fecha": "2025-10-01",
                    "Descripción": "Pago",
                    "Débito": 25.00,
                    "Crédito": 0.00,
                    "Saldo": 125.00,
                },
            ]
        )
        return export_to_excel(df, req.archivo, req.metadata or {})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
