# Exportador IBM i → Excel con FastAPI

Este proyecto implementa una API REST en Python usando **FastAPI** para exportar datos desde IBM i (AS/400) a archivos Excel (`.xlsx`) utilizando JDBC (jaydebeapi).
Está protegido con API Key y permite recibir desde una llamada HTTP el nombre de la tabla y el nombre de archivo de salida.

## 📂 Estructura del proyecto

```
ibmi-export-api/
├─ app/
│  ├─ __init__.py
│  ├─ main.py                 # Punto de entrada FastAPI
│  ├─ config.py               # Configuración (env vars, rutas, host IBM i)
│  ├─ security.py             # API Key
│  ├─ schemas.py              # Modelos Pydantic
│  ├─ exporter.py             # Lógica de exportación a Excel
│  └─ services/
│     ├─ jdbc.py              # Conexión JDBC
│     └─ io_utils.py          # Validaciones de I/O
├─ jt400/                     # (Opcional) carpeta para jt400.jar
│  └─ jt400.jar
├─ output/                    # Archivos .xlsx generados
├─ .env.example               # Variables de entorno de ejemplo
├─ requirements.txt           # Dependencias
├─ README.md                  # Documentación
├─ run_dev.bat                # Script ejecución Windows
└─ run_dev.sh                 # Script ejecución Linux/macOS
```

## ⚙️ Requisitos

- Python 3.10 o superior
- Acceso a servidor IBM i con JDBC habilitado
- Archivo `jt400.jar` (IBM Toolbox for Java)
- Librerías Python (ver `requirements.txt`)

## 📦 Instalación

1. **Clonar el repositorio**

```bash
git clone https://github.com/usuario/ibmi-export-api.git
cd ibmi-export-api
```

2. **Crear y activar entorno virtual**

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

3. **Instalar dependencias**

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

4. **Configurar variables de entorno**

- Copiar `.env.example` a `.env` y ajustar valores.

```env
EXPORT_API_KEY=MiSecreto_2025
IBMI_HOST=10.246.17.67
IBMI_USER=ALDNOVACOM
IBMI_PASSWORD=ALDNOVACOM
JAR_PATH=C:\Users\distu\Documents\IBM\jt400.jar
OUTPUT_DIR=C:\Users\distu\OneDrive\Documentos\bel_excel\conexion
DEFAULT_SCHEMA=DACCYFILES

Coloque estos archivos en su proyecto:
  app/services/ibmi.py
  app/services/ftp.py

  OUTPUT_DIR=./output
  WRITE_LOCAL_COPY=True

  FTP_HOST=10.246.15.7
  FTP_PORT=21
  FTP_USER=cybtest
  FTP_PASSWORD=panama2019
  FTP_DIR=/FORMATOS-MT-PDF
  FTP_TLS=True
```

## ▶️ Ejecución en desarrollo

En Windows:

```bash
run_dev.bat
```

En Linux/macOS:

```bash
./run_dev.sh
```

O directamente:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

La API estará disponible en:

```
http://localhost:8000/docs
```

## 🔑 Seguridad con API Key

Todas las peticiones deben incluir el header:

```
X-API-Key: <tu_api_key>
```

## 📡 Uso de la API

**Endpoint:** `POST /export`  
**Headers:**

```
Content-Type: application/json
X-API-Key: MiSecreto_2025
```

**Body (JSON):**

```json
{
  "tabla": "BOLGENXLS",
  "archivo": "reporte_bolgen"
}
```

**Respuesta ejemplo:**

```json
{
  "ok": true,
  "table": "DACCYFILES.BOLGENXLS",
  "rows": 125,
  "cols": 8,
  "path": "C:UsersdistuOneDriveDocumentos\bel_excelconexion\reporte_bolgen.xlsx",
  "elapsed_ms": 942
}
```

## 📞 Llamada desde IBM i

### Usando curl en QSH (CL)

```cl
PGM PARM(&TABLA &ARCHIVO)
DCL VAR(&TABLA) TYPE(*CHAR) LEN(30)
DCL VAR(&ARCHIVO) TYPE(*CHAR) LEN(30)
DCL VAR(&CMD) TYPE(*CHAR) LEN(512)

CHGVAR VAR(&CMD) VALUE('curl -s -X POST http://<IP_PC>:8000/export ' +
   '-H "Content-Type: application/json" ' +
   '-H "X-API-Key: MiSecreto_2025" ' +
   '-d "{\"tabla\":\"' *TCAT &TABLA *TCAT '\",\"archivo\":\"' *TCAT &ARCHIVO *TCAT '\"}"')

QSH CMD(&CMD)
ENDPGM
```

## 📜 Licencia

MIT
