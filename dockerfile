# FROM python:3.12-slim-bookworm

# ENV DEBIAN_FRONTEND=noninteractive
# RUN apt-get update \
#     && apt-get install -y --no-install-recommends \
#     openjdk-17-jre-headless \
#     build-essential \
#     ca-certificates \
#     && rm -rf /var/lib/apt/lists/*

# ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
# ENV PATH="${JAVA_HOME}/bin:${PATH}"

# ENV APP_HOME=/app
# WORKDIR ${APP_HOME}

# COPY requirements.txt ./requirements.txt
# RUN python -m pip install --no-cache-dir --upgrade pip \
#     && python -m pip install --no-cache-dir -r requirements.txt

# COPY app ./app
# COPY /jt400/jt400.jar /jt400/jt400.jar

# ENV PYTHONUNBUFFERED=1 \
#     JAR_PATH=/app/jt400/jt400.jar \
#     OUTPUT_DIR=/data/output \
#     DEFAULT_SCHEMA=DACCYFILES

# RUN useradd -m appuser \
#     && mkdir -p /data/output \
#     && chown -R appuser:appuser /data

# USER appuser
# EXPOSE 8000
# CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]



FROM python:3.9-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Java para jt400 y utilidades mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jre ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/*

# Usuario no root
RUN useradd -m appuser

WORKDIR /app

# Instala deps primero (aprovecha caché)
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copia jt400.jar desde tu repo
COPY jt400/jt400.jar /app/lib/jt400.jar

# CLASSPATH para el driver JDBC
ENV CLASSPATH="/app/lib/jt400.jar:${CLASSPATH}"

# Copia el código
COPY . /app

# Permisos
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Arranque
CMD uvicorn app.main:app --host 0.0.0.0 --port 8000