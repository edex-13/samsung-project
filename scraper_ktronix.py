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
MAX_PAGINAS = 1
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080
TIMEOUT_PRODUCTOS = 8000
DELAY_ENTRE_BUSQUEDAS = 0.5
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4_0) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15"
]

# Configuración específica de Ktronix
KTRONIX_CONFIG = {
    "base_url": "https://www.ktronix.com",
    "search_url": "https://www.ktronix.com/celulares/smartphones/celulares-samsung/c/BI_M017_KTRON?sort=relevance&q=%3Arelevance%3Afamilias-celulares%3A{query}",
    "listing": {
        "container": "li.product__item",
        "link": "a.product__item__top__link",
        "title": "h3.product__item__top__title",
        "price": ".product__item__information__price .price",
        "features": ".product__item__information__key-features--list li.item"
    },
    "product_page": {
        "price_main": "#js-original_price, .price-ktronix .price",
        "specs_container": ".new-container__table__classifications___type__item",
        "spec_name": ".new-container__table__classifications___type__item_feature",
        "spec_value": ".new-container__table__classifications___type__item_result",
        "benefits": ".badges_item_text"
    },
    "defaults": {
        "seller": "Ktronix"
    }
}

def get_url_ktronix(dispositivo):
    # URLs específicas para cada dispositivo
    urls_dispositivos = {
        "samsung galaxy s25 ultra": "https://www.ktronix.com/celulares/smartphones/celulares-samsung/c/BI_M017_KTRON?sort=relevance&q=%3Arelevance%3Afamilias-celulares%3AGalaxy%20S25%20Ultra",
        "samsung galaxy s24 ultra": "https://www.ktronix.com/celulares/smartphones/celulares-samsung/c/BI_M017_KTRON?sort=relevance&q=%3Arelevance%3Afamilias-celulares%3AGalaxy%20S24%20Ultra",
        "samsung z flip 6": "https://www.ktronix.com/celulares/smartphones/celulares-samsung/c/BI_M017_KTRON?sort=relevance&q=%3Arelevance%3Afamilias-celulares%3AGalaxyZ%20Flip7",
        "samsung galaxy a56": "https://www.ktronix.com/celulares/smartphones/celulares-samsung/c/BI_M017_KTRON?sort=relevance&q=%3Arelevance%3Afamilias-celulares%3AGalaxy%20A56",
        "samsung galaxy a16": "https://www.ktronix.com/celulares/smartphones/celulares-samsung/c/BI_M017_KTRON?sort=relevance&q=%3Arelevance%3Afamilias-celulares%3AGalaxy%20A16"
    }
    
    return urls_dispositivos.get(dispositivo.lower(), urls_dispositivos["samsung galaxy s25 ultra"])

async def scrape_busqueda_inicial_ktronix(page, dispositivo: str):
    url = get_url_ktronix(dispositivo)
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
                timeout = random.randint(5000, 8000)
                print(f"🔄 Intentando cargar página {pagina_actual} (intento {intento + 1}/3)")
                await page.goto(url_pagina, wait_until="networkidle", timeout=timeout)
                # Espera adicional para asegurar carga de JS
                await asyncio.sleep(1.0)
                
                try:
                    # Intentar esperar por el contenedor de productos
                    await page.wait_for_selector(KTRONIX_CONFIG["listing"]["container"], timeout=TIMEOUT_PRODUCTOS)
                    break  # Si encuentra el selector, salir del bucle de reintentos
                except:
                    if intento == 2:  # Último intento
                        print(f"    ❌ No se encontraron elementos de productos después de 3 intentos")
                        # Guardar HTML para depuración
                        html = await page.content()
                        with open(f"debug_ktronix_{dispositivo.replace(' ','_')}.html", "w", encoding="utf-8") as f:
                            f.write(html)
                        print(f"    📝 HTML guardado para depuración: debug_ktronix_{dispositivo.replace(' ','_')}.html")
                        return productos
                    else:
                        print(f"    ⚠️ Intento {intento + 1} fallido, reintentando...")
                        await asyncio.sleep(0.05)
                        continue
                        
            except Exception as e:
                if intento == 2:  # Último intento
                    print(f"    ❌ Error en página {pagina_actual} después de 3 intentos: {str(e)}")
                    return productos
                else:
                    print(f"    ⚠️ Error en intento {intento + 1}: {str(e)}, reintentando...")
                    await asyncio.sleep(0.2)
                    continue
        
        productos_pagina = await extraer_productos_pagina_ktronix(page, dispositivo)
        if not productos_pagina:
            # Guardar HTML si no se encontraron productos
            html = await page.content()
            with open(f"debug_ktronix_{dispositivo.replace(' ','_')}_no_productos.html", "w", encoding="utf-8") as f:
                f.write(html)
            print(f"    📝 HTML guardado para depuración: debug_ktronix_{dispositivo.replace(' ','_')}_no_productos.html")
            break
        productos.extend(productos_pagina)
        print(f"    📊 Encontrados {len(productos_pagina)} productos en página {pagina_actual}")
        pagina_actual += 1
        await asyncio.sleep(random.uniform(0.05, 0.15))
    return productos

async def extraer_productos_pagina_ktronix(page, dispositivo: str):
    productos = []
    
    # Usar el selector de contenedor de productos de Ktronix
    elementos_producto = await page.query_selector_all(KTRONIX_CONFIG["listing"]["container"])
    
    if not elementos_producto:
        print("    ⚠️ No se encontraron productos con el selector de Ktronix")
        return productos
    
    print(f"    🔍 Encontrados {len(elementos_producto)} elementos de producto")
    
    for elemento in elementos_producto:
        try:
            producto = {}
            
            # Obtener URL del producto usando el selector de Ktronix
            link_element = await elemento.query_selector(KTRONIX_CONFIG["listing"]["link"])
            if link_element:
                producto['url'] = await link_element.get_attribute("href")
                if producto['url']:
                    if producto['url'].startswith('/'):
                        producto['url'] = f"{KTRONIX_CONFIG['base_url']}{producto['url']}"
                    elif not producto['url'].startswith('http'):
                        producto['url'] = f"{KTRONIX_CONFIG['base_url']}/{producto['url']}"
            
            if not producto['url']:
                continue
                
            # Obtener nombre del producto usando el selector de Ktronix
            titulo_element = await elemento.query_selector(KTRONIX_CONFIG["listing"]["title"])
            if titulo_element:
                producto['nombre'] = await titulo_element.inner_text()
            else:
                producto['nombre'] = None
            
            # Obtener precio del listado si está disponible
            precio_element = await elemento.query_selector(KTRONIX_CONFIG["listing"]["price"])
            if precio_element:
                precio_texto = await precio_element.inner_text()
                precio_limpio = re.sub(r'[^\d]', '', precio_texto)
                producto['precio_listado'] = int(precio_limpio) if precio_limpio else None
            else:
                producto['precio_listado'] = None
            
            producto['dispositivo'] = dispositivo
            producto['vendedor'] = KTRONIX_CONFIG["defaults"]["seller"]
            
            if producto['nombre'] and producto['url']:
                productos.append(producto)
                print(f"      ✅ Producto encontrado: {producto['nombre'][:50]}...")
            
        except Exception as e:
            print(f"      ⚠️ Error procesando elemento: {str(e)}")
            continue
    
    return productos

async def extraer_detalles_producto_ktronix(page, producto: dict, fecha_scraping: str):
    url = producto['url']
    producto['fecha_scraping'] = fecha_scraping
    
    # Reintentos para cargar la página del producto
    for intento in range(3):
        try:
            print(f"🔄 Cargando producto (intento {intento + 1}/3)")
            
            # Timeout progresivo
            timeouts = [10000, 15000, 20000]
            timeout = timeouts[intento]
            
            # Estrategia de carga múltiple
            carga_exitosa = False
            
            # Método 1: domcontentloaded (más rápido)
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                await asyncio.sleep(0.5)
                carga_exitosa = True
                print(f"    ✅ Carga exitosa con domcontentloaded")
            except Exception as e1:
                print(f"    ⚠️ domcontentloaded falló: {str(e1)[:50]}...")
                
                # Método 2: networkidle (más lento pero más completo)
                try:
                    await page.goto(url, wait_until="networkidle", timeout=timeout)
                    await asyncio.sleep(0.3)
                    carga_exitosa = True
                    print(f"    ✅ Carga exitosa con networkidle")
                except Exception as e2:
                    print(f"    ⚠️ networkidle falló: {str(e2)[:50]}...")
                    
                    # Método 3: load (fallback básico)
                    try:
                        await page.goto(url, wait_until="load", timeout=timeout)
                        await asyncio.sleep(0.5)
                        carga_exitosa = True
                        print(f"    ✅ Carga exitosa con load")
                    except Exception as e3:
                        print(f"    ❌ Todos los métodos de carga fallaron")
                        raise e3
            
            if not carga_exitosa:
                raise Exception("No se pudo cargar la página con ningún método")
            
            # Extraer datos con timeouts individuales
            try:
                precios = await extraer_precios_producto_ktronix(page)
                producto.update(precios)
            except Exception as e:
                print(f"      ⚠️ Error extrayendo precios: {str(e)}")
            
            try:
                especificaciones = await extraer_especificaciones_ktronix(page)
                producto.update(especificaciones)
            except Exception as e:
                print(f"      ⚠️ Error extrayendo especificaciones: {str(e)}")
            
            print(f"      ✅ Producto procesado exitosamente")
            break  # Si llegamos aquí, el producto se procesó correctamente
            
        except Exception as e:
            if intento == 2:  # Último intento
                print(f"      ❌ Error procesando producto después de 3 intentos: {str(e)}")
                print(f"      🔄 Intentando extracción básica sin cargar página completa...")
                
                # Estrategia de fallback: intentar extraer datos básicos sin carga completa
                try:
                    # Intentar cargar solo el HTML básico
                    await page.goto(url, wait_until="domcontentloaded", timeout=5000)
                    await asyncio.sleep(0.2)
                    
                    # Intentar extraer solo precios básicos
                    try:
                        precios_basicos = await extraer_precios_basicos_ktronix(page)
                        producto.update(precios_basicos)
                        print(f"      ✅ Datos básicos extraídos exitosamente")
                    except:
                        print(f"      ⚠️ No se pudieron extraer datos básicos")
                    
                except:
                    print(f"      ❌ Fallback también falló")
                
                # Agregar datos básicos al producto
                producto.update({
                    'precio_ktronix': producto.get('precio_ktronix'),
                    'precio_descuento': producto.get('precio_descuento'),
                    'precio_normal': producto.get('precio_normal'),
                    'porcentaje_descuento': producto.get('porcentaje_descuento'),
                    'memoria_interna': None,
                    'memoria_ram': None,
                    'color': None,
                    'modelo': None,
                    'condicion': None,
                    'vendedor': KTRONIX_CONFIG["defaults"]["seller"]
                })
            else:
                print(f"⚠️ Error en intento {intento + 1}: {str(e)}, reintentando...")
                await asyncio.sleep(0.5)
                continue
    
    return producto

async def extraer_precios_producto_ktronix(page):
    precios = {
        'precio_ktronix': None,      # Precio principal
        'precio_descuento': None,    # Precio con descuento
        'precio_normal': None,       # Precio original tachado
        'porcentaje_descuento': None
    }
    try:
        # Buscar precio principal usando los selectores de Ktronix
        precio_main_element = await page.query_selector(KTRONIX_CONFIG["product_page"]["price_main"])
        if precio_main_element:
            precio_texto = await precio_main_element.inner_text()
            precio_limpio = re.sub(r'[^\d]', '', precio_texto)
            precios['precio_ktronix'] = int(precio_limpio) if precio_limpio else None
        
        # Buscar precio tachado (precio original)
        precio_tachado_selectors = [
            '.price-original',
            '.price-before',
            '.old-price',
            '.price-tachado',
            '.price-crossed'
        ]
        
        for selector in precio_tachado_selectors:
            precio_element = await page.query_selector(selector)
            if precio_element:
                precio_texto = await precio_element.inner_text()
                precio_limpio = re.sub(r'[^\d]', '', precio_texto)
                if precio_limpio:
                    precios['precio_normal'] = int(precio_limpio)
                    break
        
        # Buscar precio con descuento
        precio_descuento_selectors = [
            '.price-discount',
            '.price-sale',
            '.price-promo',
            '.price-offer'
        ]
        
        for selector in precio_descuento_selectors:
            precio_element = await page.query_selector(selector)
            if precio_element:
                precio_texto = await precio_element.inner_text()
                precio_limpio = re.sub(r'[^\d]', '', precio_texto)
                if precio_limpio:
                    precios['precio_descuento'] = int(precio_limpio)
                    break
        
        # Calcular porcentaje de descuento si tenemos ambos precios
        if precios['precio_normal'] and precios['precio_ktronix']:
            descuento = ((precios['precio_normal'] - precios['precio_ktronix']) / precios['precio_normal']) * 100
            precios['porcentaje_descuento'] = int(descuento)
        
        # Buscar porcentaje de descuento en badges o elementos especiales
        badges_element = await page.query_selector(KTRONIX_CONFIG["product_page"]["benefits"])
        if badges_element:
            badges_texto = await badges_element.inner_text()
            match = re.search(r'(\d+)%', badges_texto)
            if match:
                precios['porcentaje_descuento'] = int(match.group(1))
            
    except Exception as e:
        print(f"    ⚠️ Error extrayendo precios: {str(e)}")
    return precios

async def extraer_precios_basicos_ktronix(page):
    """Extrae precios básicos con timeouts más cortos para páginas problemáticas"""
    precios = {
        'precio_ktronix': None,
        'precio_descuento': None,
        'precio_normal': None,
        'porcentaje_descuento': None
    }
    try:
        # Buscar precios con timeouts más cortos
        selectores_precio = [
            (KTRONIX_CONFIG["product_page"]["price_main"], 'precio_ktronix'),
            ('.price-discount', 'precio_descuento'),
            ('.price-original', 'precio_normal'),
            (KTRONIX_CONFIG["product_page"]["benefits"], 'porcentaje_descuento')
        ]
        
        for selector, campo in selectores_precio:
            try:
                elemento = await page.query_selector(selector)
                if elemento:
                    texto = await elemento.inner_text()
                    if campo == 'porcentaje_descuento':
                        match = re.search(r'(\d+)%', texto)
                        if match:
                            precios[campo] = int(match.group(1))
                    else:
                        precio_limpio = re.sub(r'[^\d]', '', texto)
                        if precio_limpio:
                            precios[campo] = int(precio_limpio)
            except:
                continue
                
    except Exception as e:
        print(f"    ⚠️ Error extrayendo precios básicos: {str(e)}")
    return precios

async def extraer_especificaciones_ktronix(page):
    especificaciones = {
        'memoria_interna': None,
        'memoria_ram': None,
        'color': None,
        'modelo': None,
        'condicion': None
    }
    try:
        # Buscar especificaciones usando los selectores de Ktronix
        specs_elements = await page.query_selector_all(KTRONIX_CONFIG["product_page"]["specs_container"])
        
        for spec_element in specs_elements:
            try:
                # Nombre de la característica
                nombre_element = await spec_element.query_selector(KTRONIX_CONFIG["product_page"]["spec_name"])
                # Valor de la característica
                valor_element = await spec_element.query_selector(KTRONIX_CONFIG["product_page"]["spec_value"])
                
                if nombre_element and valor_element:
                    nombre = await nombre_element.inner_text()
                    valor = await valor_element.inner_text()
                    
                    # Mapear características específicas
                    if "Capacidad de almacenamiento" in nombre or "Memoria interna" in nombre or "Almacenamiento" in nombre:
                        especificaciones['memoria_interna'] = valor
                    elif "Memoria RAM" in nombre or "RAM" in nombre or "Memoria del sistema" in nombre:
                        especificaciones['memoria_ram'] = valor
                    elif "Modelo" in nombre or "Versión" in nombre:
                        especificaciones['modelo'] = valor
                    elif "Color" in nombre or "Colores" in nombre:
                        especificaciones['color'] = valor
                    elif "Condición" in nombre or "Estado" in nombre:
                        especificaciones['condicion'] = valor
                        
            except Exception:
                continue
        
        # Si no se encontraron especificaciones estructuradas, intentar extraer del título
        if not any(especificaciones.values()):
            titulo_element = await page.query_selector('h1')
            if titulo_element:
                titulo_texto = await titulo_element.inner_text()
                especificaciones_texto = await extraer_especificaciones_texto_ktronix(titulo_texto)
                especificaciones.update(especificaciones_texto)
        
        # Condición por defecto
        if not especificaciones['condicion']:
            especificaciones['condicion'] = "Nuevo"
            
    except Exception as e:
        print(f"    ⚠️ Error extrayendo especificaciones: {str(e)}")
    return especificaciones

async def extraer_especificaciones_texto_ktronix(titulo_texto):
    """Extrae especificaciones del texto del título cuando no hay especificaciones estructuradas"""
    especificaciones = {}
    try:
        titulo_normalizado = titulo_texto.lower()
        
        # Patrones para memoria interna
        patrones_memoria_interna = [
            r'(\d+)\s*gb\s*(?!ram)',
            r'(\d+)\s*tb',
            r'(\d+)gb\s*(?!ram)',
            r'(\d+)tb'
        ]
        
        for patron in patrones_memoria_interna:
            match = re.search(patron, titulo_normalizado)
            if match:
                valor = int(match.group(1))
                if valor >= 32:  # Filtrar valores que probablemente son memoria interna
                    especificaciones['memoria_interna'] = f"{valor} GB"
                    break
        
        # Patrones para memoria RAM
        patrones_memoria_ram = [
            r'(\d+)\s*gb\s*ram',
            r'(\d+)\s*ram',
            r'ram\s*(\d+)\s*gb',
            r'(\d+)gb\s*ram',
            r'ram\s*(\d+)gb'
        ]
        
        for patron in patrones_memoria_ram:
            match = re.search(patron, titulo_normalizado)
            if match:
                especificaciones['memoria_ram'] = f"{match.group(1)} GB"
                break
        
        # Patrones para modelo
        patrones_modelo = [
            r'(s25|s24|s23|s22|s21)',
            r'galaxy\s+(s25|s24|s23|s22|s21)',
            r'samsung\s+galaxy\s+(s25|s24|s23|s22|s21)',
            r'(a56|a54|a34|a16)',
            r'galaxy\s+(a56|a54|a34|a16)',
            r'(z\s*flip\s*6|z\s*flip\s*5|z\s*flip\s*4)',
            r'galaxy\s+(z\s*flip\s*6|z\s*flip\s*5|z\s*flip\s*4)'
        ]
        
        for patron in patrones_modelo:
            match = re.search(patron, titulo_normalizado)
            if match:
                especificaciones['modelo'] = match.group(1).upper()
                break
        
        # Patrones para color
        colores_comunes = [
            "negro", "blanco", "gris", "azul", "rojo", "verde", "amarillo", "rosa", "morado",
            "dorado", "plateado", "bronce", "titanio", "grafito", "crema", "beige"
        ]
        
        for color in colores_comunes:
            if color in titulo_normalizado:
                especificaciones['color'] = color.capitalize()
                break
        
    except Exception as e:
        print(f"    ⚠️ Error extrayendo especificaciones del texto: {str(e)}")
    return especificaciones

async def scrape_ktronix():
    fecha_scraping = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🚀 Iniciando scraper Ktronix para {len(DISPOSITIVOS)} dispositivos")
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
        productos_dispositivo = await procesar_dispositivo_individual_ktronix(dispositivo, fecha_scraping)
        
        if productos_dispositivo:
            # Guardar Excel temporal para este dispositivo
            archivo_temporal = await guardar_excel_temporal_ktronix(productos_dispositivo, dispositivo, i+1)
            if archivo_temporal:
                archivos_temporales.append(archivo_temporal)
                print(f"[SAVE] Archivo temporal guardado: {archivo_temporal}")
        else:
            print(f"[WARN] No se encontraron productos para {dispositivo}")
        
        # Liberar memoria explícitamente
        await liberar_memoria_ktronix()
        print(f"[MEMORY] Memoria liberada después de procesar {dispositivo}")
    
    # Combinar todos los archivos Excel al final
    if archivos_temporales:
        print(f"\n[COMBINE] Combinando {len(archivos_temporales)} archivos temporales...")
        archivo_final = await combinar_archivos_excel_ktronix(archivos_temporales)
        
        if archivo_final:
            print(f"[FINAL] Archivo final creado: {archivo_final}")
            print(f"[INFO] El archivo está listo para ser procesado por el script de Firebase")
        else:
            print("[ERROR] No se pudo crear el archivo final")
    else:
        print("[ERROR] No se encontraron productos para ningún dispositivo")

async def procesar_dispositivo_individual_ktronix(dispositivo: str, fecha_scraping: str):
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
                print(f"🖥️ User-Agent usado: {user_agent}")
                
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
                
                print(f"🔍 Búsqueda: {dispositivo}")
                await asyncio.sleep(random.uniform(0.05, 0.15))
                
                productos_busqueda = await scrape_busqueda_inicial_ktronix(page, dispositivo)
                if productos_busqueda:
                    print(f"✅ Encontrados {len(productos_busqueda)} productos en búsqueda inicial")
                    # Procesar productos en lotes para reducir CPU y memoria
                    productos_dispositivo = await procesar_productos_por_lotes_ktronix(page, productos_busqueda, fecha_scraping)
                else:
                    print(f"⚠️ No se encontraron productos para {dispositivo}")
                
                # Limpieza explícita y ordenada
                if page:
                    await page.close()
                if context:
                    await context.close()
                if browser:
                    await browser.close()
                
                break  # Si llegamos aquí, el procesamiento fue exitoso
                
            except Exception as e:
                print(f"❌ Error en intento {intento + 1} para {dispositivo}: {str(e)}")
                
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
                    print(f"❌ Falló después de 3 intentos para {dispositivo}")
                else:
                    await asyncio.sleep(1)  # Esperar antes del siguiente intento
                continue
    
    return productos_dispositivo

async def guardar_excel_temporal_ktronix(productos, dispositivo, numero_dispositivo):
    """Guarda un Excel temporal para un dispositivo específico"""
    try:
        print(f"[INFO] Creando DataFrame temporal con {len(productos)} productos...")
        df_temporal = pd.DataFrame(productos)
        print(f"[INFO] DataFrame temporal creado. Columnas: {list(df_temporal.columns)}")
        
        # Crear nombre de archivo temporal
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dispositivo_limpio = dispositivo.replace(" ", "_").replace("+", "_")
        
        if os.path.exists('/app/output'):
            archivo_temporal = f"/app/output/temp_ktronix_{dispositivo_limpio}_{timestamp}.xlsx"
        else:
            archivo_temporal = f"temp_ktronix_{dispositivo_limpio}_{timestamp}.xlsx"
        
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

async def combinar_archivos_excel_ktronix(archivos_temporales):
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
                archivo_final = f"/app/output/resultados_ktronix_final_{timestamp}.xlsx"
            else:
                archivo_final = f"resultados_ktronix_final_{timestamp}.xlsx"
            
            df_final.to_excel(archivo_final, index=False)
            
            if os.path.exists(archivo_final):
                tamaño = os.path.getsize(archivo_final)
                print(f"🎉 ¡Archivo final creado!")
                print(f"[FINAL] Archivo: {archivo_final} ({tamaño} bytes)")
                print(f"[FINAL] Total productos: {len(df_final)}")
                print(f"[FINAL] Ruta completa: {os.path.abspath(archivo_final)}")
                
                # Limpiar archivos temporales
                await limpiar_archivos_temporales_ktronix(archivos_temporales)
                
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

async def limpiar_archivos_temporales_ktronix(archivos_temporales):
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

async def procesar_productos_por_lotes_ktronix(page, productos_busqueda, fecha_scraping):
    """Procesa productos en lotes para reducir CPU y memoria"""
    productos_dispositivo = []
    TAMANO_LOTE = 4  # Procesar 4 productos por lote
    fallos_consecutivos = 0
    MAX_FALLOS_CONSECUTIVOS = 3  # Saltar lote si hay muchos fallos seguidos
    
    # Dividir productos en lotes
    lotes = [productos_busqueda[i:i + TAMANO_LOTE] for i in range(0, len(productos_busqueda), TAMANO_LOTE)]
    
    print(f"[LOTES] Procesando {len(productos_busqueda)} productos en {len(lotes)} lotes de {TAMANO_LOTE}")
    
    for lote_idx, lote in enumerate(lotes):
        print(f"[LOTE {lote_idx + 1}/{len(lotes)}] Procesando {len(lote)} productos...")
        
        # Verificar si hay demasiados fallos consecutivos
        if fallos_consecutivos >= MAX_FALLOS_CONSECUTIVOS:
            print(f"[SKIP] Demasiados fallos consecutivos ({fallos_consecutivos}), saltando lote...")
            fallos_consecutivos = 0  # Resetear contador
            continue
        
        fallos_lote = 0
        
        # Procesar productos del lote sin delays individuales
        for i, producto in enumerate(lote):
            print(f"  🔍 Procesando producto {i+1}/{len(lote)}: {producto['nombre'][:50]}...")
            print(f"    🔗 URL: {producto['url']}")
            
            try:
                producto_con_detalles = await extraer_detalles_producto_ktronix(page, producto, fecha_scraping)
                productos_dispositivo.append(producto_con_detalles)
                fallos_consecutivos = 0  # Resetear contador de fallos
            except Exception as e:
                print(f"    ❌ Error procesando producto: {str(e)}")
                producto['fecha_scraping'] = fecha_scraping
                productos_dispositivo.append(producto)
                fallos_lote += 1
                fallos_consecutivos += 1
                continue
        
        # Actualizar contador de fallos consecutivos
        if fallos_lote == len(lote):
            print(f"[WARN] Todos los productos del lote fallaron")
        else:
            fallos_consecutivos = 0  # Resetear si al menos uno funcionó
        
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

async def liberar_memoria_ktronix():
    """Libera memoria explícitamente"""
    try:
        # Forzar recolección de basura
        gc.collect()
        print("[MEMORY] Recolección de basura ejecutada")
        
        # Pausa mínima para reducir CPU
        await asyncio.sleep(0.1)
        
    except Exception as e:
        print(f"[WARN] Error liberando memoria: {e}")

if __name__ == "__main__":
    print("[INICIANDO] Scraper Ktronix...")
    print("=" * 60)
    asyncio.run(scrape_ktronix())
