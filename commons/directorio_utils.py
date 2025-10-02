from pathlib import Path
import logging
from tqdm import tqdm
from commons.archivo_utils import procesar_archivo

def validar_directorio(path) -> Path:
    ruta = Path(path).resolve()
    if not ruta.exists():
        raise ValueError(f"La ruta proporcionada no existe $$ {ruta}")
    if not ruta.is_dir():
        raise ValueError(f"La ruta proporcionada no es un directorio válido $$ {ruta}")
    return ruta  # <- devuelve Path útil

def procesar_directorio(
    ruta: Path,
    tipos_validos: list[str] | None = None,
    glob_patron: str = "**/*",
    barra_progreso: bool = True,
) -> dict:

    tipos_validos = [e.lower() for e in (tipos_validos or ["docx", "doc", "rtf"])]

    num_files = 0
    num_dirs = 0
    archivos_validos = 0

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
                logging.info(f"Procesando archivo válido: {archivo}")
                try:
                    procesar_archivo(archivo)
                except Exception as e:
                    logging.critical(f"Error al procesar el archivo {archivo} $$ {e}")
            else:
                logging.warning(f"Archivo descartado por tipo no válido ({extension}) $$ {archivo}")
        elif archivo.is_dir():
            num_dirs += 1

    return {"num_files": num_files, "num_dirs": num_dirs, "archivos_validos": archivos_validos}
