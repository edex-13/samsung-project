@echo off
echo Ejecutando scraper multiple de MercadoLibre...

REM Activar entorno virtual
call venv\Scripts\activate.bat

REM Ejecutar scraper multiple
python scraper_multiple.py

echo.
echo Scraper multiple completado! Revisa el archivo resultados_completos.xlsx
echo.
pause 