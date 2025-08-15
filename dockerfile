# Usa una imagen base de Python
FROM python:3.9-slim

# Instala Java para el uso de jt400.jar
RUN apt-get update && apt-get install -y openjdk-17-jre && rm -rf /var/lib/apt/lists/*

# Crea un directorio de trabajo.
WORKDIR /app

# Copia los archivos del proyecto
COPY . /app

# Copia el jt400.jar a un directorio específico.
#COPY /usr/yappy-p2pusr-service/jt400.jar /app/lib/jt400.jar
COPY /lib/jt400.jar /app/lib/jt400.jar


# Establece la variable de entorno CLASSPATH
ENV CLASSPATH="/app/lib/jt400.jar:$CLASSPATH"

# Instala dependencias
RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org  --no-cache-dir -r requirements.txt

# Expone el puerto del servicio
EXPOSE 4000

# Add build arguments
ARG HOSTNAME
ARG AS400_USERNAME
ARG AS400_PASSWORD
ARG IMB_ESQUEMA
ARG IBM_DB_JAR
ARG AUTH_USER
ARG AUTH_PASS



# Add environment variable debugging before running the application
RUN echo "Environment Variables:" && \
    echo "HOSTNAME: $HOSTNAME" && \
    echo "AS400_USERNAME: $AS400_USERNAME" && \
    echo "AS400_PASSWORD: $AS400_PASSWORD" && \
    echo "IMB_ESQUEMA: $IMB_ESQUEMA" && \
    echo "IBM_DB_JAR: $IBM_DB_JAR"

# Comando para ejecutar la aplicación
CMD printenv && echo "Starting application..." && uvicorn main:app --host 0.0.0.0 --port 4000