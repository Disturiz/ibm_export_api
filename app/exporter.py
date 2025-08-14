import os
import time
import io
import pandas as pd
from .config import (
    OUTPUT_DIR,
    DEFAULT_SCHEMA,
    FTP_HOST,
    FTP_PORT,
    FTP_USER,
    FTP_PASSWORD,
    FTP_DIR,
    FTP_TLS,
    WRITE_LOCAL_COPY,
)
from .services.jdbc import connect_ibmi
from .services.io_utils import ensure_dir, validate_table, validate_file

# from .services import ftp_client
from .services.ftp_client import upload_file, upload_bytes


def _excel_bytes_from_df(df: pd.DataFrame) -> bytes:
    # Genera el .xlsx en memoria (sin tocar disco)
    with io.BytesIO() as buf:
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        return buf.getvalue()


def export_to_excel(nombre_tabla: str, nombre_archivo: str) -> dict:
    validate_table(nombre_tabla)
    validate_file(nombre_archivo)

    if "." in nombre_tabla:
        sql = f"SELECT * FROM {nombre_tabla}"
        table_full = nombre_tabla
    else:
        sql = f"SELECT * FROM {DEFAULT_SCHEMA}.{nombre_tabla}"
        table_full = f"{DEFAULT_SCHEMA}.{nombre_tabla}"

    t0 = time.time()
    conn = connect_ibmi()
    try:
        cur = conn.cursor()
        try:
            cur.execute(sql)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
            df = pd.DataFrame(rows, columns=cols)
        finally:
            cur.close()
    finally:
        conn.close()

    # Nombre remoto final
    remote_name = f"{nombre_archivo}.xlsx"

    uploaded_to = {
        "host": FTP_HOST,
        "dir": FTP_DIR,
        "filename": remote_name,
        "tls": FTP_TLS,
        "port": FTP_PORT,
    }

    local_path = os.path.join(OUTPUT_DIR, remote_name)
    kept_local = False

    if WRITE_LOCAL_COPY:
        # 1) Guardar local y 2) subir ese archivo
        ensure_dir(OUTPUT_DIR)
        import openpyxl  # asegura dependencia instalada

        df.to_excel(local_path, index=False)
        upload_file(
            host=FTP_HOST,
            port=FTP_PORT,
            user=FTP_USER,
            password=FTP_PASSWORD,
            remote_dir=FTP_DIR,
            local_path=local_path,
            remote_name=remote_name,
            use_tls=FTP_TLS,
        )
        kept_local = True
    else:
        # Subir directamente en memoria (sin dejar copia en disco)
        data = _excel_bytes_from_df(df)
        upload_bytes(
            host=FTP_HOST,
            port=FTP_PORT,
            user=FTP_USER,
            password=FTP_PASSWORD,
            remote_dir=FTP_DIR,
            data=data,
            remote_name=remote_name,
            use_tls=FTP_TLS,
        )

    elapsed = int((time.time() - t0) * 1000)
    return {
        "ok": True,
        "table": table_full,
        "rows": len(df.index),
        "cols": len(df.columns),
        "uploaded_to": uploaded_to,
        "local_copy": local_path if kept_local else None,
        "elapsed_ms": elapsed,
    }
