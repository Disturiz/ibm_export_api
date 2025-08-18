FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 DEBIAN_FRONTEND=noninteractive

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
    openjdk-21-jre-headless \
    ca-certificates \
    ; \
    rm -rf /var/lib/apt/lists/*

# Descubre JAVA_HOME dinámicamente (sin hardcodear ruta)
RUN set -eux; JAVA_BIN="$(readlink -f $(command -v java))"; \
    JAVA_HOME="$(dirname $(dirname "$JAVA_BIN"))"; \
    echo "export JAVA_HOME=$JAVA_HOME" > /etc/profile.d/java.sh
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
# Usuario no root
RUN useradd -m appuser

WORKDIR /app

# Instala dependencias (asegúrate de tener este archivo en tu repo)
COPY requirements.txt ./requirements.txt
RUN python -m pip install --upgrade pip && \
    python -m pip install --no-cache-dir -r requirements.txt

# CLASSPATH para jt400 (si copias el jar a /app/jt400/jt400.jar)
ENV CLASSPATH="/app/jt400/jt400.jar:${CLASSPATH}"

# Copia el código
COPY . /app

# Permisos
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Arranque
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
