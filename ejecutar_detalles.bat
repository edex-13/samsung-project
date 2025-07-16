@echo off
echo Ejecutando scraper de detalles de productos...

REM Activar entorno virtual
call venv\Scripts\activate.bat

REM Ejecutar scraper de detalles
python scraper_detalles.py

echo.
echo Scraper de detalles completado! Revisa el archivo resultados_con_detalles.xlsx
echo.
pause 