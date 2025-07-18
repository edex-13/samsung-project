import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import os
from datetime import datetime
import glob
import re

# Configuración de Firebase
CREDENTIALS_FILE = 'firebase-credentials.json'

# Modelos específicos que estamos scrapeando
MODELOS_VALIDOS = {
    "samsung galaxy s25 ultra",
    "samsung galaxy s24 ultra", 
    "samsung z flip 6",
    "samsung galaxy a56",
    "samsung galaxy a16"
}

def inicializar_firebase():
    """Inicializa la conexión con Firebase"""
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate(CREDENTIALS_FILE)
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        return db
    except Exception as e:
        print(f"Error inicializando Firebase: {str(e)}")
        return None

def extraer_especificaciones_producto(nombre_producto, caracteristicas_extraidas):
    """
    Extrae RAM y memoria interna del producto
    Retorna: (ram_gb, memoria_interna_gb, modelo_detectado)
    """
    if not nombre_producto:
        return None, None, None
    
    nombre_normalizado = nombre_producto.lower()
    caracteristicas_normalizadas = caracteristicas_extraidas.lower() if caracteristicas_extraidas else ""
    
    # Buscar RAM
    ram_gb = None
    patrones_ram = [
        r'(\d+)\s*gb\s*ram',
        r'(\d+)\s*ram',
        r'ram\s*(\d+)\s*gb',
        r'(\d+)gb\s*ram',
        r'ram\s*(\d+)gb'
    ]
    
    for patron in patrones_ram:
        match = re.search(patron, nombre_normalizado + " " + caracteristicas_normalizadas)
        if match:
            ram_gb = int(match.group(1))
            break
    
    # Buscar memoria interna
    memoria_interna_gb = None
    patrones_memoria = [
        r'(\d+)\s*gb\s*(?!ram|de\s*ram)',
        r'(\d+)\s*tb',
        r'(\d+)gb\s*(?!ram)',
        r'(\d+)tb'
    ]
    
    for patron in patrones_memoria:
        match = re.search(patron, nombre_normalizado + " " + caracteristicas_normalizadas)
        if match:
            valor = int(match.group(1))
            if valor >= 32:  # Filtrar valores que probablemente son memoria interna
                memoria_interna_gb = valor
                break
    
    # Detectar modelo
    modelo_detectado = None
    for modelo in MODELOS_VALIDOS:
        if modelo in nombre_normalizado:
            modelo_detectado = modelo
            break
    
    return ram_gb, memoria_interna_gb, modelo_detectado

def normalizar_vendedor(vendedor):
    """Normaliza el nombre del vendedor para agrupación"""
    if not vendedor or pd.isna(vendedor):
        return "Sin vendedor"
    
    # Convertir a string y limpiar
    vendedor_str = str(vendedor).strip()
    
    # Normalizar espacios múltiples y caracteres especiales
    vendedor_limpio = re.sub(r'\s+', ' ', vendedor_str)  # Múltiples espacios a uno
    vendedor_limpio = re.sub(r'[^\w\s]', '', vendedor_limpio)  # Remover caracteres especiales
    vendedor_limpio = vendedor_limpio.lower().strip()
    
    # Mapear variaciones comunes y duplicados
    mapeo_vendedores = {
        # Comercios principales
        "exito": "Éxito",
        "falabella": "Falabella", 
        "linio": "Linio",
        "mercadolibre": "MercadoLibre",
        "mercadolibre colombia": "MercadoLibre",
        
        # Variaciones de tiendas oficiales
        "tienda oficial": "Tienda Oficial",
        "tienda oficial samsung": "Samsung Oficial",
        "samsung oficial": "Samsung Oficial",
        "samsung store": "Samsung Oficial",
        
        # Variaciones de vendedores comunes
        "worldmobile av": "Worldmobile Av",
        "worldmobile": "Worldmobile Av",
        "teczone": "Teczone",
        "amn phone": "Amn Phone",
        "amnphone": "Amn Phone",
        
        # Variaciones de nombres con números
        "724 distribuciones": "724 Distribuciones",
        "724distribuciones": "724 Distribuciones",
        "724": "724 Distribuciones",
        
        # Variaciones de nombres con palabras comunes
        "cell transit": "Cell Transit",
        "celumovil store sas": "Celumovil Store Sas",
        "celumovil": "Celumovil Store Sas",
        "river technology sas": "River Technology Sas",
        "river technology": "River Technology Sas",
        "haru group": "Haru Group",
        "river technology ltda": "River Technology Ltda",
        "lisertec": "Lisertec",
        "pass call technology": "Pass Call Technology",
        "macrocell": "Macrocell",
        "artezcom": "Artezcom",
        "team comunicaciones": "Team Comunicaciones",
        "comunicaciones": "Team Comunicaciones",
        "ktienda": "Ktienda",
        "hometec store": "Hometec Store",
        "marketplace ten": "Marketplace Ten",
        "smartbuy": "Smartbuy",
        "celbeeper sas": "Celbeeper Sas",
        "jd market sas": "Jd Market Sas",
        "comprando ando": "Comprando Ando",
        
        # Variaciones de ventas
        "ventas hatior colombia": "Ventas Hatior Colombia",
        "hatior": "Ventas Hatior Colombia",
        "tecnoliser": "Tecnoliser",
        "korolos": "Korolos",
        "mundomovil 2020": "Mundomovil 2020",
        "mundomovil": "Mundomovil 2020",
        "technology express": "Technology Express",
        "intelcom negocios integrales": "Intelcom Negocios Integrales",
        "je mayorista": "Je Mayorista",
        "game and technology ansa": "Game And Technology Ansa",
        "star": "Star"
    }
    
    # Buscar coincidencias exactas primero
    for clave, valor in mapeo_vendedores.items():
        if clave == vendedor_limpio:
            return valor
    
    # Buscar coincidencias parciales
    for clave, valor in mapeo_vendedores.items():
        if clave in vendedor_limpio or vendedor_limpio in clave:
            return valor
    
    # Si no hay coincidencias, normalizar el nombre
    palabras = vendedor_limpio.split()
    if palabras:
        # Capitalizar primera letra de cada palabra
        vendedor_normalizado = ' '.join(palabra.capitalize() for palabra in palabras)
        return vendedor_normalizado
    
    return "Sin vendedor"

def leer_archivos_data():
    """Lee todos los archivos de la carpeta data y los organiza por tipo"""
    archivos_validos = []
    archivos_invalidos = []
    
    # Buscar archivos en la carpeta data
    if os.path.exists('data'):
        for archivo in os.listdir('data'):
            if archivo.endswith('.xlsx'):
                ruta_completa = os.path.join('data', archivo)
                if '_limpio.xlsx' in archivo:
                    archivos_validos.append(ruta_completa)
                elif '_invalidos.xlsx' in archivo:
                    archivos_invalidos.append(ruta_completa)
    
    return archivos_validos, archivos_invalidos

def procesar_archivo_excel(archivo, tipo):
    """Procesa un archivo Excel y retorna los datos con metadatos"""
    try:
        df = pd.read_excel(archivo)
        datos = []
        
        for idx, row in df.iterrows():
            dato = row.to_dict()
            
            # Agregar metadatos
            dato['archivo_origen'] = os.path.basename(archivo)
            dato['fecha_carga'] = datetime.now().isoformat()
            dato['timestamp_carga'] = datetime.now().timestamp()
            dato['tipo_producto'] = tipo  # 'valido' o 'invalido'
            
            # Determinar comercio
            nombre_archivo = os.path.basename(archivo).lower()
            if 'exito' in nombre_archivo:
                dato['comercio'] = 'Éxito'
            elif 'falabella' in nombre_archivo:
                dato['comercio'] = 'Falabella'
            elif 'mercadolibre' in nombre_archivo:
                dato['comercio'] = 'MercadoLibre'
            else:
                dato['comercio'] = 'Otro'
            
            # Extraer especificaciones si es producto válido
            if tipo == 'valido':
                nombre_producto = dato.get('nombre', '')
                caracteristicas = dato.get('caracteristicas_extraidas', '')
                
                ram_gb, memoria_interna_gb, modelo_detectado = extraer_especificaciones_producto(
                    nombre_producto, caracteristicas
                )
                
                dato['ram_gb'] = ram_gb
                dato['memoria_interna_gb'] = memoria_interna_gb
                dato['modelo_detectado'] = modelo_detectado
                
                # Crear clave única para modelo con especificaciones
                if modelo_detectado and ram_gb and memoria_interna_gb:
                    dato['modelo_especifico'] = f"{modelo_detectado}_{ram_gb}gb_{memoria_interna_gb}gb"
                elif modelo_detectado:
                    dato['modelo_especifico'] = modelo_detectado
                else:
                    dato['modelo_especifico'] = "modelo_no_detectado"
            
            # Normalizar vendedor
            vendedor_original = dato.get('vendedor', '')
            dato['vendedor_normalizado'] = normalizar_vendedor(vendedor_original)
            
            datos.append(dato)
        
        return datos
    except Exception as e:
        print(f"Error procesando {archivo}: {str(e)}")
        return []

def subir_datos_a_coleccion(db, datos, nombre_coleccion):
    """Sube datos a una colección específica usando batch operations"""
    try:
        batch = db.batch()
        contador = 0
        
        for dato in datos:
            # Crear ID único
            timestamp = dato.get('timestamp_carga', datetime.now().timestamp())
            doc_id = f"{nombre_coleccion}_{timestamp}_{contador}"
            
            # Crear referencia y agregar al batch
            doc_ref = db.collection(nombre_coleccion).document(doc_id)
            batch.set(doc_ref, dato)
            contador += 1
        
        # Ejecutar batch
        batch.commit()
        print(f"✅ Subidos {contador} documentos a '{nombre_coleccion}'")
        return contador
        
    except Exception as e:
        print(f"Error subiendo a {nombre_coleccion}: {str(e)}")
        return 0

def subir_datos_a_subcoleccion(db, coleccion_principal, nombre_subcoleccion, datos):
    """Sube datos a una subcolección específica usando batch operations"""
    try:
        batch = db.batch()
        contador = 0
        
        for dato in datos:
            # Crear ID único
            timestamp = dato.get('timestamp_carga', datetime.now().timestamp())
            doc_id = f"{nombre_subcoleccion}_{timestamp}_{contador}"
            
            # Crear referencia a la subcolección y agregar al batch
            doc_ref = db.collection(coleccion_principal).document(nombre_subcoleccion).collection('productos').document(doc_id)
            batch.set(doc_ref, dato)
            contador += 1
        
        # Ejecutar batch
        batch.commit()
        print(f"   ✅ Subidos {contador} documentos a subcolección '{nombre_subcoleccion}'")
        return contador
        
    except Exception as e:
        print(f"Error subiendo a subcolección {nombre_subcoleccion}: {str(e)}")
        return 0

def crear_colecciones_organizadas(db, datos_validos, datos_invalidos):
    """Crea colecciones principales con subcolecciones organizadas"""
    
    total_documentos = 0
    
    # 1. COLECCIÓN PRINCIPAL: productos_scraping
    print(f"\n📤 Creando colección principal 'productos_scraping'")
    
    # Subir todos los productos válidos a la colección principal
    if datos_validos:
        total_documentos += subir_datos_a_coleccion(db, datos_validos, 'productos_scraping')
    
    # 2. COLECCIÓN: productos_invalidos
    if datos_invalidos:
        print(f"\n📤 Subiendo {len(datos_invalidos)} productos inválidos a 'productos_invalidos'")
        total_documentos += subir_datos_a_coleccion(db, datos_invalidos, 'productos_invalidos')
    
    # 3. COLECCIÓN: productos_por_comercio (con subcolecciones)
    print(f"\n📤 Creando colección 'productos_por_comercio' con subcolecciones")
    comercios = {}
    for dato in datos_validos:
        comercio = dato.get('comercio', 'Otro')
        if comercio not in comercios:
            comercios[comercio] = []
        comercios[comercio].append(dato)
    
    for comercio, datos_comercio in comercios.items():
        nombre_subcoleccion = comercio.lower().replace(' ', '_').replace('é', 'e')
        print(f"   📁 Subcolección '{nombre_subcoleccion}': {len(datos_comercio)} productos")
        total_documentos += subir_datos_a_subcoleccion(db, 'productos_por_comercio', nombre_subcoleccion, datos_comercio)
    
    # 4. COLECCIÓN: productos_por_modelo (con subcolecciones)
    print(f"\n📤 Creando colección 'productos_por_modelo' con subcolecciones")
    modelos_especificos = {}
    for dato in datos_validos:
        modelo_especifico = dato.get('modelo_especifico', 'modelo_no_detectado')
        if modelo_especifico not in modelos_especificos:
            modelos_especificos[modelo_especifico] = []
        modelos_especificos[modelo_especifico].append(dato)
    
    for modelo, datos_modelo in modelos_especificos.items():
        nombre_subcoleccion = modelo.lower().replace(' ', '_').replace('/', '_').replace('é', 'e')
        print(f"   📁 Subcolección '{nombre_subcoleccion}': {len(datos_modelo)} productos")
        total_documentos += subir_datos_a_subcoleccion(db, 'productos_por_modelo', nombre_subcoleccion, datos_modelo)
    
    # 5. COLECCIÓN: productos_por_vendedor (con subcolecciones)
    print(f"\n📤 Creando colección 'productos_por_vendedor' con subcolecciones")
    vendedores = {}
    for dato in datos_validos:
        vendedor = dato.get('vendedor_normalizado', 'Sin vendedor')
        if vendedor not in vendedores:
            vendedores[vendedor] = []
        vendedores[vendedor].append(dato)
    
    for vendedor, datos_vendedor in vendedores.items():
        nombre_subcoleccion = vendedor.lower().replace(' ', '_').replace('/', '_').replace('é', 'e')
        print(f"   📁 Subcolección '{nombre_subcoleccion}': {len(datos_vendedor)} productos")
        total_documentos += subir_datos_a_subcoleccion(db, 'productos_por_vendedor', nombre_subcoleccion, datos_vendedor)
    
    # 6. COLECCIÓN: productos_por_condicion (con subcolecciones)
    print(f"\n📤 Creando colección 'productos_por_condicion' con subcolecciones")
    condiciones = {}
    for dato in datos_validos:
        condicion = dato.get('condicion', 'No especificada')
        # Manejar valores NaN o None
        if pd.isna(condicion) or condicion is None:
            condicion = 'No especificada'
        else:
            condicion = str(condicion)
        
        if condicion not in condiciones:
            condiciones[condicion] = []
        condiciones[condicion].append(dato)
    
    for condicion, datos_condicion in condiciones.items():
        nombre_subcoleccion = condicion.lower().replace(' ', '_').replace('é', 'e')
        print(f"   📁 Subcolección '{nombre_subcoleccion}': {len(datos_condicion)} productos")
        total_documentos += subir_datos_a_subcoleccion(db, 'productos_por_condicion', nombre_subcoleccion, datos_condicion)
    
    return total_documentos

def main():
    """Función principal"""
    print("🚀 UPLOADER FIREBASE ORGANIZADO")
    print("=" * 50)
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Verificar credenciales
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ Error: No se encontró '{CREDENTIALS_FILE}'")
        print("📝 Descarga las credenciales de Firebase Console")
        return
    
    # Inicializar Firebase
    db = inicializar_firebase()
    if not db:
        print("❌ No se pudo conectar a Firebase")
        return
    
    # Leer archivos de la carpeta data
    archivos_validos, archivos_invalidos = leer_archivos_data()
    
    if not archivos_validos and not archivos_invalidos:
        print("❌ No se encontraron archivos en la carpeta 'data'")
        return
    
    print(f"📁 Archivos válidos encontrados: {len(archivos_validos)}")
    print(f"📁 Archivos inválidos encontrados: {len(archivos_invalidos)}")
    
    # Procesar archivos válidos
    datos_validos = []
    for archivo in archivos_validos:
        print(f"\n📊 Procesando válidos: {os.path.basename(archivo)}")
        datos = procesar_archivo_excel(archivo, 'valido')
        datos_validos.extend(datos)
    
    # Procesar archivos inválidos
    datos_invalidos = []
    for archivo in archivos_invalidos:
        print(f"\n📊 Procesando inválidos: {os.path.basename(archivo)}")
        datos = procesar_archivo_excel(archivo, 'invalido')
        datos_invalidos.extend(datos)
    
    print(f"\n📊 Total productos válidos: {len(datos_validos)}")
    print(f"📊 Total productos inválidos: {len(datos_invalidos)}")
    
    # Crear colecciones organizadas
    print(f"\n🏗️ Creando colecciones organizadas...")
    total_documentos = crear_colecciones_organizadas(db, datos_validos, datos_invalidos)
    
    print(f"\n🎉 Proceso completado!")
    print(f"📊 Total de documentos subidos: {total_documentos}")
    print(f"📁 Estructura de colecciones creada:")
    print(f"   • productos_scraping (colección principal)")
    print(f"   • productos_invalidos")
    print(f"   • productos_por_comercio/")
    print(f"     └── [comercio]/productos/")
    print(f"   • productos_por_modelo/")
    print(f"     └── [modelo_especifico]/productos/")
    print(f"   • productos_por_vendedor/")
    print(f"     └── [vendedor]/productos/")
    print(f"   • productos_por_condicion/")
    print(f"     └── [condicion]/productos/")

if __name__ == "__main__":
    main() 