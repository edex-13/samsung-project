import asyncio
import re
import pandas as pd
import time
import random
from datetime import datetime
from playwright.async_api import async_playwright
from typing import List, Dict, Optional
from config import DISPOSITIVOS, CONDICIONES, MAX_PAGINAS, USER_AGENT, VIEWPORT_WIDTH, VIEWPORT_HEIGHT, TIMEOUT_PRODUCTOS, DELAY_ENTRE_BUSQUEDAS

# Lista de user-agents de escritorio populares
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15"
]

def get_url_mercadolibre(dispositivo_formateado, condicion):
    base = f"https://listado.mercadolibre.com.co/celulares-telefonos/celulares-smartphones/samsung/{condicion}/5g/{dispositivo_formateado}_NoIndex_True"
    if condicion == "nuevo":
        hash_filtro = "#applied_filter_id%3DITEM_CONDITION%26applied_filter_name%3DCondición%26applied_filter_order%3D4%26applied_value_id%3D2230284%26applied_value_name%3DNuevo%26applied_value_order%3D1%26applied_value_results%3D20%26is_custom%3Dfalse"
    else:
        hash_filtro = "#applied_filter_id%3DITEM_CONDITION%26applied_filter_name%3DCondición%26applied_filter_order%3D4%26applied_value_id%3D2230581%26applied_value_name%3DUsado%26applied_value_order%3D3%26applied_value_results%3D10%26is_custom%3Dfalse"
    return base + hash_filtro

def extraer_id_producto(url: str) -> Optional[str]:
    match = re.search(r'(MCO-?\d{10,})', url)
    if match:
        return match.group(1)
    match2 = re.search(r'/MCO(\d{10,})', url)
    if match2:
        return f"MCO-{match2.group(1)}"
    return None

async def scrape_completo():
    """
    Scraper completo que integra búsqueda inicial, detalles y variaciones
    """
    
    todos_productos = []
    total_busquedas = len(DISPOSITIVOS) * len(CONDICIONES)
    busqueda_actual = 0
    fecha_scraping = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print(f"🚀 Iniciando scraper completo para {len(DISPOSITIVOS)} dispositivos y {len(CONDICIONES)} condiciones")
    print(f"📊 Total de búsquedas a realizar: {total_busquedas}")
    print("=" * 60)
    
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
        
        for dispositivo in DISPOSITIVOS:
            for condicion in CONDICIONES:
                busqueda_actual += 1
                print(f"\n🔍 Búsqueda {busqueda_actual}/{total_busquedas}: {dispositivo} - {condicion}")
                
                try:
                    # PASO 1: Búsqueda inicial
                    productos_busqueda = await scrape_busqueda_inicial(page, dispositivo, condicion)
                    
                    if productos_busqueda:
                        print(f"✅ Encontrados {len(productos_busqueda)} productos en búsqueda inicial")
                        
                        # PASO 2: Extraer detalles de cada producto
                        for i, producto in enumerate(productos_busqueda):
                            print(f"  🔍 Procesando producto {i+1}/{len(productos_busqueda)}: {producto['nombre'][:50]}...")
                            
                            try:
                                # Extraer detalles del producto
                                producto_con_detalles = await extraer_detalles_producto(page, producto, fecha_scraping)
                                todos_productos.append(producto_con_detalles)
                                
                                # PASO 3: Extraer variaciones si existen
                                variaciones = await extraer_variaciones_producto(page, producto, fecha_scraping)
                                if variaciones:
                                    print(f"    ✅ Encontradas {len(variaciones)} variaciones")
                                    todos_productos.extend(variaciones)
                                else:
                                    print(f"    ⚠️ No se encontraron variaciones")
                                
                                await asyncio.sleep(random.uniform(2.0, 4.0))
                                
                            except Exception as e:
                                print(f"    ❌ Error procesando producto: {str(e)}")
                                producto['fecha_scraping'] = fecha_scraping
                                producto['es_variacion'] = False
                                todos_productos.append(producto)
                                continue
                    else:
                        print(f"⚠️ No se encontraron productos para {dispositivo} ({condicion})")
                    
                    # Delay entre búsquedas
                    if busqueda_actual < total_busquedas:
                        print(f"⏳ Esperando {DELAY_ENTRE_BUSQUEDAS} segundos...")
                        await asyncio.sleep(DELAY_ENTRE_BUSQUEDAS)
                    
                except Exception as e:
                    print(f"❌ Error en búsqueda {dispositivo} ({condicion}): {str(e)}")
                    continue
        
        await browser.close()
    
    # Guardar resultados completos
    if todos_productos:
        df_completo = pd.DataFrame(todos_productos)
        try:
            df_completo.to_excel("resultados_completos.xlsx", index=False)
            print(f"\n🎉 ¡Scraping completo finalizado!")
            print(f"📊 Total de productos (incluyendo variaciones): {len(todos_productos)}")
            print(f"💾 Archivo guardado: resultados_completos.xlsx")
        except PermissionError:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nuevo_archivo = f"resultados_completos_{timestamp}.xlsx"
            df_completo.to_excel(nuevo_archivo, index=False)
            print(f"\n🎉 ¡Scraping completo finalizado!")
            print(f"📊 Total de productos (incluyendo variaciones): {len(todos_productos)}")
            print(f"💾 Archivo guardado: {nuevo_archivo}")
    else:
        print("❌ No se encontraron productos")

async def scrape_busqueda_inicial(page, dispositivo: str, condicion: str) -> List[Dict]:
    """
    PASO 1: Búsqueda inicial de productos
    """
    dispositivo_formateado = dispositivo.lower().replace(" ", "-")
    url = get_url_mercadolibre(dispositivo_formateado, condicion)
    
    print(f"  🔗 URL: {url}")
    
    productos = []
    pagina_actual = 1
    
    while pagina_actual <= MAX_PAGINAS:
        if pagina_actual == 1:
            url_pagina = url
        else:
            url_pagina = f"{url}_Desde_{(pagina_actual-1)*50+1}"
        
        try:
            timeout = random.randint(80000, 100000)
            await page.goto(url_pagina, wait_until="networkidle", timeout=timeout)
            
            try:
                await page.wait_for_selector("a.poly-component__title", timeout=TIMEOUT_PRODUCTOS)
            except:
                try:
                    await page.wait_for_selector("div.poly-card", timeout=10000)
                except:
                    print(f"    ❌ No se encontraron elementos de productos")
                    return []
            
            productos_pagina = await extraer_productos_pagina(page, condicion, dispositivo)
            
            if not productos_pagina:
                break
            
            productos.extend(productos_pagina)
            print(f"    📊 Encontrados {len(productos_pagina)} productos en página {pagina_actual}")
            
            siguiente_btn = await page.query_selector('a[title="Siguiente"]')
            if not siguiente_btn:
                break
            
            pagina_actual += 1
            
        except Exception as e:
            print(f"    ⚠️ Error en página {pagina_actual}: {str(e)}")
            break
    
    return productos

async def extraer_productos_pagina(page, condicion: str, dispositivo: str) -> List[Dict]:
    """Extrae todos los productos de una página"""
    productos = []
    
    elementos_producto = await page.query_selector_all("div.poly-card")
    
    for elemento in elementos_producto:
        try:
            producto = {}
            
            titulo_element = await elemento.query_selector("a.poly-component__title")
            if titulo_element:
                producto['nombre'] = await titulo_element.inner_text()
                producto['url'] = await titulo_element.get_attribute("href")
            else:
                producto['nombre'] = None
                producto['url'] = None
            
            precio_element = await elemento.query_selector("span.andes-money-amount__fraction")
            if precio_element:
                precio_texto = await precio_element.inner_text()
                precio_limpio = re.sub(r'[^\d]', '', precio_texto)
                producto['precio'] = int(precio_limpio) if precio_limpio else None
            else:
                producto['precio'] = None
            
            calificacion_element = await elemento.query_selector("span.poly-reviews__rating")
            if calificacion_element:
                calificacion_texto = await calificacion_element.inner_text()
                match = re.search(r'Calificación\s+(\d+[,.]?\d*)\s+de\s+5', calificacion_texto)
                if match:
                    calificacion = match.group(1).replace(',', '.')
                    producto['calificacion'] = float(calificacion)
                else:
                    numero_match = re.search(r'(\d+[,.]?\d*)', calificacion_texto)
                    if numero_match:
                        calificacion = numero_match.group(1).replace(',', '.')
                        producto['calificacion'] = float(calificacion)
                    else:
                        producto['calificacion'] = None
            else:
                producto['calificacion'] = None
            
            producto['condicion'] = condicion
            producto['dispositivo'] = dispositivo
            
            if producto['nombre'] or producto['precio']:
                productos.append(producto)
                
        except Exception as e:
            continue
    
    return productos

async def extraer_detalles_producto(page, producto: Dict, fecha_scraping: str) -> Dict:
    """
    PASO 2: Extraer detalles del producto
    """
    url = producto['url']
    id_producto = extraer_id_producto(url)
    
    producto['id_producto'] = id_producto
    producto['fecha_scraping'] = fecha_scraping
    producto['es_variacion'] = False
    
    try:
        timeout = random.randint(80000, 100000)
        await page.goto(url, wait_until="networkidle", timeout=timeout)
        
        # Buscar botón de características
        boton_caracteristicas = await page.query_selector('button[data-testid="action-collapsable-target"]')
        
        if boton_caracteristicas:
            await boton_caracteristicas.click()
            await asyncio.sleep(random.uniform(1.5, 3.5))
            
            tabla_memoria = await page.query_selector('div.ui-vpp-striped-specs__table')
            
            if tabla_memoria:
                datos_memoria = await extraer_datos_memoria(page)
                producto.update(datos_memoria)
            
            datos_vendedor = await extraer_datos_vendedor(page)
            producto.update(datos_vendedor)
        
    except Exception as e:
        print(f"    ⚠️ Error extrayendo detalles: {str(e)}")
    
    return producto

async def extraer_variaciones_producto(page, producto: Dict, fecha_scraping: str) -> List[Dict]:
    """
    PASO 3: Extraer variaciones del producto
    """
    variaciones = []
    url = producto['url']
    
    try:
        # Buscar contenedor de variaciones
        contenedor_variaciones = await page.query_selector('div.ui-pdp-variations')
        
        if not contenedor_variaciones:
            return []
        
        pickers = await contenedor_variaciones.query_selector_all('div.ui-pdp-variations__picker')
        
        if not pickers:
            return []
        
        urls_variaciones = set()
        
        for picker in pickers:
            enlaces = await picker.query_selector_all('a[href*="/p/MCO"]')
            
            for enlace in enlaces:
                href = await enlace.get_attribute("href")
                if href and "MCO" in href:
                    if href.startswith("/"):
                        href = f"https://www.mercadolibre.com.co{href}"
                    urls_variaciones.add(href)
        
        # Visitar cada variación
        for url_variacion in urls_variaciones:
            try:
                await page.goto(url_variacion, wait_until="networkidle", timeout=60000)
                await asyncio.sleep(random.uniform(1.0, 2.5))
                
                datos_variacion = await extraer_datos_variacion(page, producto, fecha_scraping, url_variacion)
                variaciones.append(datos_variacion)
                
            except Exception as e:
                print(f"    ❌ Error procesando variación: {str(e)}")
                continue
        
    except Exception as e:
        print(f"    ❌ Error extrayendo variaciones: {str(e)}")
    
    return variaciones

async def extraer_datos_variacion(page, producto_original: Dict, fecha_scraping: str, url_variacion: str) -> Dict:
    """Extrae los datos de una variación específica"""
    datos_variacion = producto_original.copy()
    datos_variacion['url'] = url_variacion  # URL de la variación
    datos_variacion['url_variacion'] = url_variacion
    datos_variacion['fecha_scraping'] = fecha_scraping
    datos_variacion['es_variacion'] = True
    
    # Extraer ID del producto de la URL de la variación
    id_variacion = extraer_id_producto(url_variacion)
    datos_variacion['id_producto'] = id_variacion
    
    try:
        titulo_element = await page.query_selector('h1.ui-pdp-title')
        if titulo_element:
            datos_variacion['nombre'] = await titulo_element.inner_text()
        
        precio_element = await page.query_selector('span.andes-money-amount__fraction')
        if precio_element:
            precio_texto = await precio_element.inner_text()
            precio_limpio = re.sub(r'[^\d]', '', precio_texto)
            datos_variacion['precio'] = int(precio_limpio) if precio_limpio else None
        
        datos_memoria = await extraer_datos_memoria(page)
        datos_variacion.update(datos_memoria)
        
        datos_vendedor = await extraer_datos_vendedor(page)
        datos_variacion.update(datos_vendedor)
        
    except Exception as e:
        print(f"    ⚠️ Error extrayendo datos de variación: {str(e)}")
    
    return datos_variacion

async def extraer_datos_memoria(page) -> Dict:
    """Extrae los datos de memoria de la tabla"""
    datos = {
        'memoria_interna': None,
        'memoria_ram': None,
        'capacidad_maxima_tarjeta': None,
        'ranura_tarjeta_memoria': None
    }
    
    try:
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
        print(f"    ⚠️ Error extrayendo datos de memoria: {str(e)}")
    
    return datos

async def extraer_datos_vendedor(page) -> Dict:
    """Extrae los datos del vendedor"""
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
        print(f"    ⚠️ Error extrayendo datos del vendedor: {str(e)}")
    
    return datos

if __name__ == "__main__":
    print("🚀 Iniciando scraper completo integrado...")
    print("=" * 60)
    
    asyncio.run(scrape_completo()) 