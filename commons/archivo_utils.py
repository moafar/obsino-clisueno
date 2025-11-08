from __future__ import annotations
from pathlib import Path
import re, csv, logging, os
from dataclasses import dataclass
from typing import Callable, Dict, Optional, List

# --- utils de texto ---
from commons.texto_utils import (
    extraer_texto_docx, extraer_texto_rtf, extraer_texto_doc,
    normalizar_texto, extraer_subcadenas, determinar_tipos_examenes
)

# --- tus imports (src.*) ---
from src.basal.procesar_basal import procesar_basal_doc, procesar_basal_rtf
from src.xpap.procesar_xpap import procesar_xpap_doc, procesar_xpap_rtf, procesar_xpap_docx
from src.dam.procesar_dam import procesar_dam_doc, procesar_dam_rtf
from src.actigrafia.procesar_actigrafia import procesar_actigrafia_doc
from src.capnografia.procesar_capnografia import procesar_capnografia_doc, procesar_capnografia_rtf
from src.autocpap.procesar_autocpap import procesar_autocpap_docx
from src.poligrafia.procesar_poligrafia import procesar_poligrafia_docx

# --- configuración general ---
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Limpieza preventiva (opcional): elimina unificado.csv si quedara de versiones previas
GENERIC_PATH = OUTPUT_DIR / "unificado.csv"
if GENERIC_PATH.exists():
    try:
        GENERIC_PATH.unlink()
        logging.info("Eliminado output/unificado.csv residual de ejecuciones anteriores.")
    except Exception as e:
        logging.warning(f"No se pudo eliminar output/unificado.csv: {e}")

EXCLUDE_PATTERNS = re.compile(r"(?:\bO2\b|OXIG|OXÍG|OXIGENO|OXÍGENO)", re.IGNORECASE)

TEXT_EXTRACTORS: Dict[str, Callable[[Path], str]] = {
    ".docx": extraer_texto_docx,
    ".rtf":  extraer_texto_rtf,
    ".doc":  extraer_texto_doc,
}

# Activa solo lo implementado
TIPOS_ACTIVOS = {"BASAL", "CPAP", "BPAP"}

def _extract_text(archivo: Path) -> Optional[str]:
    ext = archivo.suffix.lower()
    extractor = TEXT_EXTRACTORS.get(ext)
    if not extractor:
        logging.error(f"Extensión de archivo no soportada: {ext}")
        return None
    try:
        return extractor(archivo)
    except Exception as e:
        logging.error(f"Error inesperado al leer {archivo} $$ {e}")
        return None

# ---- utilidades CSV con unión de cabeceras ----
def _read_existing_rows_and_header(path: Path) -> tuple[List[dict], List[str]]:
    if not path.exists():
        return [], []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        rows = list(reader)
    return rows, header

def _rewrite_with_header(path: Path, header: List[str], rows: List[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in header})

def _append_row_unified(row: Dict, outfile: Path) -> None:
    # Guardia dura: nunca escribir a unificado.csv
    if outfile.name == "unificado.csv":
        logging.error("Intento de escribir en 'unificado.csv' bloqueado. Revisa el mapeo UNIFIED_FILE_FOR.")
        return

    rows, header = _read_existing_rows_and_header(outfile)
    new_keys = list(row.keys())

    if not header:
        _rewrite_with_header(outfile, new_keys, [row])
        return

    if set(header) != set(new_keys):
        union = header[:]  # preservar orden previo
        for k in new_keys:
            if k not in union:
                union.append(k)
        rows.append(row)
        _rewrite_with_header(outfile, union, rows)
        return

    with outfile.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writerow(row)

# -----------------------------------------------

@dataclass(frozen=True)
class ExamSpec:
    start_pattern: str
    end_pattern: str
    processors: Dict[str, Callable]  # por extensión

EXAMS: Dict[str, ExamSpec] = {
    "BASAL": ExamSpec(
        r"INFORME\s+DE\s+POLISOMNOGRAFIA\s+BASAL",
        r"Saturacion\s+O2\s+Minima\s+durante\s+el\s+sueno",
        {".rtf": procesar_basal_rtf, ".doc": procesar_basal_doc}
    ),
    "CPAP": ExamSpec(
        r"^", r"$",
        {".rtf": procesar_xpap_rtf, ".doc": procesar_xpap_doc, ".docx": procesar_xpap_docx}
    ),
    "BPAP": ExamSpec(
        r"^", r"$",
        {".rtf": procesar_xpap_rtf, ".doc": procesar_xpap_doc, ".docx": procesar_xpap_docx}
    ),
    # Definidos pero desactivados (no se escribirán)
    "DAM": ExamSpec(
        r"INFORME\s+DE\s+POLISOMNOGRAFIA\s+BASAL\s+CON\s+DISPOSITIVO\s+(?:DE\s+AVANCE\s+)?MANDIBULAR",
        r"CONCLUSION(?:ES)?",
        {".rtf": procesar_dam_rtf, ".doc": procesar_dam_doc}
    ),
    "ACTIGRAFIA": ExamSpec(
        r"Fecha", r"ESTADISTICAS DIARIAS",
        {".doc": procesar_actigrafia_doc}
    ),
    "CAPNOGRAFIA": ExamSpec(
        r"INFORME\s+DE\s+CAPNOGRAFIA", r"CONCLUSION(?:ES)?",
        {".rtf": procesar_capnografia_rtf, ".doc": procesar_capnografia_doc}
    ),
    "AUTOCPAP": ExamSpec(
        r"^", r"Informe\s+de\s+cumplimiento",
        {".docx": procesar_autocpap_docx}
    ),
    "POLIGRAFIA": ExamSpec(
        r"^", r"Indicacion\s+del\s+estudio",
        {".docx": procesar_poligrafia_docx}
    ),
}

# SOLO los activos en el mapeo de salida
UNIFIED_FILE_FOR: Dict[str, str] = {
    "BASAL": "unificado_basal.csv",
    "CPAP":  "unificado_xpap.csv",
    "BPAP":  "unificado_xpap.csv",
}

def _outfile_for_tipo(tipo: str) -> Optional[Path]:
    """
    Devuelve el Path del CSV unificado para el tipo activo.
    Sin fallback: si no está mapeado o no está activo, se omite.
    """
    if tipo not in TIPOS_ACTIVOS:
        return None
    nombre = UNIFIED_FILE_FOR.get(tipo)
    if not nombre:
        logging.warning(f"Tipo {tipo} activo sin archivo unificado configurado. Se omite escritura.")
        return None
    # Guardia adicional: bloquear cualquier genérico
    if nombre == "unificado.csv":
        logging.error("Nombre 'unificado.csv' no permitido. Ajusta UNIFIED_FILE_FOR.")
        return None
    return OUTPUT_DIR / nombre

def procesar_archivo(archivo: Path) -> None:
    """Procesa un archivo y escribe en un CSV unificado por tipo de examen (solo activos)."""
    if EXCLUDE_PATTERNS.search(archivo.name):
        logging.info(f"Archivo excluido por patrón OXIGENO en filename: {archivo.name}")
        return

    texto = _extract_text(archivo)
    if not texto:
        return

    texto_norm = normalizar_texto(texto)
    logging.debug(f"Texto normalizado: {texto_norm}")

    tipos = determinar_tipos_examenes(texto_norm)
    if not tipos:
        logging.warning(f"No se encontraron tipos de examen en el archivo {archivo}.")
        return

    ext = archivo.suffix.lower()

    for tipo in tipos:
        if tipo not in TIPOS_ACTIVOS:
            logging.info(f"Omitido tipo no implementado: {tipo}")
            continue

        spec = EXAMS.get(tipo)
        logging.info(f"Procesando examen de {tipo}")
        if not spec:
            logging.warning(f"Tipo de examen no manejado: {tipo}")
            continue

        texto_relevante = extraer_subcadenas(texto_norm, spec.start_pattern, spec.end_pattern)
        if not texto_relevante:
            logging.error(f"No se encontraron subcadenas para {tipo} en el archivo {archivo}.")
            continue

        procesador = spec.processors.get(ext)
        if not procesador:
            logging.warning(f"Extensión {ext} no soportada para tipo {tipo} en archivo {archivo}.")
            continue

        logging.info(f"** INICIO ** Procesando archivo {tipo} válido: {archivo}")
        try:
            try:
                resultados = procesador(texto_relevante, archivo)  # (texto, archivo)
            except TypeError:
                resultados = procesador(texto_relevante)           # (texto)
        except Exception as e:
            logging.error(f"Error procesando {tipo} en {archivo}: {e}")
            continue

        outfile = _outfile_for_tipo(tipo)
        if not outfile:
            continue  # sin archivo mapeado → no escribir
        _append_row_unified(resultados, outfile)
        logging.info(f"** FIN ** Procesamiento {tipo} → {outfile.name} para {archivo}")
