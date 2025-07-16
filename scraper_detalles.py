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
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Chrome Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Safari Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15"
]

# Función para extraer el ID del producto desde la URL

def extraer_id_producto(url: str) -> Optional[str]:
    # Busca patrones tipo MCO-1606750701 o /MCO1606750701-
    match = re.search(r'(MCO-?\d{10,})', url)
    if match:
        return match.group(1)
    # Alternativamente, busca /MCO\d{10,}
    match2 = re.search(r'/MCO(\d{10,})', url)
    if match2:
        return f"MCO-{match2.group(1)}"
    return None

async def scrape_detalles_productos(archivo_excel: str = "resultados_multiple.xlsx"):
    """
    Scraper que visita cada página de producto y extrae detalles de memoria y vendedor
    """
    
    # Leer el archivo Excel con los productos
    try:
        df = pd.read_excel(archivo_excel)
        print(f"📊 Cargados {len(df)} productos del archivo {archivo_excel}")
    except FileNotFoundError:
        print(f"❌ No se encontró el archivo {archivo_excel}")
        return
    
    productos_con_detalles = []
    fecha_scraping = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    async with async_playwright() as p:
        # User-Agent y viewport aleatorio para cada sesión
        user_agent = random.choice(USER_AGENTS)
        viewport_width = random.randint(1200, 1920)
        viewport_height = random.randint(700, 1080)
        print(f"🖥️ User-Agent usado: {user_agent}")
        print(f"🖥️ Viewport: {viewport_width}x{viewport_height}")
        
        # Iniciar navegador
        browser = await p.chromium.launch(
            headless=True,
            args=[
                f'--user-agent={user_agent}',
                f'--window-size={viewport_width},{viewport_height}'
            ]
        )
        
        page = await browser.new_page()
        await page.set_viewport_size({"width": viewport_width, "height": viewport_height})
        
        for index, producto in df.iterrows():
            url = producto['url']
            nombre = producto['nombre']
            id_producto = extraer_id_producto(url)
            
            print(f"\n🔍 Producto {index + 1}/{len(df)}: {nombre[:50]}...")
            print(f"   URL: {url}")
            print(f"   ID producto: {id_producto}")
            
            try:
                # Timeout aleatorio entre 80 y 100 segundos
                timeout = random.randint(80000, 100000)
                # Navegar a la página del producto con timeout aumentado
                await page.goto(url, wait_until="networkidle", timeout=timeout)
                
                # Buscar y hacer clic en el botón "Ver todas las características"
                boton_caracteristicas = await page.query_selector('button[data-testid="action-collapsable-target"]')
                
                if boton_caracteristicas:
                    print("   ✅ Botón encontrado, haciendo clic...")
                    await boton_caracteristicas.click()
                    
                    # Esperar a que se carguen las características
                    await asyncio.sleep(random.uniform(1.5, 3.5))
                    
                    # Buscar la tabla de memoria
                    tabla_memoria = await page.query_selector('div.ui-vpp-striped-specs__table')
                    
                    if tabla_memoria:
                        print("   📋 Tabla de memoria encontrada, extrayendo datos...")
                        
                        # Extraer datos de memoria
                        datos_memoria = await extraer_datos_memoria(page)
                        
                        # Extraer datos del vendedor
                        datos_vendedor = await extraer_datos_vendedor(page)
                        
                        # Agregar datos al producto
                        producto_dict = producto.to_dict()
                        producto_dict['id_producto'] = id_producto
                        producto_dict.update(datos_memoria)
                        producto_dict.update(datos_vendedor)
                        producto_dict['fecha_scraping'] = fecha_scraping
                        productos_con_detalles.append(producto_dict)
                        
                        print(f"   ✅ Datos extraídos: {datos_memoria}")
                    else:
                        print("   ⚠️ No se encontró tabla de memoria")
                        producto_dict = producto.to_dict()
                        producto_dict['id_producto'] = id_producto
                        producto_dict['fecha_scraping'] = fecha_scraping
                        productos_con_detalles.append(producto_dict)
                else:
                    print("   ⚠️ No se encontró botón de características")
                    producto_dict = producto.to_dict()
                    producto_dict['id_producto'] = id_producto
                    producto_dict['fecha_scraping'] = fecha_scraping
                    productos_con_detalles.append(producto_dict)
                
                # Delay aleatorio entre productos
                await asyncio.sleep(random.uniform(2.5, 6.5))
                
            except Exception as e:
                print(f"   ❌ Error procesando producto: {str(e)}")
                producto_dict = producto.to_dict()
                producto_dict['id_producto'] = id_producto
                producto_dict['fecha_scraping'] = fecha_scraping
                productos_con_detalles.append(producto_dict)
                continue
        
        await browser.close()
    
    # Guardar resultados con detalles
    if productos_con_detalles:
        df_detalles = pd.DataFrame(productos_con_detalles)
        try:
            df_detalles.to_excel("resultados_con_detalles.xlsx", index=False)
            print(f"\n🎉 ¡Scraping de detalles completado!")
            print(f"📊 Productos procesados: {len(productos_con_detalles)}")
            print(f"💾 Archivo guardado: resultados_con_detalles.xlsx")
        except PermissionError:
            # Si hay error de permisos, guardar con timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nuevo_archivo = f"resultados_con_detalles_{timestamp}.xlsx"
            df_detalles.to_excel(nuevo_archivo, index=False)
            print(f"\n🎉 ¡Scraping de detalles completado!")
            print(f"📊 Productos procesados: {len(productos_con_detalles)}")
            print(f"💾 Archivo guardado: {nuevo_archivo} (archivo original estaba en uso)")
    else:
        print("❌ No se procesaron productos")


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
            # Obtener el encabezado (primera columna)
            encabezado_element = await fila.query_selector('th .andes-table__header__container')
            if encabezado_element:
                encabezado = await encabezado_element.inner_text()
                
                # Obtener el valor (segunda columna)
                valor_element = await fila.query_selector('td .andes-table__column--value')
                if valor_element:
                    valor = await valor_element.inner_text()
                    
                    # Mapear según el encabezado
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
        # Buscar el nombre del vendedor
        vendedor_element = await page.query_selector('h2.ui-seller-data-header__title')
        if vendedor_element:
            vendedor_texto = await vendedor_element.inner_text()
            # Limpiar el texto "Vendido por "
            datos['vendedor'] = vendedor_texto.replace("Vendido por ", "").strip()
        
        # Buscar información de productos del vendedor
        productos_element = await page.query_selector('.ui-seller-data-header__products')
        if productos_element:
            productos_texto = await productos_element.inner_text()
            datos['productos_vendedor'] = productos_texto.strip()
        
        # Buscar evaluación del vendedor
        evaluacion_element = await page.query_selector('.ui-seller-data-status__default-info')
        if evaluacion_element:
            evaluacion_texto = await evaluacion_element.inner_text()
            datos['evaluacion_vendedor'] = evaluacion_texto.strip()
            
    except Exception as e:
        print(f"   ⚠️ Error extrayendo datos del vendedor: {str(e)}")
    
    return datos


if __name__ == "__main__":
    print("🔍 Iniciando scraper de detalles de productos...")
    print("=" * 60)
    
    # Ejecutar scraper
    asyncio.run(scrape_detalles_productos()) 