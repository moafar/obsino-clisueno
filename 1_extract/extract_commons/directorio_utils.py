from pathlib import Path
import logging
import os
from tqdm import tqdm
from extract_commons.archivo_utils import procesar_archivo
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
    psg_archive_dir: Path | None = None,
    known_psg: dict[str, str] | None = None,
) -> dict:

    tipos_validos = [e.lower() for e in (tipos_validos or ["docx", "doc", "rtf"])]

    num_files = 0
    num_dirs = 0
    archivos_validos = 0
    archivos_extraidos = 0
    archivos_registrados = 0
    archivos_rechazados = 0
    archivos_duplicados = 0
    archivos_fallo_archivado = 0
    archivos_reintentados = 0
    errores_recorrido = 0

    ruta = Path(ruta).resolve()
    if psg_archive_dir is not None:
        destination = psg_archive_dir.resolve()
        def scan_error(error):
            nonlocal errores_recorrido
            errores_recorrido += 1
            logging.error("Directorio PSG no accesible: %s", error.filename)
        def psg_files():
            nonlocal num_dirs
            for current, directories, files in os.walk(
                    ruta, topdown=True, followlinks=False, onerror=scan_error):
                directories[:] = [name for name in directories
                                  if not Path(current, name).resolve().is_relative_to(destination)]
                num_dirs += len(directories)
                for name in files:
                    yield Path(current, name)
        archivos = psg_files()
    else:
        archivos = list(ruta.glob(glob_patron))

    iterable = tqdm(archivos, desc="Procesando archivos") if barra_progreso else archivos
    for archivo in iterable:
        if archivo.is_file():
            num_files += 1
            extension = archivo.suffix[1:].lower()
            if extension in tipos_validos:
                archivos_validos += 1
                logging.info("Procesando archivo válido")
                try:
                    if psg_archive_dir is not None and archivo.is_symlink():
                        raise RuntimeError("No se procesan enlaces simbólicos PSG")
                    result = (procesar_archivo(archivo, psg_archive_dir=psg_archive_dir,
                                               known_psg=known_psg)
                              if psg_archive_dir is not None else procesar_archivo(archivo))
                    if result == "duplicate":
                        archivos_duplicados += 1
                    elif result in ("new_archive_failed", "retry_archive_failed"):
                        archivos_fallo_archivado += 1
                        if result == "new_archive_failed":
                            archivos_registrados += 1
                    elif result == "retried":
                        archivos_reintentados += 1
                    elif result == "new" or result is True:
                        archivos_extraidos += 1
                        archivos_registrados += 1
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
        "archivos_registrados": archivos_registrados,
        "archivos_rechazados": archivos_rechazados,
        "archivos_duplicados": archivos_duplicados,
        "archivos_fallo_archivado": archivos_fallo_archivado,
        "archivos_reintentados": archivos_reintentados,
        "errores_recorrido": errores_recorrido,
    }
