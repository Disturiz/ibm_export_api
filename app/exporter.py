# app/exporter.py
from __future__ import annotations

import os
import io
from typing import Any, Dict, Optional, Tuple

import pandas as pd
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

# ---- Integraciones del proyecto (con fallback si no están aún) ----
try:
    from app.services.ibmi import get_df_from_ibmi  # (tabla: str) -> pd.DataFrame
except Exception:
    get_df_from_ibmi = None

try:
    from app.services.ftp import upload_file  # ver firma en tu proyecto
except Exception:
    upload_file = None

# ==========================
# Router público del módulo
# ==========================
router = APIRouter(tags=["export"])


# ==========================
# Esquema de entrada
# ==========================
class ExportRequest(BaseModel):
    tabla: str
    archivo: str
    metadata: Optional[Dict[str, Any]] = None  # { logo_path, banner_cols_override }


# ==========================
# Utilidades de formato/IO
# ==========================
def _env_hex(name: str, default: str) -> str:
    """Lee color 'RRGGBB' desde env (tolera '#RRGGBB')."""
    val = (os.getenv(name, default) or "").strip()
    if val.startswith("#"):
        val = val[1:]
    val = val.upper()
    if len(val) != 6:
        val = default.lstrip("#").upper()
    return val


def _argb(rgb_hex: str) -> str:
    """Convierte 'RRGGBB' -> 'AARRGGBB' opaco."""
    h = rgb_hex.strip().lstrip("#").upper()
    if len(h) != 6:
        raise ValueError("Colors must be 6-hex RGB")
    return "FF" + h


def _resolve_logo_path(logo_path: Optional[str]) -> Optional[str]:
    if not logo_path:
        return None
    if not os.path.isabs(logo_path):
        app_dir = os.path.dirname(os.path.abspath(__file__))  # .../app
        candidate = os.path.join(os.path.dirname(app_dir), logo_path)  # raíz del repo
        if os.path.exists(candidate):
            return candidate
        candidate = os.path.join(app_dir, logo_path)  # relativo a /app
        if os.path.exists(candidate):
            return candidate
    return logo_path if os.path.exists(logo_path) else None


def _thin_border() -> Border:
    thin = Side(style="thin", color="FFBFBFBF")
    return Border(left=thin, right=thin, top=thin, bottom=thin)


def _autofit(ws, min_width: int = 9, max_width: int = 45) -> None:
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.value is None:
                continue
            s = str(cell.value)
            if len(s) > max_len:
                max_len = len(s)
        ws.column_dimensions[col_letter].width = max(
            min_width, min(max_len + 2, max_width)
        )


# ——— Estimación de ancho en píxeles (para escalar logo al ancho del merge) ———
def _col_pixels(ws, col_idx: int) -> int:
    """
    Aproxima ancho de columna en píxeles.
    Si no hay width definida, Excel usa ~8.43 (≈64 px).
    px ≈ width*7 + 5
    """
    letter = get_column_letter(col_idx)
    width = ws.column_dimensions[letter].width
    if width is None:
        width = 8.43
    return int(width * 7 + 5)


def _merged_pixels(ws, start_col: int, end_col: int) -> int:
    """Suma de píxeles aproximados entre columnas start_col..end_col."""
    return sum(_col_pixels(ws, c) for c in range(start_col, end_col + 1))


# ==========================
# Bloques de escritura
# ==========================
def _write_banner_and_logo(
    ws, cols: int, banner_hex: str, logo_path: Optional[str], row: int = 1
) -> None:
    # 1) Franja roja (A1:Ex)
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=cols)
    ws.cell(row=row, column=1).fill = PatternFill("solid", fgColor=_argb(banner_hex))

    # 2) Logo escalado al ancho del merge y ajustando altura de la fila 1
    if not logo_path:
        return
    try:
        img = XLImage(logo_path)
        target_w = _merged_pixels(ws, 1, cols)

        # Escalar manteniendo proporción al ancho del banner
        scale = target_w / float(img.width if img.width else 1)
        img.width = int(target_w)
        img.height = int(img.height * scale)

        # Limitar altura para no desproporcionar
        max_h_px = 70  # ajustable
        if img.height > max_h_px:
            s = max_h_px / float(img.height)
            img.height = int(max_h_px)
            img.width = int(img.width * s)

        # >>> Ajuste clave: altura de la fila 1 = altura del logo (px -> puntos)
        # Excel maneja alto de fila en "puntos" (1 pt ≈ 1/72 in). A 96 DPI: 1 px ≈ 0.75 pt.
        px_to_pt = 0.75
        ws.row_dimensions[row].height = img.height * px_to_pt  # p.ej. 70 px ≈ 52.5 pt

        img.anchor = f"A{row}"
        ws.add_image(img)
    except Exception:
        pass


def _write_metadata_from_df(ws, df: pd.DataFrame, start_row: int = 2) -> int:
    """
    Escribe las primeras 6 filas del DF como metadatos:
      - Col A: etiqueta (df.iloc[i,0])
      - Col B: valor   (df.iloc[i,1])
    **Ambos en negritas**.
    Devuelve la siguiente fila disponible.
    """
    meta = df.iloc[:6, :2].fillna("")
    r = start_row
    for _, (label, value) in meta.iterrows():
        c1 = ws.cell(row=r, column=1, value=str(label or ""))
        c2 = ws.cell(row=r, column=2, value=str(value or ""))
        c1.font = Font(bold=True)
        c2.font = Font(bold=True)
        r += 1
    return r


def _write_center_title(
    ws, text: str, cols: int, row: int, font_size: int = 14, color_hex: str = "333333"
) -> None:
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=cols)
    c = ws.cell(row=row, column=1, value=text)
    c.alignment = Alignment(horizontal="center", vertical="center")
    c.font = Font(size=font_size, bold=True, color=_argb(color_hex))


# ==========================
# Preparación de detalle
# ==========================
REQUIRED_HEADERS = ["FECHA", "DESCRIPCION", "DEBITO", "CREDITO", "SALDO CONTABLE"]


def _prepare_detail(df: pd.DataFrame) -> pd.DataFrame:
    """
    Toma el DF original, usa filas 0..5 como metadatos y
    devuelve el detalle desde la fila 6 en adelante con columnas:
    FECHA, DESCRIPCION, DEBITO, CREDITO, SALDO CONTABLE.
    """
    if len(df) <= 6:
        raise ValueError(
            "La tabla no contiene suficiente información (se requieren al menos 7 filas)."
        )

    detail = df.iloc[6:].reset_index(drop=True).copy()

    # Intentar por nombres
    cols = {c.upper().strip(): c for c in detail.columns}
    mapping = {}
    if "FECHA" in cols:
        mapping["FECHA"] = cols["FECHA"]
    if "DESCRIPCION" in cols:
        mapping["DESCRIPCION"] = cols["DESCRIPCION"]
    if "DEBITO" in cols:
        mapping["DEBITO"] = cols["DEBITO"]
    if "CREDITO" in cols:
        mapping["CREDITO"] = cols["CREDITO"]
    if "SALDO CONTABLE" in cols:
        mapping["SALDO CONTABLE"] = cols["SALDO CONTABLE"]
    elif "SALDO" in cols:
        mapping["SALDO CONTABLE"] = cols["SALDO"]

    if len(mapping) < 5:
        # Fallback por posición
        if detail.shape[1] < 5:
            raise ValueError("El detalle no tiene al menos 5 columnas.")
        sel = detail.iloc[:, :5]
        sel.columns = REQUIRED_HEADERS
    else:
        sel = detail[list(mapping.values())].copy()
        sel.columns = REQUIRED_HEADERS  # renombra a los requeridos

    # Normalizaciones
    # FECHA -> fecha si posible
    try:
        sel["FECHA"] = pd.to_datetime(sel["FECHA"], errors="coerce").dt.date
    except Exception:
        pass

    # Montos
    for col in ["DEBITO", "CREDITO", "SALDO CONTABLE"]:
        try:
            sel[col] = (
                sel[col]
                .astype(str)
                .str.replace(".", "", regex=False)  # quita miles si vinieran con '.'
                .str.replace(",", ".", regex=False)  # coma decimal -> punto
            )
            sel[col] = pd.to_numeric(sel[col], errors="coerce")
        except Exception:
            sel[col] = pd.to_numeric(sel[col], errors="coerce")

    return sel


# ==========================
# Lectura de datos IBMi
# ==========================
def _fetch_df(table_name: str) -> pd.DataFrame:
    if get_df_from_ibmi is None:
        raise RuntimeError("No está disponible app.services.ibmi.get_df_from_ibmi")
    df = get_df_from_ibmi(table_name)
    if not isinstance(df, pd.DataFrame):
        raise RuntimeError("get_df_from_ibmi no devolvió un DataFrame")
    return df


# ==========================
# Export principal
# ==========================
def export_to_excel(
    tabla: str, archivo: str, metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Orden específico:
      1) Banner rojo + logo (ancho completo, fila 1 ajustada a la altura del logo).
      2) Metadatos = primeras 6 filas (negritas).
      3) Título 'Consulta de movimientos' centrado.
      4) Encabezados fijos: FECHA, DESCRIPCION, DEBITO, CREDITO, SALDO CONTABLE.
      5) Detalle desde la 7ª fila del DF original.
    """
    import time

    t0 = time.time()

    # Config .env
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "/app/output").strip()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    BANNER_COLOR = _env_hex("BANNER_COLOR", "ED1C24")
    HEADER_GRAY = _env_hex("HEADER_GRAY", "F2F2F2")
    TEXT_DARK = _env_hex("TEXT_DARK", "333333")

    DEFAULT_BANNER_COLS = int(os.getenv("BANNER_COLS", "5") or "5")

    FTP_HOST = os.getenv("FTP_HOST", "").strip()
    FTP_PORT = int(os.getenv("FTP_PORT", "21") or "21")
    FTP_USER = os.getenv("FTP_USER", "").strip()
    FTP_PASSWORD = os.getenv("FTP_PASSWORD", "").strip()
    FTP_DIR = os.getenv("FTP_DIR", "/").strip()
    FTP_TLS = os.getenv("FTP_TLS", "false").strip().lower() == "true"

    WRITE_LOCAL_COPY = os.getenv("WRITE_LOCAL_COPY", "true").strip().lower() != "false"

    # Metadata del request
    meta = metadata or {}
    logo_path = _resolve_logo_path(meta.get("logo_path"))
    banner_cols_override = (
        int(meta["banner_cols_override"]) if meta.get("banner_cols_override") else None
    )

    # 1) Traer DF
    df = _fetch_df(tabla)

    # 2) Preparar detalle (desde fila 6)
    detail_df = _prepare_detail(df)

    # 3) Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte"

    # Cantidad de columnas del banner (usamos 5 para coincidir con el layout)
    banner_cols = banner_cols_override or 5 or DEFAULT_BANNER_COLS
    banner_cols = max(banner_cols, 5)  # mínimo 5 para FECHA..SALDO CONTABLE

    # Banner + logo (ajusta altura de la fila 1)
    _write_banner_and_logo(
        ws, cols=banner_cols, banner_hex=BANNER_COLOR, logo_path=logo_path, row=1
    )

    # Metadatos (filas 2..7)
    next_row = _write_metadata_from_df(ws, df, start_row=2)

    # Fila en blanco
    # next_row += 1

    # Título centrado
    _write_center_title(
        ws,
        "Consulta de movimientos",
        cols=banner_cols,
        row=next_row,
        font_size=14,
        color_hex=TEXT_DARK,
    )

    # Encabezados dos filas después
    header_row = next_row + 2

    # Encabezados fijos
    for j, name in enumerate(
        ["FECHA", "DESCRIPCION", "DEBITO", "CREDITO", "SALDO CONTABLE"], start=1
    ):
        c = ws.cell(row=header_row, column=j, value=name)
        c.font = Font(bold=True)
        c.alignment = Alignment(horizontal="center")
        c.fill = PatternFill("solid", fgColor=_argb(HEADER_GRAY))
        c.border = _thin_border()

    # Datos (a partir de la fila siguiente)
    r = header_row + 1
    for _, row_vals in detail_df.iterrows():
        # FECHA (centrada + formato)
        val_fecha = row_vals["FECHA"]
        c_fecha = ws.cell(row=r, column=1, value=val_fecha)
        c_fecha.border = _thin_border()
        c_fecha.alignment = Alignment(horizontal="center")  # <<— centrado solicitado
        if pd.notna(val_fecha):
            c_fecha.number_format = "yyyy-mm-dd"

        # DESCRIPCION
        c_desc = ws.cell(row=r, column=2, value=row_vals["DESCRIPCION"])
        c_desc.border = _thin_border()

        # DEBITO, CREDITO, SALDO CONTABLE
        for j, colname in enumerate(["DEBITO", "CREDITO", "SALDO CONTABLE"], start=3):
            v = row_vals[colname]
            c = ws.cell(row=r, column=j, value=(None if pd.isna(v) else float(v)))
            c.border = _thin_border()
            c.alignment = Alignment(horizontal="right")
            c.number_format = "#,##0.00"

        r += 1

    # Autoajuste de columnas
    _autofit(ws, min_width=9, max_width=45)

    # Guardar local
    local_xlsx = os.path.join(OUTPUT_DIR, f"{archivo}.xlsx")
    if WRITE_LOCAL_COPY:
        wb.save(local_xlsx)
    else:
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)

    # FTP opcional (nombre remoto SIN extensión)
    uploaded_info = None
    if FTP_HOST and FTP_USER and FTP_PASSWORD and upload_file:
        remote_name = archivo
        try:
            if WRITE_LOCAL_COPY:
                uploaded_info = upload_file(
                    local_path=local_xlsx,
                    host=FTP_HOST,
                    port=FTP_PORT,
                    user=FTP_USER,
                    password=FTP_PASSWORD,
                    remote_dir=FTP_DIR,
                    remote_name=remote_name,
                    tls=FTP_TLS,
                )
            else:
                tmp_path = os.path.join(OUTPUT_DIR, f"__tmp_{archivo}.xlsx")
                with open(tmp_path, "wb") as f:
                    f.write(bio.getbuffer())
                uploaded_info = upload_file(
                    local_path=tmp_path,
                    host=FTP_HOST,
                    port=FTP_PORT,
                    user=FTP_USER,
                    password=FTP_PASSWORD,
                    remote_dir=FTP_DIR,
                    remote_name=remote_name,
                    tls=FTP_TLS,
                )
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
        except Exception as ex:
            uploaded_info = {"status": "error", "error": str(ex)}

    elapsed_ms = int((time.time() - t0) * 1000)
    return {
        "ok": True,
        "table": tabla,
        "rows": int(detail_df.shape[0]),
        "cols": int(detail_df.shape[1]),
        "uploaded_to": uploaded_info or {"status": "skipped"},
        "local_copy": local_xlsx if WRITE_LOCAL_COPY else None,
        "elapsed_ms": elapsed_ms,
    }


# ==========================
# Endpoint HTTP
# ==========================
@router.post("/export")
def export(req: ExportRequest = Body(...)) -> Dict[str, Any]:
    try:
        return export_to_excel(req.tabla, req.archivo, req.metadata)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
