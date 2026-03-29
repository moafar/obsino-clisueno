# commons/unificar_resultados.py

import os, glob, re, logging
from typing import List, Dict
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)



# ---------------------- UTILIDADES ----------------------






# ---------------------- FUNCIÓN PRINCIPAL ----------------------

def analizar_y_unificar(
    carpeta: str,
) -> None:
    """
    Analiza los CSV generados en 'carpeta' y muestra un resumen en logs/consola.
    No crea archivos adicionales.

    Args:
        carpeta: Ruta del directorio donde se encuentran los CSV (p.ej. "output").

    Returns:
        None
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

    if not archivos_csv:
        print("Análisis completado (sin archivos).")
        return

    logger.info("Analizando %s archivos CSV en %s", len(archivos_csv), carpeta_abs)

    # Resumen y mapa de faltantes por grupo
    for grupo, archivos in grupos.items():
        union_cols = union_por_grupo[grupo]
        logger.info("Grupo '%s' | archivos=%s | columnas_union=%s",
                    grupo,
                    len(archivos),
                    len(union_cols))

        # Resumen de columnas por archivo contra la unión del grupo
        for a in archivos:
            faltantes = sorted(list(union_cols - info[a]["cols"]))
            logger.info("  %s | faltantes=%s",
                        os.path.basename(a),
                        faltantes if faltantes else "[]")

    print("Extracción finalizada.")
