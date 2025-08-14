from fastapi import FastAPI, HTTPException, Security
from .security import require_api_key
from .schemas import ExportRequest, ExportResponse
from .exporter import export_to_excel

app = FastAPI(
    title="Exportador IBM i → Excel",
    swagger_ui_parameters={"persistAuthorization": True},  # opcional
)


@app.get("/")
def root():
    return {"service": "Exportador IBM i → Excel", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/export", response_model=ExportResponse, response_model_exclude_none=True)
def exportar(req: ExportRequest, _: bool = Security(require_api_key)):
    try:
        return export_to_excel(req.tabla, req.archivo)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
