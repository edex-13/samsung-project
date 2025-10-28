# Usar imagen base con Python y dependencias del sistema para Playwright
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Información del mantenedor
LABEL maintainer="Scraping Pipeline"
LABEL description="Pipeline automatizado de scraping para Éxito y Falabella con verificación y Firebase"

# Configurar directorio de trabajo
WORKDIR /app

# Instalar dependencias adicionales del sistema
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    unzip \
    git \
    vim \
    nano \
    htop \
    tree \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de requirements primero (para optimizar cache de Docker)
COPY requirements*.txt ./

# Crear requirements unificado para Docker
RUN echo "playwright==1.40.0" > requirements_docker.txt && \
    echo "pandas==2.1.4" >> requirements_docker.txt && \
    echo "openpyxl==3.1.2" >> requirements_docker.txt && \
    echo "firebase-admin==6.4.0" >> requirements_docker.txt && \
    echo "google-cloud-firestore==2.13.1" >> requirements_docker.txt && \
    echo "google-api-core==2.11.1" >> requirements_docker.txt && \
    echo "requests==2.31.0" >> requirements_docker.txt && \
    echo "beautifulsoup4==4.12.2" >> requirements_docker.txt

# Instalar dependencias Python
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements_docker.txt

# Instalar navegadores Playwright (ya están las dependencias del sistema)
RUN playwright install chromium && \
    playwright install-deps chromium

# Copiar todos los archivos del proyecto
COPY . .

# Dar permisos de ejecución al script principal
RUN chmod +x run_pipeline.sh

# Crear directorios necesarios
RUN mkdir -p /app/data /app/backup /app/logs

# Configurar variables de entorno
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Exponer puerto si se necesita (opcional)
EXPOSE 8080

# Healthcheck para verificar que el contenedor está funcionando
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import playwright; print('OK')" || exit 1

# Comando por defecto: ejecutar el pipeline
CMD ["./run_pipeline.sh"]
