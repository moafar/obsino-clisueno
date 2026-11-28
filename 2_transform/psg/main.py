from __future__ import annotations

import argparse
import csv
import logging
from pathlib import Path
import re
import sys
from typing import Any
import yaml

TRANSFORM_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = TRANSFORM_ROOT.parent
PIPELINE_ROOT = Path(__file__).resolve().parent
FLOW_NAME = PIPELINE_ROOT.name
STAGING_DIR = PROJECT_ROOT / "staging"
EXTRACT_FILE_PREFIX = f"extract_{FLOW_NAME}_"
if str(TRANSFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(TRANSFORM_ROOT))

from transform_commons.logging import configure_flow_logging

configure_flow_logging(FLOW_NAME)

from transform_commons.engine import OperationRegistry, run_pipeline
from transform_commons.io import (
    build_default_output_path,
    read_dataset,
    resolve_existing_path,
    resolve_output_path,
    write_dataset,
)
from transform_commons.ops import register_builtin_operations
from transform_commons.schema import validate_input_schema, validate_output_schema
from psg.core.transforms import register_psg_operations, validate_psg_technical_metadata

SUPPORTED_INPUT_EXTENSIONS = {".csv"}


def _search_bases() -> list[Path]:
    return [Path.cwd(), PROJECT_ROOT, TRANSFORM_ROOT]


def _discover_input_files() -> list[Path]:
    input_dir = STAGING_DIR
    if not input_dir.exists():
        return []

    files = [
        path
        for path in sorted(input_dir.iterdir())
        if (
            path.is_file()
            and path.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS
            and path.stem.startswith(EXTRACT_FILE_PREFIX)
            and "_transformed" not in path.stem
        )
    ]
    return files


def _safe_file_label(path: Path, index: int) -> str:
    if re.fullmatch(r"extract_psg_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}\.csv", path.name):
        return path.name
    return f"archivo #{index}"


def _check_selected_uuids(input_files: list[Path], input_config: dict) -> dict[Path, list[int]]:
    """Conserva la primera fila por UUID en el lote seleccionado."""
    seen: dict[str, dict[str, str]] = {}
    keep: dict[Path, list[int]] = {}
    duplicates = different = 0
    separator = input_config.get("sep", ",")
    encoding = input_config.get("encoding", "utf-8")
    for index, path in enumerate(input_files, start=1):
        label = _safe_file_label(path, index)
        keep[path] = []
        try:
            with path.open("r", newline="", encoding=encoding) as source:
                reader = csv.DictReader(source, delimiter=separator, strict=True)
                if not reader.fieldnames or "meta_uuid" not in reader.fieldnames:
                    raise ValueError(f"Falta meta_uuid en {label}")
                for position, record in enumerate(reader):
                    if None in record or any(value is None for value in record.values()):
                        raise ValueError(f"Fila PSG incompleta o con columnas extra en {label}")
                    uuid = record.get("meta_uuid")
                    if uuid is None or not re.fullmatch(r"[0-9a-f]{32}", uuid.strip()):
                        raise ValueError(f"UUID PSG ausente o inválido en {label}")
                    uuid = uuid.strip()
                    if uuid in seen:
                        duplicates += 1
                        different += record != seen[uuid]
                    else:
                        seen[uuid] = record
                        keep[path].append(position)
        except (OSError, UnicodeError, csv.Error):
            raise ValueError(f"No se pudo leer meta_uuid en {label}") from None
    if duplicates:
        logging.warning("UUID PSG repetidos en lote: %s omitidos; %s con valores distintos",
                        duplicates, different)
    logging.info("UUID PSG: entradas=%s, conservadas=%s, duplicadas=%s",
                 sum(len(rows) for rows in keep.values()) + duplicates,
                 sum(len(rows) for rows in keep.values()), duplicates)
    return keep


def _load_pipeline_config(config_path: str, search_bases: list[Path]) -> dict:
    config_file = resolve_existing_path(config_path, search_bases)
    with config_file.open("r", encoding="utf-8") as file:
        document = yaml.safe_load(file) or {}
    if "transform" in document:
        pipeline_config = dict(document["transform"])
        pipeline_config["schema"] = document.get("schema", {}).get("transform", {})
        return pipeline_config
    return _apply_declared_schemas(document, search_bases)


def _require_exact_columns(dataframe, schema_config: dict, section: str) -> None:
    expected = list(schema_config.get("columns", {}))
    if not expected or list(dataframe.columns) != expected:
        raise ValueError(f"Columnas u orden incorrectos en {section} PSG")


def _validate_psg_input_schema(dataframe, schema_config: dict) -> None:
    # Los números clínicos se convierten con incidencias en la operación PSG.
    metadata = {name: kind for name, kind in schema_config["columns"].items()
                if name.startswith("meta_") and name != "meta_fecha_estudio"}
    validate_input_schema(dataframe, {"columns": metadata})


def _resolve_nested_path(payload: Any, dotted_path: str) -> Any:
    current = payload
    for segment in [part.strip() for part in dotted_path.split(".") if part.strip()]:
        if not isinstance(current, dict) or segment not in current:
            raise ValueError(f"No existe la ruta de schema declarada: {dotted_path}")
        current = current[segment]
    return current


def _coerce_columns_mapping(schema_payload: Any) -> dict[str, str]:
    if not isinstance(schema_payload, dict) or not schema_payload:
        raise ValueError("El schema declarado debe ser un diccionario no vacío")

    return {str(column): str(field_type) for column, field_type in schema_payload.items()}


def _apply_declared_schema(
    pipeline_config: dict,
    declarations: dict,
    search_bases: list[Path],
    section_name: str,
) -> None:
    schema_yaml_path = str(declarations.get(f"{section_name}_schema_yaml_path", "")).strip()
    if not schema_yaml_path:
        return

    schema_file = resolve_existing_path(schema_yaml_path, search_bases)
    with schema_file.open("r", encoding="utf-8") as file:
        schema_yaml = yaml.safe_load(file) or {}

    schema_path = str(declarations.get(f"{section_name}_schema_path_in_yaml", "")).strip()
    schema_payload = _resolve_nested_path(schema_yaml, schema_path) if schema_path else schema_yaml
    columns = _coerce_columns_mapping(schema_payload)

    schema_section = pipeline_config.setdefault("schema", {})
    section_config = schema_section.setdefault(section_name, {})
    section_config["columns"] = columns


def _apply_declared_schemas(pipeline_config: dict, search_bases: list[Path]) -> dict:
    declarations = pipeline_config.get("declarations")
    if not isinstance(declarations, dict):
        return pipeline_config

    _apply_declared_schema(pipeline_config, declarations, search_bases, "input")
    _apply_declared_schema(pipeline_config, declarations, search_bases, "output")
    return pipeline_config


def _resolve_output_target(
    resolved_input_path: Path,
    output_path: str | None,
    pipeline_config: dict,
    search_bases: list[Path],
) -> Path:
    if output_path:
        return resolve_output_path(output_path, search_bases)

    return build_default_output_path(
        input_path=resolved_input_path,
        pipeline_output_dir=STAGING_DIR,
        pipeline_config=pipeline_config,
    )


def _confirm_execution(plans: list[tuple[Path, Path]], dry_run: bool) -> bool:
    print("\nPlan de ejecución PSG:")
    for input_file, output_file in plans:
        print(f"- Input: {input_file}")
        if dry_run:
            print(f"  Output estimado: {output_file} (dry-run, no se escribirá)")
        else:
            print(f"  Output: {output_file}")
            if output_file.exists():
                print(f"  WARNING: El archivo de destino ya existe y será sobrescrito: {output_file}")

    answer = input("\n¿Deseas continuar con el procesamiento? [y/N]: ").strip().lower()
    return answer in {"y", "yes", "s", "si", "sí"}


def run(
    config_path: str,
    input_path: str,
    output_path: str | None,
    dry_run: bool = False,
    keep_rows: list[int] | None = None,
) -> Path | None:
    search_bases = _search_bases()
    pipeline_config = _load_pipeline_config(config_path, search_bases)

    registry = OperationRegistry()
    register_builtin_operations(registry)
    register_psg_operations(registry)

    resolved_input_path = resolve_existing_path(input_path, search_bases)
    if resolved_input_path.suffix.lower() not in SUPPORTED_INPUT_EXTENSIONS:
        raise ValueError("La entrada PSG debe ser un CSV de extracción")
    dataframe = read_dataset(str(resolved_input_path), config=pipeline_config.get("input", {}))
    _require_exact_columns(dataframe, pipeline_config.get("schema", {}).get("input", {}), "entrada")
    _validate_psg_input_schema(dataframe, pipeline_config["schema"]["input"])
    if keep_rows is None:
        keep_rows = _check_selected_uuids([resolved_input_path], pipeline_config.get("input", {}))[resolved_input_path]
    discarded = ~dataframe.index.isin(keep_rows)
    validate_psg_technical_metadata(dataframe.loc[discarded])
    dataframe = dataframe.iloc[keep_rows].copy()
    if dataframe.empty:
        return None

    transformed = run_pipeline(
        pipeline_config=pipeline_config,
        registry=registry,
        dataframe=dataframe,
    )
    if len(transformed) != len(dataframe):
        raise ValueError("La transformación PSG cambió el número de registros")
    _require_exact_columns(transformed, pipeline_config.get("schema", {}).get("output", {}), "salida")

    validate_output_schema(
        dataframe=transformed,
        schema_config=pipeline_config.get("schema", {}).get("output", {}),
    )

    if dry_run:
        return None

    resolved_output_path = _resolve_output_target(
        resolved_input_path=resolved_input_path,
        output_path=output_path,
        pipeline_config=pipeline_config,
        search_bases=search_bases,
    )
    return write_dataset(
        dataframe=transformed,
        output_path=str(resolved_output_path),
        config=pipeline_config.get("output", {}),
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Runner del pipeline PSG")
    parser.add_argument(
        "--config",
        required=False,
        default=str(PROJECT_ROOT / "0_declarations" / "psg.yaml"),
        help="Ruta al archivo config.yaml del pipeline PSG.",
    )
    parser.add_argument(
        "--input",
        required=False,
        default=None,
        help=(
            "Ruta al CSV de extracción PSG. "
            "Si no se indica, procesa automáticamente todos los archivos válidos de este flow en staging/."
        ),
    )
    parser.add_argument(
        "--output",
        required=False,
        default=None,
        help=(
            "Ruta de salida del archivo procesado. "
            "Si no se indica, usa el nombre del input + '_transformed' en staging/."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ejecuta validación y transformaciones sin escribir salida.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    return execute(
        config_path=args.config,
        input_path=args.input,
        output_path=args.output,
        dry_run=args.dry_run,
    )


def execute(
    config_path: str,
    input_path: str | None,
    output_path: str | None,
    dry_run: bool,
) -> int:
    search_bases = _search_bases()
    pipeline_config = _load_pipeline_config(config_path, search_bases)

    input_files: list[Path]
    if input_path:
        input_files = [resolve_existing_path(input_path, search_bases)]
    else:
        input_files = _discover_input_files()

    if not input_files:
        raise FileNotFoundError(
            "No se encontraron archivos de entrada para este flow en staging/. "
            "Agrega un archivo 'extract_<flow>_...(.csv/.xlsx/.xls)' o usa --input."
        )

    if output_path and len(input_files) > 1:
        raise ValueError(
            "No se puede usar --output con múltiples archivos detectados en staging/. "
            "Usa --input para procesar uno específico."
        )

    keep_rows = _check_selected_uuids(input_files, pipeline_config.get("input", {}))

    plans: list[tuple[Path, Path]] = []
    for input_file in input_files:
        plans.append(
            (
                input_file,
                _resolve_output_target(
                    resolved_input_path=input_file,
                    output_path=output_path,
                    pipeline_config=pipeline_config,
                    search_bases=search_bases,
                ),
            )
        )

    if not _confirm_execution(plans, dry_run):
        print("Procesamiento cancelado por el usuario.")
        return 0

    for input_file in input_files:
        generated_output = run(
            config_path=config_path,
            input_path=str(input_file),
            output_path=output_path,
            dry_run=dry_run,
            keep_rows=keep_rows[input_file],
        )
        if generated_output:
            print(f"✅ Procesamiento completado. Archivo generado: {generated_output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
