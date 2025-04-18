import argparse
import time
import sys
import logging
from utils.logger import setup_logger
from utils.directorio_utils import validar_directorio, procesar_directorio

def main():
    # Configuración del parser de argumentos
    parser = argparse.ArgumentParser(
        description='Contador de archivos en directorios',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        'directorio',
        type=str,
        help='Ruta del directorio a analizar'
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Muestra información detallada'
    )
    args = parser.parse_args()
    
    # Configurar el logger
    log_directory = 'logs'
    setup_logger(log_directory)
    
    path = args.directorio
    try:
        logging.info(f"Inicio del proceso para el directorio $$ {path}")
        validacion_directorio = validar_directorio(path) # Devuelve 1 si el directorio es válido
    except ValueError as e:
        logging.error(f"Error al validar el directorio {path} $$ {e}")
        return
    
    if validacion_directorio != 1:
        logging.error(f"El directorio no es válido $$ {path}")
        print(f"\nError: El directorio no es válido.", file=sys.stderr)
        return
    logging.info(f"El directorio es válido $$ {path}")    
    
    try:
        inicio = time.time()
        resultados = procesar_directorio(path)  # Llamada a la función para analizar el directorio
        
        #resultados = {"num_files": 0, "num_dirs": 0, "archivos_validos": 0}  # Simulación de resultados
        tiempo = time.time() - inicio

        # Mostrar resultados
        if args.verbose:
            logging.info(f"Directorio analizado: {path}")
            logging.info(f"Archivos procesados: {resultados['num_files']:,}")
            logging.info(f"Subdirectorios encontrados: {resultados['num_dirs']:,}")
            logging.info(f"Archivos válidos procesados: {resultados['archivos_validos']:,}")
            logging.info(f"Archivos descartados por tipo no válido: {resultados['num_files'] - resultados['archivos_validos']:,}")
            logging.info(f"Tiempo de análisis: {tiempo:.2f} segundos")
            print(f"\n{' Directorio analizado ':-^50}") # Encabezado de 50 caracteres, centrado
            print(f"Ruta completa: {path}")
            print(f"Archivos procesados: {resultados['num_files']:,}")
            print(f"Archivos válidos procesados: {resultados['archivos_validos']:,}")
            print(f"Archivos descartados por tipo no válido: {resultados['num_files'] - resultados['archivos_validos']:,}")
            print(f"Subdirectorios encontrados: {resultados['num_dirs']:,}")
            print(f"Tiempo de análisis: {tiempo:.2f} segundos")
            print('-' * 50)
        else:
            print(f"\nArchivos encontrados: {resultados['num_files']}")
            print(f"Subdirectorios encontrados: {resultados['num_dirs']}")
            print(f"Archivos válidos procesados: {resultados['archivos_validos']}")
            print(f"Archivos descartados por tipo no válido: {resultados['num_files'] - resultados['archivos_validos']}\n")
        
        logging.info(f"Fin del proceso para el directorio: {args.directorio}")

    except Exception as e:
        logging.error(f" Se ha producido un error $$ {e}")
        print(f"\n Se ha producido un error: {e}", file=sys.stderr)

if __name__ == "__main__":
    sys.exit(main())