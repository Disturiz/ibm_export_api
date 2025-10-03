# app/exporter.py
from __future__ import annotations

import os
import time
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.drawing.image import Image as XLImage
from openpyxl.utils import get_column_letter  # <- para evitar MergedCell.column_letter

from app.services.ibmi import get_df_from_ibmi
from app.services.ftp import upload_file

# ==========================
# Carga .env y utilidades
# ==========================
load_dotenv()
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output").strip() or "./output"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _env_color(key: str, default_hex: str) -> str:
    v = (os.getenv(key, default_hex) or default_hex).strip()
    return (v[1:] if v.startswith("#") else v).upper()


def _env_int(key: str, default_val: int) -> int:
    try:
        return int(os.getenv(key, str(default_val)))
    except Exception:
        return default_val


# Colores / tamaños por .env
BANNER_COLOR = _env_color("BANNER_COLOR", "ED1C24")
HEADER_GRAY = _env_color("HEADER_GRAY", "F2F2F2")
BORDER_GRAY = _env_color("BORDER_GRAY", "D9D9D9")
TEXT_DARK = _env_color("TEXT_DARK", "333333")

DEFAULT_BANNER_COLS = _env_int("BANNER_COLS", 6)
DEFAULT_BANNER_HEIGHT = _env_int("BANNER_HEIGHT_PX", 38)
DEFAULT_LOGO_HEIGHT = _env_int("LOGO_HEIGHT_PX", 28)
DEFAULT_TITLE_TEXT = os.getenv("TITLE_TEXT", "Consulta de movimientos")


# ==========================
# Estilos
# ==========================
def _border(thin: bool = True) -> Border:
    style = "thin" if thin else "medium"
    color = BORDER_GRAY
    return Border(
        left=Side(style=style, color=color),
        right=Side(style=style, color=color),
        top=Side(style=style, color=color),
        bottom=Side(style=style, color=color),
    )


def _autofit_columns(
    ws, from_col: int, to_col: int, min_width: float = 8.0, max_width: float = 60.0
) -> None:
    """
    Autoajuste seguro: usa get_column_letter(col) en lugar de ws.cell(...).column_letter
    para evitar errores con celdas fusionadas del banner.
    """
    for col in range(from_col, to_col + 1):
        letter = get_column_letter(col)
        width = min_width
        for row in ws.iter_rows(min_row=1, max_col=to_col, max_row=ws.max_row):
            val = row[col - 1].value
            if val is None:
                continue
            s = str(val)
            width = max(width, len(s) * 1.2 + 2)
        ws.column_dimensions[letter].width = min(width, max_width)


# ==========================
# Banner + título
# ==========================
def _render_banner_and_title(
    ws,
    *,
    banner_cols: int,
    logo_path: Optional[str],
    logo_height_px: int,
    banner_height_px: int,
    title_text: str,
) -> Dict[str, int]:
    start_col, end_col = 1, max(1, banner_cols)

    # Banner (fila 1 fusionada)
    ws.merge_cells(start_row=1, start_column=start_col, end_row=1, end_column=end_col)
    ws.cell(row=1, column=1).fill = PatternFill("solid", fgColor=BANNER_COLOR)
    ws.row_dimensions[1].height = banner_height_px

    # Logo (opcional)
    if logo_path and os.path.exists(logo_path):
        try:
            img = XLImage(logo_path)
            if logo_height_px and img.height:
                ratio = logo_height_px / img.height
                img.width = int(img.width * ratio)
                img.height = int(img.height * ratio)
            ws.add_image(img, "A1")
        except Exception:
            pass

    # Título (fila 3)
    title_row = 3
    ws.merge_cells(
        start_row=title_row, start_column=1, end_row=title_row, end_column=end_col
    )
    c_title = ws.cell(row=title_row, column=1, value=title_text)
    c_title.font = Font(bold=True, size=14, color=TEXT_DARK)
    c_title.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[title_row].height = 24
    return {"title_row": title_row}


# ==========================
# Tabla (sin bloque de metadatos)
# ==========================
def _render_table(ws, df, *, start_row: int) -> None:
    # Encabezados
    header_row = start_row
    for idx, col in enumerate(df.columns, start=1):
        c = ws.cell(row=header_row, column=idx, value=str(col))
        c.font = Font(bold=True, color=TEXT_DARK)
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.fill = PatternFill("solid", fgColor=HEADER_GRAY)
        c.border = _border()

    # Datos
    for r, row in enumerate(df.itertuples(index=False), start=header_row + 1):
        for c, val in enumerate(row, start=1):
            cell = ws.cell(row=r, column=c, value=val)
            cell.alignment = Alignment(vertical="top")
            cell.border = _border()

    _autofit_columns(ws, 1, len(df.columns))


# ==========================
# Generación completa
# ==========================
def write_excel(
    df,
    archivo: str,
    *,
    logo_path: Optional[str],
    banner_cols_override: Optional[int],
    title_text: Optional[str],
    logo_height_px: Optional[int],
    banner_height_px: Optional[int],
) -> str:
    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte"

    # Parámetros (metadata > .env)
    _title_text = title_text or DEFAULT_TITLE_TEXT
    _logo_h = int(logo_height_px or DEFAULT_LOGO_HEIGHT)
    _banner_h = int(banner_height_px or DEFAULT_BANNER_HEIGHT)
    banner_cols_min = max(DEFAULT_BANNER_COLS, len(df.columns))
    banner_cols = int(banner_cols_override or banner_cols_min)

    # Banner + título
    info = _render_banner_and_title(
        ws,
        banner_cols=banner_cols,
        logo_path=logo_path,
        logo_height_px=_logo_h,
        banner_height_px=_banner_h,
        title_text=_title_text,
    )

    # Tabla directamente bajo el título
    table_start = info["title_row"] + 2
    _render_table(ws, df, start_row=table_start)

    # Guardar local
    safe_name = f"{archivo}.xlsx" if not archivo.lower().endswith(".xlsx") else archivo
    out_path = os.path.abspath(os.path.join(OUTPUT_DIR, safe_name))
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    wb.save(out_path)
    return out_path


# ==========================
# Endpoint / lógica de exportación
# ==========================
def export_from_table(
    tabla: str, archivo: str, metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    t0 = time.time()
    meta = metadata or {}

    df = get_df_from_ibmi(tabla)
    local_path = write_excel(
        df,
        archivo=archivo,
        logo_path=meta.get("logo_path"),
        banner_cols_override=meta.get("banner_cols_override"),
        title_text=meta.get("title_text"),
        logo_height_px=meta.get("logo_height_px"),
        banner_height_px=meta.get("banner_height_px"),
    )

    # Subida a FTP SIN extensión
    remote_name = os.path.splitext(os.path.basename(local_path))[0]
    uploaded = upload_file(local_path=local_path, remote_name=remote_name)

    elapsed_ms = int((time.time() - t0) * 1000)
    return {
        "ok": True,
        "table": tabla,
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
        "uploaded_to": uploaded,
        "local_copy": local_path,
        "elapsed_ms": elapsed_ms,
    }


# ---- Compatibilidad con main.py que importa export_to_excel ----
def export_to_excel(tabla: str, archivo: str, metadata: dict | None = None) -> dict:
    return export_from_table(tabla=tabla, archivo=archivo, metadata=metadata or {})
