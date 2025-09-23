#!/usr/bin/env bash
set -euo pipefail

# Script helper para ejecutar el pipeline en Docker
# Este script simplifica los comandos de Docker Compose

# Colores
Y="\033[33m"; G="\033[32m"; R="\033[31m"; B="\033[34m"; NC="\033[0m"

echo -e "${B}🐳 SCRAPING PIPELINE - DOCKER MANAGER${NC}"
echo "================================================="

# Verificar que Docker esté instalado y corriendo
if ! command -v docker &> /dev/null; then
    echo -e "${R}❌ Docker no está instalado${NC}"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${R}❌ Docker no está corriendo${NC}"
    echo "   Inicia Docker Desktop o el daemon de Docker"
    exit 1
fi

# Verificar que Docker Compose esté disponible
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${R}❌ Docker Compose no está disponible${NC}"
    exit 1
fi

# Usar docker compose si está disponible, sino docker-compose
COMPOSE_CMD="docker-compose"
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
fi

# Función para mostrar uso
show_usage() {
    echo "Uso: $0 [COMANDO]"
    echo ""
    echo "Comandos disponibles:"
    echo "  build       - Construir la imagen Docker"
    echo "  run         - Ejecutar el pipeline (foreground)"
    echo "  start       - Ejecutar el pipeline (background)"
    echo "  stop        - Parar contenedores"
    echo "  logs        - Ver logs del pipeline"
    echo "  status      - Ver estado de contenedores"
    echo "  shell       - Acceder al contenedor"
    echo "  clean       - Limpiar contenedores e imágenes"
    echo "  help        - Mostrar esta ayuda"
    echo ""
    echo "Ejemplos:"
    echo "  $0 build && $0 run     # Construir y ejecutar"
    echo "  $0 start && $0 logs    # Ejecutar en background y ver logs"
}

# Procesar comando
COMMAND=${1:-"help"}

case $COMMAND in
    "build")
        echo -e "${B}🔨 Construyendo imagen Docker...${NC}"
        $COMPOSE_CMD build --no-cache
        echo -e "${G}✅ Imagen construida exitosamente${NC}"
        ;;
    
    "run")
        echo -e "${B}🚀 Ejecutando pipeline (foreground)...${NC}"
        echo "   Para detener: Ctrl+C"
        $COMPOSE_CMD up --abort-on-container-exit
        ;;
    
    "start")
        echo -e "${B}🚀 Ejecutando pipeline (background)...${NC}"
        $COMPOSE_CMD up -d
        echo -e "${G}✅ Pipeline iniciado en background${NC}"
        echo "   Ver logs: $0 logs"
        echo "   Parar: $0 stop"
        ;;
    
    "stop")
        echo -e "${Y}⏹️ Parando contenedores...${NC}"
        $COMPOSE_CMD down
        echo -e "${G}✅ Contenedores parados${NC}"
        ;;
    
    "logs")
        echo -e "${B}📋 Mostrando logs del pipeline...${NC}"
        echo "   Para salir: Ctrl+C"
        $COMPOSE_CMD logs -f scraper
        ;;
    
    "status")
        echo -e "${B}📊 Estado de contenedores:${NC}"
        $COMPOSE_CMD ps
        echo ""
        echo -e "${B}💾 Uso de recursos:${NC}"
        docker stats --no-stream scraping-pipeline 2>/dev/null || echo "   Contenedor no está corriendo"
        ;;
    
    "shell")
        echo -e "${B}🐚 Accediendo al contenedor...${NC}"
        $COMPOSE_CMD exec scraper bash || {
            echo -e "${Y}⚠️ Contenedor no está corriendo, iniciando uno temporal...${NC}"
            $COMPOSE_CMD run --rm scraper bash
        }
        ;;
    
    "clean")
        echo -e "${Y}🧹 Limpiando contenedores e imágenes...${NC}"
        $COMPOSE_CMD down --rmi all --volumes --remove-orphans
        echo "¿Limpiar también imágenes huérfanas? (y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            docker system prune -f
        fi
        echo -e "${G}✅ Limpieza completada${NC}"
        ;;
    
    "help"|"-h"|"--help")
        show_usage
        ;;
    
    *)
        echo -e "${R}❌ Comando desconocido: $COMMAND${NC}"
        echo ""
        show_usage
        exit 1
        ;;
esac

# Mostrar archivos generados si existen
if [ "$COMMAND" = "run" ] || [ "$COMMAND" = "stop" ]; then
    echo ""
    echo -e "${B}📁 Archivos generados:${NC}"
    ls -la data/ 2>/dev/null || echo "   Ningún archivo generado aún"
    ls -la backup/ 2>/dev/null || true
fi
