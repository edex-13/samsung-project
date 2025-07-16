@echo off
echo Ejecutando scraper de MercadoLibre...

REM Activar entorno virtual
call venv\Scripts\activate.bat

REM Ejecutar scraper
python scraper_mercadolibre.py

echo.
echo Scraper completado! Revisa el archivo resultados.xlsx
echo.
pause 