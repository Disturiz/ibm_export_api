# Imagen base mínima
FROM python:3.11-slim

# Ajustes básicos de Python/pip
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Paquetes del sistema:
# - default-jre-headless: requerido por el driver JDBC (jt400.jar)
# - curl: usado por el healthcheck del compose
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jre-headless curl \
    && rm -rf /var/lib/apt/lists/*

# Carpeta de trabajo
WORKDIR /app

# Instalar deps de Python
COPY requirements.txt  .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la app y el jar de jt400
COPY app ./app
COPY jt400/jt400.jar ./jt400/jt400.jar

# Carpeta para salidas
RUN mkdir -p /app/output

# Usuario no root
RUN useradd -ms /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Arranque del servicio
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
