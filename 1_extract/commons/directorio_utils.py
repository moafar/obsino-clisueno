from pathlib import Path
import logging
from tqdm import tqdm
from commons.archivo_utils import procesar_archivo
from typing import List, Optional

def validar_directorio(path) -> Path:
    ruta = Path(path).resolve()
    if not ruta.exists():
        raise ValueError(f"La ruta proporcionada no existe $$ {ruta}")
    if not ruta.is_dir():
        raise ValueError(f"La ruta proporcionada no es un directorio válido $$ {ruta}")
    return ruta  # <- devuelve Path útil

def procesar_directorio(
    ruta: Path,
    tipos_validos: Optional[List[str]] = None,
    glob_patron: str = "**/*",
    barra_progreso: bool = True,
) -> dict:

    tipos_validos = [e.lower() for e in (tipos_validos or ["docx", "doc", "rtf"])]

    num_files = 0
    num_dirs = 0
    archivos_validos = 0
    archivos_extraidos = 0
    archivos_rechazados = 0

    ruta = Path(ruta).resolve()
    archivos_iter = ruta.glob(glob_patron)
    archivos = list(archivos_iter)

    iterable = tqdm(archivos, desc="Procesando archivos") if barra_progreso else archivos
    for archivo in iterable:
        if archivo.is_file():
            num_files += 1
            extension = archivo.suffix[1:].lower()
            if extension in tipos_validos:
                archivos_validos += 1
                logging.info("Procesando archivo válido")
                try:
                    if procesar_archivo(archivo):
                        archivos_extraidos += 1
                    else:
                        archivos_rechazados += 1
                except Exception as e:
                    archivos_rechazados += 1
                    logging.critical("Error al procesar documento: %s", type(e).__name__)
            else:
                logging.warning("Archivo descartado por tipo no válido (%s)", extension)
        elif archivo.is_dir():
            num_dirs += 1

    return {
        "num_files": num_files, "num_dirs": num_dirs,
        "archivos_validos": archivos_validos,
        "archivos_extraidos": archivos_extraidos,
        "archivos_rechazados": archivos_rechazados,
    }
