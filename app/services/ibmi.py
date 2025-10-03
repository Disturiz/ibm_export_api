from __future__ import annotations
import os
import jaydebeapi
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# Carga .env desde la RAÍZ del repo (dos niveles arriba de este archivo)
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH)


def _cfg(key: str, default: str | None = None) -> str:
    val = os.getenv(key, default or "")
    return (val or "").strip()


def _qualify_table(tabla: str, default_schema: str | None) -> tuple[str, str | None]:
    t = (tabla or "").strip()
    if not t:
        raise ValueError("Tabla vacía")
    if "/" in t:
        lib, name = t.split("/", 1)
        return f"{lib.strip()}.{name.strip()}", lib.strip()
    if "." in t:
        lib, name = t.split(".", 1)
        return f"{lib.strip()}.{name.strip()}", lib.strip()
    if default_schema:
        return f"{default_schema}.{t}", default_schema
    return t, None


def get_df_from_ibmi(tabla: str):
    host = _cfg("IBMI_HOST")
    user = _cfg("IBMI_USER")
    password = _cfg("IBMI_PASSWORD")
    default_schema = _cfg("DEFAULT_SCHEMA")
    jar_path = _cfg("JAR_PATH", "./jt400/jt400.jar")

    if not host or not user or not password:
        raise RuntimeError("Faltan IBMI_HOST / IBMI_USER / IBMI_PASSWORD en .env")

    full_table, used_schema = _qualify_table(
        tabla, default_schema if default_schema else None
    )

    libraries = used_schema or default_schema or ""
    url = (
        f"jdbc:as400://{host};"
        f"naming=sql;libraries={libraries};"
        f"date format=iso;time format=iso;decimal separator=.;"
        f"translate binary=true;big decimal=true"
    )
    driver = "com.ibm.as400.access.AS400JDBCDriver"

    conn = jaydebeapi.connect(driver, url, [user, password], jar_path)
    try:
        cur = conn.cursor()
        sql = f"SELECT * FROM {full_table} FETCH FIRST 100000 ROWS ONLY"
        cur.execute(sql)
        cols = [d[0].strip() for d in cur.description]
        rows = cur.fetchall()
        import pandas as pd

        df = pd.DataFrame(rows, columns=cols).convert_dtypes()
        df.columns = [c.strip() for c in df.columns]
        return df
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()
