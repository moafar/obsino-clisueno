# commons/unificar_resultados.py

import os, glob, re, logging, datetime
from typing import List, Optional, Dict
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)

EXCLUIR_PATRONES = [r"^unificado\.csv$"]   # excluye el genérico
IGNORAR_COLUMNAS = {"uuid"}                # columnas sintéticas a ignorar


# ---------------------- UTILIDADES ----------------------

def _excluir(nombre: str) -> bool:
    """Determina si un archivo debe excluirse según los patrones."""
    return any(re.search(pat, nombre, flags=re.IGNORECASE) for pat in EXCLUIR_PATRONES)

def _listar_csvs(carpeta: str) -> List[str]:
    """Lista archivos CSV válidos dentro de una carpeta (sin los excluidos)."""
    carpeta_abs = str(Path(carpeta).resolve())
    encontrados = glob.glob(os.path.join(carpeta_abs, "*.csv"))
    filtrados = [p for p in encontrados if not _excluir(os.path.basename(p))]
    logger.debug("Carpeta=%s encontrados=%s usados=%s",
                 carpeta_abs,
                 [os.path.basename(x) for x in encontrados],
                 [os.path.basename(x) for x in filtrados])
    return filtrados

def _cols_sin_ignoradas(df: pd.DataFrame) -> set:
    """Devuelve las columnas del DataFrame ignorando las sintéticas."""
    return set(c for c in df.columns if c not in IGNORAR_COLUMNAS)

def _timestamp() -> str:
    """Devuelve timestamp YYYY-MM-DD_HH-MM-SS."""
    return datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

def _write_text(path: Path, text: str) -> None:
    """Escribe un texto en un archivo UTF-8."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    logger.info("Reporte escrito: %s", str(path))

def _family_from_filename(nombre: str) -> str:
    """
    Extrae la familia (grupo) a partir de 'unificado_<familia>.csv'.
    Si no coincide, devuelve 'otros'.
    """
    m = re.match(r"^unificado_([a-z0-9]+)\.csv$", nombre, flags=re.IGNORECASE)
    return m.group(1).lower() if m else "otros"


# ---------------------- FUNCIÓN PRINCIPAL ----------------------

def analizar_y_unificar(
    carpeta: str,
) -> str:
    """
    Analiza los CSV generados en 'carpeta' y crea SIEMPRE un reporte Markdown
    con nombre 'reporte_analisis_<timestamp>.md'. No crea CSVs adicionales.

    Args:
        carpeta: Ruta del directorio donde se encuentran los CSV (p.ej. "output").

    Returns:
        str: Ruta del reporte Markdown generado.
    """
    carpeta_abs = Path(carpeta).resolve()
    archivos_csv = _listar_csvs(str(carpeta_abs))

    # ================== Preparar datos ==================
    info: Dict[str, Dict] = {}
    if archivos_csv:
        for archivo in archivos_csv:
            df = pd.read_csv(archivo)
            grupo = _family_from_filename(os.path.basename(archivo))
            info[archivo] = {
                "shape": df.shape,
                "cols": _cols_sin_ignoradas(df),
                "cols_all": list(df.columns),
                "grupo": grupo,
            }
            logger.debug("Archivo=%s grupo=%s shape=%s cols=%s",
                         archivo, grupo, df.shape, df.columns.tolist())

    # Agrupar por grupo y calcular uniones de columnas por grupo
    grupos: Dict[str, List[str]] = {}
    union_por_grupo: Dict[str, set] = {}
    if info:
        for a, d in info.items():
            grupos.setdefault(d["grupo"], []).append(a)
        union_por_grupo = {
            g: set().union(*[info[a]["cols"] for a in archivos])
            for g, archivos in grupos.items()
        }

    # ================== Generar reporte ==================
    ts = _timestamp()
    rep_path = carpeta_abs / f"reporte_analisis_{ts}.md"

    lineas: List[str] = []
    lineas.append("# Reporte de análisis de CSV\n")
    lineas.append(f"- Carpeta analizada: `{carpeta_abs}`")
    lineas.append(f"- Archivos detectados: **{len(archivos_csv)}**\n")

    if not archivos_csv:
        lineas.append("No se encontraron archivos CSV (o todos fueron excluidos).")
        _write_text(rep_path, "\n".join(lineas))
        print(f"Reporte generado: {rep_path}")
        print("Análisis completado (sin archivos).")
        return str(rep_path)

    # Listado de archivos con forma y grupo
    lineas.append("## Archivos procesados")
    for a in archivos_csv:
        shape = info[a]["shape"]
        lineas.append(f"- `{os.path.basename(a)}` | grupo: `{info[a]['grupo']}` | forma: {shape[0]} filas × {shape[1]} cols")

    # Resumen y mapa de faltantes POR GRUPO
    lineas.append("\n## Resumen por grupo (ignorando: " + ", ".join(sorted(IGNORAR_COLUMNAS)) + ")")
    for grupo, archivos in grupos.items():
        lineas.append(f"\n### Grupo: `{grupo}`")
        union_cols = union_por_grupo[grupo]

        # Resumen de columnas por archivo (contra la unión del grupo)
        for a in archivos:
            faltantes = sorted(list(union_cols - info[a]["cols"]))
            sobrantes = sorted(list(info[a]["cols"] - union_cols))
            lineas.append(f"- **{os.path.basename(a)}**")
            lineas.append(f"  - Faltantes: {faltantes if faltantes else '[]'}")
            lineas.append(f"  - Adicionales: {sobrantes if sobrantes else '[]'}")

        # Mapa de faltantes por columna (dentro del grupo)
        lineas.append("\n#### Mapa de faltantes por columna")
        faltantes_por_archivo = {a: sorted(list(union_cols - info[a]["cols"])) for a in archivos}
        faltantes_por_columna: Dict[str, List[str]] = {}
        for col in sorted(list(union_cols)):
            archivos_donde_falta = [
                os.path.basename(a) for a in archivos if col in faltantes_por_archivo[a]
            ]
            if archivos_donde_falta:
                faltantes_por_columna[col] = archivos_donde_falta

        if not faltantes_por_columna:
            lineas.append("- No hay columnas faltantes dentro de este grupo.")
        else:
            for col, archivos_faltantes in faltantes_por_columna.items():
                n = len(archivos_faltantes)
                plural = "archivo" if n == 1 else "archivos"
                lista_arch = ", ".join(archivos_faltantes)
                lineas.append(f"- **{col}** → falta en {n} {plural}: {lista_arch}")

        # Detalle de columnas por archivo (todas)
        lineas.append("\n#### Detalle de columnas por archivo (todas, incluyendo ignoradas)")
        for a in archivos:
            lineas.append(f"- **{os.path.basename(a)}**: {info[a]['cols_all']}")

    _write_text(rep_path, "\n".join(lineas))

    # ================== Consola mínima ==================
    print(f"Reporte generado: {rep_path}")
    print("Análisis completado (solo reporte).")

    return str(rep_path)
