import pandas as pd
import re
import os
from datetime import datetime

# Modelos específicos que estamos scrapeando (extraídos de los scrapers)
MODELOS_VALIDOS = {
    "samsung galaxy s25 ultra",
    "samsung galaxy s24 ultra", 
    "samsung z flip 6",
    "samsung galaxy a56",
    "samsung galaxy a16"
}

# Variaciones y sinónimos de los modelos
VARIACIONES_MODELOS = {
    "samsung galaxy s25 ultra": [
        "s25 ultra", "galaxy s25 ultra", "samsung s25 ultra", "s25ultra", "s25-ultra",
        "galaxy s 25 ultra", "samsung galaxy s 25 ultra"
    ],
    "samsung galaxy s24 ultra": [
        "s24 ultra", "galaxy s24 ultra", "samsung s24 ultra", "s24ultra", "s24-ultra",
        "galaxy s 24 ultra", "samsung galaxy s 24 ultra"
    ],
    "samsung z flip 6": [
        "z flip 6", "galaxy z flip 6", "samsung z flip 6", "zflip6", "z-flip-6",
        "galaxy z flip6", "samsung galaxy z flip 6", "flip6", "flip 6"
    ],
    "samsung galaxy a56": [
        "a56", "galaxy a56", "samsung a56", "a-56", "galaxy a 56", "samsung galaxy a 56"
    ],
    "samsung galaxy a16": [
        "a16", "galaxy a16", "samsung a16", "a-16", "galaxy a 16", "samsung galaxy a 16"
    ],
}

# Palabras clave que indican que NO es un celular (accesorios, repuestos, etc.)
PALABRAS_NO_CELULAR = [
    # Protectores y vidrios
    "protector", "protectores", "vidrio", "vidrios", "templado", "templados", "cristal",
    "hidrogel", "antiespia", "privacidad", "transparente", "pantalla",
    
    # Fundas y carcasas
    "funda", "fundas", "carcasa", "carcasas", "case", "cases", "cover", "covers",
    "estuche", "estuches", "soporte", "soportes",
    
    # Cables y cargadores
    "cable", "cables", "cargador", "cargadores", "adaptador", "adaptadores",
    "usb", "type-c", "lightning", "wireless", "inalambrico",
    
    # Auriculares y audio
    "auricular", "auriculares", "headphone", "headphones", "earbud", "earbuds",
    "bluetooth", "inalambrico", "cableado",
    
    # Repuestos y partes
    "repuesto", "repuestos", "parte", "partes", "componente", "componentes",
    "bateria", "baterias", "pantalla", "pantallas", "display", "displays",
    "modulo", "modulos", "placa", "placas",
    
    # Accesorios varios
    "accesorio", "accesorios", "complemento", "complementos", "aditamento",
    "aditamentos", "gadget", "gadgets", "herramienta", "herramientas",
    
    # Productos no móviles
    "tablet", "tablets", "ipad", "smartwatch", "reloj", "relojes", "laptop",
    "computador", "computadora", "pc", "notebook", "netbook",
    
    # Otros
    "kit", "kits", "set", "sets", "pack", "packs", "combo", "combos",
    "bundle", "bundles", "oferta", "ofertas", "promocion", "promociones"
]

def normalizar_texto(texto):
    """Normaliza el texto para comparación"""
    if not texto:
        return ""
    return re.sub(r'[^\w\s]', '', texto.lower()).strip()

def extraer_especificaciones_nombre(nombre_producto):
    """
    Extrae RAM y espacio interno del nombre del producto
    Retorna: (ram_detectada, espacio_interno_detectado, datos_extraidos)
    """
    if not nombre_producto:
        return None, None, ""
    
    nombre_normalizado = nombre_producto.lower()
    datos_extraidos = []
    
    # Patrones para RAM (mejorados basándose en los nombres reales)
    patrones_ram = [
        r'(\d+)\s*gb\s*ram',      # 12 GB RAM
        r'(\d+)\s*ram',           # 12 RAM
        r'ram\s*(\d+)\s*gb',      # RAM 12 GB
        r'(\d+)gb\s*ram',         # 12GB RAM
        r'ram\s*(\d+)gb',         # RAM 12GB
        r'(\d+)\s*ram\s*gb',      # 12 RAM GB
        r'(\d+)\s*gb\s*de\s*ram', # 12 GB de RAM
    ]
    
    ram_detectada = None
    for patron in patrones_ram:
        match = re.search(patron, nombre_normalizado)
        if match:
            ram_detectada = int(match.group(1))
            datos_extraidos.append(f"RAM: {ram_detectada}GB")
            break
    
    # Patrones para espacio interno (mejorados)
    patrones_espacio = [
        r'(\d+)\s*gb\s*(?!ram|de\s*ram)',  # 256 GB (pero no RAM)
        r'(\d+)\s*tb',                      # 1 TB
        r'(\d+)gb\s*(?!ram)',              # 256GB (pero no RAM)
        r'(\d+)tb',                         # 1TB
        r'(\d+)\s*terabyte',               # 1 terabyte
        r'(\d+)\s*gigabyte',               # 256 gigabyte
        r'(\d+)\s*gb\s*de\s*almacenamiento', # 256 GB de almacenamiento
    ]
    
    espacio_interno = None
    for patron in patrones_espacio:
        match = re.search(patron, nombre_normalizado)
        if match:
            valor = int(match.group(1))
            # Si es menor a 32, probablemente es RAM, no espacio interno
            if valor >= 32:
                espacio_interno = valor
                datos_extraidos.append(f"Almacenamiento: {espacio_interno}GB")
                break
    
    # Extraer color si está presente
    colores_comunes = [
        "negro", "blanco", "gris", "azul", "rojo", "verde", "amarillo", "rosa", "morado",
        "dorado", "plateado", "bronce", "titanio", "grafito", "crema", "beige"
    ]
    
    color_detectado = None
    for color in colores_comunes:
        if color in nombre_normalizado:
            color_detectado = color
            datos_extraidos.append(f"Color: {color.capitalize()}")
            break
    
    # Extraer 5G si está presente
    if "5g" in nombre_normalizado:
        datos_extraidos.append("5G: Sí")
    
    # Extraer AI si está presente
    if "ai" in nombre_normalizado:
        datos_extraidos.append("AI: Sí")
    
    return ram_detectada, espacio_interno, " | ".join(datos_extraidos)

def completar_datos_faltantes(row, nombre_producto):
    """
    Completa datos faltantes extrayéndolos del nombre del producto
    Retorna: (datos_completados, caracteristicas_extraidas)
    """
    datos_completados = {}
    caracteristicas_extraidas = []
    
    # Extraer especificaciones del nombre
    ram_detectada, espacio_interno, datos_extraidos = extraer_especificaciones_nombre(nombre_producto)
    
    # Verificar y completar RAM
    if pd.isna(row.get('memoria_ram')) or row.get('memoria_ram') == '' or row.get('memoria_ram') is None:
        if ram_detectada:
            datos_completados['memoria_ram'] = f"{ram_detectada} GB"
            caracteristicas_extraidas.append(f"RAM: {ram_detectada}GB")
    
    # Verificar y completar memoria interna
    if pd.isna(row.get('memoria_interna')) or row.get('memoria_interna') == '' or row.get('memoria_interna') is None:
        if espacio_interno:
            datos_completados['memoria_interna'] = f"{espacio_interno} GB"
            caracteristicas_extraidas.append(f"Almacenamiento: {espacio_interno}GB")
    
    # Verificar y completar color
    if pd.isna(row.get('color')) or row.get('color') == '' or row.get('color') is None:
        nombre_normalizado = nombre_producto.lower()
        colores_comunes = [
            "negro", "blanco", "gris", "azul", "rojo", "verde", "amarillo", "rosa", "morado",
            "dorado", "plateado", "bronce", "titanio", "grafito", "crema", "beige"
        ]
        
        for color in colores_comunes:
            if color in nombre_normalizado:
                datos_completados['color'] = color.capitalize()
                caracteristicas_extraidas.append(f"Color: {color.capitalize()}")
                break
    
    # Verificar y completar modelo
    if pd.isna(row.get('modelo')) or row.get('modelo') == '' or row.get('modelo') is None:
        # Extraer modelo del nombre
        nombre_normalizado = nombre_producto.lower()
        for modelo in MODELOS_VALIDOS:
            if modelo in nombre_normalizado:
                datos_completados['modelo'] = modelo
                caracteristicas_extraidas.append(f"Modelo: {modelo}")
                break
    
    # Verificar y completar condición
    if pd.isna(row.get('condicion')) or row.get('condicion') == '' or row.get('condicion') is None:
        nombre_normalizado = nombre_producto.lower()
        if "reacondicionado" in nombre_normalizado or "usado" in nombre_normalizado:
            datos_completados['condicion'] = "Usado"
            caracteristicas_extraidas.append("Condición: Usado")
        elif "nuevo" in nombre_normalizado:
            datos_completados['condicion'] = "Nuevo"
            caracteristicas_extraidas.append("Condición: Nuevo")
    
    return datos_completados, " | ".join(caracteristicas_extraidas)

def es_accesorio_o_no_celular(nombre_producto):
    """
    Verifica si el producto es un accesorio o no es un celular
    Retorna: (es_accesorio, tipo_accesorio)
    """
    if not nombre_producto:
        return False, None
    
    nombre_normalizado = normalizar_texto(nombre_producto)
    
    # Verificar palabras que indican que NO es un celular
    for palabra in PALABRAS_NO_CELULAR:
        if palabra in nombre_normalizado:
            return True, palabra
    
    # Verificar patrones específicos de accesorios
    patrones_accesorios = [
        r'para\s+\w+',  # "para Samsung Galaxy"
        r'compatible\s+con',  # "compatible con"
        r'fits\s+\w+',  # "fits Samsung"
        r'designed\s+for',  # "designed for"
    ]
    
    for patron in patrones_accesorios:
        if re.search(patron, nombre_normalizado):
            return True, "patron_accesorio"
    
    return False, None

def verificar_modelo_estricto(nombre_producto, dispositivo_buscado):
    """
    Verifica si el producto corresponde EXACTAMENTE al modelo buscado
    Retorna: (es_valido, modelo_detectado, nivel_confianza, tipo_error)
    """
    if not nombre_producto:
        return False, None, 0, "nombre_vacio"
    
    # PRIMERO: Verificar si es un accesorio
    es_accesorio, tipo_accesorio = es_accesorio_o_no_celular(nombre_producto)
    if es_accesorio:
        return False, None, 0, f"accesorio_{tipo_accesorio}"
    
    nombre_normalizado = normalizar_texto(nombre_producto)
    dispositivo_normalizado = normalizar_texto(dispositivo_buscado)
    
    # Verificar que el nombre contenga el modelo esperado
    modelo_esperado_encontrado = False
    modelo_detectado = None
    
    # Verificar coincidencia exacta con el dispositivo buscado
    if dispositivo_normalizado in nombre_normalizado:
        modelo_esperado_encontrado = True
        modelo_detectado = dispositivo_buscado
    
    # Verificar con variaciones del modelo buscado
    if not modelo_esperado_encontrado and dispositivo_buscado in VARIACIONES_MODELOS:
        for variacion in VARIACIONES_MODELOS[dispositivo_buscado]:
            if normalizar_texto(variacion) in nombre_normalizado:
                modelo_esperado_encontrado = True
                modelo_detectado = dispositivo_buscado
                break
    
    # Si no se encontró el modelo esperado, verificar si contiene otros modelos
    if not modelo_esperado_encontrado:
        for modelo in MODELOS_VALIDOS:
            modelo_normalizado = normalizar_texto(modelo)
            if modelo_normalizado in nombre_normalizado:
                # Encontró un modelo válido pero NO es el esperado
                return False, modelo, 50, "modelo_incorrecto"
            
            # Verificar variaciones de otros modelos
            if modelo in VARIACIONES_MODELOS:
                for variacion in VARIACIONES_MODELOS[modelo]:
                    if normalizar_texto(variacion) in nombre_normalizado:
                        # Encontró una variación de otro modelo válido pero NO es el esperado
                        return False, modelo, 45, "modelo_incorrecto"
    
    # Si se encontró el modelo esperado, verificar que NO contenga otros modelos
    if modelo_esperado_encontrado:
        for modelo in MODELOS_VALIDOS:
            if modelo != dispositivo_buscado:  # No verificar contra sí mismo
                modelo_normalizado = normalizar_texto(modelo)
                if modelo_normalizado in nombre_normalizado:
                    # Contiene el modelo esperado PERO TAMBIÉN otro modelo
                    return False, modelo_detectado, 60, "modelo_mixto"
                
                # Verificar variaciones de otros modelos
                if modelo in VARIACIONES_MODELOS:
                    for variacion in VARIACIONES_MODELOS[modelo]:
                        if normalizar_texto(variacion) in nombre_normalizado:
                            # Contiene el modelo esperado PERO TAMBIÉN otra variación
                            return False, modelo_detectado, 55, "modelo_mixto"
        
        # Si llegamos aquí, el producto contiene SOLO el modelo esperado
        return True, modelo_detectado, 100, None
    
    # Verificar palabras clave de Samsung
    palabras_samsung = ["samsung", "galaxy"]
    tiene_palabras_samsung = any(palabra in nombre_normalizado for palabra in palabras_samsung)
    
    if tiene_palabras_samsung:
        return False, None, 30, "samsung_no_especifico"  # Posible Samsung pero no modelo específico
    
    return False, None, 0, "no_samsung"

def estandarizar_columnas_precio(df):
    """
    Estandariza todas las columnas de precio para que todos los scrapers tengan el mismo formato
    Columnas estándar:
    - precio_actual: Precio principal actual
    - precio_original: Precio original (antes del descuento)
    - porcentaje_descuento: Porcentaje de descuento
    - precio_promocion: Precio promocional (si aplica)
    """
    
    # Crear columnas estándar si no existen
    if 'precio_actual' not in df.columns:
        df['precio_actual'] = None
    if 'precio_original' not in df.columns:
        df['precio_original'] = None
    if 'porcentaje_descuento' not in df.columns:
        df['porcentaje_descuento'] = None
    if 'precio_promocion' not in df.columns:
        df['precio_promocion'] = None
    
    for idx, row in df.iterrows():
        # Obtener todos los precios disponibles
        precios_disponibles = {}
        
        # Precios de Éxito
        if 'precio_actual' in df.columns and pd.notna(row.get('precio_actual')):
            precios_disponibles['precio_actual_exito'] = row.get('precio_actual')
        if 'precio_promocion' in df.columns and pd.notna(row.get('precio_promocion')):
            precios_disponibles['precio_promocion_exito'] = row.get('precio_promocion')
        
        # Precios de Falabella
        if 'precio_tarjeta_falabella' in df.columns and pd.notna(row.get('precio_tarjeta_falabella')):
            precios_disponibles['precio_tarjeta_falabella'] = row.get('precio_tarjeta_falabella')
        if 'precio_descuento' in df.columns and pd.notna(row.get('precio_descuento')):
            precios_disponibles['precio_descuento_falabella'] = row.get('precio_descuento')
        if 'precio_normal' in df.columns and pd.notna(row.get('precio_normal')):
            precios_disponibles['precio_normal_falabella'] = row.get('precio_normal')
        
        # Precios de Ktronix
        if 'precio_ktronix' in df.columns and pd.notna(row.get('precio_ktronix')):
            precios_disponibles['precio_ktronix'] = row.get('precio_ktronix')
        if 'precio_listado' in df.columns and pd.notna(row.get('precio_listado')):
            precios_disponibles['precio_listado_ktronix'] = row.get('precio_listado')
        
        # Precios de MercadoLibre
        if 'precio_meli' in df.columns and pd.notna(row.get('precio_meli')):
            precios_disponibles['precio_meli'] = row.get('precio_meli')
        
        # Lógica de estandarización
        precio_actual = None
        precio_original = None
        porcentaje_descuento = 0
        precio_promocion = None
        
        # Prioridad 1: Si hay precio_actual de Éxito, usarlo
        if 'precio_actual_exito' in precios_disponibles:
            precio_actual = precios_disponibles['precio_actual_exito']
            if 'precio_promocion_exito' in precios_disponibles:
                precio_original = precios_disponibles['precio_promocion_exito']
                precio_promocion = precios_disponibles['precio_promocion_exito']
                # Calcular porcentaje de descuento
                if precio_original and precio_actual:
                    descuento = ((precio_original - precio_actual) / precio_original) * 100
                    porcentaje_descuento = int(descuento) if descuento > 0 else 0
        
        # Prioridad 2: Si hay precio de Ktronix
        elif 'precio_ktronix' in precios_disponibles:
            precio_actual = precios_disponibles['precio_ktronix']
            precio_original = precios_disponibles['precio_ktronix']  # Sin descuento
        
        # Prioridad 3: Si hay precio de MercadoLibre
        elif 'precio_meli' in precios_disponibles:
            precio_actual = precios_disponibles['precio_meli']
            precio_original = precios_disponibles['precio_meli']  # Sin descuento
        
        # Prioridad 4: Si hay precio de Falabella
        elif 'precio_tarjeta_falabella' in precios_disponibles:
            precio_actual = precios_disponibles['precio_tarjeta_falabella']
            if 'precio_normal_falabella' in precios_disponibles:
                precio_original = precios_disponibles['precio_normal_falabella']
                # Calcular porcentaje de descuento
                if precio_original and precio_actual:
                    descuento = ((precio_original - precio_actual) / precio_original) * 100
                    porcentaje_descuento = int(descuento) if descuento > 0 else 0
            else:
                precio_original = precio_actual
        
        elif 'precio_descuento_falabella' in precios_disponibles:
            precio_actual = precios_disponibles['precio_descuento_falabella']
            if 'precio_normal_falabella' in precios_disponibles:
                precio_original = precios_disponibles['precio_normal_falabella']
                # Calcular porcentaje de descuento
                if precio_original and precio_actual:
                    descuento = ((precio_original - precio_actual) / precio_original) * 100
                    porcentaje_descuento = int(descuento) if descuento > 0 else 0
            else:
                precio_original = precio_actual
        
        # Actualizar el DataFrame con los valores estandarizados
        df.at[idx, 'precio_actual'] = precio_actual
        df.at[idx, 'precio_original'] = precio_original
        df.at[idx, 'porcentaje_descuento'] = porcentaje_descuento
        df.at[idx, 'precio_promocion'] = precio_promocion
    
    return df

def crear_archivo_limpio(df_validos, nombre_archivo):
    """
    Crea un archivo limpio con solo las columnas de datos y características extraídas
    """
    # Determinar directorio data (Docker o local)
    if os.path.exists('/app/output'):
        data_dir = '/app/output'
    else:
        data_dir = 'data'
    
    # Crear carpeta data si no existe
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"   📁 Carpeta '{data_dir}' creada")
    
    # Columnas estándar que SIEMPRE deben estar presentes (después de estandarización)
    columnas_estandar = [
        'url', 'nombre', 'dispositivo', 'fecha_scraping', 
        'precio_actual', 'precio_original', 'porcentaje_descuento', 'precio_promocion',
        'memoria_interna', 'memoria_ram', 'color', 'condicion', 'vendedor'
    ]
    
    # Columnas adicionales que pueden existir en algunos archivos
    columnas_adicionales = [
        'moneda', 'envio_gratis', 'vendedor_verificado', 'ubicacion',
        'producto_id', 'categoria', 'imagenes'
    ]
    
    # Filtrar solo las columnas que existen en el DataFrame
    columnas_finales = []
    for col in columnas_estandar + columnas_adicionales:
        if col in df_validos.columns:
            columnas_finales.append(col)
    
    # Agregar la columna de características extraídas
    columnas_finales.append('caracteristicas_extraidas')
    
    # Crear DataFrame limpio
    df_limpio = df_validos[columnas_finales].copy()
    
    # Estandarizar columnas de precio para que todos tengan el mismo formato
    df_limpio = estandarizar_columnas_precio(df_limpio)
    
    # Guardar archivo limpio en la carpeta correcta (usando data_dir)
    archivo_limpio = f"{data_dir}/{nombre_archivo}_limpio.xlsx"
    df_limpio.to_excel(archivo_limpio, index=False)
    return archivo_limpio

def crear_archivo_invalidos(df_invalidos, nombre_archivo):
    """
    Crea un archivo con productos inválidos y columna de estado
    """
    # Determinar directorio data (Docker o local)
    if os.path.exists('/app/output'):
        data_dir = '/app/output'
    else:
        data_dir = 'data'
        if not os.path.exists('data'):
            os.makedirs('data')
            print("   📁 Carpeta 'data' creada")
    
    # Agregar columna de estado
    df_invalidos['estado'] = 'inválido'
    
    # Guardar archivo de inválidos en la carpeta correcta
    archivo_invalidos = f"{data_dir}/{nombre_archivo}_invalidos.xlsx"
    df_invalidos.to_excel(archivo_invalidos, index=False)
    return archivo_invalidos

def analizar_archivo_excel(archivo):
    """Analiza un archivo Excel y genera archivos limpios e inválidos"""
    try:
        print(f"\n🔍 Analizando archivo: {archivo}")
        
        # Leer el archivo Excel
        df = pd.read_excel(archivo)
        
        if df.empty:
            print(f"   ⚠️ Archivo vacío: {archivo}")
            return None
        
        print(f"   📊 Total de productos: {len(df)}")
        
        # Verificar columnas necesarias
        columnas_requeridas = ['nombre', 'dispositivo']
        columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]
        
        if columnas_faltantes:
            print(f"   ❌ Columnas faltantes: {columnas_faltantes}")
            return None
        
        # Agregar columna de características extraídas
        df['caracteristicas_extraidas'] = ""
        
        productos_validos = 0
        productos_invalidos = 0
        accesorios_detectados = 0
        datos_completados = 0
        modelos_incorrectos = 0
        
        for idx, row in df.iterrows():
            nombre = row.get('nombre', '')
            dispositivo = row.get('dispositivo', '')
            
            # Verificar modelo con validación estricta
            es_valido, modelo_detectado, confianza, tipo_error = verificar_modelo_estricto(nombre, dispositivo)
            
            if es_valido:
                productos_validos += 1
                
                # Completar datos faltantes solo para productos válidos
                datos_completados_row, caracteristicas_extraidas = completar_datos_faltantes(row, nombre)
                
                if datos_completados_row:
                    datos_completados += 1
                    # Actualizar las columnas originales con los datos extraídos
                    for columna, valor in datos_completados_row.items():
                        if columna in df.columns:
                            df.at[idx, columna] = valor
                    
                    df.at[idx, 'caracteristicas_extraidas'] = caracteristicas_extraidas
                else:
                    df.at[idx, 'caracteristicas_extraidas'] = "Sin datos extraídos"
                    
            else:
                productos_invalidos += 1
                
                # Determinar tipo de error específico
                if tipo_error and tipo_error.startswith('accesorio_'):
                    accesorios_detectados += 1
                elif tipo_error in ['modelo_incorrecto', 'modelo_mixto']:
                    modelos_incorrectos += 1
        
        # Separar productos válidos e inválidos
        df_validos = df[df['caracteristicas_extraidas'] != ""].copy()
        df_invalidos = df[df['caracteristicas_extraidas'] == ""].copy()
        
        # Estadísticas
        print(f"   ✅ Productos válidos: {productos_validos}")
        print(f"   ❌ Productos con posible error: {productos_invalidos}")
        print(f"   📦 Accesorios detectados: {accesorios_detectados}")
        print(f"   🔧 Datos completados: {datos_completados}")
        print(f"   📱 Modelos incorrectos: {modelos_incorrectos}")
        print(f"   📈 Porcentaje de validez: {(productos_validos/len(df)*100):.1f}%")
        
        # Crear archivos
        nombre_archivo_base = os.path.splitext(os.path.basename(archivo))[0]
        
        # Archivo limpio con productos válidos
        archivo_limpio = crear_archivo_limpio(df_validos, nombre_archivo_base)
        print(f"   ✅ Archivo limpio guardado: {archivo_limpio} ({len(df_validos)} productos válidos)")
        
        # Archivo con productos inválidos
        archivo_invalidos = crear_archivo_invalidos(df_invalidos, nombre_archivo_base)
        print(f"   ❌ Archivo inválidos guardado: {archivo_invalidos} ({len(df_invalidos)} productos inválidos)")
        
        return df
        
    except Exception as e:
        print(f"   ❌ Error analizando {archivo}: {str(e)}")
        return None

def main():
    """Función principal que analiza todos los archivos Excel"""
    print("🔍 VERIFICADOR DE PRODUCTOS")
    print("=" * 50)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📋 Modelos válidos: {len(MODELOS_VALIDOS)}")
    print(f"🚫 Palabras no-celular detectadas: {len(PALABRAS_NO_CELULAR)}")
    
    # Buscar archivos Excel (en directorio actual o en /app/output si es Docker)
    archivos_excel = []
    
    # Determinar directorio de búsqueda
    if os.path.exists('/app/output'):
        directorios_busqueda = ['/app/output', '.']
        print("🐳 Detectado entorno Docker, buscando archivos en /app/output y directorio actual")
    else:
        directorios_busqueda = ['.']
        print("💻 Entorno local, buscando archivos en directorio actual")
    
    for directorio in directorios_busqueda:
        try:
            for archivo in os.listdir(directorio):
                if archivo.endswith('.xlsx') and not archivo.endswith('_limpio.xlsx') and not archivo.endswith('_invalidos.xlsx'):
                    if directorio == '.':
                        archivos_excel.append(archivo)
                    else:
                        archivos_excel.append(os.path.join(directorio, archivo))
        except FileNotFoundError:
            continue
    
    if not archivos_excel:
        print("❌ No se encontraron archivos Excel para analizar")
        return
    
    print(f"\n📁 Archivos encontrados: {len(archivos_excel)}")
    
    resultados_totales = []
    
    for archivo in archivos_excel:
        df_resultado = analizar_archivo_excel(archivo)
        if df_resultado is not None:
            accesorios = len(df_resultado[df_resultado['caracteristicas_extraidas'] == ""])
            productos_validos = len(df_resultado[df_resultado['caracteristicas_extraidas'] != ""])
            datos_completados = len(df_resultado[df_resultado['caracteristicas_extraidas'].str.contains('extraído', na=False)])
            resultados_totales.append({
                'archivo': archivo,
                'total_productos': len(df_resultado),
                'productos_validos': productos_validos,
                'productos_invalidos': len(df_resultado[df_resultado['caracteristicas_extraidas'] == ""]),
                'accesorios_detectados': accesorios,
                'datos_completados': datos_completados,
                'porcentaje_validez': productos_validos / len(df_resultado) * 100
            })
    
    # Resumen general
    if resultados_totales:
        print(f"\n📊 RESUMEN GENERAL")
        print("=" * 50)
        
        total_productos = sum(r['total_productos'] for r in resultados_totales)
        total_validos = sum(r['productos_validos'] for r in resultados_totales)
        total_invalidos = sum(r['productos_invalidos'] for r in resultados_totales)
        total_accesorios = sum(r['accesorios_detectados'] for r in resultados_totales)
        total_datos_completados = sum(r['datos_completados'] for r in resultados_totales)
        
        print(f"📁 Total de archivos: {len(resultados_totales)}")
        print(f"📦 Total de productos: {total_productos}")
        print(f"✅ Productos válidos: {total_validos}")
        print(f"❌ Productos con errores: {total_invalidos}")
        print(f"📦 Accesorios detectados: {total_accesorios}")
        print(f"🔧 Datos completados: {total_datos_completados}")
        print(f"📈 Porcentaje general de validez: {(total_validos/total_productos*100):.1f}%")
        
        # Mostrar archivos con peor rendimiento
        archivos_problema = [r for r in resultados_totales if r['porcentaje_validez'] < 80]
        if archivos_problema:
            print(f"\n⚠️ Archivos con problemas (validez < 80%):")
            for archivo in archivos_problema:
                print(f"   • {archivo['archivo']}: {archivo['porcentaje_validez']:.1f}% válidos")

if __name__ == "__main__":
    main() 