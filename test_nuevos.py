import asyncio
import re
import pandas as pd
from playwright.async_api import async_playwright
from typing import List, Dict

async def test_productos_nuevos():
    """
    Script de prueba para diagnosticar productos nuevos
    """
    
    dispositivo = "samsung galaxy s24 ultra 5g"
    condicion = "nuevo"
    
    # Formatear el dispositivo para la URL
    dispositivo_formateado = dispositivo.lower().replace(" ", "-")
    url = f"https://listado.mercadolibre.com.co/{dispositivo_formateado}/{condicion}"
    
    print(f"🔍 Probando URL: {url}")
    print("=" * 60)
    
    async with async_playwright() as p:
        # Iniciar navegador en modo headless
        browser = await p.chromium.launch(
            headless=False,  # Cambiar a False para ver qué pasa
            args=[
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                '--window-size=1920,1080'
            ]
        )
        
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1920, "height": 1080})
        
        try:
            print("🌐 Navegando a la página...")
            await page.goto(url, wait_until="networkidle")
            
            print("⏳ Esperando elementos de productos...")
            # Aumentar timeout a 30 segundos
            await page.wait_for_selector("a.poly-component__title", timeout=30000)
            
            print("✅ Elementos encontrados, extrayendo productos...")
            
            # Contar elementos de producto
            elementos_producto = await page.query_selector_all("div.poly-card")
            print(f"📊 Encontrados {len(elementos_producto)} elementos de producto")
            
            productos = []
            for i, elemento in enumerate(elementos_producto[:5]):  # Solo los primeros 5 para debug
                try:
                    producto = {}
                    
                    # Extraer nombre
                    titulo_element = await elemento.query_selector("a.poly-component__title")
                    if titulo_element:
                        producto['nombre'] = await titulo_element.inner_text()
                        producto['url'] = await titulo_element.get_attribute("href")
                        print(f"  {i+1}. Nombre: {producto['nombre'][:50]}...")
                    else:
                        print(f"  {i+1}. ❌ No se encontró título")
                    
                    # Extraer precio
                    precio_element = await elemento.query_selector("span.andes-money-amount__fraction")
                    if precio_element:
                        precio_texto = await precio_element.inner_text()
                        precio_limpio = re.sub(r'[^\d]', '', precio_texto)
                        producto['precio'] = int(precio_limpio) if precio_limpio else None
                        print(f"     💰 Precio: {precio_texto} -> {producto['precio']}")
                    else:
                        print(f"     ❌ No se encontró precio")
                    
                    productos.append(producto)
                    
                except Exception as e:
                    print(f"  {i+1}. ❌ Error: {str(e)}")
                    continue
            
            print(f"\n📈 Total de productos extraídos: {len(productos)}")
            
            # Tomar screenshot para debug
            await page.screenshot(path="debug_nuevos.png")
            print("📸 Screenshot guardado como debug_nuevos.png")
            
        except Exception as e:
            print(f"❌ Error general: {str(e)}")
            await page.screenshot(path="error_nuevos.png")
            print("📸 Screenshot de error guardado como error_nuevos.png")
        
        await browser.close()

if __name__ == "__main__":
    print("🧪 Iniciando prueba de productos nuevos...")
    asyncio.run(test_productos_nuevos()) 