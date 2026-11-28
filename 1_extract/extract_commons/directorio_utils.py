from pathlib import Path
import json
import logging
import os
from tqdm import tqdm
from extract_commons.archivo_utils import procesar_archivo
from typing import List, Optional

PSG_REJECTION_REASONS = {
    "EXCLUIDO_OXIGENO": "Nombre excluido por patrón OXIGENO",
    "TEXTO_ILEGIBLE": "Texto del documento ausente o ilegible",
    "NO_PSG_BASAL": "No se identificó un informe PSG basal procesable",
    "UUID_NO_GENERADO": "No se pudo generar el UUID del documento original",
    "EXTRACCION_ILEGIBLE": "Estructura PSG no recuperable",
    "ENLACE_SIMBOLICO": "Enlace simbólico no admitido como documento PSG",
    "ERROR_DOCUMENTO": "Error individual al procesar el documento",
}


def _log_psg_rejection(archivo: Path, code: str) -> None:
    if code not in PSG_REJECTION_REASONS:
        code = "ERROR_DOCUMENTO"
    logging.warning("Rechazo PSG: %s", json.dumps({
        "codigo": code, "origen": str(archivo), "motivo": PSG_REJECTION_REASONS[code]
    }, ensure_ascii=False))

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
    errores_procesamiento = 0

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
                if psg_archive_dir is not None and archivo.is_symlink():
                    archivos_rechazados += 1
                    _log_psg_rejection(archivo, "ENLACE_SIMBOLICO")
                    continue
                try:
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
                        if psg_archive_dir is not None:
                            code = (result.removeprefix("rejected:")
                                    if isinstance(result, str) and result.startswith("rejected:")
                                    else "ERROR_DOCUMENTO")
                            _log_psg_rejection(archivo, code)
                except Exception as e:
                    if psg_archive_dir is not None:
                        errores_procesamiento += 1
                        logging.critical("Fallo técnico PSG al procesar documento: %s",
                                         type(e).__name__)
                    else:
                        archivos_rechazados += 1
                        logging.critical("Error al procesar documento: %s", type(e).__name__)
            else:
                logging.warning("Archivo descartado por tipo no válido (%s)", extension)
        elif archivo.is_dir():
            num_dirs += 1

    result = {
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
    if psg_archive_dir is not None:
        result["errores_procesamiento"] = errores_procesamiento
    return result
