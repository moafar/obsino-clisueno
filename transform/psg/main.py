from __future__ import annotations

import argparse
from pathlib import Path
import sys

TRANSFORM_ROOT = Path(__file__).resolve().parents[1]
if str(TRANSFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(TRANSFORM_ROOT))

from commons.engine import OperationRegistry, run_pipeline
from commons.io import read_dataset, write_dataset
from commons.ops import register_builtin_operations
from commons.schema import validate_input_schema, validate_output_schema
from psg.core.transforms import register_psg_operations


def run(config_path: str, input_path: str, output_path: str, dry_run: bool = False) -> Path | None:
    import yaml

    config_file = Path(config_path)
    with config_file.open("r", encoding="utf-8") as file:
        pipeline_config = yaml.safe_load(file) or {}

    registry = OperationRegistry()
    register_builtin_operations(registry)
    register_psg_operations(registry)

    dataframe = read_dataset(input_path, config=pipeline_config.get("input", {}))

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

    return write_dataset(
        dataframe=transformed,
        output_path=output_path,
        config=pipeline_config.get("output", {}),
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Runner del pipeline PSG")
    parser.add_argument(
        "--config",
        required=False,
        default="transform/psg/config.yaml",
        help="Ruta al archivo config.yaml del pipeline PSG.",
    )
    parser.add_argument(
        "--input",
        required=False,
        default="transform/psg/input/unificado_basal.csv",
        help="Ruta al archivo de entrada (xlsx/csv).",
    )
    parser.add_argument(
        "--output",
        required=False,
        default="transform/psg/output/processed.xlsx",
        help="Ruta de salida del archivo procesado.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Ejecuta validación y transformaciones sin escribir salida.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    run(
        config_path=args.config,
        input_path=args.input,
        output_path=args.output,
        dry_run=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
