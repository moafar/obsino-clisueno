from pathlib import Path
import logging
from tqdm import tqdm 
from utils.archivo_utils import procesar_archivo

def validar_directorio(path) -> int:
    """
    Valida si el directorio especificado es válido y accesible.
    
    Returns:
        int: 1 si es válido
    Raises:
        ValueError: Si la ruta no es un directorio válido
    """
    
    ruta = Path(path).resolve()
    
    # Verificar si la ruta es un directorio
    if not ruta.exists():
        raise ValueError(f"La ruta proporcionada no existe: {ruta}")
    if not ruta.is_dir():
        raise ValueError(f"La ruta proporcionada no es un directorio válido: {ruta}")
    return 1


def procesar_directorio(ruta: Path) -> dict:
    """
    Analiza archivos en un directorio dado, verifica su tipo, cuenta archivos y subdirectorios,
    y envía a procesar los archivos válidos.
    
    Args:
        ruta: Path del directorio a analizar
        
    Returns:
        dict: Diccionario con el número total de archivos, subdirectorios encontrados y archivos válidos procesados
        
    """
    
    TIPOS_VALIDOS = ["docx", "doc", "rtf"]  # Tipos de archivos válidos para procesar
    
    num_files = 0
    num_dirs = 0
    archivos_validos = 0

    ruta = Path(ruta).resolve()
    archivos = list(ruta.glob('**/*'))  # Convertir el generador en una lista para usarlo con tqdm
    for archivo in tqdm(archivos, desc="Procesando archivos"):  # Agregar tqdm para la barra de progreso
        if archivo.is_file():
            num_files += 1
            extension = archivo.suffix[1:].lower()  # Obtener la extensión del archivo sin el punto inicial y en minúsculas
            if extension in TIPOS_VALIDOS:
                archivos_validos += 1
                logging.info(f"Procesando archivo válido: {archivo}")
                procesar_archivo(archivo) # <-- Llamada a la función para analizar el archivo ***

            else:
                logging.warning(f"Archivo descartado por tipo no válido ({extension}): {archivo}")
        elif archivo.is_dir():
            num_dirs += 1

    return {
        'num_files': num_files,
        'num_dirs': num_dirs,
        'archivos_validos': archivos_validos
    }