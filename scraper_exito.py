import asyncio
import re
import pandas as pd
import random
import gc
import os
import shutil
from datetime import datetime
from playwright.async_api import async_playwright

# Configuración
DISPOSITIVOS = [
    "samsung galaxy s25 ultra",
    "samsung galaxy s24 ultra", 
    "samsung z flip 6",
    "samsung galaxy a56",
    "samsung galaxy a16"
]
MAX_PAGINAS = 1  # Cambiado de 1 a 2 páginas
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080
TIMEOUT_PRODUCTOS = 5000   # Más agresivo: reducido de 7000 a 5000
DELAY_ENTRE_BUSQUEDAS = 0.5   # Más rápido: reducido de 1 a 0.5
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15"
]

def get_url_exito(dispositivo):
    dispositivo_formateado = dispositivo.replace(" ", "+").upper()
    return f"https://www.exito.com/s?q={dispositivo_formateado}&sort=score_desc&page=0"

async def scrape_exito():
    fecha_scraping = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[INICIANDO] Scraper Exito para {len(DISPOSITIVOS)} dispositivos")
    print("=" * 60)
    
    # Limpiar caché de Playwright al inicio
    await limpiar_cache_playwright()
    
    # Lista para almacenar archivos temporales
    archivos_temporales = []
    
    # Procesar cada dispositivo por separado
    for i, dispositivo in enumerate(DISPOSITIVOS):
        print(f"\n[DEVICE {i+1}/{len(DISPOSITIVOS)}] Procesando: {dispositivo}")
        print("=" * 50)
        
        # Procesar dispositivo individual
        productos_dispositivo = await procesar_dispositivo_individual(dispositivo, fecha_scraping)
        
        if productos_dispositivo:
            # Guardar Excel temporal para este dispositivo
            archivo_temporal = await guardar_excel_temporal(productos_dispositivo, dispositivo, i+1)
            if archivo_temporal:
                archivos_temporales.append(archivo_temporal)
                print(f"[SAVE] Archivo temporal guardado: {archivo_temporal}")
        else:
            print(f"[WARN] No se encontraron productos para {dispositivo}")
        
        # Liberar memoria explícitamente
        await liberar_memoria()
        print(f"[MEMORY] Memoria liberada después de procesar {dispositivo}")
    
    # Combinar todos los archivos Excel al final
    if archivos_temporales:
        print(f"\n[COMBINE] Combinando {len(archivos_temporales)} archivos temporales...")
        archivo_final = await combinar_archivos_excel(archivos_temporales)
        
        if archivo_final:
            print(f"[FINAL] Archivo final creado: {archivo_final}")
            print(f"[INFO] El archivo está listo para ser procesado por el script de Firebase")
        else:
            print("[ERROR] No se pudo crear el archivo final")
    else:
        print("[ERROR] No se encontraron productos para ningún dispositivo")

async def procesar_dispositivo_individual(dispositivo: str, fecha_scraping: str):
    """Procesa un dispositivo individual con su propia instancia de Playwright"""
    productos_dispositivo = []
    
    # Pequeña pausa para evitar sobrecarga del sistema
    await asyncio.sleep(0.1)
    
    async with async_playwright() as p:
        browser = None
        context = None
        page = None
        
        for intento in range(3):
            try:
                user_agent = random.choice(USER_AGENTS)
                print(f"[PC] User-Agent usado: {user_agent}")
                
                # Crear browser con opciones optimizadas
                browser = await p.chromium.launch(
                    headless=True, 
                    args=[
                        f'--user-agent={user_agent}',
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-gpu',
                        '--disable-web-security',
                        '--disable-features=VizDisplayCompositor'
                    ]
                )
                
                # Crear context con configuración optimizada
                context = await browser.new_context(
                    viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
                    user_agent=user_agent
                )
                
                # Crear página
                page = await context.new_page()
                
                print(f"[LUP] Búsqueda: {dispositivo}")
                await asyncio.sleep(random.uniform(0.05, 0.15))
                
                productos_busqueda = await scrape_busqueda_inicial_exito(page, dispositivo)
                if productos_busqueda:
                    print(f"[OK] Encontrados {len(productos_busqueda)} productos en búsqueda inicial")
                    # Procesar productos en lotes para reducir CPU y memoria
                    productos_dispositivo = await procesar_productos_por_lotes_exito(page, productos_busqueda, fecha_scraping)
                else:
                    print(f"[WARN] No se encontraron productos para {dispositivo}")
                
                # Limpieza explícita y ordenada
                if page:
                    await page.close()
                if context:
                    await context.close()
                if browser:
                    await browser.close()
                
                break  # Si llegamos aquí, el procesamiento fue exitoso
                
            except Exception as e:
                print(f"[ERROR] Error en intento {intento + 1} para {dispositivo}: {str(e)}")
                
                # Limpieza en caso de error
                try:
                    if page:
                        await page.close()
                except:
                    pass
                try:
                    if context:
                        await context.close()
                except:
                    pass
                try:
                    if browser:
                        await browser.close()
                except:
                    pass
                
                if intento == 2:  # Último intento
                    print(f"[ERROR] Falló después de 3 intentos para {dispositivo}")
                else:
                    await asyncio.sleep(1)  # Esperar antes del siguiente intento
                continue
    
    return productos_dispositivo

async def guardar_excel_temporal(productos, dispositivo, numero_dispositivo):
    """Guarda un Excel temporal para un dispositivo específico"""
    try:
        print(f"[INFO] Creando DataFrame temporal con {len(productos)} productos...")
        df_temporal = pd.DataFrame(productos)
        print(f"[INFO] DataFrame temporal creado. Columnas: {list(df_temporal.columns)}")
        
        # Crear nombre de archivo temporal
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dispositivo_limpio = dispositivo.replace(" ", "_").replace("+", "_")
        
        if os.path.exists('/app/output'):
            archivo_temporal = f"/app/output/temp_exito_{dispositivo_limpio}_{timestamp}.xlsx"
        else:
            archivo_temporal = f"temp_exito_{dispositivo_limpio}_{timestamp}.xlsx"
        
        print(f"[INFO] Guardando archivo temporal: {archivo_temporal}")
        df_temporal.to_excel(archivo_temporal, index=False)
        
        # Verificar que el archivo se creó
        if os.path.exists(archivo_temporal):
            tamaño = os.path.getsize(archivo_temporal)
            print(f"[OK] Archivo temporal guardado: {archivo_temporal} ({tamaño} bytes)")
            return archivo_temporal
        else:
            print(f"[ERROR] El archivo temporal no se pudo crear: {archivo_temporal}")
            return None
            
    except Exception as e:
        print(f"[ERROR] Error guardando archivo temporal: {e}")
        return None

async def combinar_archivos_excel(archivos_temporales):
    """Combina todos los archivos Excel temporales en uno final"""
    try:
        print(f"[COMBINE] Combinando {len(archivos_temporales)} archivos...")
        todos_dataframes = []
        
        for archivo in archivos_temporales:
            if os.path.exists(archivo):
                df = pd.read_excel(archivo)
                todos_dataframes.append(df)
                print(f"[OK] Cargado: {archivo} ({len(df)} productos)")
            else:
                print(f"[WARN] Archivo no encontrado: {archivo}")
        
        if todos_dataframes:
            # Combinar todos los DataFrames
            df_final = pd.concat(todos_dataframes, ignore_index=True)
            print(f"[INFO] DataFrame final creado con {len(df_final)} productos")
            
            # Guardar archivo final
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if os.path.exists('/app/output'):
                archivo_final = f"/app/output/resultados_exito_final_{timestamp}.xlsx"
            else:
                archivo_final = f"resultados_exito_final_{timestamp}.xlsx"
            
            df_final.to_excel(archivo_final, index=False)
            
            if os.path.exists(archivo_final):
                tamaño = os.path.getsize(archivo_final)
                print(f"[CELEBRATE] ¡Archivo final creado!")
                print(f"[FINAL] Archivo: {archivo_final} ({tamaño} bytes)")
                print(f"[FINAL] Total productos: {len(df_final)}")
                print(f"[FINAL] Ruta completa: {os.path.abspath(archivo_final)}")
                
                # Limpiar archivos temporales
                await limpiar_archivos_temporales(archivos_temporales)
                
                return archivo_final
            else:
                print(f"[ERROR] No se pudo crear el archivo final")
                return None
        else:
            print("[ERROR] No se encontraron DataFrames para combinar")
            return None
            
    except Exception as e:
        print(f"[ERROR] Error combinando archivos: {e}")
        return None

async def limpiar_archivos_temporales(archivos_temporales):
    """Limpia los archivos temporales después de combinar"""
    try:
        print(f"[CLEANUP] Limpiando {len(archivos_temporales)} archivos temporales...")
        for archivo in archivos_temporales:
            if os.path.exists(archivo):
                os.remove(archivo)
                print(f"[CLEAN] Eliminado: {archivo}")
        print("[CLEANUP] Archivos temporales eliminados")
    except Exception as e:
        print(f"[WARN] Error limpiando archivos temporales: {e}")

async def procesar_productos_por_lotes_exito(page, productos_busqueda, fecha_scraping):
    """Procesa productos en lotes para reducir CPU y memoria"""
    productos_dispositivo = []
    TAMANO_LOTE = 4  # Procesar 4 productos por lote
    
    # Dividir productos en lotes
    lotes = [productos_busqueda[i:i + TAMANO_LOTE] for i in range(0, len(productos_busqueda), TAMANO_LOTE)]
    
    print(f"[LOTES] Procesando {len(productos_busqueda)} productos en {len(lotes)} lotes de {TAMANO_LOTE}")
    
    for lote_idx, lote in enumerate(lotes):
        print(f"[LOTE {lote_idx + 1}/{len(lotes)}] Procesando {len(lote)} productos...")
        
        # Procesar productos del lote sin delays individuales
        for i, producto in enumerate(lote):
            print(f"  [LUP] Procesando producto {i+1}/{len(lote)}: {producto['nombre'][:50]}...")
            print(f"    [LINK] URL: {producto['url']}")
            
            try:
                producto_con_detalles = await extraer_detalles_producto_exito(page, producto, fecha_scraping)
                productos_dispositivo.append(producto_con_detalles)
            except Exception as e:
                print(f"    [ERROR] Error procesando producto: {str(e)}")
                producto['fecha_scraping'] = fecha_scraping
                productos_dispositivo.append(producto)
                continue
        
        # Delay solo al final de cada lote (no entre productos individuales)
        if lote_idx < len(lotes) - 1:  # No delay en el último lote
            print(f"[LOTE] Pausa entre lotes...")
            await asyncio.sleep(0.1)  # Pausa solo entre lotes
            
            # Liberar memoria después de cada lote
            gc.collect()
            print(f"[MEMORY] Memoria liberada después del lote {lote_idx + 1}")
    
    print(f"[LOTES] Procesamiento por lotes completado: {len(productos_dispositivo)} productos")
    return productos_dispositivo

async def limpiar_cache_playwright():
    """Limpia el caché de Playwright para evitar errores de sincronización"""
    try:
        cache_paths = [
            "/root/.cache/ms-playwright",
            os.path.expanduser("~/.cache/ms-playwright"),
            "/tmp/ms-playwright"
        ]
        
        for cache_path in cache_paths:
            if os.path.exists(cache_path):
                shutil.rmtree(cache_path)
                print(f"[CACHE] Caché limpiado: {cache_path}")
        
        print("[CACHE] Limpieza de caché de Playwright completada")
        
    except Exception as e:
        print(f"[WARN] Error limpiando caché de Playwright: {e}")

async def liberar_memoria():
    """Libera memoria explícitamente"""
    try:
        # Forzar recolección de basura
        gc.collect()
        print("[MEMORY] Recolección de basura ejecutada")
        
        # Pausa mínima para reducir CPU
        await asyncio.sleep(0.1)  # Reducido de 0.5 a 0.1 para menos CPU
        
    except Exception as e:
        print(f"[WARN] Error liberando memoria: {e}")

async def scrape_busqueda_inicial_exito(page, dispositivo: str):
    url = get_url_exito(dispositivo)
    print(f"  [LINK] URL: {url}")
    productos = []
    pagina_actual = 1
    while pagina_actual <= MAX_PAGINAS:
        if pagina_actual == 1:
            url_pagina = url
        else:
            url_pagina = f"{url}&page={pagina_actual-1}"
        # Reintentos para cada página
        for intento in range(3):
            try:
                timeout = random.randint(3000, 5000)   # Ultra agresivo: reducido de (5000,7000) a (3000,5000)
                print(f"[RELOAD] Intentando cargar página {pagina_actual} (intento {intento + 1}/3)")
                await page.goto(url_pagina, wait_until="domcontentloaded", timeout=timeout)
                # Espera adicional para asegurar carga de JS
                await asyncio.sleep(0.1)  # Ultra agresivo: reducido de 0.2 a 0.1
                
                try:
                    await page.wait_for_selector("article.productCard_productCard__M0677", timeout=TIMEOUT_PRODUCTOS)
                    break  # Si encuentra el selector, salir del bucle de reintentos
                except:
                    if intento == 2:  # Último intento
                        print(f"    [ERROR] No se encontraron elementos de productos después de 3 intentos")
                        # Guardar HTML para depuración
                        html = await page.content()
                        with open(f"debug_exito_{dispositivo.replace(' ','_')}.html", "w", encoding="utf-8") as f:
                            f.write(html)
                        print(f"    [NOTE] HTML guardado para depuración: debug_exito_{dispositivo.replace(' ','_')}.html")
                        return productos
                    else:
                        print(f"     Intento {intento + 1} fallido, reintentando...")
                        await asyncio.sleep(0.05)  # Ultra agresivo: reducido de 0.1 a 0.05
                        continue
                        
            except Exception as e:
                if intento == 2:  # Último intento
                    print(f"     Error en página {pagina_actual} después de 3 intentos: {str(e)}")
                    return productos
                else:
                    print(f"     Error en intento {intento + 1}: {str(e)}, reintentando...")
                    await asyncio.sleep(0.05)  # Ultra agresivo: reducido de 0.1 a 0.05
                    continue
        
        productos_pagina = await extraer_productos_pagina_exito(page, dispositivo)
        if not productos_pagina:
            # Guardar HTML si no se encontraron productos
            html = await page.content()
            with open(f"debug_exito_{dispositivo.replace(' ','_')}_no_productos.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"     HTML guardado para depuración: debug_exito_{dispositivo.replace(' ','_')}_no_productos.html")
            break
        productos.extend(productos_pagina)
        print(f"     Encontrados {len(productos_pagina)} productos en página {pagina_actual}")
        pagina_actual += 1
        await asyncio.sleep(random.uniform(0.2, 0.4))  # Ultra agresivo: reducido de (0.5,1) a (0.2,0.4)
    return productos

async def extraer_productos_pagina_exito(page, dispositivo: str):
    productos = []
    
    # Usar el selector correcto basado en la estructura HTML real
    elementos_producto = await page.query_selector_all("article.productCard_productCard__M0677")
    if not elementos_producto:
        print("     No se encontraron productos con el selector article.productCard_productCard__M0677")
        return productos
    
    print(f"     Encontrados {len(elementos_producto)} elementos de producto")
    
    for elemento in elementos_producto:
        try:
            producto = {}
            
            # Obtener URL del producto
            link_element = await elemento.query_selector("a[data-testid='product-link']")
            if link_element:
                producto['url'] = await link_element.get_attribute("href")
                if producto['url']:
                    if producto['url'].startswith('/'):
                        producto['url'] = f"https://www.exito.com{producto['url']}"
                    elif not producto['url'].startswith('http'):
                        producto['url'] = f"https://www.exito.com/{producto['url']}"
            
            if not producto['url']:
                continue
                
            # Obtener nombre del producto
            titulo_element = await elemento.query_selector("h3.styles_name__qQJiK")
            if titulo_element:
                producto['nombre'] = await titulo_element.inner_text()
            else:
                producto['nombre'] = None
            
            producto['dispositivo'] = dispositivo
            
            if producto['nombre'] and producto['url']:
                productos.append(producto)
                print(f"       Producto encontrado: {producto['nombre'][:50]}...")
            
        except Exception as e:
            print(f"       Error procesando elemento: {str(e)}")
            continue
    
    return productos

async def extraer_detalles_producto_exito(page, producto: dict, fecha_scraping: str):
    url = producto['url']
    producto['fecha_scraping'] = fecha_scraping
    
    # Reintentos para cargar la página del producto
    for intento in range(3):
        try:
            print(f"       Cargando producto (intento {intento + 1}/3)")
            timeout = random.randint(3000, 5000)   # Ultra agresivo: reducido de (5000,7000) a (3000,5000)
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            
            # Espera mínima para reducir CPU
            await asyncio.sleep(0.02)  # Ultra optimizado: reducido de 0.05 a 0.02
            
            # Extraer datos con timeouts individuales
            try:
                precios = await extraer_precios_producto_exito(page)
                producto.update(precios)
            except Exception as e:
                print(f"       Error extrayendo precios: {str(e)}")
            
            try:
                especificaciones = await extraer_especificaciones_exito(page)
                producto.update(especificaciones)
            except Exception as e:
                print(f"       Error extrayendo especificaciones: {str(e)}")
            
            try:
                datos_vendedor = await extraer_datos_vendedor_exito(page)
                producto.update(datos_vendedor)
            except Exception as e:
                print(f"       Error extrayendo datos del vendedor: {str(e)}")
            
            print(f"       Producto procesado exitosamente")
            break  # Si llegamos aquí, el producto se procesó correctamente
            
        except Exception as e:
            if intento == 2:  # Último intento
                print(f"       Error procesando producto después de 3 intentos: {str(e)}")
                # Agregar datos básicos al producto
                producto.update({
                    'precio_promocion': None,
                    'precio_actual': None,
                    'porcentaje_descuento': None,
                    'memoria_interna': None,
                    'memoria_ram': None,
                    'color': None,
                    'modelo': None,
                    'condicion': None,
                    'vendedor': None
                })
            else:
                print(f"       Error en intento {intento + 1}: {str(e)}, reintentando...")
                await asyncio.sleep(0.2)  # Ultra agresivo: reducido de 0.5 a 0.2
                continue
    
    return producto

async def extraer_precios_producto_exito(page):
    precios = {
        'precio_promocion': None,  # Precio tachado
        'precio_actual': None,     # Precio actual
        'porcentaje_descuento': None
    }
    try:
        # Buscar precio promocional (tachado)
        precio_promocion_element = await page.query_selector('p.priceSection_container-promotion_price-dashed__FJ7nI')
        if precio_promocion_element:
            precio_texto = await precio_promocion_element.inner_text()
            precio_limpio = re.sub(r'[^\d]', '', precio_texto)
            precios['precio_promocion'] = int(precio_limpio) if precio_limpio else None
        
        # Buscar precio actual
        precio_actual_element = await page.query_selector('p.ProductPrice_container__price__XmMWA')
        if precio_actual_element:
            precio_texto = await precio_actual_element.inner_text()
            precio_limpio = re.sub(r'[^\d]', '', precio_texto)
            precios['precio_actual'] = int(precio_limpio) if precio_limpio else None
        
        # Calcular porcentaje de descuento si ambos precios existen
        if precios['precio_promocion'] and precios['precio_actual']:
            descuento = ((precios['precio_promocion'] - precios['precio_actual']) / precios['precio_promocion']) * 100
            precios['porcentaje_descuento'] = int(descuento)
            
    except Exception as e:
        print(f"     Error extrayendo precios: {str(e)}")
    return precios

async def extraer_especificaciones_exito(page):
    especificaciones = {
        'memoria_interna': None,
        'memoria_ram': None,
        'color': None,
        'modelo': None,
        'condicion': None
    }
    try:
        # Primero intentar extraer de especificaciones estructuradas
        especificaciones_estructuradas = await extraer_especificaciones_estructuradas_exito(page)
        if especificaciones_estructuradas:
            especificaciones.update(especificaciones_estructuradas)
        
        # Si no se encontraron especificaciones estructuradas, intentar del texto libre
        if not especificaciones['memoria_interna'] and not especificaciones['memoria_ram']:
            especificaciones_texto = await extraer_especificaciones_texto_exito(page)
            if especificaciones_texto:
                especificaciones.update(especificaciones_texto)
        
        # Extraer color del título siempre
        color_titulo = await extraer_color_titulo_exito(page)
        if color_titulo:
            especificaciones['color'] = color_titulo
            
    except Exception as e:
        print(f"     Error extrayendo especificaciones: {str(e)}")
    return especificaciones

async def extraer_especificaciones_estructuradas_exito(page):
    especificaciones = {}
    try:
        # Buscar especificaciones estructuradas
        especificaciones_element = await page.query_selector('div[data-fs-content-specification="true"]')
        if especificaciones_element:
            bloques = await especificaciones_element.query_selector_all('div[data-fs-specification-gray-block="true"], div[data-fs-specification-gray-block="false"]')
            
            for bloque in bloques:
                try:
                    titulo_element = await bloque.query_selector('p[data-fs-title-specification="true"]')
                    valor_element = await bloque.query_selector('p[data-fs-text-specification="true"]')
                    
                    if titulo_element and valor_element:
                        titulo = await titulo_element.inner_text()
                        valor = await valor_element.inner_text()
                        
                        if "Capacidad de almacenamiento" in titulo:
                            especificaciones['memoria_interna'] = valor
                        elif "Memoria del Sistema Ram" in titulo or "Memoria RAM" in titulo:
                            especificaciones['memoria_ram'] = valor
                        elif "Modelo" in titulo:
                            especificaciones['modelo'] = valor
                        elif "Color" in titulo:
                            especificaciones['color'] = valor
                except Exception:
                    continue
                    
    except Exception as e:
        print(f"       Error extrayendo especificaciones estructuradas: {str(e)}")
    return especificaciones

async def extraer_especificaciones_texto_exito(page):
    especificaciones = {}
    try:
        # Buscar la descripción del producto
        descripcion_element = await page.query_selector('div[data-fs-description-container="true"]')
        descripcion_texto = ""
        if descripcion_element:
            descripcion_texto = await descripcion_element.inner_text()
        
        # También buscar en el título del producto
        titulo_element = await page.query_selector('h1')
        titulo_texto = ""
        if titulo_element:
            titulo_texto = await titulo_element.inner_text()
        
        # Combinar texto de descripción y título para búsqueda
        texto_completo = f"{titulo_texto} {descripcion_texto}"
        
        # Múltiples patrones para memoria interna
        patrones_memoria_interna = [
            r'Memoria Interna de (\d+GB)',
            r'Memoria Interna (\d+GB)',
            r'Capacidad de almacenamiento (\d+GB)',
            r'Almacenamiento (\d+GB)',
            r'(\d+GB) de almacenamiento',
            r'(\d+GB) almacenamiento'
        ]
        
        for patron in patrones_memoria_interna:
            match = re.search(patron, texto_completo, re.IGNORECASE)
            if match:
                especificaciones['memoria_interna'] = match.group(1)
                break
        
        # Múltiples patrones para memoria RAM
        patrones_memoria_ram = [
            r'Memoria RAM de (\d+ GB)',
            r'Memoria RAM (\d+GB)',
            r'Memoria RAM (\d+ GB)',
            r'RAM (\d+GB)',
            r'RAM (\d+ GB)',
            r'(\d+GB) RAM',
            r'(\d+ GB) RAM',
            r'Memoria del Sistema Ram (\d+ GB)',
            r'(\d+GB) de RAM',
            r'(\d+ GB) de RAM'
        ]
        
        for patron in patrones_memoria_ram:
            match = re.search(patron, texto_completo, re.IGNORECASE)
            if match:
                especificaciones['memoria_ram'] = match.group(1)
                break
        
        # Múltiples patrones para modelo
        patrones_modelo = [
            r'(S25|S24|S23)',
            r'Galaxy (S25|S24|S23)',
            r'Samsung Galaxy (S25|S24|S23)',
            r'(S25|S24|S23) Ultra',
            r'Galaxy (S25|S24|S23) Ultra'
        ]
        
        for patron in patrones_modelo:
            match = re.search(patron, texto_completo, re.IGNORECASE)
            if match:
                especificaciones['modelo'] = match.group(1)
                break
        
        # El color se extraerá del título del producto en la función extraer_color_titulo_exito
        
        # Condición por defecto
        especificaciones['condicion'] = "Nuevo"
        
        # Debug: imprimir texto encontrado si no se extrajo nada
        if not especificaciones.get('memoria_interna') and not especificaciones.get('memoria_ram'):
            print(f"       Texto encontrado para extracción: {texto_completo[:200]}...")
            
    except Exception as e:
        print(f"       Error extrayendo especificaciones de texto: {str(e)}")
    return especificaciones

async def extraer_color_titulo_exito(page):
    try:
        # Extraer color del título del producto
        titulo_element = await page.query_selector('h1')
        if titulo_element:
            titulo_texto = await titulo_element.inner_text()
            # Buscar cualquier palabra que pueda ser un color en el título
            # Patrones comunes de colores en títulos de productos
            patrones_color = [
                r'\b(Negro|Blanco|Gris|Azul|Dorado|Titanio|Silver|Gold|Violeta|Verde|Rojo|Amarillo|Marrón|Naranja|Rosa|Morado|Cian|Turquesa)\b',
                r'\b(Black|White|Gray|Blue|Gold|Silver|Green|Red|Yellow|Brown|Orange|Pink|Purple|Cyan|Turquoise)\b'
            ]
            
            for patron in patrones_color:
                match = re.search(patron, titulo_texto, re.IGNORECASE)
                if match:
                    return match.group(1)
                    
    except Exception as e:
        print(f"       Error extrayendo color del título: {str(e)}")
    return None

async def extraer_datos_vendedor_exito(page):
    datos = {
        'vendedor': None
    }
    try:
        vendedor_element = await page.query_selector('div[data-fs-product-details-seller__content="true"] a')
        if vendedor_element:
            vendedor_texto = await vendedor_element.inner_text()
            datos['vendedor'] = vendedor_texto.strip()
    except Exception as e:
        print(f"     Error extrayendo datos del vendedor: {str(e)}")
    return datos


if __name__ == "__main__":
    print("[INICIANDO] Scraper Exito...")
    print("=" * 60)
    asyncio.run(scrape_exito()) 