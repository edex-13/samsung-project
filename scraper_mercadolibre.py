import asyncio
import re
import pandas as pd
from playwright.async_api import async_playwright
from typing import List, Dict, Optional
from config import MODELO, CONDICION, MAX_PAGINAS, USER_AGENT, VIEWPORT_WIDTH, VIEWPORT_HEIGHT, TIMEOUT_PRODUCTOS, ARCHIVO_SALIDA


async def scrape_mercadolibre(modelo: str, condicion: str, max_paginas: int):
    """
    Scraper de MercadoLibre Colombia
    
    Args:
        modelo: Modelo del producto a buscar (ej: "samsung a15")
        condicion: Condición del producto ("nuevo" o "usado")
        max_paginas: Número máximo de páginas a recorrer
    """
    
    # Formatear el modelo para la URL
    modelo_formateado = modelo.lower().replace(" ", "-")
    
    # Construir URL base
    base_url = f"https://listado.mercadolibre.com.co/{modelo_formateado}/{condicion}"
    
    productos = []
    
    async with async_playwright() as p:
        # Iniciar navegador en modo headless con user-agent de escritorio
        browser = await p.chromium.launch(
            headless=True,
            args=[
                f'--user-agent={USER_AGENT}',
                f'--window-size={VIEWPORT_WIDTH},{VIEWPORT_HEIGHT}'
            ]
        )
        
        page = await browser.new_page()
        
        # Configurar viewport de escritorio
        await page.set_viewport_size({"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})
        
        pagina_actual = 1
        
        while pagina_actual <= max_paginas:
            print(f"Scrapeando página {pagina_actual}...")
            
            # Construir URL con parámetro de página
            if pagina_actual == 1:
                url = base_url
            else:
                url = f"{base_url}_Desde_{(pagina_actual-1)*50+1}"
            
            try:
                await page.goto(url, wait_until="networkidle")
                
                # Esperar a que carguen los productos
                await page.wait_for_selector("a.poly-component__title", timeout=TIMEOUT_PRODUCTOS)
                
                # Extraer productos de la página actual
                productos_pagina = await extraer_productos_pagina(page, condicion)
                
                if not productos_pagina:
                    print(f"No se encontraron más productos en la página {pagina_actual}")
                    break
                
                productos.extend(productos_pagina)
                print(f"Encontrados {len(productos_pagina)} productos en página {pagina_actual}")
                
                # Verificar si hay botón "Siguiente"
                siguiente_btn = await page.query_selector('a[title="Siguiente"]')
                if not siguiente_btn:
                    print("No hay más páginas disponibles")
                    break
                
                pagina_actual += 1
                
            except Exception as e:
                print(f"Error en página {pagina_actual}: {str(e)}")
                break
        
        await browser.close()
    
    # Guardar resultados en Excel
    if productos:
        df = pd.DataFrame(productos)
        df.to_excel(ARCHIVO_SALIDA, index=False)
        print(f"Se guardaron {len(productos)} productos en {ARCHIVO_SALIDA}")
    else:
        print("No se encontraron productos")


async def extraer_productos_pagina(page, condicion: str) -> List[Dict]:
    """Extrae todos los productos de una página"""
    
    productos = []
    
    # Obtener todos los elementos de producto
    elementos_producto = await page.query_selector_all("div.poly-card")
    
    for elemento in elementos_producto:
        try:
            producto = {}
            
            # Extraer nombre
            titulo_element = await elemento.query_selector("a.poly-component__title")
            if titulo_element:
                producto['nombre'] = await titulo_element.inner_text()
                producto['url'] = await titulo_element.get_attribute("href")
            else:
                producto['nombre'] = None
                producto['url'] = None
            
            # Extraer precio
            precio_element = await elemento.query_selector("span.andes-money-amount__fraction")
            if precio_element:
                precio_texto = await precio_element.inner_text()
                # Limpiar precio: "679.900" -> 679900
                precio_limpio = re.sub(r'[^\d]', '', precio_texto)
                producto['precio'] = int(precio_limpio) if precio_limpio else None
            else:
                producto['precio'] = None
            
            # Extraer calificación
            calificacion_element = await elemento.query_selector("span.poly-reviews__rating")
            if calificacion_element:
                calificacion_texto = await calificacion_element.inner_text()
                # Buscar patrón "Calificación X,X de 5" o número directo
                match = re.search(r'Calificación\s+(\d+[,.]?\d*)\s+de\s+5', calificacion_texto)
                if match:
                    # Convertir coma a punto para float
                    calificacion = match.group(1).replace(',', '.')
                    producto['calificacion'] = float(calificacion)
                else:
                    # Intentar extraer número directo
                    numero_match = re.search(r'(\d+[,.]?\d*)', calificacion_texto)
                    if numero_match:
                        calificacion = numero_match.group(1).replace(',', '.')
                        producto['calificacion'] = float(calificacion)
                    else:
                        producto['calificacion'] = None
            else:
                producto['calificacion'] = None
            
            # Agregar condición
            producto['condicion'] = condicion
            
            # Solo agregar si tiene al menos nombre o precio
            if producto['nombre'] or producto['precio']:
                productos.append(producto)
                
        except Exception as e:
            print(f"Error extrayendo producto: {str(e)}")
            continue
    
    return productos


if __name__ == "__main__":
    print(f"Iniciando scraper para: {MODELO} - {CONDICION}")
    print(f"Máximo de páginas: {MAX_PAGINAS}")
    
    # Ejecutar scraper
    asyncio.run(scrape_mercadolibre(
        modelo=MODELO,
        condicion=CONDICION,
        max_paginas=MAX_PAGINAS
    )) 