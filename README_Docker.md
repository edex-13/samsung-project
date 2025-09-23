# Pipeline de Scraping con Docker

Este proyecto automatiza el scraping de productos Samsung de Éxito y Falabella, con verificación de datos y subida a Firebase, todo corriendo en un contenedor Docker.

## 🚀 Inicio Rápido

### Prerrequisitos
- Docker instalado
- Docker Compose instalado
- Archivo `firebase-credentials.json` (opcional, para subida a Firebase)

### Construcción y Ejecución

```bash
# Construir la imagen
docker-compose build

# Ejecutar el pipeline completo
docker-compose up

# Ejecutar en segundo plano
docker-compose up -d

# Ver logs en tiempo real
docker-compose logs -f scraper
```

## 📁 Estructura de Archivos

```
scraping/
├── Dockerfile                 # Imagen Docker con todas las dependencias
├── docker-compose.yml         # Orquestación del contenedor
├── run_pipeline.sh           # Script principal que ejecuta todo el pipeline
├── scraper_exito.py          # Scraper de Éxito
├── scraper_falabella.py      # Scraper de Falabella
├── verificar_productos.py    # Verificación y limpieza de datos
├── firebase_uploader_organizado.py  # Subida a Firebase
├── firebase-credentials.json # Credenciales Firebase (crear manualmente)
├── data/                     # Salidas limpias e inválidas (montado desde host)
├── backup/                   # Backups automáticos (montado desde host)
└── logs/                     # Logs del pipeline (montado desde host)
```

## 🔧 Configuración

### Firebase (Opcional)
1. Ve a [Firebase Console](https://console.firebase.google.com/)
2. Proyecto > Configuración > Cuentas de servicio
3. Genera una nueva clave privada
4. Descarga el archivo JSON y renómbralo a `firebase-credentials.json`
5. Colócalo en la carpeta del proyecto

### Variables de Entorno
Puedes modificar el `docker-compose.yml` para agregar variables:

```yaml
environment:
  - TZ=America/Bogota          # Zona horaria
  - MAX_PAGINAS=2              # Páginas máximas por scraper
  - DELAY_ENTRE_BUSQUEDAS=60   # Segundos entre búsquedas
```

## 🎯 Pipeline Automatizado

El script `run_pipeline.sh` ejecuta en orden:

1. **🔧 Configuración de entorno**: Verifica Python y dependencias
2. **📦 Instalación**: Playwright, pandas, Firebase admin, etc.
3. **🌐 Navegadores**: Descarga Chromium para scraping
4. **🛒 Scraper Éxito**: Extrae productos de Éxito
5. **🛍️ Scraper Falabella**: Extrae productos de Falabella
6. **✅ Verificación**: Limpia datos y separa válidos/inválidos
7. **☁️ Firebase**: Sube datos organizados (si hay credenciales)

## 📊 Salidas

### Archivos Generados
- `resultados_exito.xlsx` - Datos crudos de Éxito
- `resultados_falabella.xlsx` - Datos crudos de Falabella
- `data/exito_limpio.xlsx` - Productos válidos de Éxito
- `data/exito_invalidos.xlsx` - Productos inválidos de Éxito
- `data/falabella_limpio.xlsx` - Productos válidos de Falabella
- `data/falabella_invalidos.xlsx` - Productos inválidos de Falabella

### Firebase Collections
- `productos_scraping` - Colección principal
- `productos_por_comercio/[comercio]/productos/`
- `productos_por_modelo/[modelo]/productos/`
- `productos_por_vendedor/[vendedor]/productos/`

## 🐳 Comandos Docker Útiles

```bash
# Ver contenedores en ejecución
docker ps

# Acceder al contenedor
docker-compose exec scraper bash

# Ver logs específicos
docker-compose logs scraper

# Parar y limpiar
docker-compose down

# Reconstruir imagen
docker-compose build --no-cache

# Ver espacio usado
docker system df

# Limpiar contenedores e imágenes no usadas
docker system prune
```

## 🔍 Troubleshooting

### Problema: No se generan archivos
```bash
# Verificar permisos de volúmenes
docker-compose exec scraper ls -la /app/data

# Verificar logs del contenedor
docker-compose logs scraper
```

### Problema: Error de Firebase
```bash
# Verificar que el archivo de credenciales existe
docker-compose exec scraper ls -la firebase-credentials.json

# Verificar formato del JSON
docker-compose exec scraper python3 -c "import json; print('Valid' if json.load(open('firebase-credentials.json')) else 'Invalid')"
```

### Problema: Scrapers fallan
```bash
# Verificar que Playwright está instalado
docker-compose exec scraper playwright --version

# Probar navegador manualmente
docker-compose exec scraper python3 -c "from playwright.sync_api import sync_playwright; print('OK')"
```

## ⚡ Ejecución Programada

### Con Docker + Cron (Host)
```bash
# Editar crontab
crontab -e

# Ejecutar cada día a las 6:00 AM
0 6 * * * cd /path/to/scraping && docker-compose up --abort-on-container-exit
```

### Con Docker Compose (Reinicio automático)
```yaml
# En docker-compose.yml
restart: unless-stopped
```

## 📈 Monitoreo

### Logs en tiempo real
```bash
docker-compose logs -f scraper | grep -E "(OK|ERROR|WARN)"
```

### Verificar recursos
```bash
docker stats scraping-pipeline
```

## 🚀 Optimización

### Para mejor rendimiento:
- Aumenta memoria en `docker-compose.yml`
- Usa SSD para volúmenes
- Ejecuta en horarios de menor carga de red

### Para debugging:
- Cambia `CMD` en Dockerfile a `CMD ["bash"]`
- Ejecuta comandos manualmente dentro del contenedor
