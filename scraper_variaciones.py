import asyncio
import re
import pandas as pd
import time
import random
from datetime import datetime
from playwright.async_api import async_playwright
from typing import List, Dict, Optional
from config import USER_AGENT, VIEWPORT_WIDTH, VIEWPORT_HEIGHT, TIMEOUT_PRODUCTOS

# Lista de user-agents de escritorio populares
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15"
]

def extraer_id_producto(url: str) -> Optional[str]:
    match = re.search(r'(MCO-?\d{10,})', url)
    if match:
        return match.group(1)
    match2 = re.search(r'/MCO(\d{10,})', url)
    if match2:
        return f"MCO-{match2.group(1)}"
    return None

async def scrape_variaciones_productos(archivo_excel: str = "resultados_multiple.xlsx"):
    """
    Scraper que extrae todas las variaciones disponibles de cada producto
    """
    
    try:
        df = pd.read_excel(archivo_excel)
        print(f"📊 Cargados {len(df)} productos del archivo {archivo_excel}")
    except FileNotFoundError:
        print(f"❌ No se encontró el archivo {archivo_excel}")
        return
    
    # Limitar a 3 productos para prueba
    df_limite = df.head(3)
    print(f"🧪 Modo prueba: procesando solo los primeros 3 productos")
    
    todas_variaciones = []
    fecha_scraping = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    async with async_playwright() as p:
        user_agent = random.choice(USER_AGENTS)
        viewport_width = random.randint(1200, 1920)
        viewport_height = random.randint(700, 1080)
        print(f"🖥️ User-Agent usado: {user_agent}")
        print(f"🖥️ Viewport: {viewport_width}x{viewport_height}")
        
        browser = await p.chromium.launch(
            headless=True,
            args=[
                f'--user-agent={user_agent}',
                f'--window-size={viewport_width},{viewport_height}'
            ]
        )
        
        page = await browser.new_page()
        await page.set_viewport_size({"width": viewport_width, "height": viewport_height})
        
        for index, producto in df_limite.iterrows():
            url = producto['url']
            nombre = producto['nombre']
            id_producto = extraer_id_producto(url)
            
            print(f"\n🔍 Producto {index + 1}/{len(df_limite)}: {nombre[:50]}...")
            print(f"   URL: {url}")
            print(f"   ID producto: {id_producto}")
            
            try:
                timeout = random.randint(80000, 100000)
                await page.goto(url, wait_until="networkidle", timeout=timeout)
                
                # Buscar variaciones disponibles
                variaciones = await extraer_variaciones_disponibles(page, producto, id_producto, fecha_scraping)
                
                if variaciones:
                    print(f"   ✅ Encontradas {len(variaciones)} variaciones")
                    todas_variaciones.extend(variaciones)
                else:
                    print(f"   ⚠️ No se encontraron variaciones, agregando producto original")
                    producto_dict = producto.to_dict()
                    producto_dict['id_producto'] = id_producto
                    producto_dict['fecha_scraping'] = fecha_scraping
                    producto_dict['es_variacion'] = False
                    todas_variaciones.append(producto_dict)
                
                await asyncio.sleep(random.uniform(3.0, 7.0))
                
            except Exception as e:
                print(f"   ❌ Error procesando producto: {str(e)}")
                producto_dict = producto.to_dict()
                producto_dict['id_producto'] = id_producto
                producto_dict['fecha_scraping'] = fecha_scraping
                producto_dict['es_variacion'] = False
                todas_variaciones.append(producto_dict)
                continue
        
        await browser.close()
    
    if todas_variaciones:
        df_variaciones = pd.DataFrame(todas_variaciones)
        try:
            df_variaciones.to_excel("resultados_variaciones.xlsx", index=False)
            print(f"\n🎉 ¡Scraping de variaciones completado!")
            print(f"📊 Total de productos (incluyendo variaciones): {len(todas_variaciones)}")
            print(f"💾 Archivo guardado: resultados_variaciones.xlsx")
        except PermissionError:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nuevo_archivo = f"resultados_variaciones_{timestamp}.xlsx"
            df_variaciones.to_excel(nuevo_archivo, index=False)
            print(f"\n🎉 ¡Scraping de variaciones completado!")
            print(f"📊 Total de productos (incluyendo variaciones): {len(todas_variaciones)}")
            print(f"💾 Archivo guardado: {nuevo_archivo}")
    else:
        print("❌ No se procesaron productos")

async def extraer_variaciones_disponibles(page, producto_original, id_producto, fecha_scraping) -> List[Dict]:
    """
    Extrae todas las variaciones disponibles de un producto
    """
    variaciones = []
    
    try:
        # Buscar contenedor de variaciones
        contenedor_variaciones = await page.query_selector('div.ui-pdp-variations')
        
        if not contenedor_variaciones:
            print("   ⚠️ No se encontró contenedor de variaciones")
            return []
        
        # Buscar todos los pickers (color, memoria, RAM)
        pickers = await contenedor_variaciones.query_selector_all('div.ui-pdp-variations__picker')
        
        if not pickers:
            print("   ⚠️ No se encontraron pickers de variaciones")
            return []
        
        print(f"   📋 Encontrados {len(pickers)} tipos de variaciones")
        
        # Extraer URLs de todas las variaciones disponibles
        urls_variaciones = set()
        
        for picker in pickers:
            # Buscar todos los enlaces de variaciones en este picker
            enlaces = await picker.query_selector_all('a[href*="/p/MCO"]')
            
            for enlace in enlaces:
                href = await enlace.get_attribute("href")
                if href and "MCO" in href:
                    # Convertir URL relativa a absoluta
                    if href.startswith("/"):
                        href = f"https://www.mercadolibre.com.co{href}"
                    urls_variaciones.add(href)
        
        print(f"   🔗 Encontradas {len(urls_variaciones)} URLs de variaciones únicas")
        
        # Visitar cada variación y extraer datos
        for i, url_variacion in enumerate(urls_variaciones):
            try:
                print(f"   🔍 Procesando variación {i+1}/{len(urls_variaciones)}: {url_variacion}")
                
                # Navegar a la variación
                await page.goto(url_variacion, wait_until="networkidle", timeout=60000)
                await asyncio.sleep(random.uniform(1.0, 2.5))
                
                # Extraer datos básicos de la variación
                datos_variacion = await extraer_datos_variacion(page, producto_original, id_producto, fecha_scraping, url_variacion)
                variaciones.append(datos_variacion)
                
                print(f"   ✅ Variación procesada: {datos_variacion.get('nombre', 'N/A')[:30]}...")
                
            except Exception as e:
                print(f"   ❌ Error procesando variación: {str(e)}")
                continue
        
    except Exception as e:
        print(f"   ❌ Error extrayendo variaciones: {str(e)}")
    
    return variaciones

async def extraer_datos_variacion(page, producto_original, id_producto, fecha_scraping, url_variacion) -> Dict:
    """
    Extrae los datos de una variación específica
    """
    datos_variacion = producto_original.to_dict()
    datos_variacion['url_variacion'] = url_variacion
    datos_variacion['id_producto'] = id_producto
    datos_variacion['fecha_scraping'] = fecha_scraping
    datos_variacion['es_variacion'] = True
    
    try:
        # Extraer nombre actualizado
        titulo_element = await page.query_selector('h1.ui-pdp-title')
        if titulo_element:
            datos_variacion['nombre'] = await titulo_element.inner_text()
        
        # Extraer precio actualizado
        precio_element = await page.query_selector('span.andes-money-amount__fraction')
        if precio_element:
            precio_texto = await precio_element.inner_text()
            precio_limpio = re.sub(r'[^\d]', '', precio_texto)
            datos_variacion['precio'] = int(precio_limpio) if precio_limpio else None
        
        # Extraer datos de memoria si están disponibles
        datos_memoria = await extraer_datos_memoria(page)
        datos_variacion.update(datos_memoria)
        
        # Extraer datos del vendedor
        datos_vendedor = await extraer_datos_vendedor(page)
        datos_variacion.update(datos_vendedor)
        
    except Exception as e:
        print(f"   ⚠️ Error extrayendo datos de variación: {str(e)}")
    
    return datos_variacion

async def extraer_datos_memoria(page) -> Dict:
    """
    Extrae los datos de memoria de la tabla
    """
    datos = {
        'memoria_interna': None,
        'memoria_ram': None,
        'capacidad_maxima_tarjeta': None,
        'ranura_tarjeta_memoria': None
    }
    
    try:
        # Buscar todas las filas de la tabla
        filas = await page.query_selector_all('tr.andes-table__row')
        
        for fila in filas:
            encabezado_element = await fila.query_selector('th .andes-table__header__container')
            if encabezado_element:
                encabezado = await encabezado_element.inner_text()
                
                valor_element = await fila.query_selector('td .andes-table__column--value')
                if valor_element:
                    valor = await valor_element.inner_text()
                    
                    if "Memoria interna" in encabezado:
                        datos['memoria_interna'] = valor
                    elif "Memoria RAM" in encabezado:
                        datos['memoria_ram'] = valor
                    elif "Capacidad máxima de la tarjeta de memoria" in encabezado:
                        datos['capacidad_maxima_tarjeta'] = valor
                    elif "Con ranura para tarjeta de memoria" in encabezado:
                        datos['ranura_tarjeta_memoria'] = valor
                        
    except Exception as e:
        print(f"   ⚠️ Error extrayendo datos de memoria: {str(e)}")
    
    return datos

async def extraer_datos_vendedor(page) -> Dict:
    """
    Extrae los datos del vendedor
    """
    datos = {
        'vendedor': None,
        'productos_vendedor': None,
        'evaluacion_vendedor': None
    }
    
    try:
        vendedor_element = await page.query_selector('h2.ui-seller-data-header__title')
        if vendedor_element:
            vendedor_texto = await vendedor_element.inner_text()
            datos['vendedor'] = vendedor_texto.replace("Vendido por ", "").strip()
        
        productos_element = await page.query_selector('.ui-seller-data-header__products')
        if productos_element:
            productos_texto = await productos_element.inner_text()
            datos['productos_vendedor'] = productos_texto.strip()
        
        evaluacion_element = await page.query_selector('.ui-seller-data-status__default-info')
        if evaluacion_element:
            evaluacion_texto = await evaluacion_element.inner_text()
            datos['evaluacion_vendedor'] = evaluacion_texto.strip()
            
    except Exception as e:
        print(f"   ⚠️ Error extrayendo datos del vendedor: {str(e)}")
    
    return datos

if __name__ == "__main__":
    print("🔍 Iniciando scraper de variaciones de productos...")
    print("=" * 60)
    
    asyncio.run(scrape_variaciones_productos()) 