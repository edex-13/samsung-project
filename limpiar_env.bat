@echo off
echo Limpiando entorno virtual...

REM Desactivar entorno virtual si está activo
call venv\Scripts\deactivate.bat 2>nul

REM Eliminar directorio del entorno virtual
if exist venv (
    rmdir /s /q venv
    echo Entorno virtual eliminado.
) else (
    echo No se encontró entorno virtual para eliminar.
)

REM Eliminar archivos de resultados
if exist resultados.xlsx (
    del resultados.xlsx
    echo Archivo de resultados eliminado.
)

echo.
echo Limpieza completada! Ejecuta setup_env.bat para recrear el entorno.
echo.
pause 