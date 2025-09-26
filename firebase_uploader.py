import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import os
from datetime import datetime
import glob

# Configuración de Firebase
# Necesitarás descargar el archivo de credenciales de Firebase Console
# y ponerlo en la misma carpeta con el nombre 'firebase-credentials.json'
CREDENTIALS_FILE = 'firebase-credentials.json'

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

def leer_excel_a_datos(archivo):
    """Lee un archivo Excel y retorna los datos como lista de diccionarios"""
    try:
        df = pd.read_excel(archivo)
        # Convertir DataFrame a lista de diccionarios
        datos = df.to_dict('records')
        
        # Agregar metadatos
        for dato in datos:
            dato['archivo_origen'] = os.path.basename(archivo)
            dato['fecha_carga'] = datetime.now().isoformat()
            dato['timestamp_carga'] = datetime.now().timestamp()
            
            # Determinar el comercio basado en el nombre del archivo
            nombre_archivo = os.path.basename(archivo).lower()
            if 'mercadolibre' in nombre_archivo:
                dato['comercio'] = 'MercadoLibre'
            elif 'exito' in nombre_archivo:
                dato['comercio'] = 'Éxito'
            elif 'falabella' in nombre_archivo:
                dato['comercio'] = 'Falabella'
            elif 'completos' in nombre_archivo:
                dato['comercio'] = 'Scraping Completo'
            else:
                dato['comercio'] = 'Otro'
        
        return datos
    except Exception as e:
        print(f"Error leyendo {archivo}: {str(e)}")
        return []

def subir_datos_a_firebase(db, datos, coleccion):
    """Sube los datos a una colección específica de Firebase"""
    try:
        batch = db.batch()
        contador = 0
        
        for dato in datos:
            # Crear un ID único para cada documento
            doc_id = f"{coleccion}_{dato.get('timestamp_carga', datetime.now().timestamp())}_{contador}"
            
            # Crear referencia al documento
            doc_ref = db.collection(coleccion).document(doc_id)
            
            # Agregar al batch
            batch.set(doc_ref, dato)
            contador += 1
        
        # Ejecutar el batch
        batch.commit()
        print(f"✅ Subidos {contador} documentos a la colección '{coleccion}'")
        return contador
        
    except Exception as e:
        print(f"Error subiendo datos a Firebase: {str(e)}")
        return 0

def procesar_archivos_excel():
    """Procesa todos los archivos Excel generados por los scrapers"""
    
    # Inicializar Firebase
    db = inicializar_firebase()
    if not db:
        print("❌ No se pudo conectar a Firebase")
        return
    
    # Buscar archivos en la carpeta correcta (Docker: /app/output, local: directorio actual)
    if os.path.exists('/app/output'):
        carpeta_busqueda = '/app/output'
        archivos_excel = glob.glob(f"{carpeta_busqueda}/*.xlsx")
    else:
        carpeta_busqueda = '.'
        archivos_excel = glob.glob("*.xlsx")
    
    if not archivos_excel:
        print(f"❌ No se encontraron archivos Excel en la carpeta '{carpeta_busqueda}'")
        return
    
    print(f"📁 Encontrados {len(archivos_excel)} archivos Excel")
    
    total_documentos = 0
    
    for archivo in archivos_excel:
        print(f"\n📊 Procesando: {archivo}")
        
        # Leer datos del Excel
        datos = leer_excel_a_datos(archivo)
        
        if not datos:
            print(f"⚠️ No se pudieron leer datos de {archivo}")
            continue
        
        # Usar una sola colección para todos los datos
        coleccion = 'productos_scraping'
        
        print(f"📤 Subiendo {len(datos)} registros a colección '{coleccion}'")
        
        # Subir datos a Firebase
        documentos_subidos = subir_datos_a_firebase(db, datos, coleccion)
        total_documentos += documentos_subidos
    
    print(f"\n🎉 Proceso completado!")
    print(f"📊 Total de documentos subidos: {total_documentos}")
    print(f"📁 Archivos procesados: {len(archivos_excel)}")

def crear_colecciones_firebase():
    """Crea las colecciones necesarias en Firebase (opcional)"""
    db = inicializar_firebase()
    if not db:
        return
    
    colecciones = [
        'productos_scraping'
    ]
    
    for coleccion in colecciones:
        try:
            # Crear un documento de prueba para crear la colección
            doc_ref = db.collection(coleccion).document('inicial')
            doc_ref.set({
                'creado_el': datetime.now().isoformat(),
                'descripcion': f'Colección para datos de {coleccion}'
            })
            print(f"✅ Colección '{coleccion}' creada/verificada")
        except Exception as e:
            print(f"⚠️ Error con colección '{coleccion}': {str(e)}")

if __name__ == "__main__":
    print("🚀 Iniciando uploader de Firebase")
    print("=" * 50)
    
    # Verificar que existe el archivo de credenciales
    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ Error: No se encontró el archivo de credenciales '{CREDENTIALS_FILE}'")
        print("📝 Por favor:")
        print("1. Ve a Firebase Console")
        print("2. Configuración del proyecto > Cuentas de servicio")
        print("3. Genera una nueva clave privada")
        print("4. Descarga el archivo JSON y renómbralo a 'firebase-credentials.json'")
        print("5. Colócalo en esta carpeta")
        exit(1)
    
    # Crear colecciones (opcional)
    print("📋 Verificando/creando colecciones...")
    crear_colecciones_firebase()
    
    # Procesar archivos
    print("\n📁 Procesando archivos Excel...")
    procesar_archivos_excel()
    
    print("\n✅ Proceso completado!") 