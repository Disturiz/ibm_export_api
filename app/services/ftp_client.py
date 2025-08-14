# app/services/ftp_client.py
import ftplib
from io import BytesIO
from typing import Optional


def _connect(
    host: str,
    port: int,
    user: str,
    password: str,
    use_tls: bool,
    timeout: int = 30,
    debug: bool = False,
) -> ftplib.FTP:
    if use_tls:
        # FTPS (TLS explícito en 21)
        ftp = ftplib.FTP_TLS()
        if debug:
            ftp.set_debuglevel(2)  # verbose en stdout
        ftp.connect(host=host, port=port, timeout=timeout)
        # AUTENTICACIÓN TLS explícita ANTES de login
        ftp.auth()
        # Login en canal de control ya cifrado
        ftp.login(user=user, passwd=password)
        # Protege canal de datos (LIST/STOR/RETR)
        ftp.prot_p()
    else:
        # FTP plano
        ftp = ftplib.FTP()
        if debug:
            ftp.set_debuglevel(2)
        ftp.connect(host=host, port=port, timeout=timeout)
        ftp.login(user=user, passwd=password)
    # Modo pasivo (recomendado detrás de NAT/Firewall)
    ftp.set_pasv(True)
    # Opcional: keep-alive si el servidor cierra rápido sesiones inactivas
    try:
        ftp.voidcmd("NOOP")
    except Exception:
        pass
    return ftp


def _ensure_cwd(ftp: ftplib.FTP, remote_dir: Optional[str]):
    if not remote_dir:
        return
    parts = [p for p in str(remote_dir).replace("\\", "/").split("/") if p]
    for p in parts:
        try:
            ftp.cwd(p)
        except ftplib.error_perm:
            # crea y entra si no existe
            ftp.mkd(p)
            ftp.cwd(p)


def upload_file(
    host: str,
    port: int,
    user: str,
    password: str,
    remote_dir: str,
    local_path: str,
    remote_name: str,
    use_tls: bool,
    timeout: int = 60,
    debug: bool = False,
):
    ftp = _connect(host, port, user, password, use_tls, timeout, debug)
    try:
        _ensure_cwd(ftp, remote_dir)
        with open(local_path, "rb") as fh:
            ftp.storbinary(f"STOR {remote_name}", fh)
    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()


def upload_bytes(
    host: str,
    port: int,
    user: str,
    password: str,
    remote_dir: str,
    data: bytes,
    remote_name: str,
    use_tls: bool,
    timeout: int = 60,
    debug: bool = False,
):
    ftp = _connect(host, port, user, password, use_tls, timeout, debug)
    try:
        _ensure_cwd(ftp, remote_dir)
        bio = BytesIO(data)
        ftp.storbinary(f"STOR {remote_name}", bio)
    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()
