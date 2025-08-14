import os, re

VALID_TABLE = re.compile(r"^[A-Za-z0-9_\.]+$")
VALID_FILE = re.compile(r"^[A-Za-z0-9_\-]+$")


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def validate_table(t: str):
    if not VALID_TABLE.fullmatch(t):
        raise ValueError("Nombre de tabla inválido. Use [A-Za-z0-9_ .]")


def validate_file(f: str):
    if not VALID_FILE.fullmatch(f):
        raise ValueError("Nombre de archivo inválido. Use [A-Za-z0-9_-]")
