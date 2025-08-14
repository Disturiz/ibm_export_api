import os
from dotenv import load_dotenv

load_dotenv()

EXPORT_API_KEY = os.getenv("EXPORT_API_KEY", "MiSecreto_2025")
IBMI_HOST = os.getenv("IBMI_HOST")
IBMI_USER = os.getenv("IBMI_USER")
IBMI_PASSWORD = os.getenv("IBMI_PASSWORD")
JAR_PATH = os.getenv("JAR_PATH")
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")
DEFAULT_SCHEMA = os.getenv("DEFAULT_SCHEMA", "DACCYFILES")

for var in ["IBMI_HOST", "IBMI_USER", "IBMI_PASSWORD", "JAR_PATH"]:
    if not globals()[var]:
        raise RuntimeError(f"Falta variable de entorno: {var}")

# --- FTP ---
FTP_HOST = os.getenv("FTP_HOST", "")
FTP_PORT = int(os.getenv("FTP_PORT", "21"))
FTP_USER = os.getenv("FTP_USER", "")
FTP_PASSWORD = os.getenv("FTP_PASSWORD", "")
FTP_DIR = os.getenv("FTP_DIR", "/FORMATOS-MT-PDF")
FTP_TLS = os.getenv("FTP_TLS", "true").lower() == "true"  # FTPS explícito si true
WRITE_LOCAL_COPY = os.getenv("WRITE_LOCAL_COPY", "true").lower() == "true"
