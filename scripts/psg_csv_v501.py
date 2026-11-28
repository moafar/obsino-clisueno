#!/usr/bin/env python3
"""Adapta un CSV PSG v5.0.0 (158 columnas) al contrato v5.0.1 (159).

Solo agrega meta_completitud_pct; no modifica los valores ni los metadatos
originales, no relee informes clínicos y nunca sobrescribe el CSV fuente.

Ejemplos, desde la raíz del repositorio:
  python scripts/psg_csv_v501.py --input staging/extract_psg_ANTERIOR.csv --dry-run
  python scripts/psg_csv_v501.py --input staging/extract_psg_ANTERIOR.csv \
      --output /ruta/aislada/extract_psg_ANTERIOR.csv
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import tempfile
from contextlib import ExitStack
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "1_extract"))

from src.basal.procesar_basal import PSG_COLUMNS, _completeness  # noqa: E402


def convert_psg_csv(source: Path, destination: Path | None = None, *,
                    dry_run: bool = False) -> tuple[int, float, float, float]:
    """Devuelve (registros, mínimo, promedio, máximo) sin alterar el origen."""
    source = source.resolve()
    if not source.is_file():
        raise ValueError(f"No existe el CSV de entrada: {source}")
    if PSG_COLUMNS[-1] != "meta_completitud_pct" or len(PSG_COLUMNS) != 159:
        raise ValueError("Contrato PSG v5.0.1 inesperado")

    if not dry_run:
        if destination is None:
            raise ValueError("Debes indicar --output o usar --dry-run")
        destination = destination.resolve()
        if destination == source:
            raise ValueError("La salida no puede ser el CSV original")
        if not destination.parent.is_dir():
            raise ValueError(f"El directorio de salida no existe: {destination.parent}")
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"La salida ya existe: {destination}")

    legacy_columns = list(PSG_COLUMNS[:-1])
    uuid_index = legacy_columns.index("meta_uuid")
    uuids: set[str] = set()
    count = 0
    sum_pct = 0.0
    min_pct = 100.0
    max_pct = 0.0
    temporary: Path | None = None

    try:
        with ExitStack() as stack:
            input_stream = stack.enter_context(
                source.open("r", encoding="utf-8-sig", newline="")
            )
            reader = csv.reader(input_stream, delimiter=",", strict=True)
            header = next(reader, None)
            if header != legacy_columns:
                raise ValueError(
                    "El CSV de entrada no coincide exactamente con las 158 "
                    "columnas y el orden de PSG v5.0.0"
                )

            writer = None
            if not dry_run:
                output_stream = tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", newline="", delete=False,
                    dir=destination.parent, prefix=f".{destination.name}.",
                    suffix=".tmp",
                )
                temporary = Path(output_stream.name)
                stack.enter_context(output_stream)
                writer = csv.writer(output_stream, lineterminator="\n")
                writer.writerow(PSG_COLUMNS)

            for record in reader:
                if len(record) != len(legacy_columns):
                    raise ValueError(
                        f"Fila CSV terminada en línea {reader.line_num}: "
                        f"{len(record)} columnas, esperadas {len(legacy_columns)}"
                    )
                uuid = record[uuid_index].strip().lower()
                if not uuid or uuid in uuids:
                    raise ValueError(
                        f"UUID PSG vacío o repetido en línea CSV {reader.line_num}"
                    )
                uuids.add(uuid)

                row = dict(zip(legacy_columns, record))
                percentage = _completeness(row, "legacy")
                value = float(percentage)
                count += 1
                sum_pct += value
                min_pct = min(min_pct, value)
                max_pct = max(max_pct, value)

                if writer is not None:
                    writer.writerow([*record, percentage])

            if not count:
                raise ValueError("El CSV de entrada no contiene registros")
            if writer is not None:
                output_stream.flush()
                os.fsync(output_stream.fileno())

        if temporary is not None:
            # Creación atómica sin sobrescritura, incluso ante escrituras concurrentes.
            os.link(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)

    return count, min_pct, sum_pct / count, max_pct


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", required=True, type=Path, help="CSV PSG v5.0.0 de 158 columnas")
    parser.add_argument("--output", type=Path, help="CSV nuevo (no debe existir)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validar y calcular estadísticas sin escribir")
    args = parser.parse_args()

    try:
        count, minimum, average, maximum = convert_psg_csv(
            args.input, args.output, dry_run=args.dry_run
        )
    except (OSError, ValueError, csv.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Modo: {'VALIDACIÓN SIN ESCRITURA' if args.dry_run else 'CONVERSIÓN'}")
    print(f"Registros/UUID únicos: {count:,}")
    print("Columnas: 158 -> 159")
    print(f"Completitud (%): mín={minimum:.2f}; media={average:.2f}; máx={maximum:.2f}")
    if not args.dry_run:
        print(f"CSV generado: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
