# app/services/ftp.py
from __future__ import annotations
import os
import tempfile
from typing import Dict, Optional
from ftplib import FTP, FTP_TLS, error_perm
from dotenv import load_dotenv


# ------------------------
# Utilidades de configuración
# ------------------------
def _load_env() -> dict:
    load_dotenv()
    return {
        "host": os.getenv("FTP_HOST", "").strip(),
        "port": int(os.getenv("FTP_PORT", "21")),
        "user": os.getenv("FTP_USER", "").strip(),
        "password": os.getenv("FTP_PASSWORD", "").strip(),
        "remote_dir": (os.getenv("FTP_DIR", "/") or "/").strip(),
        "use_tls": os.getenv("FTP_TLS", "false").strip().lower() == "true",
        "timeout": int(os.getenv("FTP_TIMEOUT", "30")),
        "passive": os.getenv("FTP_PASSIVE", "true").strip().lower() == "true",
    }


def _resolve_cfg(
    *,
    host: Optional[str] = None,
    port: Optional[int] = None,
    user: Optional[str] = None,
    password: Optional[str] = None,
    remote_dir: Optional[str] = None,
    use_tls: Optional[bool] = None,
    timeout: Optional[int] = None,
    passive: Optional[bool] = None,
) -> dict:
    """Toma kwargs si vienen; si no, usa .env."""
    env = _load_env()
    cfg = {
        "host": host or env["host"],
        "port": int(port if port is not None else env["port"]),
        "user": user or env["user"],
        "password": password or env["password"],
        "remote_dir": (remote_dir or env["remote_dir"] or "/").strip(),
        "use_tls": bool(env["use_tls"] if use_tls is None else use_tls),
        "timeout": int(timeout if timeout is not None else env["timeout"]),
        "passive": bool(env["passive"] if passive is None else passive),
    }
    missing = [k for k in ("host", "user", "password") if not cfg[k]]
    if missing:
        raise RuntimeError(f"Faltan variables/params para FTP: {', '.join(missing)}")
    return cfg


# ------------------------
# Conexión y directorios
# ------------------------
def _connect(cfg: dict):
    """Abre conexión FTP/FTPS (TLS explícito) y devuelve instancia ya autenticada."""
    if cfg["use_tls"]:
        ftp = FTP_TLS()
        ftp.connect(host=cfg["host"], port=cfg["port"], timeout=cfg["timeout"])
        ftp.login(user=cfg["user"], passwd=cfg["password"])
        ftp.prot_p()  # canal de datos cifrado
    else:
        ftp = FTP()
        ftp.connect(host=cfg["host"], port=cfg["port"], timeout=cfg["timeout"])
        ftp.login(user=cfg["user"], passwd=cfg["password"])

    ftp.set_pasv(bool(cfg["passive"]))
    return ftp


def _ensure_cwd(ftp: FTP, path: str) -> None:
    """Cambia al directorio remoto; si no existe, intenta crearlo recursivamente."""
    if not path or path == "/":
        ftp.cwd("/")
        return

    parts = [p for p in path.split("/") if p]
    if path.startswith("/"):
        ftp.cwd("/")
    for part in parts:
        try:
            ftp.cwd(part)
        except error_perm:
            ftp.mkd(part)
            ftp.cwd(part)


# ------------------------
# API pública compatible
# ------------------------
def upload_file(
    local_path: str = None,
    remote_name: str = None,
    # kwargs opcionales para compatibilidad con endpoints existentes:
    host: str = None,
    port: int = None,
    user: str = None,
    password: str = None,
    remote_dir: str = None,
    use_tls: bool = None,
    timeout: int = None,
    passive: bool = None,
    **_ignore,
) -> Dict[str, str]:
    """
    Compatible con dos estilos:
      1) upload_file(local_path, remote_name) -> lee .env
      2) upload_file(local_path=..., remote_name=..., host=..., port=..., ...) -> usa kwargs
    """
    if not local_path or not remote_name:
        raise ValueError("Debe proporcionar local_path y remote_name.")

    cfg = _resolve_cfg(
        host=host,
        port=port,
        user=user,
        password=password,
        remote_dir=remote_dir,
        use_tls=use_tls,
        timeout=timeout,
        passive=passive,
    )

    if not os.path.isfile(local_path):
        raise FileNotFoundError(f"Archivo local no encontrado: {local_path}")

    ftp = _connect(cfg)
    try:
        _ensure_cwd(ftp, cfg["remote_dir"])
        with open(local_path, "rb") as f:
            ftp.storbinary(f"STOR {remote_name}", f)
        return {
            "host": cfg["host"],
            "port": str(cfg["port"]),
            "dir": cfg["remote_dir"],
            "file": remote_name,
            "status": "uploaded",
        }
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


def upload_bytes(
    content: bytes = None,
    remote_name: str = None,
    # mismos kwargs opcionales que upload_file:
    host: str = None,
    port: int = None,
    user: str = None,
    password: str = None,
    remote_dir: str = None,
    use_tls: bool = None,
    timeout: int = None,
    passive: bool = None,
    **_ignore,
) -> Dict[str, str]:
    """Sube bytes en memoria creando un temporal. Acepta kwargs (host, port, etc.) o .env."""
    if content is None or remote_name is None:
        raise ValueError("Debe proporcionar content (bytes) y remote_name.")
    suffix = os.path.splitext(remote_name)[1] or ".bin"

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        return upload_file(
            local_path=tmp_path,
            remote_name=remote_name,
            host=host,
            port=port,
            user=user,
            password=password,
            remote_dir=remote_dir,
            use_tls=use_tls,
            timeout=timeout,
            passive=passive,
        )
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except Exception:
                pass
