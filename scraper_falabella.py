import asyncio
import re
import pandas as pd
import random
import gc
import os
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
MAX_PAGINAS = 1
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080
TIMEOUT_PRODUCTOS = 8000   # Aumentado para permitir carga completa de JS
DELAY_ENTRE_BUSQUEDAS = 0.5   # Ultra agresivo: reducido de 1 a 0.5
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15"
]

def get_url_falabella(dispositivo):
    dispositivo_formateado = dispositivo.replace(" ", "+")
    return f"https://linio.falabella.com.co/linio-co/search?Ntt=celular+{dispositivo_formateado}&f.product.L2_category_paths=cat50868%7C%7CTecnolog%C3%ADa%2Fcat910963%7C%7CTelefon%C3%ADa%2Fcat1660941%7C%7CCelulares+y+Tel%C3%A9fonos"

async def scrape_busqueda_inicial_falabella(page, dispositivo: str):
    url = get_url_falabella(dispositivo)
    print(f"  🔗 URL: {url}")
    productos = []
    pagina_actual = 1
    while pagina_actual <= MAX_PAGINAS:
        if pagina_actual == 1:
            url_pagina = url
        else:
            url_pagina = f"{url}&page={pagina_actual}"
        # Reintentos para cada página
        for intento in range(3):
            try:
                timeout = random.randint(5000, 8000)   # Aumentado para permitir carga completa
                print(f"🔄 Intentando cargar página {pagina_actual} (intento {intento + 1}/3)")
                await page.goto(url_pagina, wait_until="networkidle", timeout=timeout)
                # Espera adicional para asegurar carga de JS
                await asyncio.sleep(1.0)  # Aumentado para permitir carga completa de elementos dinámicos
                
                try:
                    # Intentar esperar por múltiples selectores de productos
                    selectores_espera = [
                        "a[data-pod]",
                        ".pod-item",
                        ".search-results-list .pod",
                        "[data-testid*='product']"
                    ]
                    
                    elemento_encontrado = False
                    for selector in selectores_espera:
                        try:
                            await page.wait_for_selector(selector, timeout=TIMEOUT_PRODUCTOS//len(selectores_espera))
                            elemento_encontrado = True
                            break
                        except:
                            continue
                    
                    if elemento_encontrado:
                        break  # Si encuentra algún selector, salir del bucle de reintentos
                    else:
                        raise Exception("No se encontraron elementos de productos")
                except:
                    if intento == 2:  # Último intento
                        print(f"    ❌ No se encontraron elementos de productos después de 3 intentos")
                        # Guardar HTML para depuración
                        html = await page.content()
                        with open(f"debug_falabella_{dispositivo.replace(' ','_')}.html", "w", encoding="utf-8") as f:
                            f.write(html)
                        print(f"    📝 HTML guardado para depuración: debug_falabella_{dispositivo.replace(' ','_')}.html")
                        return productos
                    else:
                        print(f"    ⚠️ Intento {intento + 1} fallido, reintentando...")
                        await asyncio.sleep(0.05)  # Ultra agresivo: reducido de 0.1 a 0.05
                        continue
                        
            except Exception as e:
                if intento == 2:  # Último intento
                    print(f"    ❌ Error en página {pagina_actual} después de 3 intentos: {str(e)}")
                    return productos
                else:
                    print(f"    ⚠️ Error en intento {intento + 1}: {str(e)}, reintentando...")
                    await asyncio.sleep(0.2)  # Ultra agresivo: reducido de 0.5 a 0.2
                    continue
        
        productos_pagina = await extraer_productos_pagina_falabella(page, dispositivo)
        if not productos_pagina:
            # Guardar HTML si no se encontraron productos
            html = await page.content()
            with open(f"debug_falabella_{dispositivo.replace(' ','_')}_no_productos.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"    📝 HTML guardado para depuración: debug_falabella_{dispositivo.replace(' ','_')}_no_productos.html")
            break
        productos.extend(productos_pagina)
        print(f"    📊 Encontrados {len(productos_pagina)} productos en página {pagina_actual}")
        pagina_actual += 1
        await asyncio.sleep(random.uniform(0.05, 0.15))  # Ultra agresivo: reducido de (0.1,0.3) a (0.05,0.15)
    return productos

async def extraer_productos_pagina_falabella(page, dispositivo: str):
    productos = []
    
    # Intentar múltiples selectores para encontrar productos
    selectores_productos = [
        "a[data-pod]",
        ".pod-item",
        ".search-results-list .pod",
        "[data-testid*='product']",
        ".product-item"
    ]
    
    elementos_producto = []
    for selector in selectores_productos:
        elementos = await page.query_selector_all(selector)
        if elementos:
            elementos_producto = elementos
            print(f"    🔍 Encontrados {len(elementos_producto)} elementos con selector: {selector}")
            break
    
    if not elementos_producto:
        print("    ⚠️ No se encontraron productos con ningún selector")
        return productos
    
    for elemento in elementos_producto:
        try:
            producto = {}
            
            # Obtener URL del producto
            producto['url'] = await elemento.get_attribute("href")
            if not producto['url']:
                continue
                
            # Asegurar que la URL sea completa
            if producto['url'].startswith('/'):
                producto['url'] = f"https://www.falabella.com.co{producto['url']}"
            elif not producto['url'].startswith('http'):
                producto['url'] = f"https://www.falabella.com.co/{producto['url']}"      
            # Obtener nombre del producto usando múltiples selectores
            selectores_titulo = [
                '#testId-pod-displaySubTitle-140706748',
                '.pod-subTitle',
                '.pod-title',
                '[data-testid*="title"]',
                '.product-title',
                'h3',
                'h4',
                '.title',
                'a[title]'
            ]
            
            producto['nombre'] = None
            for selector in selectores_titulo:
                titulo_element = await elemento.query_selector(selector)
                if titulo_element:
                    try:
                        nombre_texto = await titulo_element.inner_text()
                        if nombre_texto and nombre_texto.strip():
                            producto['nombre'] = nombre_texto.strip()
                            break
                    except:
                        continue
            
            # Si no se encontró con selectores, intentar obtener el atributo title
            if not producto['nombre']:
                try:
                    titulo_attr = await elemento.get_attribute('title')
                    if titulo_attr and titulo_attr.strip():
                        producto['nombre'] = titulo_attr.strip()
                except:
                    pass
            
            producto['dispositivo'] = dispositivo
            
            if producto['nombre'] and producto['url']:
                productos.append(producto)
                print(f"      ✅ Producto encontrado: {producto['nombre'][:50]}...")
            
        except Exception as e:
            print(f"      ⚠️ Error procesando elemento: {str(e)}")
            continue
    
    return productos

async def extraer_detalles_producto_falabella(page, producto: dict, fecha_scraping: str):
    url = producto['url']
    producto['fecha_scraping'] = fecha_scraping
    
    # Reintentos para cargar la página del producto
    for intento in range(3):
        try:
            print(f"🔄 Cargando producto (intento {intento + 1}/3)")
            timeout = random.randint(5000, 8000)   # Aumentado para permitir carga completa
            await page.goto(url, wait_until="networkidle", timeout=timeout)
            
            # Espera para permitir carga completa de elementos dinámicos
            await asyncio.sleep(0.5)  # Aumentado para permitir carga completa
            
            # Extraer datos con timeouts individuales
            try:
                precios = await extraer_precios_producto_falabella(page)
                producto.update(precios)
            except Exception as e:
                print(f"      ⚠️ Error extrayendo precios: {str(e)}")
            
            try:
                especificaciones = await extraer_especificaciones_falabella(page)
                producto.update(especificaciones)
            except Exception as e:
                print(f"      ⚠️ Error extrayendo especificaciones: {str(e)}")
            
            try:
                datos_vendedor = await extraer_datos_vendedor_falabella(page)
                producto.update(datos_vendedor)
            except Exception as e:
                print(f"      ⚠️ Error extrayendo datos del vendedor: {str(e)}")
            
            print(f"      ✅ Producto procesado exitosamente")
            break  # Si llegamos aquí, el producto se procesó correctamente
            
        except Exception as e:
            if intento == 2:  # Último intento
                print(f"      ❌ Error procesando producto después de 3intentos: {str(e)}")
                # Agregar datos básicos al producto
                producto.update({
                    'precio_tarjeta_falabella': None,
                    'precio_descuento': None,
                    'precio_normal': None,
                    'porcentaje_descuento': None,
                    'memoria_interna': None,
                    'memoria_ram': None,
                    'color': None,
                    'modelo': None,
                    'condicion': None,
                    'vendedor': None
                })
            else:
                print(f"⚠️ Error en intento {intento + 1}: {str(e)}, reintentando...")
                await asyncio.sleep(0.2)  # Ultra agresivo: reducido de 0.5 a 0.2
                continue
    
    return producto

async def extraer_precios_producto_falabella(page):
    precios = {
        'precio_tarjeta_falabella': None,  # data-cmr-price (más bajo)
        'precio_descuento': None,          # data-event-price (intermedio)
        'precio_normal': None,              # data-normal-price (original tachado)
        'porcentaje_descuento': None
    }
    try:
        # Buscar precio con tarjeta Falabella (data-cmr-price) - el más bajo
        precio_tarjeta_element = await page.query_selector('li[data-cmr-price] span')
        if precio_tarjeta_element:
            precio_texto = await precio_tarjeta_element.inner_text()
            precio_limpio = re.sub(r'[^\d]', '', precio_texto)
            precios['precio_tarjeta_falabella'] = int(precio_limpio) if precio_limpio else None
        
        # Buscar precio con descuento (data-event-price) - precio intermedio
        precio_descuento_element = await page.query_selector('li[data-event-price] span')
        if precio_descuento_element:
            precio_texto = await precio_descuento_element.inner_text()
            precio_limpio = re.sub(r'[^\d]', '', precio_texto)
            precios['precio_descuento'] = int(precio_limpio) if precio_limpio else None
        
        # Buscar precio normal (data-normal-price) - precio original tachado
        precio_normal_element = await page.query_selector('li[data-normal-price] span')
        if precio_normal_element:
            precio_texto = await precio_normal_element.inner_text()
            precio_limpio = re.sub(r'[^\d]', '', precio_texto)
            precios['precio_normal'] = int(precio_limpio) if precio_limpio else None
        
        # Buscar porcentaje de descuento
        descuento_element = await page.query_selector('.discount-badge-item')
        if descuento_element:
            descuento_texto = await descuento_element.inner_text()
            match = re.search(r'(\d+)%', descuento_texto)
            if match:
                precios['porcentaje_descuento'] = int(match.group(1))
            else:
                # Buscar el signo negativo
                match = re.search(r'-(\d+)%', descuento_texto)
                if match:
                    precios['porcentaje_descuento'] = int(match.group(1))
    except Exception as e:
        print(f"    ⚠️ Error extrayendo precios: {str(e)}")
    return precios

async def extraer_especificaciones_falabella(page):
    especificaciones = {
        'memoria_interna': None,
        'memoria_ram': None,
        'color': None,
        'modelo': None,
        'condicion': None
    }
    try:
        boton_ver_mas = await page.query_selector('button#swatch-collapsed-id')
        if boton_ver_mas:
            await boton_ver_mas.click()
            await asyncio.sleep(random.uniform(0.05, 0.15))  # Ultra agresivo: reducido de (0.1,0.3) a (0.05,0.15)
        filas = await page.query_selector_all('table.specification-table tr')
        for fila in filas:
            try:
                nombre_element = await fila.query_selector('td.property-name')
                valor_element = await fila.query_selector('td.property-value')
                if nombre_element and valor_element:
                    nombre = await nombre_element.inner_text()
                    valor = await valor_element.inner_text()
                    if "Capacidad de almacenamiento" in nombre:
                        especificaciones['memoria_interna'] = valor
                    elif "Memoria RAM" in nombre:
                        especificaciones['memoria_ram'] = valor
                    elif "Modelo" in nombre:
                        especificaciones['modelo'] = valor
                    elif "Condición del producto" in nombre:
                        especificaciones['condicion'] = valor
                    elif "Color" in nombre:
                        especificaciones['color'] = valor
            except Exception:
                continue
    except Exception as e:
        print(f"    ⚠️ Error extrayendo especificaciones: {str(e)}")
    return especificaciones

async def extraer_datos_vendedor_falabella(page):
    datos = {
        'vendedor': None
    }
    try:
        vendedor_element = await page.query_selector('#testId-SellerInfo-sellerName')
        if vendedor_element:
            vendedor_texto = await vendedor_element.inner_text()
            datos['vendedor'] = vendedor_texto.strip()
    except Exception as e:
        print(f"    ⚠️ Error extrayendo datos del vendedor: {str(e)}")
    return datos

async def scrape_falabella():
    fecha_scraping = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🚀 Iniciando scraper Falabella/Linio para {len(DISPOSITIVOS)} dispositivos")
    print("=" * 60)
    
    # Lista para almacenar archivos temporales
    archivos_temporales = []
    
    # Procesar cada dispositivo por separado
    for i, dispositivo in enumerate(DISPOSITIVOS):
        print(f"\n[DEVICE {i+1}/{len(DISPOSITIVOS)}] Procesando: {dispositivo}")
        print("=" * 50)
        
        # Procesar dispositivo individual
        productos_dispositivo = await procesar_dispositivo_individual_falabella(dispositivo, fecha_scraping)
        
        if productos_dispositivo:
            # Guardar Excel temporal para este dispositivo
            archivo_temporal = await guardar_excel_temporal_falabella(productos_dispositivo, dispositivo, i+1)
            if archivo_temporal:
                archivos_temporales.append(archivo_temporal)
                print(f"[SAVE] Archivo temporal guardado: {archivo_temporal}")
        else:
            print(f"[WARN] No se encontraron productos para {dispositivo}")
        
        # Liberar memoria explícitamente
        await liberar_memoria_falabella()
        print(f"[MEMORY] Memoria liberada después de procesar {dispositivo}")
    
    # Combinar todos los archivos Excel al final
    if archivos_temporales:
        print(f"\n[COMBINE] Combinando {len(archivos_temporales)} archivos temporales...")
        archivo_final = await combinar_archivos_excel_falabella(archivos_temporales)
        
        if archivo_final:
            print(f"[FINAL] Archivo final creado: {archivo_final}")
            print(f"[INFO] El archivo está listo para ser procesado por el script de Firebase")
        else:
            print("[ERROR] No se pudo crear el archivo final")
    else:
        print("[ERROR] No se encontraron productos para ningún dispositivo")

async def procesar_dispositivo_individual_falabella(dispositivo: str, fecha_scraping: str):
    """Procesa un dispositivo individual con su propia instancia de Playwright"""
    productos_dispositivo = []
    
    # Pequeña pausa para evitar sobrecarga del sistema
    await asyncio.sleep(0.1)
    
    async with async_playwright() as p:
        for intento in range(3):
            try:
                user_agent = random.choice(USER_AGENTS)
                print(f"🖥️ User-Agent usado: {user_agent}")
                browser = await p.chromium.launch(headless=True, args=[f'--user-agent={user_agent}'])
                page = await browser.new_page()
                await page.set_viewport_size({"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})
                
                print(f"🔍 Búsqueda: {dispositivo}")
                await asyncio.sleep(random.uniform(0.05, 0.15))
                
                productos_busqueda = await scrape_busqueda_inicial_falabella(page, dispositivo)
                if productos_busqueda:
                    print(f"✅ Encontrados {len(productos_busqueda)} productos en búsqueda inicial")
                    # Procesar productos en lotes para reducir CPU y memoria
                    productos_dispositivo = await procesar_productos_por_lotes_falabella(page, productos_busqueda, fecha_scraping)
                else:
                    print(f"⚠️ No se encontraron productos para {dispositivo}")
                
                await browser.close()
                break  # Si llegamos aquí, el procesamiento fue exitoso
                
            except Exception as e:
                print(f"❌ Error en intento {intento + 1} para {dispositivo}: {str(e)}")
                if intento == 2:  # Último intento
                    print(f"❌ Falló después de 3 intentos para {dispositivo}")
                else:
                    await asyncio.sleep(1)  # Esperar antes del siguiente intento
                continue
    
    return productos_dispositivo

async def guardar_excel_temporal_falabella(productos, dispositivo, numero_dispositivo):
    """Guarda un Excel temporal para un dispositivo específico"""
    try:
        print(f"[INFO] Creando DataFrame temporal con {len(productos)} productos...")
        df_temporal = pd.DataFrame(productos)
        print(f"[INFO] DataFrame temporal creado. Columnas: {list(df_temporal.columns)}")
        
        # Crear nombre de archivo temporal
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dispositivo_limpio = dispositivo.replace(" ", "_").replace("+", "_")
        
        if os.path.exists('/app/output'):
            archivo_temporal = f"/app/output/temp_falabella_{dispositivo_limpio}_{timestamp}.xlsx"
        else:
            archivo_temporal = f"temp_falabella_{dispositivo_limpio}_{timestamp}.xlsx"
        
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

async def combinar_archivos_excel_falabella(archivos_temporales):
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
                archivo_final = f"/app/output/resultados_falabella_final_{timestamp}.xlsx"
            else:
                archivo_final = f"resultados_falabella_final_{timestamp}.xlsx"
            
            df_final.to_excel(archivo_final, index=False)
            
            if os.path.exists(archivo_final):
                tamaño = os.path.getsize(archivo_final)
                print(f"🎉 ¡Archivo final creado!")
                print(f"[FINAL] Archivo: {archivo_final} ({tamaño} bytes)")
                print(f"[FINAL] Total productos: {len(df_final)}")
                print(f"[FINAL] Ruta completa: {os.path.abspath(archivo_final)}")
                
                # Limpiar archivos temporales
                await limpiar_archivos_temporales_falabella(archivos_temporales)
                
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

async def limpiar_archivos_temporales_falabella(archivos_temporales):
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

async def procesar_productos_por_lotes_falabella(page, productos_busqueda, fecha_scraping):
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
            print(f"  🔍 Procesando producto {i+1}/{len(lote)}: {producto['nombre'][:50]}...")
            print(f"    🔗 URL: {producto['url']}")
            
            try:
                producto_con_detalles = await extraer_detalles_producto_falabella(page, producto, fecha_scraping)
                productos_dispositivo.append(producto_con_detalles)
            except Exception as e:
                print(f"    ❌ Error procesando producto: {str(e)}")
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

async def liberar_memoria_falabella():
    """Libera memoria explícitamente"""
    try:
        # Forzar recolección de basura
        gc.collect()
        print("[MEMORY] Recolección de basura ejecutada")
        
        # Pausa mínima para reducir CPU
        await asyncio.sleep(0.1)  # Reducido de 0.5 a 0.1 para menos CPU
        
    except Exception as e:
        print(f"[WARN] Error liberando memoria: {e}")

if __name__ == "__main__":
    print("[INICIANDO] Scraper Falabella/Linio...")
    print("=" * 60)
    asyncio.run(scrape_falabella()) 