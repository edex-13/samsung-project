import asyncio
import re
import pandas as pd
import time
from playwright.async_api import async_playwright
from typing import List, Dict, Optional
from config import DISPOSITIVOS, CONDICIONES, MAX_PAGINAS, USER_AGENT, VIEWPORT_WIDTH, VIEWPORT_HEIGHT, TIMEOUT_PRODUCTOS, ARCHIVO_SALIDA, DELAY_ENTRE_BUSQUEDAS

def get_url_mercadolibre(dispositivo_formateado, condicion):
    base = f"https://listado.mercadolibre.com.co/celulares-telefonos/celulares-smartphones/samsung/{condicion}/5g/{dispositivo_formateado}_NoIndex_True"
    if condicion == "nuevo":
        hash_filtro = "#applied_filter_id%3DITEM_CONDITION%26applied_filter_name%3DCondición%26applied_filter_order%3D4%26applied_value_id%3D2230284%26applied_value_name%3DNuevo%26applied_value_order%3D1%26applied_value_results%3D20%26is_custom%3Dfalse"
    else:
        hash_filtro = "#applied_filter_id%3DITEM_CONDITION%26applied_filter_name%3DCondición%26applied_filter_order%3D4%26applied_value_id%3D2230581%26applied_value_name%3DUsado%26applied_value_order%3D3%26applied_value_results%3D10%26is_custom%3Dfalse"
    return base + hash_filtro


async def scrape_multiple_dispositivos():
    """
    Scraper de MercadoLibre Colombia para múltiples dispositivos y condiciones
    """
    
    todos_productos = []
    total_busquedas = len(DISPOSITIVOS) * len(CONDICIONES)
    busqueda_actual = 0
    
    print(f"🚀 Iniciando scraper para {len(DISPOSITIVOS)} dispositivos y {len(CONDICIONES)} condiciones")
    print(f"📊 Total de búsquedas a realizar: {total_busquedas}")
    print("=" * 60)
    
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
        
        for dispositivo in DISPOSITIVOS:
            for condicion in CONDICIONES:
                busqueda_actual += 1
                print(f"\n🔍 Búsqueda {busqueda_actual}/{total_busquedas}: {dispositivo} - {condicion}")
                
                try:
                    print(f"🔗 URL que se va a scrapear:")
                    dispositivo_formateado = dispositivo.lower().replace(" ", "-")
                    url_ejemplo = get_url_mercadolibre(dispositivo_formateado, condicion)
                    print(f"   {url_ejemplo}")
                    print("-" * 80)
                    
                    productos_dispositivo = await scrape_dispositivo(page, dispositivo, condicion)
                    
                    if productos_dispositivo:
                        # Agregar información del dispositivo a cada producto
                        for producto in productos_dispositivo:
                            producto['dispositivo'] = dispositivo
                        
                        todos_productos.extend(productos_dispositivo)
                        print(f"✅ Encontrados {len(productos_dispositivo)} productos para {dispositivo} ({condicion})")
                    else:
                        print(f"⚠️ No se encontraron productos para {dispositivo} ({condicion})")
                    
                    # Delay entre búsquedas para evitar bloqueos
                    if busqueda_actual < total_busquedas:
                        print(f"⏳ Esperando {DELAY_ENTRE_BUSQUEDAS} segundos...")
                        await asyncio.sleep(DELAY_ENTRE_BUSQUEDAS)
                    
                except Exception as e:
                    print(f"❌ Error en búsqueda {dispositivo} ({condicion}): {str(e)}")
                    continue
        
        await browser.close()
    
    # Guardar resultados en Excel
    if todos_productos:
        df = pd.DataFrame(todos_productos)
        
        # Reorganizar columnas para mejor visualización
        columnas_ordenadas = ['dispositivo', 'condicion', 'nombre', 'precio', 'calificacion', 'url']
        df = df[columnas_ordenadas]
        
        try:
            df.to_excel(ARCHIVO_SALIDA, index=False)
            print(f"\n🎉 ¡Scraping completado!")
            print(f"📊 Total de productos encontrados: {len(todos_productos)}")
            print(f"💾 Archivo guardado: {ARCHIVO_SALIDA}")
        except PermissionError:
            # Si hay error de permisos, guardar con timestamp
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            nuevo_archivo = f"resultados_multiple_{timestamp}.xlsx"
            df.to_excel(nuevo_archivo, index=False)
            print(f"\n🎉 ¡Scraping completado!")
            print(f"📊 Total de productos encontrados: {len(todos_productos)}")
            print(f"💾 Archivo guardado: {nuevo_archivo} (archivo original estaba en uso)")
        
        # Mostrar resumen por dispositivo
        print("\n📈 Resumen por dispositivo:")
        resumen = df.groupby(['dispositivo', 'condicion']).size().reset_index(name='cantidad')
        for _, row in resumen.iterrows():
            print(f"  • {row['dispositivo']} ({row['condicion']}): {row['cantidad']} productos")
    else:
        print("❌ No se encontraron productos")


async def scrape_dispositivo(page, dispositivo: str, condicion: str) -> List[Dict]:
    """
    Scraper para un dispositivo específico y condición
    """
    
    dispositivo_formateado = dispositivo.lower().replace(" ", "-")
    url = get_url_mercadolibre(dispositivo_formateado, condicion)
    
    productos = []
    pagina_actual = 1
    
    while pagina_actual <= MAX_PAGINAS:
        # Construir URL con parámetro de página
        if pagina_actual == 1:
            url_pagina = url
        else:
            url_pagina = f"{url}_Desde_{(pagina_actual-1)*50+1}"
        
        try:
            print(f"  🌐 Navegando a: {url_pagina}")
            await page.goto(url_pagina, wait_until="networkidle")
            
            # Esperar a que carguen los productos (probar múltiples selectores)
            print(f"  ⏳ Esperando elementos de productos...")
            try:
                await page.wait_for_selector("a.poly-component__title", timeout=TIMEOUT_PRODUCTOS)
            except:
                try:
                    await page.wait_for_selector("div.poly-card", timeout=10000)
                except:
                    print(f"  ❌ No se encontraron elementos de productos en {url_pagina}")
                    return []
            
            # Extraer productos de la página actual
            productos_pagina = await extraer_productos_pagina(page, condicion)
            
            if not productos_pagina:
                print(f"  ⚠️ No se encontraron productos en página {pagina_actual}")
                break
            
            productos.extend(productos_pagina)
            print(f"  📊 Encontrados {len(productos_pagina)} productos en página {pagina_actual}")
            
            # Verificar si hay botón "Siguiente"
            siguiente_btn = await page.query_selector('a[title="Siguiente"]')
            if not siguiente_btn:
                break
            
            pagina_actual += 1
            
        except Exception as e:
            print(f"  ⚠️ Error en página {pagina_actual}: {str(e)}")
            break
    
    return productos


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
            continue
    
    return productos


if __name__ == "__main__":
    print("🚀 Iniciando scraper múltiple de MercadoLibre Colombia")
    print("=" * 60)
    
    # Ejecutar scraper
    asyncio.run(scrape_multiple_dispositivos()) 