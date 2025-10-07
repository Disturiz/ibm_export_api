# app/exporter.py

import os
from io import BytesIO
from typing import Optional, Dict, Any

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Border, Side, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.drawing.image import Image as XLImage


# =========================
# Utilidades de configuración
# =========================


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.getenv(name)
    return v if v not in (None, "") else default


def _argb(hex_color: str) -> str:
    """
    Normaliza '#rrggbb' / 'rrggbb' / 'aarrggbb' -> 'aarrggbb'.
    """
    if not hex_color:
        return "FF000000"
    s = str(hex_color).strip().lstrip("#").upper()
    if len(s) == 6:
        return "FF" + s
    if len(s) == 8:
        return s
    return "FF000000"


def make_fill(color_hex: str) -> PatternFill:
    """
    Devuelve un PatternFill sólido a partir de un color hex.
    (IMPORTANTE: usar fgColor/start_color/end_color válidos)
    """
    return PatternFill(fill_type="solid", fgColor=_argb(color_hex))


def make_thin_border(color_hex: str) -> Border:
    c = _argb(color_hex)
    thin = Side(style="thin", color=c)
    return Border(top=thin, left=thin, right=thin, bottom=thin)


# =========================
# Parámetros visuales / defaults
# =========================

# Colores (acepta "#RRGGBB" o "RRGGBB")
BANNER_COLOR = _env("BANNER_COLOR", "#ED1C24")
HEADER_GRAY = _env("HEADER_GRAY", "#F2F2F2")
BORDER_GRAY = _env("BORDER_GRAY", "#D9D9D9")
TEXT_DARK = _env("TEXT_DARK", "#333333")

# Banner, logo y títulos
BANNER_COLS = int(_env("BANNER_COLS", "6"))
BANNER_HEIGHT_PX = int(_env("BANNER_HEIGHT_PX", "38"))
LOGO_PATH_ENV = _env("LOGO_PATH", "app/assets/davivienda_oficial.png")
LOGO_HEIGHT_PX = int(_env("LOGO_HEIGHT_PX", "28"))
TITLE_TEXT = _env("TITLE_TEXT", "Consulta de movimientos")

# Salida
OUTPUT_DIR = _env("OUTPUT_DIR", "./output")


# =========================
# Servicios externos (opcionales)
# =========================


def _try_get_df_from_ibmi(table: str) -> pd.DataFrame:
    """
    Intenta importar y ejecutar un lector de IBMi.
    Debe existir app.services.ibmi.get_df_from_ibmi(table: str) -> DataFrame
    Si no existe, levanta RuntimeError.
    """
    try:
        from app.services.ibmi import get_df_from_ibmi  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "No se encontró app.services.ibmi.get_df_from_ibmi(table)"
        ) from e

    # Algunas variantes no aceptan 'schema', usamos firma simple:
    df = get_df_from_ibmi(table)
    if not isinstance(df, pd.DataFrame):
        raise RuntimeError("get_df_from_ibmi(table) no devolvió un DataFrame")
    return df


def _try_upload_ftp(
    local_path: str, remote_name_no_ext: str
) -> Optional[Dict[str, Any]]:
    """
    Sube el archivo al FTP (sin extensión en el nombre remoto).
    Requiere app.services.ftp.upload_file(local_path, remote_name)
    Retorna dict con info si sube, o None si no hay servicio disponible.
    """
    try:
        from app.services.ftp import upload_file  # type: ignore
    except Exception:
        return None

    try:
        info = upload_file(local_path, remote_name_no_ext)
        return info
    except Exception as e:
        return {"error": str(e)}


# =========================
# Construcción del Excel
# =========================


def _apply_banner(ws, banner_cols: int, logo_path: Optional[str]):
    """
    Pinta la franja roja en fila 1, inserta logo en A1 y ajusta altura.
    """
    # Altura de la fila 1
    if BANNER_HEIGHT_PX > 0:
        ws.row_dimensions[1].height = BANNER_HEIGHT_PX

    # Relleno por celda en la fila 1
    banner_fill = make_fill(BANNER_COLOR)
    for col in range(1, banner_cols + 1):
        ws.cell(row=1, column=col).fill = banner_fill

    # Insertar logo si existe
    if logo_path and os.path.exists(logo_path):
        try:
            img = XLImage(logo_path)
            if LOGO_HEIGHT_PX > 0:
                img.height = LOGO_HEIGHT_PX
            ws.add_image(img, "A1")
        except Exception:
            # No interrumpir si el logo falla
            pass


def _apply_title(ws, banner_cols: int):
    """
    Imprime el título en fila 2 y lo centra verticalmente.
    """
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=banner_cols)
    title_cell = ws.cell(row=2, column=1, value=TITLE_TEXT)
    title_cell.font = Font(size=14, bold=True, color=_argb(TEXT_DARK))
    title_cell.alignment = Alignment(vertical="center")
    # altura de la fila 2 (ligeramente mayor para respiración)
    ws.row_dimensions[2].height = 22


def _write_table(ws, df: pd.DataFrame, start_row: int = 4, start_col: int = 1):
    """
    Escribe encabezado y datos iniciando en (start_row, start_col).
    Retorna header_row y número de columnas.
    """
    header_row = start_row

    # Encabezado
    for j, col_name in enumerate(df.columns, start=start_col):
        ws.cell(row=header_row, column=j, value=str(col_name))

    # Datos
    for i in range(df.shape[0]):
        for j in range(df.shape[1]):
            ws.cell(
                row=header_row + 1 + i,
                column=start_col + j,
                value=df.iat[i, j],
            )

    return header_row, df.shape[1], df.shape[0]


def _apply_table_styles(ws, header_row: int, start_col: int, ncols: int, nrows: int):
    """
    Aplica estilos a encabezado y cuerpo. Usa PatternFill/Borders correctos.
    """
    header_fill = make_fill(HEADER_GRAY)
    header_font = Font(bold=True, color=_argb(TEXT_DARK))
    header_border = make_thin_border(BORDER_GRAY)
    data_border = make_thin_border(BORDER_GRAY)

    # Encabezado
    for j in range(ncols):
        cell = ws.cell(row=header_row, column=start_col + j)
        cell.fill = header_fill
        cell.font = header_font
        cell.border = header_border
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Datos
    for i in range(nrows):
        for j in range(ncols):
            cell = ws.cell(row=header_row + 1 + i, column=start_col + j)
            cell.border = data_border
            val = cell.value
            # Alineación simple: números a la derecha, resto centrado vertical
            if isinstance(val, (int, float)):
                cell.alignment = Alignment(horizontal="right", vertical="center")
            else:
                cell.alignment = Alignment(vertical="center")

    # Ancho de columnas (auto básico)
    for j in range(ncols):
        col_letter = get_column_letter(start_col + j)
        max_len = 0
        for r in range(header_row, header_row + nrows + 1):
            v = ws.cell(row=r, column=start_col + j).value
            if v is None:
                continue
            max_len = max(max_len, len(str(v)))
        ws.column_dimensions[col_letter].width = min(max(10, max_len + 2), 40)


def _build_workbook(
    df: pd.DataFrame, metadata: Optional[Dict[str, Any]] = None
) -> Workbook:
    """
    Crea el workbook con banner+logo+título y la tabla (sin bloque de metadatos).
    """
    metadata = metadata or {}
    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte"

    # Banner ancho
    banner_cols_override = metadata.get("banner_cols_override")
    banner_cols = (
        int(banner_cols_override)
        if banner_cols_override
        else max(BANNER_COLS, df.shape[1])
    )

    # Banner + Logo
    logo_path = metadata.get("logo_path") or LOGO_PATH_ENV
    _apply_banner(ws, banner_cols, logo_path)

    # Título
    _apply_title(ws, banner_cols)

    # Tabla desde fila 4
    header_row, ncols, nrows = _write_table(ws, df, start_row=4, start_col=1)
    _apply_table_styles(ws, header_row, 1, ncols, nrows)

    return wb


# =========================
# Funciones públicas
# =========================


def export_to_excel(
    df: pd.DataFrame, archivo: str, metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Recibe un DataFrame y genera:
      - archivo local en OUTPUT_DIR: {archivo}.xlsx
      - (opcional) subida a FTP con nombre remoto SIN extensión (solo 'archivo')
    """
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("El DataFrame está vacío o no es válido")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    local_path = os.path.join(OUTPUT_DIR, f"{archivo}.xlsx")

    wb = _build_workbook(df, metadata)
    wb.save(local_path)

    # Subida a FTP, sin extensión
    ftp_info = _try_upload_ftp(local_path, archivo)

    result = {
        "ok": True,
        "rows": int(df.shape[0]),
        "cols": int(df.shape[1]),
        "local_copy": local_path,
    }
    if ftp_info is not None:
        result["uploaded_to"] = ftp_info
    return result


def export(
    tabla: str, archivo: str, metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Camino usado por el endpoint /export: extrae del IBMi y luego genera Excel.
    """
    df = _try_get_df_from_ibmi(tabla)
    return export_to_excel(df, archivo, metadata or {})
