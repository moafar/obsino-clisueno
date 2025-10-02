import argparse
import time
import sys
import logging
from pathlib import Path
import yaml

from commons.logger import setup_logger
from commons.directorio_utils import validar_directorio, procesar_directorio
from commons.unificar_resultados import analizar_y_unificar

def main():
    parser = argparse.ArgumentParser(
        description="Procesa un directorio y luego unifica CSVs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "directorio",
        nargs="?",
        default=None,
        help="Ruta del directorio a analizar (si se omite, usa la del YAML)"
    )
    parser.add_argument(
        "-c", "--config",
        default="commons/config.yaml",
        help="Ruta al archivo de configuración YAML"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Muestra información detallada (fuerza logging DEBUG)"
    )
    args = parser.parse_args()

    # --- Cargar configuración ---
    try:
        with open(args.config, "r") as f:
            cfg = yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Error leyendo {args.config}: {e}", file=sys.stderr)
        return 1

    # --- Logging ---
    log_dir = cfg.get("logging", {}).get("dir", "logs")
    setup_logger(log_dir)
    level_name = "DEBUG" if args.verbose else cfg.get("logging", {}).get("level", "INFO")
    logging.getLogger().setLevel(getattr(logging, level_name, logging.INFO))

    # --- Resolver rutas desde CLI o YAML ---
    ruta_cfg = (cfg.get("entrada") or {}).get("ruta")
    if not args.directorio and not ruta_cfg:
        print("Debe indicar un directorio por CLI o en config.yaml: entrada.ruta", file=sys.stderr)
        return 2
    path = args.directorio or ruta_cfg

    # --- Validar directorio (soporta retorno Path o 1) ---
    try:
        logging.info(f"Inicio del proceso para el directorio $$ {path}")
        v = validar_directorio(path)
        ruta = v if isinstance(v, Path) else Path(path).resolve()
    except ValueError as e:
        logging.error(f"Error al validar el directorio {path} $$ {e}")
        print(f"\nError: {e}", file=sys.stderr)
        return 3

    # --- Parámetros de procesamiento desde YAML ---
    p = cfg.get("procesamiento", {})
    tipos_validos = p.get("tipos_validos", None)
    glob_patron = p.get("glob_patron", "**/*")
    barra = bool(p.get("barra_progreso", True))

    # --- Procesar directorio ---
    try:
        inicio = time.time()
        resultados = procesar_directorio(
            ruta,
            tipos_validos=tipos_validos,
            glob_patron=glob_patron,
            barra_progreso=barra,
        )
        tiempo = time.time() - inicio
    except Exception as e:
        logging.error(f"Se ha producido un error en procesar_directorio $$ {e}")
        print(f"\nSe ha producido un error: {e}", file=sys.stderr)
        return 4

    # --- Salida por consola (respeta --verbose) ---
    if args.verbose:
        logging.info(f"Directorio analizado: {ruta}")
        logging.info(f"Archivos procesados: {resultados['num_files']:,}")
        logging.info(f"Subdirectorios encontrados: {resultados['num_dirs']:,}")
        logging.info(f"Archivos válidos procesados: {resultados['archivos_validos']:,}")
        logging.info(f"Archivos descartados por tipo no válido: {resultados['num_files'] - resultados['archivos_validos']:,}")
        logging.info(f"Tiempo de análisis: {tiempo:.2f} s")
        print(f"\n{' Directorio analizado ':-^50}")
        print(f"Ruta completa: {ruta}")
        print(f"Archivos procesados: {resultados['num_files']:,}")
        print(f"Archivos válidos procesados: {resultados['archivos_validos']:,}")
        print(f"Archivos descartados por tipo no válido: {resultados['num_files'] - resultados['archivos_validos']:,}")
        print(f"Subdirectorios encontrados: {resultados['num_dirs']:,}")
        print(f"Tiempo de análisis: {tiempo:.2f} s")
        print('-' * 50)
    else:
        print(f"\nArchivos encontrados: {resultados['num_files']}")
        print(f"Subdirectorios encontrados: {resultados['num_dirs']}")
        print(f"Archivos válidos procesados: {resultados['archivos_validos']}")
        print(f"Archivos descartados por tipo no válido: {resultados['num_files'] - resultados['archivos_validos']}\n")

    # --- Analizar y unificar CSVs ---
    try:
        carpeta_csv = (cfg.get("salida") or {}).get("carpeta_csv")
        if not carpeta_csv:
            logging.warning("No se configuró salida.carpeta_csv en el YAML; se omite la unificación de CSV.")
        else:
            archivo_unificado = analizar_y_unificar(carpeta_csv)
            if archivo_unificado:
                logging.info(f"Unificado generado: {archivo_unificado}")
    except Exception as e:
        logging.error(f"Fallo en analizar_y_unificar $$ {e}")
        print(f"\nError unificando CSVs: {e}", file=sys.stderr)
        return 5

    logging.info(f"Fin del proceso para el directorio: {path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
