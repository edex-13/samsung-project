@echo off
echo Ejecutando scraper completo integrado...

REM Activar entorno virtual
call venv\Scripts\activate.bat

REM Ejecutar scraper completo
python scraper_completo.py

echo.
echo Scraper completo finalizado! Revisa el archivo resultados_completos.xlsx
echo.
pause 