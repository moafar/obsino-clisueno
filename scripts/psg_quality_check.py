#!/usr/bin/env python3
"""Auditoría de calidad PSG de solo lectura. Salida JSON; 0=correcto, 1=bloqueante, 2=lectura/contrato."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from zipfile import BadZipFile

import pandas as pd
import yaml
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "1_extract"))
sys.path.insert(0, str(ROOT / "2_transform"))
from src.basal.procesar_basal import PSG_COLUMNS, _completeness, _is_present  # noqa: E402
from psg.core.transforms import _parse_date  # noqa: E402

CONTRACT = ROOT / "0_declarations" / "psg.yaml"
UUID_RE = re.compile(r"[0-9a-fA-F]{32}\Z")


def _uuid(value: object) -> tuple[str, str | None]:
    if value is None:
        return "null", None
    cleaned = str(value).strip()
    if not cleaned:
        return "empty", None
    if not _is_present(value):
        return "null", None
    if not UUID_RE.fullmatch(cleaned):
        return "invalid_md5", None
    return "valid", cleaned.lower()


def _number(value: object) -> float | None:
    if not _is_present(value):
        return None
    try:
        number = float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _percentile(values: list[float], percentile: int) -> float:
    position = (len(values) - 1) * percentile / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def _count_explicit_zeros(records: list[dict], numeric_clinical: set[str]) -> int:
    """Cuenta ceros con la misma conversión numérica, aplicada por columna."""
    return int(sum(
        pd.to_numeric(
            pd.Series([row[column] for row in records], dtype="string")
            .str.strip().str.replace(",", ".", regex=False), errors="coerce"
        ).eq(0).sum()
        for column in numeric_clinical
    ))


def _read_csv(path: Path) -> tuple[list[str], list[list[str]], int]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, strict=True)
        header = next(reader, [])
        rows = list(reader)
    return header, rows, sum(len(row) != len(header) for row in rows)


def _contract_columns() -> tuple[list[str], list[str], str, set[str]]:
    with CONTRACT.open("r", encoding="utf-8") as stream:
        contract = yaml.safe_load(stream)
    source_types = contract["schema"]["transform"]["input"]["columns"]
    source = list(source_types)
    target = list(contract["schema"]["transform"]["output"]["columns"])
    sheet = contract["transform"]["output"]["sheet_name"]
    if len(source) != 159 or len(target) != 157 or source != list(PSG_COLUMNS):
        raise ValueError("Contrato PSG inconsistente con el extractor")
    numeric_clinical = {column for column, kind in source_types.items()
                        if kind in {"int", "float"} and not column.startswith("meta_")}
    return source, target, sheet, numeric_clinical


def _add_count_error(report: dict, label: str, count: int) -> None:
    if count:
        report["errors"].append(f"{label}: {count}")


def _check_historical(paths: list[Path], report: dict) -> set[str]:
    known: set[str] = set()
    for path in paths:
        header, rows, malformed = _read_csv(path)
        if malformed or header.count("meta_uuid") != 1:
            report["errors"].append("CSV histórico con esquema o filas inválidos")
            continue
        index = header.index("meta_uuid")
        invalid = 0
        for row in rows:
            uuid = _uuid(row[index])[1]
            if uuid is None:
                invalid += 1
            else:
                known.add(uuid)
        _add_count_error(report, "UUID históricos inválidos", invalid)
    return known


def _check_xlsx(path: Path, expected: list[str], sheet: str, source_rows: list[dict],
                report: dict) -> None:
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        if sheet not in workbook:
            report["errors"].append("Falta la hoja XLSX declarada")
            return
        values = workbook[sheet].values
        header = list(next(values, ()))
        rows = list(values)
    finally:
        workbook.close()

    report["statistics"]["transformed"] = {"records": len(rows), "columns": len(header)}
    if header != expected:
        report["errors"].append("Esquema XLSX distinto de las 157 columnas del contrato")
        return
    if len(rows) != len(source_rows):
        report["errors"].append("Número de registros XLSX distinto del CSV")

    source_by_uuid = {uuid: row["meta_completitud_pct"] for row in source_rows
                      if (uuid := _uuid(row["meta_uuid"])[1]) is not None}
    transformed: dict[str, object] = {}
    invalid = duplicate = 0
    uuid_index = header.index("meta_uuid")
    pct_index = header.index("meta_completitud_pct")
    for row in rows:
        if len(row) != len(header):
            report["errors"].append("Fila XLSX con número de columnas inválido")
            return
        uuid = _uuid(row[uuid_index])[1]
        if uuid is None:
            invalid += 1
        elif uuid in transformed:
            duplicate += 1
        else:
            transformed[uuid] = row[pct_index]
    _add_count_error(report, "UUID XLSX inválidos", invalid)
    _add_count_error(report, "UUID XLSX duplicados", duplicate)
    missing = len(source_by_uuid.keys() - transformed.keys())
    extra = len(transformed.keys() - source_by_uuid.keys())
    if missing or extra:
        report["errors"].append(f"Conjuntos UUID distintos (faltan={missing}, sobran={extra})")
    changed = sum(
        _number(transformed[uuid]) is None
        or _number(source_by_uuid[uuid]) is None
        or not math.isclose(_number(transformed[uuid]), _number(source_by_uuid[uuid]),
                            rel_tol=0, abs_tol=0.005)
        for uuid in source_by_uuid.keys() & transformed.keys()
    )
    _add_count_error(report, "meta_completitud_pct cambiado en XLSX", changed)


def check_quality(input_path: Path, transformed: Path | None = None,
                  historical: list[Path] | None = None, *, today: date | None = None) -> dict:
    """Devuelve errores bloqueantes, advertencias y estadísticas sin datos de pacientes."""
    source_columns, output_columns, sheet, numeric_clinical = _contract_columns()
    report: dict = {"errors": [], "warnings": [], "statistics": {}}
    header, rows, malformed = _read_csv(input_path)
    stats = report["statistics"]
    stats["records"] = len(rows)
    stats["columns"] = len(header)
    _add_count_error(report, "Filas CSV con número de columnas inválido", malformed)
    if header != source_columns:
        report["errors"].append("Esquema CSV distinto de las 159 columnas del contrato")
        return report
    if not rows:
        report["errors"].append("CSV sin registros")
    if malformed:
        return report

    records = [dict(zip(header, row)) for row in rows]
    clinical = [column for column in source_columns if not column.startswith("meta_")]
    missing = {column: sum(not _is_present(row[column]) for row in records) for column in clinical}
    stats["missing_by_variable"] = {
        column: {"count": count, "pct": round(100 * count / len(rows), 2) if rows else 0.0}
        for column, count in missing.items()
    }
    stats["completely_empty_variables"] = [column for column in clinical
                                            if rows and missing[column] == len(rows)]
    stats["explicit_zeros_present"] = _count_explicit_zeros(records, numeric_clinical)
    if stats["completely_empty_variables"]:
        report["warnings"].append(
            f"Variables clínicas completamente vacías: {len(stats['completely_empty_variables'])}"
        )

    uuid_counts = Counter()
    valid_uuids: set[str] = set()
    for row in records:
        kind, uuid = _uuid(row["meta_uuid"])
        if uuid is None:
            uuid_counts[kind] += 1
        else:
            uuid_counts["valid_total"] += 1
            if uuid in valid_uuids:
                uuid_counts["duplicate"] += 1
            else:
                valid_uuids.add(uuid)
    known = _check_historical(historical or [], report)
    uuid_counts["valid_unique"] = len(valid_uuids)
    uuid_counts["historical_unique"] = len(known)
    uuid_counts["shared_historical"] = len(valid_uuids & known)
    stats["uuid"] = {key: uuid_counts[key] for key in
                     ("valid_total", "valid_unique", "historical_unique", "null",
                      "empty", "invalid_md5", "duplicate", "shared_historical")}
    for key, label in (("null", "UUID nulos"), ("empty", "UUID vacíos"),
                       ("invalid_md5", "UUID con formato MD5 inválido"),
                       ("duplicate", "UUID duplicados"),
                       ("shared_historical", "UUID compartidos con históricos")):
        _add_count_error(report, label, uuid_counts[key])

    valid_pct: list[float] = []
    invalid_pct = mismatched_pct = 0
    for row in records:
        stored = _number(row["meta_completitud_pct"])
        if stored is None or not 0 <= stored <= 100:
            invalid_pct += 1
        else:
            valid_pct.append(stored)
            if not math.isclose(stored, float(_completeness(row)), rel_tol=0, abs_tol=0.005):
                mismatched_pct += 1
    _add_count_error(report, "meta_completitud_pct inválido", invalid_pct)
    _add_count_error(report, "meta_completitud_pct distinto del recálculo", mismatched_pct)
    ordered = sorted(valid_pct)
    stats["completeness_pct"] = {
        "valid": len(ordered), "min": ordered[0] if ordered else None,
        "max": ordered[-1] if ordered else None,
        "mean": statistics.mean(ordered) if ordered else None,
        "median": statistics.median(ordered) if ordered else None,
        "p5": _percentile(ordered, 5) if ordered else None,
        "p95": _percentile(ordered, 95) if ordered else None,
    }

    date_text, dates = _parse_date(pd.Series([row["meta_fecha_estudio"] for row in records],
                                            dtype="string"))
    absent_dates = int(date_text.isna().sum())
    invalid_dates = int((date_text.notna() & dates.isna()).sum())
    future_dates = sum(pd.notna(parsed) and parsed.date() > (today or date.today())
                       for parsed in dates)
    years = Counter(str(parsed.year) for parsed in dates if pd.notna(parsed))
    stats["dates"] = {"by_year": dict(sorted(years.items())), "missing": absent_dates,
                      "invalid": invalid_dates, "future": future_dates}
    _add_count_error(report, "Fechas inválidas", invalid_dates)
    for label, count in (("Fechas ausentes", absent_dates), ("Fechas futuras", future_dates)):
        if count:
            report["warnings"].append(f"{label}: {count}")

    if transformed is not None:
        _check_xlsx(transformed, output_columns, sheet, records, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="CSV de extracción PSG")
    parser.add_argument("--transformed", type=Path, help="XLSX transformado")
    parser.add_argument("--historical", nargs="+", type=Path, default=[],
                        help="CSV históricos de referencia")
    args = parser.parse_args(argv)
    try:
        report = check_quality(args.input, args.transformed, args.historical)
    except (OSError, UnicodeError, csv.Error, ValueError, KeyError, BadZipFile,
            yaml.YAMLError) as exc:
        report = {"errors": [f"No se pudo leer un archivo o contrato PSG ({type(exc).__name__})"],
                  "warnings": [], "statistics": {}}
        code = 2
    else:
        code = 1 if report["errors"] else 0
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
