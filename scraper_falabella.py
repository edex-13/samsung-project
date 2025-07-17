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
MAX_PAGINAS = 1
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080
TIMEOUT_PRODUCTOS = 60000# Aumentado de150 a300
DELAY_ENTRE_BUSQUEDAS = 15
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
                timeout = random.randint(40000, 45000) # Aumentado el timeout
                print(f"🔄 Intentando cargar página {pagina_actual} (intento {intento + 1}/3)")
                await page.goto(url_pagina, wait_until="domcontentloaded", timeout=timeout)
                # Espera adicional para asegurar carga de JS
                await asyncio.sleep(6)  # Aumentado de 4 a 6 segundos
                
                try:
                    await page.wait_for_selector("a[data-pod]", timeout=TIMEOUT_PRODUCTOS)
                    break  # Si encuentra el selector, salir del bucle de reintentos
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
                        await asyncio.sleep(2)
                        continue
                        
            except Exception as e:
                if intento == 2:  # Último intento
                    print(f"    ❌ Error en página {pagina_actual} después de 3 intentos: {str(e)}")
                    return productos
                else:
                    print(f"    ⚠️ Error en intento {intento + 1}: {str(e)}, reintentando...")
                    await asyncio.sleep(2)
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
        await asyncio.sleep(random.uniform(5, 7))  # Aumentado el delay
    return productos

async def extraer_productos_pagina_falabella(page, dispositivo: str):
    productos = []
    
    # Usar el selector correcto basado en la estructura HTML real
    elementos_producto = await page.query_selector_all("a[data-pod]")
    if not elementos_producto:
        print("    ⚠️ No se encontraron productos con el selector a[data-pod]")
        return productos
    
    print(f"    🔍 Encontrados {len(elementos_producto)} elementos de producto")
    
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
            # Obtener nombre del producto usando el selector correcto
            titulo_element = await elemento.query_selector('#testId-pod-displaySubTitle-140706748, .pod-subTitle')
            if titulo_element:
                producto['nombre'] = await titulo_element.inner_text()
            else:
                # Intentar con otros selectores
                titulo_element = await elemento.query_selector('.pod-subTitle')
                if titulo_element:
                    producto['nombre'] = await titulo_element.inner_text()
                else:
                    producto['nombre'] = None
            
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
            timeout = random.randint(40000, 45000)  # Timeout más corto para productos individuales
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            
            # Espera adicional para que cargue el contenido
            await asyncio.sleep(3)
            
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
                await asyncio.sleep(2)
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
            await asyncio.sleep(random.uniform(5, 7))
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

# En la función principal, probar varios User-Agent
async def scrape_falabella():
    todos_productos = []
    fecha_scraping = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"🚀 Iniciando scraper Falabella/Linio para {len(DISPOSITIVOS)} dispositivos")
    print("=" * 60)
    async with async_playwright() as p:
        for intento in range(3):
            user_agent = random.choice(USER_AGENTS)
            print(f"🖥️ User-Agent usado: {user_agent}")
            browser = await p.chromium.launch(headless=True, args=[f'--user-agent={user_agent}'])
            page = await browser.new_page()
            await page.set_viewport_size({"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT})
            exito = False
            for dispositivo in DISPOSITIVOS:
                print(f"\n🔍 Búsqueda: {dispositivo}")
                await asyncio.sleep(random.uniform(5, 7))
                try:
                    productos_busqueda = await scrape_busqueda_inicial_falabella(page, dispositivo)
                    if productos_busqueda:
                        exito = True
                        print(f"✅ Encontrados {len(productos_busqueda)} productos en búsqueda inicial")
                        for i, producto in enumerate(productos_busqueda):
                            print(f"  🔍 Procesando producto {i+1}/{len(productos_busqueda)}: {producto['nombre'][:50]}...")
                            print(f"    🔗 URL: {producto['url']}")
                            await asyncio.sleep(random.uniform(5, 7))
                            try:
                                producto_con_detalles = await extraer_detalles_producto_falabella(page, producto, fecha_scraping)
                                todos_productos.append(producto_con_detalles)
                                await asyncio.sleep(random.uniform(5, 7))
                            except Exception as e:
                                print(f"    ❌ Error procesando producto: {str(e)}")
                                producto['fecha_scraping'] = fecha_scraping
                                todos_productos.append(producto)
                                continue
                    else:
                        print(f"⚠️ No se encontraron productos para {dispositivo}")
                    print(f"⏳ Esperando {DELAY_ENTRE_BUSQUEDAS} segundos...")
                    await asyncio.sleep(DELAY_ENTRE_BUSQUEDAS)
                except Exception as e:
                    print(f"❌ Error en búsqueda {dispositivo}: {str(e)}")
                    continue
            await browser.close()
            if exito:
                break

    if todos_productos:
        df_completo = pd.DataFrame(todos_productos)
        try:
            df_completo.to_excel("resultados_falabella.xlsx", index=False)
            print(f"\n🎉 ¡Scraping Falabella finalizado!")
            print(f"📊 Total de productos: {len(todos_productos)}")
            print(f"💾 Archivo guardado: resultados_falabella.xlsx")
        except PermissionError:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nuevo_archivo = f"resultados_falabella_{timestamp}.xlsx"
            df_completo.to_excel(nuevo_archivo, index=False)
            print(f"\n🎉 ¡Scraping Falabella finalizado!")
            print(f"📊 Total de productos: {len(todos_productos)}")
            print(f"💾 Archivo guardado: {nuevo_archivo}")
    else:
        print("❌ No se encontraron productos")

if __name__ == "__main__":
    print("[INICIANDO] Scraper Falabella/Linio...")
    print("=" * 60)
    asyncio.run(scrape_falabella()) 