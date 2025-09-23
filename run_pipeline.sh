#!/usr/bin/env bash
set -euo pipefail

# Colores
Y="\033[33m"; G="\033[32m"; R="\033[31m"; B="\033[34m"; NC="\033[0m"

# Directorio del proyecto (Docker usa /app, local usa ruta específica)
if [ -d "/app" ] && [ -f "/app/scraper_exito.py" ]; then
  PROJECT_DIR="/app"
  echo -e "${B}==> Ejecutando en contenedor Docker${NC}"
else
  PROJECT_DIR="/mnt/c/Users/eders/OneDrive/Escritorio/scraping"
  echo -e "${B}==> Ejecutando en sistema local${NC}"
fi
cd "$PROJECT_DIR"

echo -e "${B}==> [$(date '+%Y-%m-%d %H:%M:%S')] Iniciando pipeline de scraping (Éxito + Falabella)${NC}"
echo -e "${B}==> Directorio: ${NC}$PROJECT_DIR"
echo -e "${B}==> Usuario: ${NC}$(whoami)  |  Shell: $SHELL"

# 1) Crear/activar entorno virtual (solo en sistema local, Docker ya tiene todo)
if [ "$PROJECT_DIR" = "/app" ]; then
  echo -e "${Y}==> [$(date '+%H:%M:%S')] Entorno Docker: usando Python del sistema (ya configurado)${NC}"
  VENV_DIR=""
else
  echo -e "${Y}==> [$(date '+%H:%M:%S')] Sistema local: configurando entorno virtual${NC}"
  VENV_DIR=".venv"
  if [ -d "$VENV_DIR" ]; then
    echo -e "${Y}-- [$(date '+%H:%M:%S')] Detectando entorno virtual existente${NC}"
    # Verificar si el venv está corrupto (distribuciones inválidas)
    if source "$VENV_DIR/bin/activate" 2>/dev/null && pip list 2>&1 | grep -q "WARNING.*Ignoring invalid distribution"; then
      echo -e "${R}!! Entorno virtual corrupto detectado - eliminando${NC}"
      deactivate 2>/dev/null || true
      rm -rf "$VENV_DIR"
    else
      echo -e "${Y}-- Entorno virtual parece válido, reutilizando${NC}"
    fi
  fi

  if [ ! -d "$VENV_DIR" ]; then
    echo -e "${Y}-- [$(date '+%H:%M:%S')] Creando entorno virtual limpio en ${VENV_DIR}${NC}"
    
    # Intentar crear venv con timeout
    timeout 60 python3 -m venv "$VENV_DIR" || {
      echo -e "${R}!! Timeout o error creando venv con python3 -m venv${NC}"
      echo -e "${Y}-- Intentando con virtualenv como alternativa${NC}"
      
      # Instalar virtualenv si no existe
      pip3 install virtualenv 2>/dev/null || {
        echo -e "${R}!! No se pudo instalar virtualenv${NC}"
        echo -e "${Y}-- Ejecutando directamente sin venv (menos aislado)${NC}"
        VENV_DIR=""
      }
      
      if [ -n "$VENV_DIR" ]; then
        timeout 60 virtualenv "$VENV_DIR" || {
          echo -e "${R}!! También falló virtualenv${NC}"
          echo -e "${Y}-- Ejecutando sin venv${NC}"
          VENV_DIR=""
        }
      fi
    }
    
    if [ -n "$VENV_DIR" ] && [ -d "$VENV_DIR" ]; then
      echo -e "${G}OK${NC} Entorno virtual creado"
    else
      echo -e "${Y}!! Continuando sin entorno virtual${NC}"
    fi
  fi

  # 2) Activar entorno virtual (si existe)
  if [ -n "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    echo -e "${B}==> [$(date '+%H:%M:%S')] Entorno virtual activado${NC}"
  else
    echo -e "${Y}==> [$(date '+%H:%M:%S')] Ejecutando con Python del sistema${NC}"
  fi
fi
echo -e "${B}==> Python: ${NC}$(python --version 2>/dev/null || python3 --version)"
echo -e "${B}==> Pip:    ${NC}$(pip --version 2>/dev/null || pip3 --version)"

# 3) Configuración de dependencias (diferente para Docker vs local)
if [ "$PROJECT_DIR" = "/app" ]; then
  echo -e "${Y}==> [$(date '+%H:%M:%S')] Entorno Docker: dependencias ya instaladas${NC}"
  echo -e "${G}OK${NC} Usando dependencias pre-instaladas en Docker"
else
  echo -e "${Y}-- [$(date '+%H:%M:%S')] Actualizando pip/setuptools/wheel${NC}"
  $(command -v python || command -v python3) -m pip install --upgrade pip wheel setuptools >/dev/null
  echo -e "${G}OK${NC} pip/setuptools/wheel actualizados"

  # 4) Instalar dependencias (fusionadas) evitando conflictos
  # Unificar requirements base + firebase en una sola instalación
  REQ_TMP="/tmp/req_combined_$$.txt"
  cat > "$REQ_TMP" << 'EOF'
playwright==1.40.0
pandas==2.1.4
openpyxl==3.1.2
firebase-admin==6.2.0
EOF

  # Resolver instalación
  echo -e "${B}==> [$(date '+%H:%M:%S')] Instalando dependencias (puede tardar)${NC}"
  set +e
  $(command -v pip || command -v pip3) install -r "$REQ_TMP"
  PIP_STATUS=$?
  if [ $PIP_STATUS -ne 0 ]; then
    echo -e "${R}!! Falló la instalación de dependencias (${PIP_STATUS})${NC}"
    echo -e "${Y}-- Intentando recuperación: recrear venv y reinstalar sin caché${NC}"
    # Desactivar venv actual si aplica
    if command -v deactivate >/dev/null 2>&1; then deactivate || true; fi
    rm -rf "$VENV_DIR"
    echo -e "${Y}-- Creando venv limpio${NC}"
    python3 -m venv "$VENV_DIR"
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    echo -e "${Y}-- Actualizando pip/setuptools/wheel en venv limpio${NC}"
    $(command -v python || command -v python3) -m pip install --upgrade pip setuptools wheel
    echo -e "${Y}-- Reinstalando dependencias con --no-cache-dir${NC}"
    $(command -v pip || command -v pip3) install --no-cache-dir -r "$REQ_TMP"
    PIP_STATUS=$?
    if [ $PIP_STATUS -ne 0 ]; then
      echo -e "${R}❌ No fue posible instalar dependencias tras recuperación (código ${PIP_STATUS})${NC}"
      exit $PIP_STATUS
    fi
  fi
  set -e
  echo -e "${G}OK${NC} Dependencias instaladas"

  # 5) Instalar navegadores de Playwright (solo chromium)
  echo -e "${B}==> [$(date '+%H:%M:%S')] Instalando navegadores Playwright (chromium)${NC}"
  set +e
  $(command -v python || command -v python3) - << 'PY'
import sys
try:
    from playwright.__main__ import main as pw_main
    # playwright install chromium sin --with-deps para evitar sudo
    sys.argv = ["playwright", "install", "chromium"]
    pw_main()
    print("Chromium instalado para Playwright")
except Exception as e:
    print(f"Error instalando navegadores de Playwright: {e}")
    sys.exit(1)
PY
  PLAYWRIGHT_STATUS=$?
  if [ $PLAYWRIGHT_STATUS -ne 0 ]; then
    echo -e "${R}!! Falló la instalación de Playwright (código ${PLAYWRIGHT_STATUS})${NC}"
    echo -e "${Y}-- Continuando sin navegadores Playwright (scrapers pueden fallar)${NC}"
  else
    echo -e "${G}OK${NC} Playwright instalado"
    echo -e "${Y}-- Nota: Si los scrapers fallan con 'missing dependencies', ejecuta manualmente:${NC}"
    echo -e "${Y}   sudo apt-get install -y libasound2 libgtk-3-0 libdrm2 libxss1${NC}"
  fi
  set -e
fi

# 6) Ejecutar scrapers (Éxito y Falabella)
run_scraper() {
  local name="$1"
  local script="$2"
  echo -e "${B}==> [$(date '+%H:%M:%S')] Ejecutando scraper ${name}${NC}"
  $(command -v python || command -v python3) "$script" || {
    echo -e "${R}Scraper ${name} falló, continuando con el pipeline...${NC}"
  }
  echo -e "${G}OK${NC} Scraper ${name} finalizado"
}

run_scraper "Éxito" "scraper_exito.py"
run_scraper "Falabella" "scraper_falabella.py"

# 7) Verificación y limpieza de productos
# Este script genera archivos en carpeta data: *_limpio.xlsx e *_invalidos.xlsx
if [ -f "verificar_productos.py" ]; then
  echo -e "${B}==> [$(date '+%H:%M:%S')] Verificando y limpiando productos${NC}"
  $(command -v python || command -v python3) "verificar_productos.py" || echo -e "${R}Verificador con errores; continuaré si hay data válida...${NC}"
  echo -e "${G}OK${NC} Verificación completada"
else
  echo -e "${Y}No se encontró verificar_productos.py, saltando verificación${NC}"
fi

# 8) Subida a Firebase (organizado)
CRED="firebase-credentials.json"
if [ -f "$CRED" ]; then
  if [ -f "firebase_uploader_organizado.py" ]; then
    echo -e "${B}==> [$(date '+%H:%M:%S')] Subiendo a Firebase (organizado)${NC}"
    $(command -v python || command -v python3) "firebase_uploader_organizado.py" || echo -e "${R}Uploader organizado falló${NC}"
  elif [ -f "firebase_uploader.py" ]; then
    echo -e "${B}==> [$(date '+%H:%M:%S')] Subiendo a Firebase (simple)${NC}"
    $(command -v python || command -v python3) "firebase_uploader.py" || echo -e "${R}Uploader simple falló${NC}"
  else
    echo -e "${Y}No se encontró uploader de Firebase, saltando subida${NC}"
  fi
else
  echo -e "${Y}No hay credenciales Firebase (firebase-credentials.json). Saltando subida.${NC}"
fi

# 9) Resumen de salidas
echo -e "${B}==> [$(date '+%H:%M:%S')] Resumen de archivos generados${NC}"
ls -1 *.xlsx 2>/dev/null || true
if [ -d "data" ]; then
  echo -e "${G}Archivos en data/${NC}"
  ls -1 data/*.xlsx 2>/dev/null || true
fi

echo -e "${G}Pipeline finalizado$(echo -e " \xF0\x9F\x9A\x80")${NC}"
