from __future__ import annotations
from pathlib import Path
import re, csv, logging, os
from dataclasses import dataclass
from typing import Callable, Dict, Optional, List
import hashlib
from datetime import datetime


REPO_ROOT = Path(__file__).resolve().parents[2]

def marcar_version_extraccion() -> str:
    return f"Extraido: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

def generar_hash_archivo(ruta_archivo: str) -> str:
    """Genera un hash MD5 del contenido del archivo para usar como UUID determinista."""
    hash_md5 = hashlib.md5()
    try:
        with open(ruta_archivo, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logging.error(f"Error generando hash para {ruta_archivo}: {e}")
        return "N/A"

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
# Rutas absolutas para evitar dependencia del cwd de ejecución.
OUTPUT_DIR = REPO_ROOT / "staging"


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

EXCLUDE_PATTERNS = re.compile(r"(?:\bO2\b|OXIG|OXÍG|OXIGENO|OXÍGENO)", re.IGNORECASE)

TEXT_EXTRACTORS: Dict[str, Callable[[Path], str]] = {
    ".docx": extraer_texto_docx,
    ".rtf":  extraer_texto_rtf,
    ".doc":  extraer_texto_doc,
}

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
DEFAULT_UNIFIED_FILE_FOR: Dict[str, str] = {
    "BASAL": "unificado_basal.csv",
    "CPAP":  "unificado_xpap.csv",
    "BPAP":  "unificado_xpap.csv",
}

# Mapeo de prefijos para renombrado
DEFAULT_PREFIXES: Dict[str, str] = {
    "BASAL": "bs",
    "CPAP": "xp",
    "BPAP": "xp",
    "DAM": "dm",
    "ACTIGRAFIA": "ac",
    "CAPNOGRAFIA": "cp",
    "AUTOCPAP": "xp", # AutoCPAP también es XPAP
    "POLIGRAFIA": "pg"
}

PROCESSED_DIR = REPO_ROOT / "procesados"

TIPOS_ACTIVOS = set(DEFAULT_UNIFIED_FILE_FOR.keys())
UNIFIED_FILE_FOR: Dict[str, str] = dict(DEFAULT_UNIFIED_FILE_FOR)
PREFIXES: Dict[str, str] = dict(DEFAULT_PREFIXES)


def configure_subflows(
    unified_file_for: Optional[Dict[str, str]] = None,
    prefixes: Optional[Dict[str, str]] = None,
    output_dir: Optional[Path] = None,
) -> None:
    global TIPOS_ACTIVOS, UNIFIED_FILE_FOR, PREFIXES, OUTPUT_DIR

    if output_dir:
        OUTPUT_DIR = Path(output_dir).resolve()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if unified_file_for:
        UNIFIED_FILE_FOR = {
            str(tipo).upper().strip(): str(nombre).strip()
            for tipo, nombre in unified_file_for.items()
            if str(tipo).strip() and str(nombre).strip()
        }
    else:
        UNIFIED_FILE_FOR = dict(DEFAULT_UNIFIED_FILE_FOR)

    TIPOS_ACTIVOS = set(UNIFIED_FILE_FOR.keys())

    if prefixes:
        PREFIXES = {
            str(tipo).upper().strip(): str(prefijo).strip()
            for tipo, prefijo in prefixes.items()
            if str(tipo).strip() and str(prefijo).strip() and str(tipo).upper().strip() in TIPOS_ACTIVOS
        }
    else:
        PREFIXES = {
            tipo: prefijo
            for tipo, prefijo in DEFAULT_PREFIXES.items()
            if tipo in TIPOS_ACTIVOS
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
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR / nombre

def _parse_date_folder(date_str: str) -> str:
    """Extrae YYYY-MM de una fecha string para organizar carpetas."""
    if not date_str or date_str == "N/A":
        return "sin_fecha"
    
    # Normalizar separadores
    norm = date_str.replace("-", "/").strip()
    parts = norm.split("/")
    
    if len(parts) != 3:
        return "sin_fecha"
        
    # Asumimos formatos comunes: DD/MM/YYYY o YYYY/MM/DD
    try:
        # Si el primer componente es año (yyyy)
        if len(parts[0]) == 4:
            return f"{parts[0]}-{parts[1].zfill(2)}"
        # Si el último componente es año (yyyy) -> DD/MM/YYYY
        if len(parts[2]) == 4:
            return f"{parts[2]}-{parts[1].zfill(2)}"
    except Exception:
        pass
        
    return "sin_fecha"

def _move_processed_file(archivo: Path, prefixes: set, date_str: str) -> None:
    """Renombra y mueve el archivo procesado."""
    if not prefixes:
        return

    # 1. Determinar carpeta destino
    folder_name = _parse_date_folder(date_str)
    dest_dir = PROCESSED_DIR / folder_name
    dest_dir.mkdir(parents=True, exist_ok=True)

    # 2. Construir nuevo nombre
    # Evitar duplicar prefijos si ya existen (aunque el usuario dijo que agregue)
    # Ordenar prefijos para consistencia
    prefix_str = "_".join(sorted(prefixes))
    new_name = f"{prefix_str}_{archivo.name}"
    
    # 3. Mover archivo (shutil.move maneja copy+delete si es cross-fs, o rename si es mismo fs)
    import shutil
    dest_path = dest_dir / new_name
    
    try:
        shutil.move(str(archivo), str(dest_path))
        logging.info(f"Archivo movido y renombrado: {archivo.name} -> {dest_path}")
    except Exception as e:
        logging.error(f"Error moviendo archivo {archivo} a {dest_path}: {e}")

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
    
    processing_results = [] # (tipo, success)
    detected_date = None
    applied_prefixes = set()

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
            
            # Capturar fecha si aun no tenemos una
            if not detected_date and "fecha_estudio" in resultados:
                detected_date = resultados["fecha_estudio"]
                
             # Marcar éxito para este tipo
            processing_results.append((tipo, True))
            
            # Agregar prefijo correspondiente
            if prefix := PREFIXES.get(tipo):
                applied_prefixes.add(prefix)

        except Exception as e:
            logging.error(f"Error procesando {tipo} en {archivo}: {e}")
            processing_results.append((tipo, False))
            continue

        outfile = _outfile_for_tipo(tipo)
        if not outfile:
            continue  # sin archivo mapeado → no escribir
        _append_row_unified(resultados, outfile)
        logging.info(f"** FIN ** Procesamiento {tipo} → {outfile.name} para {archivo}")

    # Finalizar: Mover y renombrar si hubo al menos un éxito
    if any(success for _, success in processing_results):
        _move_processed_file(archivo, applied_prefixes, detected_date)
