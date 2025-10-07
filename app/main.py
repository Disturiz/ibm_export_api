# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.exporter import router as exporter_router

app = FastAPI(title="IBM Export API")

# CORS (ajusta orígenes según tu front)
origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rutas del módulo exporter
app.include_router(exporter_router)


@app.get("/health")
def health():
    return {"status": "ok"}
