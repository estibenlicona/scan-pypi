# Dockerfile para API de análisis de dependencias con Snyk y FastAPI
FROM python:3.11-slim

# Instala Node.js y Snyk CLI
RUN apt-get update && \
    apt-get install -y nodejs npm && \
    npm install -g snyk && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Crea directorio de trabajo
WORKDIR /app

# Copia el código fuente y archivos necesarios
COPY . /app

# Cambia permisos
RUN chmod -R 777 /app

# Instala dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Expone el puerto de FastAPI
EXPOSE 8000

# Autenticación Snyk CLI
RUN snyk auth 035c9f3e-6058-4709-b79f-10707b89cf35

# Comando para iniciar el API
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
