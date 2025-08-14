# api_server.py  (opcional)
from fastapi import FastAPI, HTTPException, Header
from app.exporter import export_to_excel
from app.config import EXPORT_API_KEY

app = FastAPI(title="Exportador IBM i → Excel (standalone)")


@app.get("/")
def root():
    return {"service": "Exportador IBM i → Excel", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/export")
def export_endpoint(payload: dict, x_api_key: str = Header(default="")):
    if x_api_key != EXPORT_API_KEY:
        raise HTTPException(status_code=401, detail="API Key inválida")
    try:
        tabla = str(payload.get("tabla", "")).strip()
        archivo = str(payload.get("archivo", "")).strip()
        return export_to_excel(tabla, archivo)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
