FROM python:3.11-slim-bullseye

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Java para jt400 y utilidades mínimas
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends openjdk-17-jre ca-certificates tzdata && \
    rm -rf /var/lib/apt/lists/*


# Usuario no root
RUN useradd -m appuser

WORKDIR /app

# Instala deps primero (aprovecha caché)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia jt400.jar desde tu repo
RUN mkdir -p /jt400
COPY jt400/jt400.jar /jt400/jt400.jar

# CLASSPATH para el driver JDBC
ENV CLASSPATH="/jt400/jt400.jar:${CLASSPATH}"

# Copia el código
COPY . /app

# Permisos
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Arranque
CMD uvicorn app.main:app --host 0.0.0.0 --port 8000