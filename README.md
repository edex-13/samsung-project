# 🛒 Pipeline de Scraping Samsung - Éxito y Falabella

Sistema automatizado para extraer información de productos Samsung de Éxito y Falabella, con verificación de datos y subida opcional a Firebase.

## 📋 **Prerrequisitos**

### **Opción A: Con Docker (Recomendado - Más Fácil)**
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y corriendo
- Git (para clonar el proyecto)

### **Opción B: Sin Docker (Manual)**
- Python 3.8 o superior
- Git
- Conexión a internet estable

---

## 🚀 **Instalación y Uso**

### **🔧 PASO 0: Verificar configuración (Importante)**
```bash
git clone [URL_DEL_REPOSITORIO]
cd scraping

# En Linux/Mac/WSL - Dar permisos primero:
chmod +x *.sh

# En Windows (Git Bash/PowerShell):
# Los permisos se manejan automáticamente

# Ejecutar el verificador automático
./setup.sh
```

El script `setup.sh` verificará automáticamente:
- ✅ **Docker y Docker Compose** (para método fácil)
- ✅ **Python y pip** (para método manual)  
- ✅ **Archivos del proyecto** completos
- ✅ **Permisos** de scripts
- ✅ **Firebase** (opcional)

**Si todo está verde**, continúa con el método que prefieras. **Si hay errores**, el script te dirá exactamente qué instalar.

---

### **🐳 MÉTODO 1: Con Docker (Recomendado - Más Fácil)**

#### **¿Por qué Docker?**
- ✅ No necesitas instalar Python, dependencias ni navegadores
- ✅ Funciona igual en Windows, Mac y Linux
- ✅ Evita conflictos con otras aplicaciones
- ✅ Configuración automática de todo

#### **Comandos:**
```bash
# 1. Verificar que todo está OK
./setup.sh

# 2. Construir imagen (solo la primera vez)
./docker-run.sh build

# 3. Ejecutar pipeline completo
./docker-run.sh run

# Ver progreso en tiempo real
./docker-run.sh logs
```

#### **🪟 Alternativa para Windows (si los .sh no funcionan):**
```cmd
# En PowerShell o CMD:
docker-compose build
docker-compose up

# Ver logs:
docker-compose logs -f
```

#### **Comandos útiles:**
```bash
./docker-run.sh status   # Ver estado
./docker-run.sh stop     # Parar
./docker-run.sh start    # Ejecutar en segundo plano
./docker-run.sh shell    # Acceder al contenedor
./docker-run.sh clean    # Limpiar todo
```

---

### **💻 MÉTODO 2: Sin Docker (Manual)**

#### **¿Cuándo usar este método?**
- Si no puedes instalar Docker
- Si prefieres tener control total
- Si quieres modificar código en tiempo real

#### **Comandos:**
```bash
# 1. Verificar que todo está OK
./setup.sh

# 2. Ejecutar pipeline completo automatizado
./run_pipeline.sh
```

#### **🪟 Alternativa para Windows (si los .sh no funcionan):**
```cmd
# En PowerShell o CMD - Ejecutar manualmente:
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements_firebase.txt
playwright install chromium

# Ejecutar scrapers:
python scraper_exito.py
python scraper_falabella.py
python verificar_productos.py
python firebase_uploader_organizado.py
```

**¡Eso es todo!** El script `run_pipeline.sh` se encarga de:
- Crear entorno virtual automáticamente
- Instalar todas las dependencias
- Instalar navegadores Playwright
- Ejecutar scrapers en orden correcto
- Verificar y limpiar datos
- Subir a Firebase (si está configurado)

---

## 🔧 **¿Qué hace exactamente `setup.sh`?**

### **Verificaciones automáticas:**
```bash
./setup.sh
```

**Si todo está bien verás:**
```
🎉 ¡Configuración completa!

🚀 PRÓXIMOS PASOS (Docker - Recomendado):
1. Construir imagen: ./docker-run.sh build
2. Ejecutar pipeline: ./docker-run.sh run
3. Ver progreso: ./docker-run.sh logs
```

**Si falta algo verás:**
```
❌ Configuración incompleta

🔧 PARA RESOLVER:
   • Instala Docker Desktop desde: https://docker.com/...
   • Verifica que descargaste todos los archivos
   • Archivos faltantes: [lista específica]
```

### **Qué verifica:**
- ✅ **Docker y Docker Compose**: Si están instalados y corriendo
- ✅ **Python y pip**: Como alternativa para método manual
- ✅ **Archivos del proyecto**: Si están todos presentes
- ✅ **Permisos de scripts**: Los configura automáticamente
- ✅ **Firebase**: Si las credenciales están configuradas (opcional)

### **Qué NO hace:**
- ❌ No instala nada automáticamente (para evitar problemas)
- ❌ No modifica tu sistema sin permiso
- ❌ No ejecuta el pipeline automáticamente

**Beneficio**: Detecta problemas ANTES de ejecutar, ahorrándote tiempo y frustración.

---

## 🔥 **Configuración Firebase (Opcional)**

**¿Quieres subir los datos a Firebase?** Si no, puedes saltarte esto.

### **Pasos rápidos:**
1. Ve a [Firebase Console](https://console.firebase.google.com/)
2. Crea proyecto → **Configuración** → **Cuentas de servicio**
3. **"Generar nueva clave privada"** → Descargar JSON
4. Renombrar a `firebase-credentials.json`
5. Poner en la carpeta del proyecto

```bash
# Verificar que está bien configurado
./setup.sh  # Te dirá si Firebase está OK
```

---

## 📁 **Archivos Generados**

Después de la ejecución encontrarás:

### **Archivos principales:**
- `resultados_exito.xlsx` - Datos crudos de Éxito
- `resultados_falabella.xlsx` - Datos crudos de Falabella

### **Carpeta `data/` (archivos verificados):**
- `resultados_exito_limpio.xlsx` - Productos válidos de Éxito
- `resultados_exito_invalidos.xlsx` - Productos inválidos de Éxito
- `resultados_falabella_limpio.xlsx` - Productos válidos de Falabella
- `resultados_falabella_invalidos.xlsx` - Productos inválidos de Falabella

### **Carpeta `backup/`:**
- Backups automáticos durante el proceso

### **Firebase (si está configurado):**
- `productos_scraping` - Colección principal
- `productos_por_comercio/` - Organizados por tienda
- `productos_por_modelo/` - Organizados por modelo Samsung
- `productos_por_vendedor/` - Organizados por vendedor

---

## ⚙️ **Configuración**

### **Dispositivos buscados:**
- Samsung Galaxy S25 Ultra
- Samsung Galaxy S24 Ultra  
- Samsung Z Flip 6
- Samsung Galaxy A56
- Samsung Galaxy A16

### **Modificar configuración:**
Edita los archivos:
- `scraper_exito.py` - Líneas 9-15 (lista DISPOSITIVOS)
- `scraper_falabella.py` - Líneas 9-15 (lista DISPOSITIVOS)

### **Cambiar tiempos de espera:**
En los mismos archivos, modifica:
- `TIMEOUT_PRODUCTOS` - Tiempo máximo para cargar productos
- `DELAY_ENTRE_BUSQUEDAS` - Pausa entre búsquedas
- `MAX_PAGINAS` - Número de páginas a procesar

---

## 🐛 **Solución de Problemas**

### **Error: Docker no está instalado**
```bash
# Windows/Mac: Descargar Docker Desktop
# Ubuntu/Debian:
sudo apt update
sudo apt install docker.io docker-compose
sudo systemctl start docker
sudo usermod -aG docker $USER  # Reiniciar sesión después
```

### **Error: Playwright navegadores**
```bash
# Si no se pueden instalar navegadores:
./docker-run.sh shell
playwright install chromium --with-deps
```

### **Error: Archivos no se generan**
1. Verificar que el contenedor está corriendo: `./docker-run.sh status`
2. Ver logs: `./docker-run.sh logs`
3. Verificar conexión a internet
4. Revisar si las páginas web cambiaron estructura

### **Error: Permisos en Linux/WSL**
```bash
sudo chown -R $USER:$USER .
chmod +x *.sh
```

### **Error: Scripts .sh no funcionan en Windows**
**Opción 1: Usar Git Bash (Recomendado)**
```bash
# Descargar Git for Windows desde: https://git-scm.com/
# Usar Git Bash en lugar de CMD/PowerShell
chmod +x *.sh
./setup.sh
```

**Opción 2: Usar comandos directos**
```cmd
# En PowerShell/CMD, usar comandos nativos:
# En lugar de ./docker-run.sh build:
docker-compose build

# En lugar de ./run_pipeline.sh:
# Seguir los pasos manuales listados arriba
```

**Opción 3: WSL (Windows Subsystem for Linux)**
```bash
# Instalar WSL2 desde Microsoft Store
# Usar Ubuntu o similar dentro de Windows
wsl
cd /mnt/c/Users/[tu-usuario]/path/to/scraping
chmod +x *.sh
./setup.sh
```

### **Error: Firebase**
1. Verificar que `firebase-credentials.json` existe
2. Verificar que el archivo JSON es válido
3. Verificar permisos en Firebase Console

---

## ⚡ **Rendimiento**

### **Tiempos estimados:**
- **Con Docker**: 6-10 minutos total
- **Sin Docker**: 5-8 minutos total
- **Solo Éxito**: 2-3 minutos
- **Solo Falabella**: 2-3 minutos
- **Verificación**: 30 segundos
- **Firebase**: 1-2 minutos

### **Optimizaciones:**
El proyecto usa tiempos agresivos optimizados. Si hay muchos timeouts:
1. Aumentar `TIMEOUT_PRODUCTOS` en los scrapers
2. Aumentar `DELAY_ENTRE_BUSQUEDAS`
3. Verificar conexión a internet

---

## 📊 **Monitoreo**

### **Ver progreso en tiempo real:**
```bash
# Docker
./docker-run.sh logs

# Sin Docker
tail -f logs/pipeline.log  # Si hay logs
```

### **Verificar recursos:**
```bash
# Docker
docker stats scraping-pipeline

# Sistema
htop  # o top
```

---

## 🔧 **Personalización**

### **Agregar nuevos dispositivos:**
Edita la lista `DISPOSITIVOS` en ambos scrapers:
```python
DISPOSITIVOS = [
    "samsung galaxy s25 ultra",
    "samsung galaxy s24 ultra", 
    "samsung z flip 6",
    "samsung galaxy a56",
    "samsung galaxy a16",
    "tu_nuevo_dispositivo"  # Agregar aquí
]
```

### **Cambiar páginas objetivo:**
- **Éxito**: Modificar `get_url_exito()` en `scraper_exito.py`
- **Falabella**: Modificar `get_url_falabella()` en `scraper_falabella.py`

### **Agregar nuevos campos:**
1. Modificar extractores en cada scraper
2. Actualizar `verificar_productos.py` para validar nuevos campos

---

## 🆘 **Soporte**

### **Si algo no funciona:**
1. **Revisar logs**: `./docker-run.sh logs` o archivos de error
2. **Verificar conexión**: Probar abrir las páginas web manualmente
3. **Verificar versiones**: Docker Desktop actualizado
4. **Limpiar cache**: `./docker-run.sh clean` y reconstruir

### **Archivos de debug:**
Si hay errores, se generan archivos HTML para depuración:
- `debug_exito_*.html`
- `debug_falabella_*.html`

---

## 📝 **Licencia y Uso Responsable**

- ⚠️ **Usar responsablemente**: Respetar robots.txt y términos de servicio
- 🕒 **No abusar**: Los delays están optimizados para ser rápidos pero responsables
- 🔒 **Datos privados**: No incluir credenciales en el código fuente
- 📋 **Solo uso educativo/personal**: Verificar legalidad según tu jurisdicción

---

## 🎯 **¿Qué hace cada script?**

1. **`scraper_exito.py`** - Extrae productos de Éxito.com
2. **`scraper_falabella.py`** - Extrae productos de Falabella.com  
3. **`verificar_productos.py`** - Limpia y valida los datos extraídos
4. **`firebase_uploader_organizado.py`** - Sube datos a Firebase de forma organizada
5. **`run_pipeline.sh`** - Ejecuta todo el proceso automáticamente
6. **`docker-run.sh`** - Helper para comandos Docker

¡Listo para usar! 🚀
