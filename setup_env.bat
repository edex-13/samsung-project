@echo off
echo Configurando entorno virtual para scraper de MercadoLibre...

REM Crear entorno virtual
python -m venv venv

REM Activar entorno virtual
call venv\Scripts\activate.bat

REM Instalar dependencias
pip install -r requirements.txt

REM Instalar navegadores de Playwright
playwright install

echo.
echo Entorno virtual configurado correctamente!
echo Para activar el entorno virtual ejecuta: venv\Scripts\activate.bat
echo Para ejecutar el scraper: python scraper_mercadolibre.py
echo.
pause 