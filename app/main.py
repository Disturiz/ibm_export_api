# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.exporter import router as exporter_router  # <-- importa el router

app = FastAPI(title="IBM Export API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ⬇️ registra el router (ruta final: /export)
app.include_router(exporter_router)
# Si quieres /api/export, usa:
# app.include_router(exporter_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
