import argparse, sys, time, logging
from dataclasses import dataclass
from pathlib import Path
import yaml

from commons.logger import setup_logger
from commons.directorio_utils import validar_directorio, procesar_directorio
from commons.unificar_resultados import analizar_y_unificar

EXIT_OK, EXIT_CFG, EXIT_INPUT, EXIT_PROCESS, EXIT_UNIFY = 0, 1, 2, 3, 4
logger = logging.getLogger(__name__)

@dataclass
class Config:
    logging_dir: Path
    logging_level: str
    entrada_ruta: Path | None
    tipos_validos: list[str] | None
    glob_patron: str
    barra_progreso: bool
    carpeta_csv: Path | None

def parse_args():
    p = argparse.ArgumentParser(
        description="Procesa un directorio y luego unifica CSVs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    p.add_argument("directorio", nargs="?", default=None,
                   help="Ruta del directorio a analizar (si se omite, usa la del YAML)")
    p.add_argument("-c","--config", default="commons/config.yaml",
                   help="Ruta al archivo de configuración YAML")
    p.add_argument("-v","--verbose", action="store_true",
                   help="Muestra información detallada (logging DEBUG)")
    p.add_argument("--no-process", action="store_true", help="No procesa; solo unifica CSVs")
    p.add_argument("--no-unify", action="store_true", help="No unifica; solo procesa")
    p.add_argument("--dry-run", action="store_true", help="Valida y muestra parámetros; no ejecuta")
    return p.parse_args()

def load_config(path_cfg: str) -> Config:
    try:
        with open(path_cfg, "r") as f:
            raw = yaml.safe_load(f) or {}
    except Exception as e:
        raise RuntimeError(f"No se pudo leer {path_cfg}: {e}") from e

    log = (raw.get("logging") or {})
    ent = (raw.get("entrada") or {})
    proc = (raw.get("procesamiento") or {})
    sal = (raw.get("salida") or {})

    cfg = Config(
        logging_dir = Path(log.get("dir", "logs")),
        logging_level = str(log.get("level", "INFO")).upper(),
        entrada_ruta = Path(ent["ruta"]).resolve() if ent.get("ruta") else None,
        tipos_validos = proc.get("tipos_validos"),
        glob_patron = proc.get("glob_patron", "**/*"),
        barra_progreso = bool(proc.get("barra_progreso", True)),
        carpeta_csv = Path(sal["carpeta_csv"]).resolve() if sal.get("carpeta_csv") else None,
    )
 
    return cfg

def setup_logging_from_config(cfg: Config, force_debug: bool):
    setup_logger(cfg.logging_dir)
    level_name = "DEBUG" if force_debug else cfg.logging_level
    logging.getLogger().setLevel(getattr(logging, level_name, logging.INFO))

def resolve_input_dir(cli_dir: str | None, cfg: Config) -> Path:
    path = Path(cli_dir).resolve() if cli_dir else cfg.entrada_ruta
    if not path:
        raise ValueError("Indica un directorio por CLI o en config.yaml: entrada.ruta")
    v = validar_directorio(str(path))
    return v if isinstance(v, Path) else path

def run_processing(ruta: Path, cfg: Config) -> tuple[dict, float]:
    t0 = time.perf_counter()
    res = procesar_directorio(
        ruta,
        tipos_validos=cfg.tipos_validos,
        glob_patron=cfg.glob_patron,
        barra_progreso=cfg.barra_progreso,
    )
    dt = time.perf_counter() - t0
    return res, dt

def report(res: dict, ruta: Path, dt: float, verbose: bool):
    base = {
        "ruta": str(ruta),
        "num_files": res["num_files"],
        "num_dirs": res["num_dirs"],
        "validos": res["archivos_validos"],
        "descartados": res["num_files"] - res["archivos_validos"],
        "tiempo_s": f"{dt:.2f}",
    }
    logger.info(f"Resumen: {base}")
    if verbose:
        print(f"\n{' Resumen de procesamiento ':-^60}")
        for k,v in base.items(): print(f"{k:>12}: {v}")
        print("-"*60)
    else:
        print(f"\nArchivos: {base['num_files']} | Subdirs: {base['num_dirs']} | "
              f"Válidos: {base['validos']} | Descartados: {base['descartados']} | "
              f"Tiempo(s): {base['tiempo_s']}\n")

def maybe_unify(cfg: Config) -> Path | None:
    if not cfg.carpeta_csv:
        logger.warning("No se configuró salida.carpeta_csv; se omite unificación.")
        return None
    out = analizar_y_unificar(str(cfg.carpeta_csv))
    if out:
        logger.info(f"Unificado: {out}")
    return out

def orchestrate():
    args = parse_args()
    try:
        cfg = load_config(args.config)
        setup_logging_from_config(cfg, force_debug=args.verbose)
        logger.info("Inicio del proceso")

        if args.dry_run:
            logger.info("Dry-run: sin efectos")
            print(f"Config: {cfg}")
            return EXIT_OK

        if not args.no_process:
            ruta = resolve_input_dir(args.directorio, cfg)
            logger.info(f"Procesando directorio: {ruta}")
            res, dt = run_processing(ruta, cfg)
            report(res, ruta, dt, args.verbose)

        if not args.no_unify:
            maybe_unify(cfg)

        logger.info("Fin del proceso")
        return EXIT_OK

    except RuntimeError as e:
        logger.error(e)
        print(f"Error de configuración: {e}", file=sys.stderr)
        return EXIT_CFG
    except ValueError as e:
        logger.error(e)
        print(f"Entrada inválida: {e}", file=sys.stderr)
        return EXIT_INPUT
    except Exception as e:
        logger.exception("Fallo inesperado")
        print(f"Error: {e}", file=sys.stderr)
        return EXIT_PROCESS

def main():
    sys.exit(orchestrate())

if __name__ == "__main__":
    main()
