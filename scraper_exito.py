import asyncio
import re
import pandas as pd
import random
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
TIMEOUT_PRODUCTOS = 7000   # Agresivo pero estable: equilibrio perfecto
DELAY_ENTRE_BUSQUEDAS = 1   # Mantener rápido
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
    todos_productos = []
    fecha_scraping = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[INICIANDO] Scraper Exito para {len(DISPOSITIVOS)} dispositivos")
    print("=" * 60)
    async with async_playwright() as p:
        for intento in range(3):
            user_agent = random.choice(USER_AGENTS)
            print(f"[PC] User-Agent usado: {user_agent}")
            browser = await p.chromium.launch(headless=True, args=[f'--user-agent={user_agent}'])
            page = await browser.new_page()
            await page.set_viewport_size({"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})
            exito = False
            for dispositivo in DISPOSITIVOS:
                print(f"\n[LUP] Búsqueda: {dispositivo}")
                await asyncio.sleep(random.uniform(0.1, 0.3))  # Súper agresivo: reducido de (0.5,1) a (0.1,0.3)
                try:
                    productos_busqueda = await scrape_busqueda_inicial_exito(page, dispositivo)
                    if productos_busqueda:
                        exito = True
                        print(f"[OK] Encontrados {len(productos_busqueda)} productos en búsqueda inicial")
                        for i, producto in enumerate(productos_busqueda):
                            print(f"  [LUP] Procesando producto {i+1}/{len(productos_busqueda)}: {producto['nombre'][:50]}...")
                            print(f"    [LINK] URL: {producto['url']}")
                            await asyncio.sleep(random.uniform(0.1, 0.3))  # Súper agresivo: reducido de (0.5,1) a (0.1,0.3)
                            try:
                                producto_con_detalles = await extraer_detalles_producto_exito(page, producto, fecha_scraping)
                                todos_productos.append(producto_con_detalles)
                                await asyncio.sleep(random.uniform(0.1, 0.3))  # Súper agresivo: reducido de (0.5,1) a (0.1,0.3)
                            except Exception as e:
                                print(f"    [ERROR] Error procesando producto: {str(e)}")
                                producto['fecha_scraping'] = fecha_scraping
                                todos_productos.append(producto)
                                continue
                    else:
                        print(f"[WARN] No se encontraron productos para {dispositivo}")
                    print(f"[WAIT] Esperando {DELAY_ENTRE_BUSQUEDAS} segundos...")
                    await asyncio.sleep(DELAY_ENTRE_BUSQUEDAS)
                except Exception as e:
                    print(f"[ERROR] Error en búsqueda {dispositivo}: {str(e)}")
                    continue
            await browser.close()
            if exito:
                break

    print(f"\n[INFO] Finalizando scraper. Productos encontrados: {len(todos_productos)}")
    
    if todos_productos:
        try:
            print(f"[INFO] Creando DataFrame con {len(todos_productos)} productos...")
            df_completo = pd.DataFrame(todos_productos)
            print(f"[INFO] DataFrame creado exitosamente. Columnas: {list(df_completo.columns)}")
            
            # Intentar guardar con nombre por defecto (en directorio montado si es Docker)
            import os
            if os.path.exists('/app/output'):
                nombre_archivo = "/app/output/resultados_exito.xlsx"
            else:
                nombre_archivo = "resultados_exito.xlsx"
            print(f"[INFO] Intentando guardar archivo: {nombre_archivo}")
            df_completo.to_excel(nombre_archivo, index=False)
            
            # Verificar que el archivo se creó
            import os
            if os.path.exists(nombre_archivo):
                tamaño = os.path.getsize(nombre_archivo)
                print(f"\n[CELEBRATE] ¡Scraping Éxito finalizado!")
                print(f"[CHART] Total de productos: {len(todos_productos)}")
                print(f"[SAVE] Archivo guardado: {nombre_archivo} ({tamaño} bytes)")
                print(f"[INFO] Ruta completa: {os.path.abspath(nombre_archivo)}")
            else:
                print(f"[ERROR] El archivo no se pudo crear: {nombre_archivo}")
                
        except PermissionError as e:
            print(f"[WARN] Error de permisos: {e}")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if os.path.exists('/app/output'):
                nuevo_archivo = f"/app/output/resultados_exito_{timestamp}.xlsx"
            else:
                nuevo_archivo = f"resultados_exito_{timestamp}.xlsx"
            print(f"[INFO] Intentando con nuevo nombre: {nuevo_archivo}")
            df_completo.to_excel(nuevo_archivo, index=False)
            
            import os
            if os.path.exists(nuevo_archivo):
                tamaño = os.path.getsize(nuevo_archivo)
                print(f"\n[CELEBRATE] ¡Scraping Éxito finalizado!")
                print(f"[CHART] Total de productos: {len(todos_productos)}")
                print(f"[SAVE] Archivo guardado: {nuevo_archivo} ({tamaño} bytes)")
                print(f"[INFO] Ruta completa: {os.path.abspath(nuevo_archivo)}")
            else:
                print(f"[ERROR] El archivo no se pudo crear: {nuevo_archivo}")
                
        except Exception as e:
            print(f"[ERROR] Error inesperado guardando archivo: {e}")
            print(f"[INFO] Tipo de error: {type(e)}")
            # Guardar como CSV alternativo
            try:
                if os.path.exists('/app/output'):
                    nombre_csv = f"/app/output/resultados_exito_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                else:
                    nombre_csv = f"resultados_exito_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                df_completo.to_csv(nombre_csv, index=False)
                print(f"[INFO] Guardado como CSV alternativo: {nombre_csv}")
            except:
                print(f"[ERROR] Tampoco se pudo guardar como CSV")
    else:
        print("[ERROR] No se encontraron productos para guardar")

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
                timeout = random.randint(5000, 7000)   # Agresivo pero estable
                print(f"[RELOAD] Intentando cargar página {pagina_actual} (intento {intento + 1}/3)")
                await page.goto(url_pagina, wait_until="domcontentloaded", timeout=timeout)
                # Espera adicional para asegurar carga de JS
                await asyncio.sleep(0.2)  # Súper agresivo: reducido de 1 a 0.2
                
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
                        await asyncio.sleep(0.1)  # Súper agresivo: reducido de 0.5 a 0.1
                        continue
                        
            except Exception as e:
                if intento == 2:  # Último intento
                    print(f"     Error en página {pagina_actual} después de 3 intentos: {str(e)}")
                    return productos
                else:
                    print(f"     Error en intento {intento + 1}: {str(e)}, reintentando...")
                    await asyncio.sleep(0.1)  # Súper agresivo: reducido de 0.5 a 0.1
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
        await asyncio.sleep(random.uniform(0.5, 1))  # Súper agresivo: reducido de (3,5) a (0.5,1)
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
            timeout = random.randint(5000, 7000)   # Agresivo pero estable
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            
            # Espera adicional para que cargue el contenido
            await asyncio.sleep(0.1)  # Súper agresivo: reducido de 0.5 a 0.1
            
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
                await asyncio.sleep(0.5)  # Súper agresivo: reducido de 2 a 0.5
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