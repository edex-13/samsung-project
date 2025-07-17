# Configuración del scraper de MercadoLibre Colombia

# Lista de dispositivos a buscar
DISPOSITIVOS = [
    "samsung galaxy s25 ultra",
    "samsung galaxy s24 ultra", 
    "samsung z flip 6",
    "samsung galaxy a56",
    "samsung galaxy a16",
    "samsung galaxy s25",
    "samsung galaxy s24",
    "samsung z fold 6"
]

# Condiciones a buscar (nuevo y usado)
CONDICIONES = ["nuevo", "usado"]

# Número máximo de páginas por búsqueda
MAX_PAGINAS = 2

# Configuración del navegador
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080

# Timeouts - INCREMENTADOS SIGNIFICATIVAMENTE
TIMEOUT_PRODUCTOS = 120000  # milisegundos (aumentado a 2 minutos)

# Archivo de salida
ARCHIVO_SALIDA = "resultados_multiple.xlsx"

# Delay entre búsquedas para evitar bloqueos - TIEMPOS REDUCIDOS A LA MITAD
DELAY_ENTRE_BUSQUEDAS = 60  # segundos (1 minuto entre búsquedas) 