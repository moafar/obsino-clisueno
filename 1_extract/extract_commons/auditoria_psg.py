"""Auditoría PSG de una sola ejecución; no modifica CSV ni documentos."""
import argparse
import csv
import hashlib
import math
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean, median

import yaml
from src.basal.procesar_basal import _completeness

ABSENT = {"", "N/A", "NA", "NONE", "NULL", "NAN"}
SUMMARY = {"archivos": "num_files", "válidos": "archivos_validos",
           "filas_nuevas": "archivos_registrados", "nuevos_archivados": "archivos_extraidos",
           "duplicados": "archivos_duplicados", "fallos_archivado": "archivos_fallo_archivado",
           "reintentos": "archivos_reintentados", "rechazados": "archivos_rechazados",
           "errores_recorrido": "errores_recorrido"}


def present(value):
    return value is not None and value.strip().upper() not in ABSENT


def date_value(value):
    if not present(value):
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(value.strip(), fmt).date()
        except ValueError:
            pass
    raise ValueError("Fecha inválida")


def typed(value, kind):
    if not present(value):
        return None
    if kind == "string":
        return value
    if kind == "date":
        return date_value(value)
    if kind not in {"int", "float"}:
        raise ValueError("Tipo no soportado")
    number = float(value.strip().replace(",", "."))
    if not math.isfinite(number) or (kind == "int" and not number.is_integer()):
        raise ValueError("Número inválido")
    return number


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "md5").hexdigest()


def read_log(path):
    """Solo mensajes agregados; las rutas nunca se copian al informe."""
    moves, duplicates, reasons = defaultdict(list), [], Counter()
    summary = None
    for line in path.read_text(encoding="utf-8").splitlines():
        message = line.split(" $$ ", 2)[-1]
        if message.startswith("Traslado PSG correcto: origen="):
            origin, sep, destination = message.removeprefix(
                "Traslado PSG correcto: origen=").rpartition(" destino=")
            if sep:
                moves[origin].append(destination)
        elif message.startswith(("UUID PSG duplicado en otro origen; no se archiva: ",
                                 "UUID PSG ya presente en CSV; no se archiva: ")):
            duplicates.append(message.split(": ", 1)[1])
        elif message.startswith("Archivo excluido por patrón OXIGENO"):
            reasons["Exclusión OXIGENO"] += 1
        elif message.startswith("Extracción PSG omitida:"):
            reasons["Extracción PSG omitida"] += 1
        elif message.startswith("Error al procesar documento:"):
            reasons["Error al procesar documento"] += 1
        elif message.startswith("Sección PSG sin datos ("):
            section = message.split("(", 1)[1].split(")", 1)[0]
            reasons["Advertencia de sección: " + section] += 1
        elif message.startswith("Resumen:"):
            fields = dict(re.findall(r"([\w]+)=(\d+)", message))
            if all(key in fields for key in SUMMARY):
                summary = {target: int(fields[key]) for key, target in SUMMARY.items()}
    return moves, duplicates, reasons, summary


def residual_count(source, archive, extensions):
    count = 0
    def fail(error):
        raise error
    for current, directories, files in os.walk(source, followlinks=False, onerror=fail):
        directories[:] = [name for name in directories
                          if not (Path(current) / name).resolve().is_relative_to(archive)]
        count += sum((Path(current) / name).is_file() and
                     Path(name).suffix.lower().lstrip(".") in extensions for name in files)
    return count


def audit_psg(csv_path, log_path, contract_path, source, archive, result=None,
              extensions=("doc", "rtf"), elapsed=None):
    """Devuelve (ruta del informe, estado). ERROR no revierte el archivado."""
    csv_path, log_path, contract_path, source, archive = map(
        Path, (csv_path, log_path, contract_path, source, archive))
    source, archive = source.resolve(), archive.resolve()
    output = log_path.with_name(log_path.stem + "_auditoria.md")
    lines = ["# Auditoría de extracción PSG", "", "CSV: " + csv_path.name,
             "Contrato: " + contract_path.name, ""]
    states = []
    def check(name, state, detail):
        states.append(state)
        lines.append(f"- **{state} — {name}:** {detail}")
    def status(ok):
        return "OK" if ok else "ERROR"

    with contract_path.open(encoding="utf-8") as stream:
        schema = yaml.safe_load(stream)["schema"]["transform"]["input"]["columns"]
    moves, duplicates, reasons, logged = read_log(log_path)
    result = result if result is not None else logged
    if result is None:
        raise ValueError("No se dispone del resumen de ejecución")
    n = result["archivos_registrados"]
    archived = result["archivos_extraidos"]
    retried = result["archivos_reintentados"]
    failed = result["archivos_fallo_archivado"]
    rejected = result["archivos_rechazados"]
    duplicate_count = result["archivos_duplicados"]
    valid = result["archivos_validos"]
    lines += ["## Integridad operativa", "",
              f"Encontrados: {result['num_files']}; válidos: {valid}; filas nuevas: {n}; "
              f"archivados nuevos: {archived}; duplicados: {duplicate_count}; "
              f"rechazados: {rejected}; reintentos: {retried}; fallos: {failed}."]
    if elapsed is not None:
        lines.append(f"Duración de extracción (s): {elapsed:.2f}.")
    check("Conciliación", status(valid == archived + retried + failed + rejected + duplicate_count
                                and archived <= n <= archived + failed
                                and valid <= result["num_files"]),
          "Contadores de la ejecución.")
    check("Archivado y recorrido", status(not failed and not result["errores_recorrido"]),
          f"Fallos de archivado: {failed}; errores de recorrido: {result['errores_recorrido']}.")
    try:
        residual = residual_count(source, archive, set(extensions))
        expected = valid - archived - retried
        check("Inventario residual", status(residual == expected),
              f"Observado: {residual}; esperado: {expected}.")
    except OSError:
        check("Inventario residual", "NO EVALUADO", "No se pudo recorrer el origen.")

    lines += ["", "## Integridad y calidad del CSV", ""]
    rows = []
    header = []
    malformed = 0
    if csv_path.is_file():
        with csv_path.open(encoding="utf-8", newline="") as stream:
            reader = csv.reader(stream, strict=True)
            header = next(reader, [])
            for values in reader:
                if len(values) != len(header):
                    malformed += 1
                    continue
                rows.append(dict(zip(header, values)))
    check("Número de registros", status(len(rows) == n and not malformed),
          f"Esperados: {n}; filas completas: {len(rows)}; filas malformadas: {malformed}.")
    schema_ok = header == list(schema)
    if not header and n == 0 and not csv_path.exists():
        check("Esquema", "NO EVALUADO", "No se generó CSV porque no hubo filas nuevas.")
    else:
        check("Esquema", status(schema_ok),
              f"Esperadas: {len(schema)}; observadas: {len(header)}; "
              f"faltantes: {len(set(schema) - set(header))}; "
              f"adicionales: {len(set(header) - set(schema))}; orden exacto: {schema_ok}.")

    uuids = Counter()
    invalid_types, available, months = Counter(), Counter(), Counter()
    by_format, format_rows = defaultdict(Counter), Counter()
    scores, dates, ids = [], [], set()
    invalid_uuid = missing_id = missing_date = invalid_date = bad_score = 0
    trace_missing = trace_bad = trace_ok = 0
    if schema_ok and rows:
        for row in rows:
            uid = row["meta_uuid"].strip()
            if not re.fullmatch(r"[0-9a-f]{32}", uid):
                invalid_uuid += 1
            uuids[uid] += 1
            missing_id += not present(row["pte_id"])
            if present(row["pte_id"]):
                ids.add(row["pte_id"].strip())
            fmt = Path(row["meta_fuente"]).suffix.lower().lstrip(".")
            fmt = fmt if fmt in {"doc", "rtf"} else "otro"
            format_rows[fmt] += 1
            for name, kind in schema.items():
                value = row[name]
                if present(value):
                    available[name] += 1
                    by_format[fmt][name] += 1
                try:
                    typed(value, kind)
                except (ValueError, OverflowError):
                    invalid_types[name] += 1
            try:
                date = date_value(row["meta_fecha_estudio"])
                if date is None:
                    missing_date += 1
                else:
                    dates.append(date)
                    months[date.strftime("%Y-%m")] += 1
            except ValueError:
                invalid_date += 1
            try:
                score = float(row["meta_completitud_pct"])
                if not math.isfinite(score) or abs(score - float(_completeness(row, fmt))) > 0.00001:
                    raise ValueError()
                scores.append(score)
            except (ValueError, KeyError):
                bad_score += 1
            paths = moves.get(row["meta_fuente"], [])
            if len(paths) != 1:
                trace_missing += 1
            else:
                try:
                    target = Path(paths[0])
                    if (not target.resolve().is_relative_to(archive) or
                            target.is_symlink() or digest(target) != uid):
                        trace_bad += 1
                    else:
                        trace_ok += 1
                except OSError:
                    trace_bad += 1
        check("UUID", status(not invalid_uuid and len(uuids) == len(rows)),
              f"Inválidos o ausentes: {invalid_uuid}; repetidos: {len(rows)-len(uuids)}.")
        check("Tipos YAML", status(not invalid_types), f"Valores inválidos: {sum(invalid_types.values())}.")
        for name, count in invalid_types.items():
            lines.append(f"  - {name}: {count}")
        check("Identificación", "ADVERTENCIA" if missing_id else "OK", f"ID ausentes: {missing_id}; identificadores distintos: {len(ids)}.")
        check("Fechas", "ADVERTENCIA" if missing_date or invalid_date else "OK",
              f"Ausentes: {missing_date}; inválidas: {invalid_date}.")
        if dates:
            lines.append(f"  - Fecha mínima: {min(dates)}; máxima: {max(dates)}.")
        for month, count in sorted(months.items()):
            lines.append(f"  - {month}: {count}")
        check("Recálculo de completitud", status(not bad_score), f"Discrepancias: {bad_score}.")
        if scores:
            lines.append(f"  - Mínimo: {min(scores):.2f}%; media: {mean(scores):.2f}%; "
                         f"mediana: {median(scores):.2f}%; máximo: {max(scores):.2f}%.")
        lines += ["", "### Completitud por variable y formato", "",
                  "| Campo | Presentes | Ausentes | % | DOC % | RTF % |",
                  "|---|---:|---:|---:|---:|---:|"]
        def pct(a, b):
            return f"{100*a/b:.2f}" if b else "—"
        groups = defaultdict(list)
        for name in schema:
            a = available[name]
            lines.append(f"| {name} | {a} | {len(rows)-a} | {pct(a,len(rows))} | "
                         f"{pct(by_format['doc'][name],format_rows['doc'])} | "
                         f"{pct(by_format['rtf'][name],format_rows['rtf'])} |")
            groups[name.split("_", 1)[0]].append(name)
        lines += ["", "### Completitud por sección", ""]
        for group, names in groups.items():
            lines.append(f"- {group}: {pct(sum(available[x] for x in names),len(rows)*len(names))}%")
        lines.append(f"- Formatos: DOC={format_rows['doc']}; RTF={format_rows['rtf']}; otro={format_rows['otro']}.")
    else:
        check("Calidad de campos", "NO EVALUADO", "Sin filas o esquema incompatible.")

    lines += ["", "## Trazabilidad y rechazos", ""]
    if schema_ok and rows:
        check("Trazabilidad CSV–log–archivo", status(trace_ok == len(rows)),
              f"MD5 correctos: {trace_ok}; rutas ausentes/ambiguas: {trace_missing}; "
              f"archivos ausentes o hash incorrecto: {trace_bad}.")
    else:
        check("Trazabilidad CSV", "NO EVALUADO", "Sin filas auditables.")
    check("Traslados registrados", status(sum(map(len, moves.values())) == archived + retried),
          f"Log: {sum(map(len,moves.values()))}; esperados: {archived+retried}.")
    check("Duplicados registrados", "OK" if len(duplicates) == duplicate_count else "ADVERTENCIA",
          f"Log: {len(duplicates)}; contador: {duplicate_count}. No se consultan CSV anteriores.")
    duplicate_matches = duplicate_unverified = 0
    for origin in duplicates:
        try:
            candidate = Path(origin)
            if (candidate.resolve().is_relative_to(source) and not candidate.is_symlink()
                    and digest(candidate) in uuids):
                duplicate_matches += 1
            else:
                duplicate_unverified += 1
        except OSError:
            duplicate_unverified += 1
    lines.append(f"- Duplicados con MD5 en este CSV: {duplicate_matches}; no verificables "
                 f"sin histórico o archivo accesible: {duplicate_unverified}.")
    lines.append(f"- Rechazados: {rejected}. Motivos explícitos y advertencias del log (no equivalen a documentos únicos):")
    for reason, count in reasons.items():
        lines.append(f"  - {reason}: {count}")
    lines.append("- Clasificación exhaustiva de rechazados: NO EVALUADO; algunas salidas no registran motivo.")
    lines.append("- Unicidad histórica: NO EVALUADO; fuera del alcance.")
    final = ("ERROR" if "ERROR" in states else "ADVERTENCIA" if
             any(s in states for s in ("ADVERTENCIA", "NO EVALUADO")) else "OK")
    lines[1:1] = ["", f"**Resultado: {final}**"]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output, final


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auditar una extracción PSG ya realizada")
    for name in ("input", "log", "source", "archive"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--contract", type=Path, default=Path(__file__).resolve().parents[2] /
                        "0_declarations/psg.yaml")
    args = parser.parse_args()
    path, state = audit_psg(args.input, args.log, args.contract, args.source, args.archive)
    print(f"Auditoría PSG: {state} | {path}")
    raise SystemExit(1 if state == "ERROR" else 0)
