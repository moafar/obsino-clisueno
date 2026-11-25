from __future__ import annotations
from pathlib import Path
import re, csv, logging, os, io, fcntl
import ctypes
import errno
import stat
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
        logging.error("Error generando hash: %s", type(e).__name__)
        return "N/A"

# --- utils de texto ---
from commons.texto_utils import (
    extraer_texto_docx, extraer_texto_rtf, extraer_texto_doc,
    normalizar_texto, extraer_subcadenas, determinar_tipos_examenes
)

# --- tus imports (src.*) ---
from src.basal.procesar_basal import PSG_COLUMNS, PSGExtractionError, procesar_basal_doc, procesar_basal_rtf
from src.xpap.procesar_xpap import procesar_xpap_doc, procesar_xpap_rtf, procesar_xpap_docx
from src.dam.procesar_dam import procesar_dam_doc, procesar_dam_rtf
from src.actigrafia.procesar_actigrafia import procesar_actigrafia_doc
from src.capnografia.procesar_capnografia import procesar_capnografia_doc, procesar_capnografia_rtf
from src.autocpap.procesar_autocpap import procesar_autocpap_docx
from src.poligrafia.procesar_poligrafia import procesar_poligrafia_docx

# --- configuración general ---
# Rutas absolutas para evitar dependencia del cwd de ejecución.
OUTPUT_DIR = (REPO_ROOT / "staging").resolve()

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
        logging.error("Error inesperado al leer documento: %s", type(e).__name__)
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


_PSG_SEEN: dict[Path, tuple[int, set[str]]] = {}


def _append_psg_row(row: Dict, outfile: Path) -> bool:
    """Añade una fila completa, con cabecera fija y UUID idempotente por CSV."""
    header = list(PSG_COLUMNS)
    if set(row) != set(header):
        raise PSGExtractionError("La fila PSG no cumple el esquema de extracción")
    if not row.get("meta_uuid"):
        raise PSGExtractionError("La fila PSG no tiene UUID de origen")
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=header)
    writer.writerow(row)
    encoded_row = buffer.getvalue().encode("utf-8")
    with outfile.open("a+b") as target:
        fcntl.flock(target, fcntl.LOCK_EX)
        try:
            target.seek(0, os.SEEK_END)
            original_size = target.tell()
            if original_size:
                target.seek(0)
                first_line = target.readline()
                if not first_line.endswith(b"\n") or next(csv.reader([first_line.decode("utf-8")]), []) != header:
                    raise PSGExtractionError("CSV PSG existente con cabecera incompatible")
                target.seek(-1, os.SEEK_END)
                if target.read(1) != b"\n":
                    raise PSGExtractionError("CSV PSG existente con última fila incompleta")
            cached = _PSG_SEEN.get(outfile)
            if cached is None or cached[0] != original_size:
                seen = set()
                if original_size:
                    with outfile.open("r", newline="", encoding="utf-8") as source:
                        seen = {record["meta_uuid"] for record in csv.DictReader(source)
                                if record.get("meta_uuid")}
            else:
                seen = cached[1]
            if row["meta_uuid"] in seen:
                _PSG_SEEN[outfile] = (original_size, seen)
                return False
            payload = encoded_row
            if not original_size:
                buffer = io.StringIO(newline="")
                csv.writer(buffer).writerow(header)
                payload = buffer.getvalue().encode("utf-8") + payload
            try:
                target.seek(0, os.SEEK_END)
                if target.write(payload) != len(payload):
                    raise OSError("Escritura CSV PSG incompleta")
                target.flush()
                os.fsync(target.fileno())
            except Exception:
                target.truncate(original_size)
                target.flush()
                raise
            seen.add(row["meta_uuid"])
            _PSG_SEEN[outfile] = (original_size + len(payload), seen)
            return True
        finally:
            fcntl.flock(target, fcntl.LOCK_UN)


def load_known_psg_uuids(output_dir: Path) -> dict[str, str]:
    """Consulta una vez los CSV PSG canónicos previos para reintentos idempotentes."""
    known: dict[str, str] = {}
    for path in output_dir.glob("extract_psg_*.csv"):
        if path.stem.endswith("_transformed"):
            continue
        with path.open("r", newline="", encoding="utf-8") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames != list(PSG_COLUMNS):
                if reader.fieldnames and "meta_uuid" in reader.fieldnames:
                    raise PSGExtractionError(f"CSV PSG incompatible en {path}")
                continue  # CSV anterior al contrato canónico
            for row in reader:
                uuid = row.get("meta_uuid")
                origin = row.get("meta_fuente")
                if not uuid or not origin:
                    raise PSGExtractionError(f"CSV PSG incompleto en {path}")
                previous = known.setdefault(uuid, origin)
                if previous != origin:
                    raise PSGExtractionError("UUID PSG repetido con orígenes distintos en CSV previos")
    return known

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
    "BASAL": "extract_psg_{timestamp}.csv",
    "CPAP":  "extract_xpap_{timestamp}.csv",
    "BPAP":  "extract_xpap_{timestamp}.csv",
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

    # El destino se valida en main antes de configurar y escribir.
    OUTPUT_DIR = Path(output_dir).resolve() if output_dir else (REPO_ROOT / "staging").resolve()

    if unified_file_for is None:
        raise RuntimeError(
            "No se definió 'subflujos.salida_unificada' al configurar los subflujos. Esto es obligatorio."
        )
    UNIFIED_FILE_FOR = {
        str(tipo).upper().strip(): str(nombre).strip()
        for tipo, nombre in unified_file_for.items()
        if str(tipo).strip() and str(nombre).strip()
    }
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
    # Reemplazar {timestamp} si está presente
    if "{timestamp}" in nombre:
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
        nombre = nombre.replace("{timestamp}", ts)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR / nombre


def _psg_date_path(date_str: str | None) -> Path:
    if date_str:
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y"):
            try:
                value = datetime.strptime(str(date_str).strip(), fmt).date()
                return Path(str(value.year)) / f"{value.year:04d}-{value.month:02d}"
            except ValueError:
                continue
    return Path("sin_fecha")


def _rename_noreplace(source: Path, destination: Path, *, destination_dir_fd: int | None = None) -> None:
    """Movimiento atómico sin reemplazo cuando el volumen lo admite."""
    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise OSError(errno.ENOSYS, "renameat2 no disponible")
    renameat2.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                          ctypes.c_char_p, ctypes.c_uint)
    renameat2.restype = ctypes.c_int
    target_fd = -100 if destination_dir_fd is None else destination_dir_fd
    target_name = destination if destination_dir_fd is None else destination.name
    if renameat2(-100, os.fsencode(source), target_fd, os.fsencode(target_name), 1) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), str(destination))


def _open_psg_destination_dir(root: Path, relative: Path) -> int:
    """Abre cada carpeta sin seguir enlaces antes de crear la siguiente."""
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(root, flags)
    try:
        for part in relative.parts:
            try:
                os.mkdir(part, dir_fd=descriptor)
            except FileExistsError:
                pass
            child = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except Exception:
        os.close(descriptor)
        raise


def _same_psg_file(source: Path, destination_name: str, destination_dir_fd: int) -> bool:
    try:
        origin = source.stat(follow_symlinks=False)
        target = os.stat(destination_name, dir_fd=destination_dir_fd, follow_symlinks=False)
    except FileNotFoundError:
        return False
    return (stat.S_ISREG(origin.st_mode) and stat.S_ISREG(target.st_mode) and
            (origin.st_dev, origin.st_ino) == (target.st_dev, target.st_ino))


def _move_psg_file(archivo: Path, prefix: str, date_str: str | None,
                   archive_root: Path, *, allow_complete_link: bool = False) -> Path:
    relative_dir = _psg_date_path(date_str)
    destination = Path(archive_root) / relative_dir / f"{prefix}_{archivo.name}"
    try:
        if not re.fullmatch(r"[A-Za-z0-9_]+", prefix):
            raise RuntimeError("Prefijo PSG no válido para archivar")
        source_stat = archivo.lstat()
        if not stat.S_ISREG(source_stat.st_mode):
            raise RuntimeError("El origen PSG no es un archivo regular")
        archive_root = archive_root.resolve(strict=True)
        if archivo.resolve().is_relative_to(archive_root):
            raise RuntimeError("El documento PSG ya está dentro del destino de archivado")
        if source_stat.st_dev != archive_root.stat().st_dev:
            raise RuntimeError("Origen y destino PSG no están en el mismo dispositivo")
        destination_fd = _open_psg_destination_dir(archive_root, relative_dir)
        try:
            try:
                _rename_noreplace(archivo, destination, destination_dir_fd=destination_fd)
            except OSError as error:
                if error.errno in (errno.EINVAL, errno.ENOSYS, errno.EOPNOTSUPP):
                    try:
                        os.link(archivo, destination.name, dst_dir_fd=destination_fd,
                                follow_symlinks=False)
                    except FileExistsError:
                        if not allow_complete_link or not _same_psg_file(
                                archivo, destination.name, destination_fd):
                            raise
                    if not _same_psg_file(archivo, destination.name, destination_fd):
                        raise RuntimeError("El enlace de archivado no coincide con el origen")
                    os.unlink(archivo)
                elif (error.errno == errno.EEXIST and allow_complete_link and
                      _same_psg_file(archivo, destination.name, destination_fd)):
                    os.unlink(archivo)
                else:
                    raise
        finally:
            os.close(destination_fd)
    except Exception as error:
        logging.error("Traslado PSG fallido (%s): origen=%s destino=%s",
                      type(error).__name__, archivo, destination)
        raise
    logging.info("Traslado PSG correcto: origen=%s destino=%s", archivo, destination)
    return destination

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
        logging.info("Archivo procesado movido y renombrado")
    except Exception as e:
        logging.error("Error moviendo archivo procesado: %s", type(e).__name__)

def procesar_archivo(archivo: Path, *, psg_archive_dir: Path | None = None,
                    known_psg: dict[str, str] | None = None) -> bool | str:
    """Procesa un archivo y escribe en un CSV unificado por tipo de examen (solo activos)."""
    if EXCLUDE_PATTERNS.search(archivo.name):
        logging.info("Archivo excluido por patrón OXIGENO")
        return False

    texto = _extract_text(archivo)
    if not texto:
        return False

    texto_norm = normalizar_texto(texto)

    tipos = determinar_tipos_examenes(texto_norm)
    # print(f"[DEBUG] Tipos detectados en {archivo.name}: {tipos}")
    if not tipos:
        # print(f"[DEBUG] No se encontraron tipos de examen en el archivo {archivo}.")
        return False

    ext = archivo.suffix.lower()
    
    processing_results = [] # (tipo, success)
    detected_date = None
    applied_prefixes = set()


    for tipo in tipos:
        if tipo not in TIPOS_ACTIVOS:
            # print(f"[DEBUG] Omitido tipo no implementado: {tipo}")
            continue

        spec = EXAMS.get(tipo)
        # print(f"[DEBUG] Procesando examen de {tipo}")
        if not spec:
            # print(f"[DEBUG] Tipo de examen no manejado: {tipo}")
            continue

        texto_relevante = (
            texto if tipo == "BASAL"
            else extraer_subcadenas(texto_norm, spec.start_pattern, spec.end_pattern)
        )
        if not texto_relevante:
            # print(f"[DEBUG] No se encontraron subcadenas para {tipo} en el archivo {archivo}.")
            continue

        procesador = spec.processors.get(ext)
        if not procesador:
            # print(f"[DEBUG] Extensión {ext} no soportada para tipo {tipo} en archivo {archivo}.")
            continue

        # print(f"[DEBUG] ** INICIO ** Procesando archivo {tipo} válido: {archivo}")
        try:
            if tipo == "BASAL":
                resultados = procesador(texto_relevante, archivo)
            else:
                try:
                    resultados = procesador(texto_relevante, archivo)  # (texto, archivo)
                except TypeError:
                    resultados = procesador(texto_relevante)           # (texto)
            if tipo == "BASAL":
                if psg_archive_dir is None:
                    raise PSGExtractionError("No se configuró destino de archivado PSG")
                uuid = resultados["meta_uuid"]
                source_path = str(archivo.resolve())
                previous = known_psg.get(uuid) if known_psg is not None else None
                if previous is not None:
                    if str(Path(previous).resolve()) != source_path:
                        logging.warning("UUID PSG duplicado en otro origen; no se archiva: %s", archivo)
                        return "duplicate"
                    try:
                        _move_psg_file(archivo, PREFIXES.get(tipo, ""),
                                       resultados.get("meta_fecha_estudio"), psg_archive_dir,
                                       allow_complete_link=True)
                        return "retried"
                    except Exception as error:
                        logging.error("Reintento de archivado PSG fallido (%s): %s", type(error).__name__, archivo)
                        return "retry_archive_failed"
                outfile = _outfile_for_tipo(tipo)
                if outfile is None:
                    raise PSGExtractionError("No hay CSV configurado para PSG")
                if not _append_psg_row(resultados, outfile):
                    logging.warning("UUID PSG ya presente en CSV; no se archiva: %s", archivo)
                    return "duplicate"
                if known_psg is not None:
                    known_psg[uuid] = source_path
                try:
                    _move_psg_file(archivo, PREFIXES.get(tipo, ""),
                                   resultados.get("meta_fecha_estudio"), psg_archive_dir)
                    return "new"
                except Exception as error:
                    logging.error("Extracción PSG registrada; archivado fallido (%s): %s", type(error).__name__, archivo)
                    return "new_archive_failed"
            # print(f"[DEBUG] Resultados para {tipo}: {resultados}")
            # Capturar fecha si aun no tenemos una
            if not detected_date and "fecha_estudio" in resultados:
                detected_date = resultados["fecha_estudio"]
            # Marcar éxito para este tipo
            processing_results.append((tipo, True))
            # Agregar prefijo correspondiente
            if prefix := PREFIXES.get(tipo):
                applied_prefixes.add(prefix)
        except Exception as e:
            if tipo == "BASAL":
                detail = str(e) if isinstance(e, PSGExtractionError) else type(e).__name__
                logging.warning("Extracción PSG omitida: %s", detail)
                return "rejected"
            # print(f"[DEBUG] Error procesando {tipo} en {archivo}: {e}")
            processing_results.append((tipo, False))
            continue

        outfile = _outfile_for_tipo(tipo)
        # print(f"[DEBUG] Archivo de salida para {tipo}: {outfile}")
        if not outfile:
            continue  # sin archivo mapeado → no escribir
        _append_row_unified(resultados, outfile)
        # print(f"[DEBUG] ** FIN ** Procesamiento {tipo} → {outfile.name} para {archivo}")

    # Finalizar: Mover y renombrar si hubo al menos un éxito
    success = any(result for _, result in processing_results)
    if success:
        _move_processed_file(archivo, applied_prefixes, detected_date)
    return success
