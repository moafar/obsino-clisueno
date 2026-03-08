from __future__ import annotations

import argparse
from pathlib import Path
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

from commons.logging import configure_flow_logging

configure_flow_logging(FLOW_NAME)

from commons.engine import OperationRegistry, run_pipeline
from commons.io import (
    build_default_output_path,
    read_dataset,
    resolve_existing_path,
    resolve_output_path,
    write_dataset,
)
from commons.ops import register_builtin_operations
from commons.schema import validate_input_schema, validate_output_schema
from xpap.core.transforms import register_xpap_operations

SUPPORTED_INPUT_EXTENSIONS = {".csv", ".xlsx", ".xls"}


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
        )
    ]
    return files


def _load_pipeline_config(config_path: str, search_bases: list[Path]) -> dict:
    config_file = resolve_existing_path(config_path, search_bases)
    with config_file.open("r", encoding="utf-8") as file:
        pipeline_config = yaml.safe_load(file) or {}
    return _apply_declared_schemas(pipeline_config, search_bases)


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
    print("\nPlan de ejecución XPAP:")
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
) -> Path | None:
    search_bases = _search_bases()
    pipeline_config = _load_pipeline_config(config_path, search_bases)

    registry = OperationRegistry()
    register_builtin_operations(registry)
    register_xpap_operations(registry)

    resolved_input_path = resolve_existing_path(input_path, search_bases)
    dataframe = read_dataset(str(resolved_input_path), config=pipeline_config.get("input", {}))

    validate_input_schema(
        dataframe=dataframe,
        schema_config=pipeline_config.get("schema", {}).get("input", {}),
    )

    transformed = run_pipeline(
        pipeline_config=pipeline_config,
        registry=registry,
        dataframe=dataframe,
    )

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
    parser = argparse.ArgumentParser(description="Runner del pipeline XPAP")
    parser.add_argument(
        "--config",
        required=False,
        default="xpap/config.yaml",
        help="Ruta al archivo config.yaml del pipeline XPAP.",
    )
    parser.add_argument(
        "--input",
        required=False,
        default=None,
        help=(
            "Ruta al archivo de entrada (xlsx/csv). "
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
        )
        if generated_output:
            print(f"✅ Procesamiento completado. Archivo generado: {generated_output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
