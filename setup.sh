#!/usr/bin/env bash
set -euo pipefail

# Script de configuración inicial para el proyecto de scraping
# Este script verifica dependencias y guía al usuario en la configuración

# Colores
Y="\033[33m"; G="\033[32m"; R="\033[31m"; B="\033[34m"; NC="\033[0m"

echo -e "${B}🛒 SETUP - Pipeline de Scraping Samsung${NC}"
echo "=================================================="
echo "Este script te ayudará a configurar el proyecto."
echo ""

# 1. Verificar Docker
echo -e "${B}1. Verificando Docker...${NC}"
if command -v docker &> /dev/null; then
    if docker info &> /dev/null; then
        echo -e "${G}✅ Docker está instalado y corriendo${NC}"
        DOCKER_OK=true
    else
        echo -e "${Y}⚠️ Docker está instalado pero no está corriendo${NC}"
        echo "   Inicia Docker Desktop y vuelve a ejecutar este script"
        DOCKER_OK=false
    fi
else
    echo -e "${R}❌ Docker no está instalado${NC}"
    echo "   Descarga Docker Desktop desde: https://www.docker.com/products/docker-desktop/"
    DOCKER_OK=false
fi

# 2. Verificar Docker Compose
if [ "$DOCKER_OK" = true ]; then
    echo -e "${B}2. Verificando Docker Compose...${NC}"
    if command -v docker-compose &> /dev/null || docker compose version &> /dev/null; then
        echo -e "${G}✅ Docker Compose está disponible${NC}"
        COMPOSE_OK=true
    else
        echo -e "${R}❌ Docker Compose no está disponible${NC}"
        COMPOSE_OK=false
    fi
else
    COMPOSE_OK=false
fi

# 3. Verificar Python (solo si no hay Docker)
if [ "$DOCKER_OK" = false ]; then
    echo -e "${B}3. Verificando Python (alternativa sin Docker)...${NC}"
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        echo -e "${G}✅ Python3 está instalado: $PYTHON_VERSION${NC}"
        PYTHON_OK=true
    else
        echo -e "${R}❌ Python3 no está instalado${NC}"
        echo "   Instala Python 3.8+ desde: https://www.python.org/downloads/"
        PYTHON_OK=false
    fi
fi

# 4. Verificar archivos del proyecto
echo -e "${B}4. Verificando archivos del proyecto...${NC}"
archivos_requeridos=(
    "docker-compose.yml"
    "Dockerfile"
    "docker-run.sh"
    "run_pipeline.sh"
    "scraper_exito.py"
    "scraper_falabella.py"
    "verificar_productos.py"
    "firebase_uploader_organizado.py"
)

archivos_faltantes=()
for archivo in "${archivos_requeridos[@]}"; do
    if [ -f "$archivo" ]; then
        echo -e "  ${G}✅${NC} $archivo"
    else
        echo -e "  ${R}❌${NC} $archivo"
        archivos_faltantes+=("$archivo")
    fi
done

if [ ${#archivos_faltantes[@]} -eq 0 ]; then
    echo -e "${G}✅ Todos los archivos del proyecto están presentes${NC}"
    ARCHIVOS_OK=true
else
    echo -e "${R}❌ Faltan archivos importantes del proyecto${NC}"
    ARCHIVOS_OK=false
fi

# 5. Configuración de Firebase (opcional)
echo -e "${B}5. Verificando configuración de Firebase...${NC}"
if [ -f "firebase-credentials.json" ]; then
    echo -e "${G}✅ Credenciales de Firebase encontradas${NC}"
    echo "   Los datos se subirán automáticamente a Firebase"
    FIREBASE_OK=true
else
    echo -e "${Y}⚠️ Credenciales de Firebase no encontradas${NC}"
    echo "   El scraping funcionará, pero no se subirán datos a Firebase"
    echo "   Para configurar Firebase:"
    echo "   1. Ve a https://console.firebase.google.com/"
    echo "   2. Crea/selecciona un proyecto"
    echo "   3. Ve a Configuración → Cuentas de servicio"
    echo "   4. Genera una nueva clave privada"
    echo "   5. Descarga el JSON y renómbralo a 'firebase-credentials.json'"
    echo "   6. Colócalo en esta carpeta"
    FIREBASE_OK=false
fi

# 6. Dar permisos a scripts
echo -e "${B}6. Configurando permisos...${NC}"
chmod +x *.sh 2>/dev/null || true
echo -e "${G}✅ Permisos configurados${NC}"

# 7. Resumen y recomendaciones
echo ""
echo -e "${B}📋 RESUMEN DE CONFIGURACIÓN${NC}"
echo "================================"

if [ "$DOCKER_OK" = true ] && [ "$COMPOSE_OK" = true ] && [ "$ARCHIVOS_OK" = true ]; then
    echo -e "${G}🎉 ¡Configuración completa!${NC}"
    echo ""
    echo -e "${B}🚀 PRÓXIMOS PASOS (Docker - Recomendado):${NC}"
    echo "1. Construir imagen: ${Y}./docker-run.sh build${NC}"
    echo "2. Ejecutar pipeline: ${Y}./docker-run.sh run${NC}"
    echo "3. Ver progreso: ${Y}./docker-run.sh logs${NC}"
    echo ""
    echo -e "${B}📁 Los archivos aparecerán en:${NC}"
    echo "   • resultados_exito.xlsx"
    echo "   • resultados_falabella.xlsx" 
    echo "   • data/ (archivos verificados)"
    echo "   • backup/ (respaldos automáticos)"
    
elif [ "$PYTHON_OK" = true ] && [ "$ARCHIVOS_OK" = true ]; then
    echo -e "${G}✅ Configuración alternativa sin Docker disponible${NC}"
    echo ""
    echo -e "${B}🚀 PRÓXIMOS PASOS (Sin Docker):${NC}"
    echo "1. Instalar dependencias: ${Y}./run_pipeline.sh${NC}"
    echo "   (El script instalará todo automáticamente)"
    echo ""
    echo -e "${Y}⚠️ Recomendación: Instala Docker para una experiencia más fácil${NC}"
    
else
    echo -e "${R}❌ Configuración incompleta${NC}"
    echo ""
    echo -e "${B}🔧 PARA RESOLVER:${NC}"
    
    if [ "$DOCKER_OK" = false ]; then
        echo "   • Instala Docker Desktop"
    fi
    
    if [ "$PYTHON_OK" = false ] && [ "$DOCKER_OK" = false ]; then
        echo "   • Instala Python 3.8+"
    fi
    
    if [ "$ARCHIVOS_OK" = false ]; then
        echo "   • Verifica que descargaste todos los archivos del proyecto"
        echo "   • Archivos faltantes: ${archivos_faltantes[*]}"
    fi
    
    echo ""
    echo "Ejecuta este script nuevamente después de resolver los problemas."
fi

if [ "$FIREBASE_OK" = false ]; then
    echo ""
    echo -e "${Y}💡 OPCIONAL: Configurar Firebase para subir datos automáticamente${NC}"
fi

echo ""
echo -e "${B}📖 Para más información, consulta: README.md${NC}"
