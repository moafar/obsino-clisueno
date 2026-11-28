import argparse, sys, time, logging, os, fcntl, re
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.psg_state import psg_lock, save
import yaml
import json

from extract_commons.logger import setup_logger
from extract_commons.auditoria_psg import audit_psg, read_log
from extract_commons.directorio_utils import validar_directorio, procesar_directorio
from extract_commons.archivo_utils import configure_subflows, load_known_psg_uuids

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
    subflujos_salida_unificada: dict[str, str] | None
    subflujos_prefijos: dict[str, str] | None
    archivo_destino: Path | None = None
    rutas_clinicas_protegidas: list[Path] | None = None


BASE_DIR = Path(__file__).resolve().parent
FLOW_CONFIG_PATHS: dict[str, Path] = {
    "psg": BASE_DIR.parent / "0_declarations" / "psg.yaml",
    "xpap": BASE_DIR.parent / "0_declarations" / "xpap.yaml",
}

def parse_args():
    p = argparse.ArgumentParser(
        description="Procesa un directorio y luego unifica CSVs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    p.add_argument("input_posicional", nargs="?", default=None,
                   help="Ruta del directorio a analizar (argumento posicional opcional)")
    p.add_argument("--flow", required=True, choices=sorted(FLOW_CONFIG_PATHS.keys()),
                   help="Flujo a ejecutar (define el YAML de configuración fijo)")
    p.add_argument("-c","--config", default=None,
                   help="Ruta al archivo de configuración YAML (override opcional del flow)")
    p.add_argument("--input", default=None,
                   help="Ruta del directorio a analizar (si se omite, usa la del YAML)")
    p.add_argument("-v","--verbose", action="store_true",
                   help="Muestra información detallada (logging DEBUG)")
    p.add_argument("--no-process", action="store_true", help="No procesa; solo unifica CSVs")
    p.add_argument("--no-unify", action="store_true", help="No unifica; solo procesa")
    p.add_argument("--dry-run", action="store_true", help="Valida y muestra parámetros; no ejecuta")
    p.add_argument("--mode", choices=("test", "normal"), default="normal")
    p.add_argument("--archive-dest", help="Destino de archivado PSG (sobrescribe el YAML)")
    p.add_argument("--output-dir", help="Directorio CSV PSG (sobrescribe el YAML)")
    p.add_argument("--test-root", help="Raíz aislada obligatoria en modo test PSG")
    p.add_argument("--yes", action="store_true", help="Confirmar operación PSG sin interacción")
    p.add_argument("--output-file", help="Nombre CSV PSG explícito dentro de --output-dir")
    p.add_argument("--result-json", help="Resumen técnico PSG para el orquestador")
    p.add_argument("--resume-extraction", action="store_true", help="Reconciliar una extracción interrumpida con checkpoint")
    args = p.parse_args()
    if args.flow != "psg" and (args.yes or args.output_file or args.result_json or args.resume_extraction):
        p.error("Las opciones de orquestación solo se admiten en PSG")
    return args


def resolve_config_yaml_path(flow: str) -> Path:
    config_yaml_path = FLOW_CONFIG_PATHS.get(flow)
    if not config_yaml_path:
        available_flows = ", ".join(sorted(FLOW_CONFIG_PATHS.keys()))
        raise RuntimeError(f"Flujo no soportado: {flow}. Flujos válidos: {available_flows}")
    return config_yaml_path

def load_config(path_cfg: str) -> Config:
    cfg_path = Path(path_cfg).resolve()
    cfg_dir = cfg_path.parent

    def _resolve_from_config(raw_path: str | None) -> Path | None:
        if not raw_path:
            return None
        candidate = Path(raw_path)
        if candidate.is_absolute():
            return candidate.resolve()
        return (cfg_dir / candidate).resolve()

    try:
        with cfg_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    except Exception as e:
        raise RuntimeError(f"No se pudo leer {path_cfg}: {e}") from e

    extract = raw.get("extract") or {}
    log = extract.get("logging") or {}
    ent = extract.get("entrada") or {}
    proc = extract.get("procesamiento") or {}
    sal = extract.get("salida") or {}
    sub = extract.get("subflujos") or {}
    archive = extract.get("archivado") or {}

    project_logs_dir = (BASE_DIR.parent / "logs").resolve()
    configured_logs_dir = _resolve_from_config(log.get("dir"))

    salida_unificada = sub.get("salida_unificada")
    if not salida_unificada:
        raise RuntimeError(
            f"El archivo de configuración {cfg_path} debe definir 'subflujos.salida_unificada' con los subflujos activos."
        )
    cfg = Config(
        logging_dir = configured_logs_dir or project_logs_dir,
        logging_level = str(log.get("level", "INFO")).upper(),
        entrada_ruta = _resolve_from_config(ent.get("ruta")),
        tipos_validos = proc.get("tipos_validos"),
        glob_patron = proc.get("glob_patron", "**/*"),
        barra_progreso = bool(proc.get("barra_progreso", True)),
        carpeta_csv = _resolve_from_config(sal.get("carpeta_csv")),
        subflujos_salida_unificada = salida_unificada,
        subflujos_prefijos = sub.get("prefijos"),
        archivo_destino = _resolve_from_config(archive.get("destino")),
        rutas_clinicas_protegidas = [path for item in archive.get("rutas_clinicas_protegidas", [])
                                    if (path := _resolve_from_config(item)) is not None],
    )
    return cfg

def setup_logging_from_config(cfg: Config, force_debug: bool, flow: str):
    level_name = "DEBUG" if force_debug else cfg.logging_level
    if flow == "psg" and getattr(logging, level_name, logging.INFO) > logging.INFO:
        level_name = "INFO"  # La auditoría requiere los eventos de traslado.
    return setup_logger(str(cfg.logging_dir), flow_name=flow, level_name=level_name)

def resolve_input_dir(cli_dir: str | None, cfg: Config) -> Path:
    path = Path(cli_dir).resolve() if cli_dir else cfg.entrada_ruta
    if not path:
        raise ValueError("Indica un directorio por CLI o en config.yaml: entrada.ruta")
    v = validar_directorio(str(path))
    return v if isinstance(v, Path) else path

def run_processing(ruta: Path, cfg: Config, *, archive_dir: Path | None = None,
                   known_psg: dict[str, str] | None = None) -> tuple[dict, float]:
    t0 = time.perf_counter()
    res = procesar_directorio(
        ruta,
        tipos_validos=cfg.tipos_validos,
        glob_patron=cfg.glob_patron,
        barra_progreso=cfg.barra_progreso,
        psg_archive_dir=archive_dir,
        known_psg=known_psg,
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
        "extraidos": res.get("archivos_extraidos", 0),
        "registrados": res.get("archivos_registrados", 0),
        "rechazados": res.get("archivos_rechazados", 0),
        "errores_procesamiento": res.get("errores_procesamiento", 0),
        "tiempo_s": f"{dt:.2f}",
    }
    logger.info(
        "Resumen: archivos=%s, válidos=%s, descartados=%s, filas_nuevas=%s, nuevos_archivados=%s, duplicados=%s, fallos_archivado=%s, reintentos=%s, rechazados=%s, errores_recorrido=%s, errores_procesamiento=%s, tiempo_s=%s",
        base["num_files"], base["validos"], base["descartados"],
        base["registrados"], base["extraidos"], res.get("archivos_duplicados", 0),
        res.get("archivos_fallo_archivado", 0), res.get("archivos_reintentados", 0),
        base["rechazados"], res.get("errores_recorrido", 0),
        base["errores_procesamiento"], base["tiempo_s"],
    )
    if verbose:
        print(f"\n{' Resumen de procesamiento ':-^60}")
        for k,v in base.items(): print(f"{k:>12}: {v}")
        for key in ("archivos_duplicados", "archivos_fallo_archivado", "archivos_reintentados", "errores_recorrido"):
            print(f"{key:>23}: {res.get(key, 0)}")
        print("-"*60)
    else:
        print(f"\nArchivos: {base['num_files']} | Subdirs: {base['num_dirs']} | "
              f"Válidos: {base['validos']} | Descartados: {base['descartados']} | "
              f"Filas nuevas: {base['registrados']} | Nuevos archivados: {base['extraidos']} | "
              f"Duplicados: {res.get('archivos_duplicados', 0)} | "
              f"Fallos de archivado: {res.get('archivos_fallo_archivado', 0)} | "
              f"Reintentos: {res.get('archivos_reintentados', 0)} | "
              f"Errores de recorrido: {res.get('errores_recorrido', 0)} | "
              f"Errores de procesamiento: {base['errores_procesamiento']} | "
              f"Rechazados: {base['rechazados']} | "
              f"Tiempo(s): {base['tiempo_s']}\n")


def _psg_runtime(args, cfg: Config) -> tuple[Path, Path, Path, Config]:
    if args.no_process:
        raise ValueError("PSG requiere procesamiento; --no-process no aplica")
    if args.mode == "test" and not all((args.test_root, args.input or args.input_posicional,
                                        args.archive_dest, args.output_dir)):
        raise ValueError("Modo test PSG requiere --test-root, --input, --archive-dest y --output-dir")
    source = resolve_input_dir(args.input or args.input_posicional, cfg)
    raw_destination = args.archive_dest or cfg.archivo_destino
    raw_output = args.output_dir or cfg.carpeta_csv
    if not raw_destination or not raw_output:
        raise ValueError("PSG requiere destino de archivo y salida CSV explícitos")
    destination = Path(raw_destination).resolve(strict=True)
    output = Path(raw_output).resolve(strict=True)
    for label, path, access in (("origen", source, os.R_OK | os.X_OK),
                                ("destino", destination, os.W_OK | os.X_OK),
                                ("salida CSV", output, os.W_OK | os.X_OK)):
        if not path.is_dir() or not os.access(path, access):
            raise ValueError(f"Directorio PSG no accesible: {label}: {path}")
    if (source == destination or source.is_relative_to(destination) or
            source.stat().st_dev != destination.stat().st_dev):
        raise ValueError("Origen y destino PSG deben ser directorios distintos del mismo dispositivo")
    if output.is_relative_to(source) or output.is_relative_to(destination):
        raise ValueError("La salida CSV PSG debe estar fuera del origen y del archivo")
    if args.mode == "test":
        test_root = Path(args.test_root).resolve(strict=True)
        if not (test_root / ".psg-test-root").is_file():
            raise ValueError("La raíz de pruebas PSG requiere el marcador .psg-test-root")
        official = load_config(str(resolve_config_yaml_path("psg")))
        protected = (official.rutas_clinicas_protegidas or []) + [
            official.entrada_ruta, official.archivo_destino,
            (BASE_DIR.parent / "staging").resolve(), (BASE_DIR.parent / "procesados").resolve(),
        ]
        if any(test_root.is_relative_to(path) or path.is_relative_to(test_root)
               for path in protected if path is not None):
            raise ValueError("La raíz de pruebas PSG se solapa con rutas clínicas u ordinarias")
        if any(not path.is_relative_to(test_root) for path in (source, destination, output)):
            raise ValueError("Todas las rutas de modo test PSG deben estar dentro de --test-root")
        cfg.logging_dir = test_root / "logs"
    elif args.test_root:
        raise ValueError("--test-root solo se admite en modo test")
    if not cfg.subflujos_prefijos or not cfg.subflujos_prefijos.get("BASAL"):
        raise ValueError("Falta el prefijo BASAL en la configuración PSG")
    if set(cfg.subflujos_salida_unificada or {}) != {"BASAL"}:
        raise ValueError("El flujo PSG solo puede activar el subflujo BASAL")
    if not re.fullmatch(r"[A-Za-z0-9_]+", cfg.subflujos_prefijos["BASAL"]):
        raise ValueError("Prefijo BASAL no válido para un nombre de archivo")
    template = (cfg.subflujos_salida_unificada or {}).get("BASAL", "")
    if (Path(template).name != template or not template.startswith("extract_psg_") or
            not template.endswith(".csv") or template.endswith("_transformed.csv")):
        raise ValueError("El CSV PSG debe tener nombre extract_psg_*.csv dentro de la salida")
    return source, destination, output, cfg


def _show_psg_configuration(mode: str, source: Path, destination: Path,
                            output: Path, dry_run: bool = False) -> None:
    print("\nOBSINO-CLISUENO | EXTRACTOR PSG")
    print(f"Modo: {mode.upper()} | Flujo: PSG | Recursivo: Sí | Tipos: DOC, RTF")
    print(f"Origen: {source}\nDestino: {destination}\nSalida CSV: {output}")
    print("Organización: AAAA/AAAA-MM o sin_fecha | Prefijos acumulativos: Sí")
    print("Destino dentro del origen: excluido por ruta real")
    print("Origen y destino accesibles: Sí | Mismo dispositivo: Sí")
    print("Movimiento: renameat2 sin reemplazo o enlace y retirada del origen")
    print("DRY-RUN: no se extraerá ni moverá nada" if dry_run else
          "ATENCIÓN: SE MOVERÁN DOCUMENTOS ORIGINALES")


def _orchestrate_psg(args, cfg: Config) -> int:
    _, _, output, _ = _psg_runtime(args, cfg)
    from extract_commons import archivo_utils
    previous = (archivo_utils.PSG_RECOVERY_DIR, archivo_utils.PSG_RECOVERY_LOG)
    try:
        with psg_lock(output):
            return _orchestrate_psg_locked(args, cfg)
    finally:
        archivo_utils.PSG_RECOVERY_DIR, archivo_utils.PSG_RECOVERY_LOG = previous


def _orchestrate_psg_locked(args, cfg: Config) -> int:
    source, destination, output, cfg = _psg_runtime(args, cfg)
    from extract_commons import archivo_utils
    archivo_utils.PSG_RECOVERY_DIR = output / ".psg-moves"
    if getattr(args, "resume_extraction", False):
        return _resume_extraction(args, source, destination, output)
    _show_psg_configuration(args.mode, source, destination, output, args.dry_run)
    if args.dry_run:
        return EXIT_OK
    if not getattr(args, "yes", False):
        try:
            answer = input("¿Confirmas el inicio de la operación? [s/N]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return EXIT_OK
        if answer not in ("s", "si", "sí"):
            return EXIT_OK
    log_path = setup_logging_from_config(cfg, force_debug=args.verbose, flow="psg")
    archivo_utils.PSG_RECOVERY_LOG = log_path
    orchestration_started_at = time.perf_counter()
    phase_times = {}
    with (output / ".psg-archive.lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            output_map = build_timestamped_output_map("psg", cfg.subflujos_salida_unificada)
            explicit = getattr(args, "output_file", None)
            if explicit:
                if Path(explicit).name != explicit or not re.fullmatch(r"extract_psg_[A-Za-z0-9_-]+\.csv", explicit):
                    raise ValueError("Nombre CSV PSG explícito inválido")
                output_map["BASAL"] = explicit
            csv_path = output / output_map["BASAL"]
            if explicit and csv_path.exists():
                raise FileExistsError(csv_path)
            # Cada auditoría debe corresponder exclusivamente a esta ejecución.
            if csv_path.exists():
                stem = csv_path.stem
                suffix = 1
                while csv_path.exists():
                    csv_path = output / f"{stem}_{suffix}.csv"
                    suffix += 1
                output_map["BASAL"] = csv_path.name
            configure_subflows(unified_file_for=output_map, prefixes=cfg.subflujos_prefijos,
                               output_dir=output)
            logger.info("PSG: modo=%s origen=%s destino=%s salida=%s", args.mode, source, destination, output)
            logger.info("Progreso PSG 1/3: lectura de UUID históricos iniciada")
            history_started_at = time.perf_counter()
            known = load_known_psg_uuids(output)
            try:
                archivo_utils.recover_psg_moves(source, destination, output, known=known)
            except Exception as error:
                logger.error("Recuperación documental PSG bloqueada: %s", type(error).__name__)
                return EXIT_PROCESS
            phase_times["historicos_s"] = time.perf_counter() - history_started_at
            logger.info("Progreso PSG 1/3: lectura de UUID históricos terminada; tiempo_s=%.3f",
                        phase_times["historicos_s"])
            logger.info("Progreso PSG 2/3: procesamiento iniciado")
            result, elapsed = run_processing(source, cfg, archive_dir=destination, known_psg=known)
            phase_times["procesamiento_s"] = elapsed
            logger.info("Progreso PSG 2/3: procesamiento terminado; tiempo_s=%.3f", elapsed)
            report(result, source, elapsed, args.verbose)
            if getattr(args, "result_json", None):
                save(Path(args.result_json).with_suffix(".checkpoint.json"), {
                    "csv": str(csv_path), "log": str(log_path), "source": str(source),
                    "archive": str(destination), "result": result, "elapsed": elapsed,
                    "times": phase_times})
            logger.info("Progreso PSG 3/3: auditoría iniciada")
            audit_started_at = time.perf_counter()
            try:
                audit_path, audit_state = audit_psg(
                    csv_path, log_path, args.config or resolve_config_yaml_path("psg"),
                    source, destination, result=result,
                    extensions=cfg.tipos_validos or ("doc", "rtf"), elapsed=elapsed,
                    phase_times=phase_times, orchestration_started_at=orchestration_started_at)
                phase_times["auditoria_s"] = time.perf_counter() - audit_started_at
                logger.info("Progreso PSG 3/3: auditoría terminada; estado=%s; tiempo_s=%.3f",
                            audit_state, phase_times["auditoria_s"])
                print(f"Auditoría PSG: {audit_state} | {audit_path}")
            except Exception as error:
                phase_times["auditoria_s"] = time.perf_counter() - audit_started_at
                logger.error("Auditoría PSG no completada: %s", type(error).__name__)
                print("Auditoría PSG no completada; consulte el log. No se revierten los traslados.",
                      file=sys.stderr)
                return EXIT_PROCESS
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)
            logger.info("Tiempo PSG: historicos_s=%s procesamiento_s=%s auditoria_s=%s "
                        "orquestacion_total_s=%.3f",
                        f"{phase_times['historicos_s']:.3f}" if "historicos_s" in phase_times else "NO_EVALUADO",
                        f"{phase_times['procesamiento_s']:.3f}" if "procesamiento_s" in phase_times else "NO_EVALUADO",
                        f"{phase_times['auditoria_s']:.3f}" if "auditoria_s" in phase_times else "NO_EVALUADO",
                        time.perf_counter() - orchestration_started_at)
    if getattr(args, "result_json", None):
        save(Path(args.result_json), {
            "csv": str(csv_path), "audit": str(audit_path), "audit_state": audit_state,
            "counts": {k: v for k, v in result.items() if isinstance(v, (int, float))},
            "times": phase_times, "log": str(log_path),
        })
    if (audit_state == "ERROR" or result.get("archivos_fallo_archivado", 0)
            or result.get("errores_recorrido", 0) or result.get("errores_procesamiento", 0)):
        return EXIT_PROCESS
    return EXIT_OK


def _resume_extraction(args, source, destination, output):
    from extract_commons import archivo_utils
    if not args.result_json:
        raise ValueError("La reanudación requiere --result-json")
    checkpoint = Path(args.result_json).with_suffix(".checkpoint.json")
    if not checkpoint.exists():
        archivo_utils.recover_psg_moves(source, destination, output)
        raise RuntimeError("Inventario de extracción no confirmado; movimientos conciliados, revisión necesaria")
    item = json.loads(checkpoint.read_text())
    if item["source"] != str(source) or item["archive"] != str(destination):
        raise RuntimeError("Checkpoint de extracción incompatible")
    log_path = Path(item["log"])
    if not log_path.is_file():
        raise RuntimeError("No existe el log de extracción original")
    logging.basicConfig(level=logging.INFO, format='%(asctime)s $$ %(levelname)s $$ %(message)s',
                        handlers=[logging.FileHandler(log_path, encoding="utf-8")], force=True)
    archivo_utils.recover_psg_moves(source, destination, output)
    # El checkpoint conserva el inventario original; solo se corrigen movimientos demostrados.
    import csv
    origins = set()
    if Path(item["csv"]).exists():
        with Path(item["csv"]).open(newline="", encoding="utf-8") as stream:
            origins = {row["meta_fuente"] for row in csv.DictReader(stream)}
    moves = read_log(log_path)[0]
    if any(len(destinations) != 1 for destinations in moves.values()):
        raise RuntimeError("Traslados repetidos o ambiguos en el log original")
    new_archived = sum(origin in origins for origin in moves)
    retried = len(moves) - new_archived
    result = dict(item["result"])
    recovered = new_archived + retried - result["archivos_extraidos"] - result["archivos_reintentados"]
    if not 0 <= recovered <= result["archivos_fallo_archivado"]:
        raise RuntimeError("No concilian los movimientos recuperados con el inventario original")
    result.update(archivos_extraidos=new_archived, archivos_reintentados=retried,
                  archivos_fallo_archivado=result["archivos_fallo_archivado"] - recovered)
    audit_path, state = audit_psg(item["csv"], log_path, args.config or resolve_config_yaml_path("psg"),
        source, destination, result=result, elapsed=item["elapsed"],
        phase_times=item["times"])
    save(Path(args.result_json), {"csv": item["csv"], "log": str(log_path),
        "audit": str(audit_path), "audit_state": state,
        "counts": {k: v for k, v in result.items() if isinstance(v, (int, float))},
        "times": item["times"]})
    return EXIT_PROCESS if state == "ERROR" else EXIT_OK

def maybe_unify(cfg: Config) -> None:
    if not cfg.carpeta_csv:
        logger.warning("No se configuró salida.carpeta_csv; se omite unificación.")
        return


def build_timestamped_output_map(
    flow: str,
    configured_outputs: dict[str, str] | None,
) -> dict[str, str] | None:
    if not configured_outputs:
        return None

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    output_map = {}
    for tipo, template in configured_outputs.items():
        if "{timestamp}" in template:
            file_name = template.replace("{timestamp}", ts)
        else:
            file_name = template
        output_map[tipo] = file_name
    return output_map

def orchestrate():
    args = parse_args()
    try:
        config_path = args.config or str(resolve_config_yaml_path(args.flow))
        cfg = load_config(config_path)
        if args.flow == "psg":
            return _orchestrate_psg(args, cfg)
        if args.mode != "normal" or args.archive_dest or args.output_dir or args.test_root:
            raise ValueError("Las opciones de archivado PSG no aplican a otros flujos")
        setup_logging_from_config(cfg, force_debug=args.verbose, flow=args.flow)
        runtime_output_map = build_timestamped_output_map(
            flow=args.flow,
            configured_outputs=cfg.subflujos_salida_unificada,
        )
        configure_subflows(
            unified_file_for=runtime_output_map,
            prefixes=cfg.subflujos_prefijos,
            output_dir=cfg.carpeta_csv,
        )
        logger.info("Inicio del proceso")

        if args.dry_run:
            logger.info("Dry-run: sin efectos")
            print(f"Config: {cfg}")
            return EXIT_OK

        if not args.no_process:
            resolved_input = args.input or args.input_posicional
            ruta = resolve_input_dir(resolved_input, cfg)
            logger.info("Procesando directorio de entrada")
            res, dt = run_processing(ruta, cfg)
            report(res, ruta, dt, args.verbose)

        if not args.no_unify:
            maybe_unify(cfg)

        logger.info("Fin del proceso")
        return EXIT_OK

    except RuntimeError as e:
        logger.error("Error de configuración: %s", type(e).__name__)
        print(f"Error de configuración: {e}", file=sys.stderr)
        return EXIT_CFG
    except ValueError as e:
        logger.error("Entrada inválida: %s", type(e).__name__)
        print(f"Entrada inválida: {e}", file=sys.stderr)
        return EXIT_INPUT
    except Exception as e:
        logger.error("Fallo inesperado: %s", type(e).__name__)
        print(f"Error: {e}", file=sys.stderr)
        return EXIT_PROCESS

def main():
    sys.exit(orchestrate())

if __name__ == "__main__":
    main()
