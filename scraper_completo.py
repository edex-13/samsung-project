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
    """
    Extrae el ID del producto de la URL de MercadoLibre
    Maneja diferentes formatos de URL y valida que el ID sea correcto
    """
    if not url:
        return None
    
    # Patrón 1: MCO-12345678901
    match = re.search(r'(MCO-?\d{10,})', url)
    if match:
        id_producto = match.group(1)
        # Asegurar formato consistente
        if id_producto.startswith('MCO-'):
            return id_producto
        else:
            return f"MCO-{id_producto[3:]}"
    
    # Patrón 2: /MCO12345678901
    match2 = re.search(r'/MCO(\d{10,})', url)
    if match2:
        return f"MCO-{match2.group(1)}"
    
    # Patrón 3: /p/MCO12345678901
    match3 = re.search(r'/p/MCO(\d{10,})', url)
    if match3:
        return f"MCO-{match3.group(1)}"
    
    # Patrón 4: /p/MCO-12345678901
    match4 = re.search(r'/p/(MCO-?\d{10,})', url)
    if match4:
        id_producto = match4.group(1)
        if id_producto.startswith('MCO-'):
            return id_producto
        else:
            return f"MCO-{id_producto[3:]}"
    
    return None


def guardar_archivo_dispositivo(dispositivo: str, productos: list, fecha_scraping: str, es_backup: bool = False):
    """Guarda un archivo Excel por dispositivo"""
    if not productos:
        print(f"    ⚠️ No hay productos para guardar del dispositivo {dispositivo}")
        return None
    
    try:
        # Crear nombre de archivo seguro
        nombre_dispositivo = dispositivo.replace(" ", "_").replace("/", "_").lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if es_backup:
            # Para backups: crear carpeta backup si no existe
            import os
            if not os.path.exists("backup"):
                os.makedirs("backup")
            nombre_archivo = f"backup/backup_{nombre_dispositivo}_{timestamp}.xlsx"
        else:
            # Para archivos normales: carpeta principal
            nombre_archivo = f"resultados_{nombre_dispositivo}_{timestamp}.xlsx"
        
        # Crear DataFrame y guardar
        df = pd.DataFrame(productos)
        df.to_excel(nombre_archivo, index=False)
        
        print(f"    💾 Archivo guardado: {nombre_archivo} ({len(productos)} productos)")
        return nombre_archivo
        
    except Exception as e:
        print(f"    ❌ Error guardando archivo para {dispositivo}: {str(e)}")
        return None


async def extraer_precios_producto(page) -> Dict:
    """
    Extrae precios del producto, manejando descuentos
    """
    precios = {
        'precio_actual': None,
        'precio_original': None,
        'porcentaje_descuento': None
    }
    
    try:
        # Buscar precio actual (con descuento si existe) - buscar en la segunda línea
        precio_actual_element = await page.query_selector('div.ui-pdp-price__second-line span.andes-money-amount__fraction')
        if not precio_actual_element:
            # Fallback: buscar cualquier precio principal
            precio_actual_element = await page.query_selector('span.andes-money-amount__fraction[style*="font-size:36"]')
        if not precio_actual_element:
            precio_actual_element = await page.query_selector('span.andes-money-amount__fraction')
        
        if precio_actual_element:
            precio_texto = await precio_actual_element.inner_text()
            precio_limpio = re.sub(r'[^\d]', '', precio_texto)
            precios['precio_actual'] = int(precio_limpio) if precio_limpio else None
        
        # Buscar precio original (tachado) - buscar en el elemento <s>
        precio_original_element = await page.query_selector('s.andes-money-amount__fraction')
        if precio_original_element:
            precio_texto = await precio_original_element.inner_text()
            precio_limpio = re.sub(r'[^\d]', '', precio_texto)
            precios['precio_original'] = int(precio_limpio) if precio_limpio else None
        
        # Buscar porcentaje de descuento
        descuento_element = await page.query_selector('span.andes-money-amount__discount')
        if descuento_element:
            descuento_texto = await descuento_element.inner_text()
            match = re.search(r'(\d+)%', descuento_texto)
            if match:
                precios['porcentaje_descuento'] = int(match.group(1))
        
    except Exception as e:
        print(f"    ⚠️ Error extrayendo precios: {str(e)}")
    return precios

async def scrape_completo():
    """
    Scraper completo que integra búsqueda inicial, detalles y variaciones
    """
    
    todos_productos = []  # Array para productos principales
    todas_variaciones = []  # Array para almacenar todas las variaciones
    productos_procesados = set()  # Para evitar duplicados
    variaciones_recolectadas = set()  # Para evitar duplicados en recolección
    total_busquedas = len(DISPOSITIVOS) * len(CONDICIONES)
    busqueda_actual = 0
    fecha_scraping = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Diccionario para almacenar productos por dispositivo
    productos_por_dispositivo = {}
    for dispositivo in DISPOSITIVOS:
        productos_por_dispositivo[dispositivo] = []
    
    print(f"🚀 Iniciando scraper completo para {len(DISPOSITIVOS)} dispositivos y {len(CONDICIONES)} condiciones")
    print(f"📊 Total de búsquedas a realizar: {total_busquedas}")
    print("🚀 MODO COMPLETO: Procesando todos los productos disponibles")
    print("⏱️ Delays de 10-15 minutos entre modelos y condiciones")
    print("=" * 60)
    
    async with async_playwright() as p:
        user_agent = random.choice(USER_AGENTS)
        viewport_width = random.randint(1200, 1920)
        viewport_height = random.randint(700, 1080)
        print(f"🖥️ User-Agent usado: {user_agent}")
        print(f"🖥️ Viewport: {viewport_width}x{viewport_height}")
        
        # Límites para controlar memoria y tiempo
        MAX_PRODUCTOS_TOTAL = 15
        MAX_VARIACIONES_TOTAL = 200
        productos_procesados_count = 0
        variaciones_procesadas_count = 0
        
        browser = await p.chromium.launch(
            headless=True,
            args=[
                f'--user-agent={user_agent}',
                f'--window-size={viewport_width},{viewport_height}',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--memory-pressure-off',
                '--max_old_space_size=2048',  # Reducido de 4096 a 2048
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection',
                '--disable-extensions',
                '--disable-plugins',
                '--disable-images',  # Deshabilitar imágenes para ahorrar memoria
                '--disable-javascript',  # Deshabilitar JS si no es necesario
                '--disable-css',
                '--disable-fonts',
                '--disable-default-apps',
                '--disable-sync',
                '--disable-translate',
                '--disable-logging',
                '--disable-dev-tools',
                '--disable-component-extensions-with-background-pages',
                '--disable-background-networking',
                '--disable-default-apps',
                '--disable-extensions-except',
                '--disable-plugins-discovery',
                '--disable-hang-monitor',
                '--disable-prompt-on-repost',
                '--disable-domain-reliability',
                '--disable-features=AudioServiceOutOfProcess',
                '--disable-features=VizDisplayCompositor',
                '--disable-features=TranslateUI',
                '--disable-features=BlinkGenPropertyTrees',
                '--disable-features=CalculateNativeWinOcclusion',
                '--disable-features=GlobalMediaControls',
                '--disable-features=MediaRouter',
                '--disable-features=OptimizationHints',
                '--disable-features=PasswordGeneration',
                '--disable-features=PreloadMediaEngagementData',
                '--disable-features=Translate',
                '--disable-features=WebUIDarkMode',
                '--disable-features=WebUIDarkModeV2',
                '--disable-features=WebUIDarkModeV3',
                '--disable-features=WebUIDarkModeV4',
                '--disable-features=WebUIDarkModeV5',
                '--disable-features=WebUIDarkModeV6',
                '--disable-features=WebUIDarkModeV7',
                '--disable-features=WebUIDarkModeV8',
                '--disable-features=WebUIDarkModeV9',
                '--disable-features=WebUIDarkModeV10'
            ]
        )
        
        page = await browser.new_page()
        await page.set_viewport_size({"width": viewport_width, "height": viewport_height})
        
        for dispositivo in DISPOSITIVOS:
            print(f"\n📱 PROCESANDO DISPOSITIVO: {dispositivo}")
            print("=" * 50)
            if busqueda_actual > 1:
                    delay_minutos = random.uniform(7, 15)  # 10-15 minutos entre modelos
                    print(f"⏳ Esperando {delay_minutos:.1f} minutos entre búsquedas...")
                    await asyncio.sleep(delay_minutos * 60)  # Convertir a segundos
                
            for condicion in CONDICIONES:
                busqueda_actual += 1
                print(f"\n🔍 Búsqueda {busqueda_actual}/{total_busquedas}: {dispositivo} - {condicion}")
                
                # Delay entre modelos y condiciones - MODO COMPLETO
                
                # Reintentos para cada búsqueda
                for intento_busqueda in range(3):
                    try:
                        # PASO 1: Búsqueda inicial
                        productos_busqueda = await scrape_busqueda_inicial(page, dispositivo, condicion)
                        
                        if productos_busqueda:
                            print(f"✅ Encontrados {len(productos_busqueda)} productos en búsqueda inicial")
                            
                            # PASO 2: Extraer detalles de cada producto y recolectar variaciones
                            for i, producto in enumerate(productos_busqueda):
                                # Verificar límite de productos
                                if productos_procesados_count >= MAX_PRODUCTOS_TOTAL:
                                    print(f"  ⚠️ Límite de {MAX_PRODUCTOS_TOTAL} productos alcanzado, saltando productos restantes")
                                    break
                                
                                print(f"  🔍 Procesando producto {i+1}/{len(productos_busqueda)} ({productos_procesados_count + 1}/{MAX_PRODUCTOS_TOTAL}): {producto['nombre'][:50]}...")
                                print(f"    🔗 URL: {producto['url']}")
                                
                                # Verificar si ya procesamos este producto - COMENTADO TEMPORALMENTE
                                # id_producto = extraer_id_producto(producto['url'])
                                # if id_producto in productos_procesados:
                                #     print(f"    ⚠️ Producto ya procesado, saltando")
                                #     continue
                                
                                # productos_procesados.add(id_producto)
                                
                                # Delay entre productos individuales - MODO COMPLETO
                                await asyncio.sleep(random.uniform(30, 60))  # 30-60 segundos entre productos
                                
                                try:
                                    # PASO 3: Recolectar variaciones ANTES de extraer detalles
                                    variaciones_producto = await recolectar_variaciones_producto(page, producto, fecha_scraping, variaciones_recolectadas)
                                    if variaciones_producto:
                                        print(f"    ✅ Recolectadas {len(variaciones_producto)} variaciones")
                                        todas_variaciones.extend(variaciones_producto)
                                    else:
                                        print(f"    ⚠️ No se encontraron variaciones")
                                    
                                    # Extraer detalles del producto
                                    producto_con_detalles = await extraer_detalles_producto(page, producto, fecha_scraping)
                                    todos_productos.append(producto_con_detalles)
                                    productos_por_dispositivo[dispositivo].append(producto_con_detalles)
                                    productos_procesados_count += 1
                                    
                                    print(f"    📊 Productos procesados: {productos_procesados_count}/{MAX_PRODUCTOS_TOTAL}")
                                    
                                    # Guardar archivo por dispositivo cada 5 productos (backup de seguridad)
                                    if len(productos_por_dispositivo[dispositivo]) % 5 == 0:
                                        guardar_archivo_dispositivo(dispositivo, productos_por_dispositivo[dispositivo], fecha_scraping, es_backup=True)
                                    
                                    # Delay después de procesar cada producto
                                    # await asyncio.sleep(random.uniform(30, 80))  # 1-1.5 minutos después de cada producto
                                    
                                    # Limpieza de memoria después de cada producto
                                    try:
                                        await page.evaluate("window.gc && window.gc()")
                                    except:
                                        pass
                                    
                                except Exception as e:
                                    print(f"    ❌ Error procesando producto: {str(e)}")
                                    producto['fecha_scraping'] = fecha_scraping
                                    todos_productos.append(producto)
                                    productos_procesados_count += 1
                                    continue
                        else:
                            print(f"⚠️ No se encontraron productos para {dispositivo} ({condicion})")
                        
                        # Delay entre búsquedas
                        if busqueda_actual < total_busquedas:
                            print(f"⏳ Esperando {DELAY_ENTRE_BUSQUEDAS} segundos...")
                            await asyncio.sleep(DELAY_ENTRE_BUSQUEDAS)
                        
                        # Si llegamos aquí, la búsqueda fue exitosa
                        break
                        
                    except Exception as e:
                        print(f"❌ Error en búsqueda {dispositivo} ({condicion}) - intento {intento_busqueda + 1}/3: {str(e)}")
                        if intento_busqueda == 2:  # Último intento
                            print(f"❌ Error en búsqueda {dispositivo} ({condicion}): {str(e)}")
                            continue
                        else:
                            # Reiniciar navegador en caso de error
                            try:
                                await browser.close()
                            except:
                                pass
                            browser = await p.chromium.launch(
                                headless=True,
                                args=[
                                    f'--user-agent={user_agent}',
                                    f'--window-size={viewport_width},{viewport_height}',
                                    '--disable-dev-shm-usage',
                                    '--no-sandbox',
                                    '--disable-setuid-sandbox',
                                    '--disable-gpu',
                                    '--disable-web-security',
                                    '--disable-features=VizDisplayCompositor',
                                    '--memory-pressure-off',
                                    '--max_old_space_size=2048',  # Reducido de 4096 a 2048
                                    '--disable-background-timer-throttling',
                                    '--disable-backgrounding-occluded-windows',
                                    '--disable-renderer-backgrounding',
                                    '--disable-features=TranslateUI',
                                    '--disable-ipc-flooding-protection',
                                    '--disable-extensions',
                                    '--disable-plugins',
                                    '--disable-images',
                                    '--disable-javascript',
                                    '--disable-css',
                                    '--disable-fonts',
                                    '--disable-default-apps',
                                    '--disable-sync',
                                    '--disable-translate',
                                    '--disable-logging',
                                    '--disable-dev-tools',
                                    '--disable-component-extensions-with-background-pages',
                                    '--disable-background-networking',
                                    '--disable-extensions-except',
                                    '--disable-plugins-discovery',
                                    '--disable-hang-monitor',
                                    '--disable-prompt-on-repost',
                                    '--disable-domain-reliability',
                                    '--disable-features=AudioServiceOutOfProcess',
                                    '--disable-features=BlinkGenPropertyTrees',
                                    '--disable-features=CalculateNativeWinOcclusion',
                                    '--disable-features=GlobalMediaControls',
                                    '--disable-features=MediaRouter',
                                    '--disable-features=OptimizationHints',
                                    '--disable-features=PasswordGeneration',
                                    '--disable-features=PreloadMediaEngagementData',
                                    '--disable-features=Translate',
                                    '--disable-features=WebUIDarkMode'
                                ]
                            )
                            page = await browser.new_page()
                            await page.set_viewport_size({"width": viewport_width, "height": viewport_height})
                            await asyncio.sleep(5)  # Esperar antes de reintentar
                productos_procesados_count = 0
            # Guardar archivo del dispositivo al terminar todas sus condiciones
            if productos_por_dispositivo[dispositivo]:
                print(f"\n💾 Guardando archivo del dispositivo {dispositivo}...")
                archivo_guardado = guardar_archivo_dispositivo(dispositivo, productos_por_dispositivo[dispositivo], fecha_scraping)
                if archivo_guardado:
                    print(f"✅ Dispositivo {dispositivo} completado y guardado: {archivo_guardado}")
                else:
                    print(f"❌ Error guardando dispositivo {dispositivo}")
            else:
                print(f"⚠️ No se encontraron productos para el dispositivo {dispositivo}")
            
            print(f"📱 DISPOSITIVO {dispositivo} COMPLETADO")
            print("=" * 50)
        
        # PASO4Procesar todas las variaciones recolectadas
        if todas_variaciones:
            print(f"\n🔄 Procesando {len(todas_variaciones)} variaciones recolectadas...")
            
            for i, variacion in enumerate(todas_variaciones):
                # Verificar límite de variaciones
                
                print(f"  🔍 Procesando variación {i+1}/{len(todas_variaciones)} ({variaciones_procesadas_count + 1}/{MAX_VARIACIONES_TOTAL})")
                print(f"    🔗 URL: {variacion['url']}")
                
                # Verificar si ya procesamos esta variación - COMENTADO TEMPORALMENTE
                # id_variacion = extraer_id_producto(variacion['url'])
                # if id_variacion in productos_procesados:
                #     print(f"    ⚠️ Variación ya procesada, saltando")
                #     continue
                
                # productos_procesados.add(id_variacion)
                
                # Delay entre variaciones - MODO COMPLETO
                await asyncio.sleep(random.uniform(60, 90))  # 1-1.5 minutos entre variaciones
                
                try:
                    # Procesar variación como producto completamente independiente
                    variacion_procesada = await procesar_variacion_completa(page, variacion, fecha_scraping)
                    todos_productos.append(variacion_procesada)
                    variaciones_procesadas_count += 1
                    
                    print(f"    📊 Variaciones procesadas: {variaciones_procesadas_count}/{MAX_VARIACIONES_TOTAL}")
                    
                    # Delay después de procesar cada variación - MODO COMPLETO
                    await asyncio.sleep(random.uniform(60, 90))  # 1-1.5 minutos después de cada variación
                    
                except Exception as e:
                    print(f"    ❌ Error procesando variación: {str(e)}")
                    variacion['fecha_scraping'] = fecha_scraping
                    variacion['es_variacion'] = True
                    todos_productos.append(variacion)
                    variaciones_procesadas_count += 1
                    continue
        
        await browser.close()
    
    # Guardar archivos por dispositivo
    print(f"\n💾 Guardando archivos por dispositivo...")
    archivos_guardados = []
    
    for dispositivo, productos_dispositivo in productos_por_dispositivo.items():
        if productos_dispositivo:
            archivo_guardado = guardar_archivo_dispositivo(dispositivo, productos_dispositivo, fecha_scraping)
            if archivo_guardado:
                archivos_guardados.append(archivo_guardado)
    
    # Guardar resultados completos
    if todos_productos:
        df_completo = pd.DataFrame(todos_productos)
        try:
            df_completo.to_excel("resultados_completos.xlsx", index=False)
            print(f"\n🎉 ¡Scraping completo finalizado!")
            print(f"📊 Total de productos (incluyendo variaciones): {len(todos_productos)}")
            print(f"💾 Archivo completo guardado: resultados_completos.xlsx")
            print(f"📁 Archivos por dispositivo guardados: {len(archivos_guardados)}")
        except PermissionError:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nuevo_archivo = f"resultados_completos_{timestamp}.xlsx"
            df_completo.to_excel(nuevo_archivo, index=False)
            print(f"\n🎉 ¡Scraping completo finalizado!")
            print(f"📊 Total de productos (incluyendo variaciones): {len(todos_productos)}")
            print(f"💾 Archivo completo guardado: {nuevo_archivo}")
            print(f"📁 Archivos por dispositivo guardados: {len(archivos_guardados)}")
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
            timeout = random.randint(60000, 120000)  # Aumentado a 1-2 minutos
            await page.goto(url_pagina, wait_until="networkidle", timeout=timeout)
            
            try:
                await page.wait_for_selector("a.poly-component__title", timeout=TIMEOUT_PRODUCTOS)
            except:
                try:
                    await page.wait_for_selector("div.poly-card", timeout=10000)
                except:
                    print(f"    ❌ No se encontraron elementos de productos")
                    break
            
            productos_pagina = await extraer_productos_pagina(page, condicion, dispositivo)
            
            if not productos_pagina:
                break
            
            productos.extend(productos_pagina)
            print(f"    📊 Encontrados {len(productos_pagina)} productos en página {pagina_actual}")
            
            siguiente_btn = await page.query_selector('a[title="Siguiente"]')
            if not siguiente_btn:
                break
            
            # Delay aleatorio entre páginas - MODO COMPLETO
            await asyncio.sleep(random.uniform(5.0, 10.0))
            pagina_actual += 1
            
        except Exception as e:
            print(f"    ❌ Error en página {pagina_actual}: {str(e)}")
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
    
    try:
        timeout = random.randint(60000, 120000)  # Aumentado a 1-2 minutos
        await page.goto(url, wait_until="networkidle", timeout=timeout)
        
        # Extraer precios actualizados
        precios = await extraer_precios_producto(page)
        producto.update(precios)
        
        # Buscar botón de características
        boton_caracteristicas = await page.query_selector('button[data-testid="action-collapsable-target"]')
        
        if boton_caracteristicas:
            await boton_caracteristicas.click()
            await asyncio.sleep(random.uniform(3.0, 6.0))  # Aumentado para modo completo
            
            tabla_memoria = await page.query_selector('div.ui-vpp-striped-specs__table')
            
            if tabla_memoria:
                datos_memoria = await extraer_datos_memoria(page)
                producto.update(datos_memoria)
            
            datos_vendedor = await extraer_datos_vendedor(page)
            producto.update(datos_vendedor)
        
    except Exception as e:
        print(f"    ⚠️ Error extrayendo detalles: {str(e)}")
    
    return producto

async def recolectar_variaciones_producto(page, producto: Dict, fecha_scraping: str, variaciones_recolectadas: set) -> List[Dict]:
    """
    PASO 3: Extraer variaciones del producto (sin procesarlas)
    """
    variaciones = []
    url = producto['url']
    try:
        await asyncio.sleep(3.0)
        contenedor_variaciones = await page.query_selector('div.ui-pdp-variations')
        if not contenedor_variaciones:
            print(f"    ⚠️ No se encontró contenedor de variaciones")
            return []
        enlaces = await contenedor_variaciones.query_selector_all('a[href*="/p/MCO"]')
        if not enlaces:
            enlaces = await contenedor_variaciones.query_selector_all('a[href*=MCO]')
        print(f"    🔍 Encontrados {len(enlaces)} enlaces de variaciones")
        if len(enlaces) == 1:
            print(f"    ⚠️ Solo se encontró una variación")
            return []

        urls_variaciones = set()
        for enlace in enlaces:
            href = await enlace.get_attribute("href")
            if href and "MCO" in href:
                if href.startswith("/"):
                    href = f"https://www.mercadolibre.com.co{href}"
                urls_variaciones.add(href)
                print(f"    🔗 URL variación: {href}")
        # Crear objetos de variación SOLO con la URL (sin filtrar por ID)
        for url_variacion in urls_variaciones:
            variacion = {
                'url': url_variacion,
                'fecha_scraping': fecha_scraping,
                'es_variacion': True
            }
            variaciones.append(variacion)

        print(f"    ✅ Recolectadas {len(variaciones)} variaciones válidas")
    except Exception as e:
        print(f"    ❌ Error recolectando variaciones: {str(e)}")
    return variaciones

async def procesar_variacion_completa(page, variacion: Dict, fecha_scraping: str) -> Dict:
    """
    Procesa una variación completa, extrayendo todos los datos desde cero
    """
    url = variacion['url']
    id_variacion = extraer_id_producto(url)
    
    print(f"    🔗 URL de la variación: {url}")
    
    try:
        # Reducir timeout y usar domcontentloaded en lugar de networkidle
        timeout = random.randint(60000, 90000)  # Aumentado a 1-1.5 minutos para modo completo
        await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        
        # Espera adicional - MODO COMPLETO
        await asyncio.sleep(random.uniform(3.0, 6.0))
        
        # Extraer datos básicos del producto
        nombre_element = await page.query_selector('h1.ui-pdp-title')
        if nombre_element:
            variacion['nombre'] = await nombre_element.inner_text()
        
        # Extraer precios actualizados
        precios = await extraer_precios_producto(page)
        variacion.update(precios)
        
        # Extraer calificación si existe
        calificacion_element = await page.query_selector('span.ui-pdp-review__rating')
        if calificacion_element:
            calificacion_texto = await calificacion_element.inner_text()
            match = re.search(r'(\d+[,.]?\d*)', calificacion_texto)
            if match:
                calificacion = match.group(1).replace(',', '.')
                variacion['calificacion'] = float(calificacion)
        
        # Establecer condición por defecto como "nuevo"
        variacion['condicion'] = "nuevo"
        # Extraer dispositivo del nombre si es posible
        if 'nombre' in variacion and variacion['nombre']:
            nombre = variacion['nombre'].lower()
            if 's24ultra' in nombre:
                variacion['dispositivo'] = "samsung galaxy s24 ultra 5g"
            elif 's24e' in nombre:
                variacion['dispositivo'] = "samsung galaxy s24"
            else:
                variacion['dispositivo'] = "samsung galaxy s24 5g defecto"
        
        # Buscar botón de características con timeout más corto
        try:
            boton_caracteristicas = await page.query_selector('button[data-testid="action-collapsable-target"]')
            
            if boton_caracteristicas:
                print(f"    🔍 Extrayendo características de la variación...")
                await boton_caracteristicas.click()
                await asyncio.sleep(random.uniform(3.0, 6.0))  # Aumentado para modo completo
                
                tabla_memoria = await page.query_selector('div.ui-vpp-striped-specs__table')
                
                if tabla_memoria:
                    print(f"    📊 Extrayendo datos de memoria y especificaciones...")
                    datos_memoria = await extraer_datos_memoria(page)
                    variacion.update(datos_memoria)
                    print(f"    ✅ Datos de memoria extraídos: {datos_memoria}")
                
                print(f"    👤 Extrayendo datos del vendedor...")
                datos_vendedor = await extraer_datos_vendedor(page)
                variacion.update(datos_vendedor)
                print(f"    ✅ Datos del vendedor extraídos: {datos_vendedor}")
            else:
                print(f"    ⚠️ No se encontró botón de características")
        except Exception as e:
            print(f"    ⚠️ Error extrayendo características: {str(e)}")
        
        # Asegurar que tenga el ID del producto
        variacion['id_producto'] = id_variacion
        
        return variacion
        
    except Exception as e:
        print(f"    ❌ Error procesando variación completa: {str(e)}")
        variacion['fecha_scraping'] = fecha_scraping
        variacion['condicion'] = "nuevo"  # Por defecto
        variacion['dispositivo'] = "samsung galaxy s24 5g"  # Por defecto
        return variacion

async def extraer_datos_memoria(page) -> Dict:
    """Extrae los datos de memoria y color de la tabla"""
    datos = {
        'memoria_interna': None,
        'memoria_ram': None,
        'capacidad_maxima_tarjeta': None,
        'ranura_tarjeta_memoria': None,
        'color': None
    }
    
    try:
        filas = await page.query_selector_all('tr.andes-table__row')
        print(f"        📋 Procesando {len(filas)} filas de especificaciones...")
        
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
                    elif "Color" in encabezado:
                        datos['color'] = valor
                        
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