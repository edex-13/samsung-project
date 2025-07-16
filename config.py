# Configuración del scraper de MercadoLibre Colombia

# Lista de dispositivos a buscar
DISPOSITIVOS = [
    "samsung galaxy s24 ultra 5g",
]

# Condiciones a buscar (nuevo y usado)
CONDICIONES = ["nuevo", "usado"]

# Número máximo de páginas por búsqueda
MAX_PAGINAS = 2

# Configuración del navegador
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
VIEWPORT_WIDTH = 1920
VIEWPORT_HEIGHT = 1080

# Timeouts
TIMEOUT_PRODUCTOS = 30000  # milisegundos (aumentado a 30 segundos)

# Archivo de salida
ARCHIVO_SALIDA = "resultados_multiple.xlsx"

# Delay entre búsquedas para evitar bloqueos
DELAY_ENTRE_BUSQUEDAS = 3  # segundos 