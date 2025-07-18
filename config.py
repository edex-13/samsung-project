# Configuración del scraper de MercadoLibre Colombia

# Lista de dispositivos a buscar
DISPOSITIVOS = [
    "samsung galaxy s25 ultra",
    # "samsung galaxy s24 ultra", 
    # "samsung z flip 6",
    # "samsung galaxy a56",
    # "samsung galaxy a16",
]

# Condiciones a buscar (nuevo y usado)
CONDICIONES = ["nuevo", "usado"]

# Número máximo de páginas por búsqueda - AUMENTADO PARA MODO COMPLETO
MAX_PAGINAS = 1

# Configuración del navegador
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080

# Timeouts - AUMENTADOS PARA MODO COMPLETO
TIMEOUT_PRODUCTOS = 60000  # milisegundos (1 minuto)

# Archivo de salida
ARCHIVO_SALIDA = "resultados_multiple.xlsx"

# Delay entre búsquedas para evitar bloqueos - AUMENTADO PARA MODO COMPLETO
DELAY_ENTRE_BUSQUEDAS = 600  # segundos (10 minutos entre búsquedas) 