import argparse
from pathlib import Path
import time
import sys
import re
import logging
from tqdm import tqdm 
from utils.logger import setup_logger
from utils.extract_text import extraer_texto_docx, extraer_texto_rtf, extraer_texto_pdf, extraer_texto_doc

TIPOS_VALIDOS = ["docx", "doc", "rtf", "pdf"]

def analizar_archivo(archivo: Path) -> None:
    extension = archivo.suffix[1:].lower()
    texto = ""

    if extension == "docx":
        texto = extraer_texto_docx(archivo)
    elif extension == "rtf":
        texto = extraer_texto_rtf(archivo)
    elif extension == "pdf":
        texto = extraer_texto_pdf(archivo)
    elif extension == "doc":
        texto = extraer_texto_doc(archivo)

    if texto is None or texto.strip() == "":
        logging.error(f"⚠️ No se pudo extraer texto del archivo: {archivo}")
        return

    texto = re.sub(r'\s+', ' ', texto)  # Reemplazar múltiples espacios por uno solo
    texto = re.sub(r'\n+', '|', texto)  # Reemplazar múltiples saltos de línea por uno solo
    texto = re.sub(r'\r+', '|', texto)  # Eliminar retornos de carro
    texto = re.sub(r'\t+', '|', texto)  # Reemplazar múltiples tabulaciones por un espacio
    texto = texto.strip()  # Eliminar espacios en blanco al inicio y al final
        
    resultado = {"archivo": archivo.name, "tamaño": archivo.stat().st_size, "texto": texto}
    logging.info(f"Archivo analizado: {archivo}")
    print(f"\n{' Archivo analizado ':-^50}")  # Encabezado de 50 caracteres, centrado
    print(f"Nombre: {resultado['archivo']}")
    print(resultado)
    print("-" * 50)
    return

def analizar_directorio(ruta: Path) -> dict:
    """
    Analiza archivos en un directorio dado, verifica su tipo, cuenta archivos y subdirectorios,
    y procesa los archivos válidos.
    
    Args:
        ruta: Path del directorio a analizar
        
    Returns:
        dict: Diccionario con el número total de archivos, subdirectorios encontrados y archivos válidos procesados
        
    Raises:
        ValueError: Si la ruta no es un directorio válido
    """
    num_files = 0
    num_dirs = 0
    archivos_validos = 0

    archivos = list(ruta.glob('**/*'))  # Convertir el generador en una lista para usarlo con tqdm
    for archivo in tqdm(archivos, desc="Procesando archivos"):  # Agregar tqdm para la barra de progreso
        if archivo.is_file():
            num_files += 1
            extension = archivo.suffix[1:].lower()  # Obtener la extensión del archivo sin el punto inicial y en minúsculas
            if extension in TIPOS_VALIDOS:
                archivos_validos += 1
                logging.info(f"Procesando archivo válido: {archivo}")
                analizar_archivo(archivo)
            else:
                logging.warning(f"Archivo descartado por tipo no válido ({extension}): {archivo}")
        elif archivo.is_dir():
            num_dirs += 1

    return {
        'num_files': num_files,
        'num_dirs': num_dirs,
        'archivos_validos': archivos_validos
    }

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
    
    try:
        logging.info(f"Inicio del proceso para el directorio: {args.directorio}")
        inicio = time.time()
        ruta = Path(args.directorio).resolve()
        
        # Verificar si la ruta es un directorio
        if not ruta.exists():
            logging.error(f"La ruta proporcionada no existe: {ruta}")
            raise ValueError(f"La ruta proporcionada no existe: {ruta}")
        if not ruta.is_absolute():
            logging.error(f"La ruta proporcionada no es absoluta: {ruta}")
            raise ValueError(f"La ruta proporcionada no es absoluta: {ruta}")
        if not ruta.is_dir():
            logging.error(f"La ruta proporcionada no es un directorio válido: {ruta}")
            raise ValueError(f"La ruta proporcionada no es un directorio válido: {ruta}")
        
        resultados = analizar_directorio(ruta)
        tiempo = time.time() - inicio
        
        # Mostrar resultados
        if args.verbose:
            logging.info(f"Directorio analizado: {ruta}")
            logging.info(f"Archivos procesados: {resultados['num_files']:,}")
            logging.info(f"Subdirectorios encontrados: {resultados['num_dirs']:,}")
            logging.info(f"Archivos válidos procesados: {resultados['archivos_validos']:,}")
            logging.info(f"Archivos descartados por tipo no válido: {resultados['num_files'] - resultados['archivos_validos']:,}")
            logging.info(f"Tiempo de análisis: {tiempo:.2f} segundos")
            print(f"\n{' Directorio analizado ':-^50}") # Encabezado de 50 caracteres, centrado
            print(f"Ruta completa: {ruta}")
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
        logging.error(f"Error: {str(e)}")
        print(f"\nError: {str(e)}", file=sys.stderr)
        print("")
        return 1
        
    return 0

if __name__ == "__main__":
    sys.exit(main())