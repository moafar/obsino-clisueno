"""Auditoría PSG de una sola ejecución; no modifica CSV ni documentos."""
import argparse
import csv
import json
import math
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean, median

import yaml
from extract_commons.directorio_utils import PSG_REJECTION_REASONS
from src.basal.procesar_basal import COMPLETENESS_FIELDS, _completeness

ABSENT = {"", "N/A", "NA", "NONE", "NULL", "NAN"}
SUMMARY = {"archivos": "num_files", "válidos": "archivos_validos",
           "filas_nuevas": "archivos_registrados", "nuevos_archivados": "archivos_extraidos",
           "duplicados": "archivos_duplicados", "fallos_archivado": "archivos_fallo_archivado",
           "reintentos": "archivos_reintentados", "rechazados": "archivos_rechazados",
           "errores_recorrido": "errores_recorrido",
           "errores_procesamiento": "errores_procesamiento"}


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
    if (not math.isfinite(number) or
            (kind == "int" and (not number.is_integer() or
                                not -(2**63) <= number < 2**63))):
        raise ValueError("Número inválido")
    return number


def indicator_present(row, field):
    if field == "pte_edad_anos":
        return any(present(row[name]) for name in
                   ("pte_edad_anos", "pte_edad_meses", "pte_edad_dias"))
    return present(row[field])


def percentile(values, fraction):
    """Percentil lineal sobre posiciones 0..n-1; requiere al menos un valor."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low = math.floor(position)
    high = math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def read_log(path):
    """Lee eventos del log; las rutas individuales nunca se copian al informe."""
    moves, duplicates, warnings, rejects = defaultdict(list), [], Counter(), []
    malformed_rejects = 0
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
        elif message.startswith("Rechazo PSG: "):
            try:
                event = json.loads(message.removeprefix("Rechazo PSG: "))
                if (not isinstance(event, dict) or
                        event.get("codigo") not in PSG_REJECTION_REASONS or
                        event.get("motivo") != PSG_REJECTION_REASONS[event["codigo"]] or
                        not isinstance(event.get("origen"), str) or not event["origen"]):
                    raise ValueError("Evento de rechazo inválido")
                rejects.append(event)
            except (ValueError, TypeError, KeyError):
                malformed_rejects += 1
        elif message.startswith("Sección PSG sin datos ("):
            section = message.split("(", 1)[1].split(")", 1)[0]
            warnings[section] += 1
        elif message.startswith("Resumen:"):
            fields = dict(re.findall(r"([\w]+)=(\d+)", message))
            if all(key in fields for key in SUMMARY if key != "errores_procesamiento"):
                summary = {target: int(fields.get(key, 0)) for key, target in SUMMARY.items()}
    return moves, duplicates, warnings, rejects, malformed_rejects, summary


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
              extensions=("doc", "rtf"), elapsed=None, phase_times=None,
              orchestration_started_at=None):
    """Devuelve (ruta del informe, estado). ERROR no revierte el archivado."""
    audit_started_at = time.perf_counter()
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
    moves, duplicates, section_warnings, rejects, malformed_rejects, logged = read_log(log_path)
    result = result if result is not None else logged
    if result is None:
        raise ValueError("No se dispone del resumen de ejecución")
    n = result["archivos_registrados"]
    archived = result["archivos_extraidos"]
    retried = result["archivos_reintentados"]
    failed = result["archivos_fallo_archivado"]
    rejected = result["archivos_rechazados"]
    processing_errors = result.get("errores_procesamiento", 0)
    duplicate_count = result["archivos_duplicados"]
    valid = result["archivos_validos"]
    reject_codes = Counter(event["codigo"] for event in rejects)
    reject_origins = [event["origen"] for event in rejects]
    invalid_reject_sources = 0
    for event in rejects:
        origin = Path(event["origen"])
        try:
            in_root = origin.is_absolute() and origin.parent.resolve().is_relative_to(source)
            valid_type = (origin.is_symlink() if event["codigo"] == "ENLACE_SIMBOLICO"
                          else origin.is_file() and not origin.is_symlink())
            invalid_reject_sources += not (in_root and valid_type)
        except OSError:
            invalid_reject_sources += 1
    lines += ["## Resumen operativo", "",
              "| Concepto | Documentos |", "|---|---:|",
              f"| Encontrados | {result['num_files']} |",
              f"| Válidos por extensión | {valid} |",
              f"| Filas nuevas | {n} |",
              f"| Archivados nuevos | {archived} |",
              f"| Reintentos de archivado | {retried} |",
              f"| Duplicados detectados | {duplicate_count} |",
              f"| Rechazados | {rejected} |",
              f"| Fallos de archivado | {failed} |",
              f"| Errores de recorrido | {result['errores_recorrido']} |",
              f"| Errores técnicos de procesamiento | {processing_errors} |", ""]
    if elapsed is not None:
        lines.append(f"Duración de extracción (s): {elapsed:.2f}.")
    counted_valid = archived + retried + failed + rejected + duplicate_count + processing_errors
    check("Conciliación", status(valid == counted_valid
                                and archived <= n <= archived + failed
                                and valid <= result["num_files"]),
          f"Válidos={valid}; archivados + reintentos + fallos + rechazados + duplicados + "
          f"errores técnicos="
          f"{counted_valid}; filas nuevas={n}; archivados nuevos={archived}; "
          f"fallos de archivado={failed}.")
    check("Procesamiento, archivado y recorrido",
          status(not failed and not result["errores_recorrido"] and not processing_errors),
          f"Fallos de archivado: {failed}; errores de recorrido: "
          f"{result['errores_recorrido']}; errores técnicos: {processing_errors}.")
    check("Rechazos por motivo", status(sum(reject_codes.values()) == rejected
          and not malformed_rejects and len(set(reject_origins)) == len(reject_origins)
          and not invalid_reject_sources),
          f"Contador: {rejected}; eventos: {sum(reject_codes.values())}; "
          f"eventos malformados: {malformed_rejects}; orígenes repetidos: "
          f"{len(reject_origins)-len(set(reject_origins))}; "
          f"orígenes ausentes o fuera de raíz: {invalid_reject_sources}.")
    try:
        if not source.is_dir():
            raise OSError("Origen PSG no accesible")
        residual = residual_count(source, archive, set(extensions))
        expected = valid - archived - retried
        check("Inventario residual", status(residual == expected),
              f"Observado: {residual}; esperado: {expected}.")
    except OSError:
        check("Inventario residual", "ERROR", "No se pudo recorrer el origen.")

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
    empty_batch = n == 0 and not rows and not malformed and (schema_ok or not csv_path.exists())
    if not header and n == 0 and not csv_path.exists():
        check("Esquema", "NO APLICA", "No se generó CSV porque no hubo filas nuevas.")
    else:
        check("Esquema", status(schema_ok),
              f"Esperadas: {len(schema)}; observadas: {len(header)}; "
              f"faltantes: {len(set(schema) - set(header))}; "
              f"adicionales: {len(set(header) - set(schema))}; orden exacto: {schema_ok}.")

    uuids = Counter()
    invalid_clinical_types, invalid_technical_types, months = Counter(), Counter(), Counter()
    indicator_counts = defaultdict(Counter)
    format_rows, scores_by_format = Counter(), defaultdict(list)
    scores, dates, ids = [], [], set()
    invalid_uuid = missing_id = missing_date = invalid_date = bad_score = 0
    trace_missing = trace_bad = trace_ok = trace_reused = 0
    seen_targets = set()
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
            if fmt in COMPLETENESS_FIELDS:
                for field in COMPLETENESS_FIELDS[fmt]:
                    indicator_counts[fmt][field] += indicator_present(row, field)
            for name, kind in schema.items():
                value = row[name]
                try:
                    typed(value, kind)
                except (ValueError, OverflowError):
                    if kind in {"int", "float"} and not name.startswith("meta_"):
                        invalid_clinical_types[name] += 1
                    else:
                        invalid_technical_types[name] += 1
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
                scores_by_format[fmt].append(score)
            except (ValueError, KeyError):
                bad_score += 1
            paths = moves.get(row["meta_fuente"], [])
            if len(paths) != 1:
                trace_missing += 1
            else:
                try:
                    origin = Path(row["meta_fuente"])
                    target = Path(paths[0])
                    resolved_target = target.resolve()
                    if (not origin.is_absolute() or
                            not origin.resolve().is_relative_to(source) or
                            not resolved_target.is_relative_to(archive) or
                            target.is_symlink() or not target.is_file()):
                        trace_bad += 1
                    elif resolved_target in seen_targets:
                        trace_reused += 1
                    else:
                        seen_targets.add(resolved_target)
                        trace_ok += 1
                except OSError:
                    trace_bad += 1
        check("UUID", status(not invalid_uuid and len(uuids) == len(rows)),
              f"Inválidos o ausentes: {invalid_uuid}; repetidos: {len(rows)-len(uuids)}.")
        check("Tipos YAML", status(not invalid_technical_types),
              f"Valores técnicos inválidos: {sum(invalid_technical_types.values())}.")
        for name, count in invalid_technical_types.items():
            lines.append(f"  - {name}: {count}")
        check("Tipos clínicos numéricos", "ADVERTENCIA" if invalid_clinical_types else "OK",
              f"Valores incompatibles tolerados por E16: {sum(invalid_clinical_types.values())}.")
        for name, count in invalid_clinical_types.items():
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
        def fraction_text(count, total):
            return f"{count}/{total}" if total else "—"
        def pct(count, total):
            return f"{100*count/total:.2f}" if total else "—"
        fields_by_format = {fmt: set(fields) for fmt, fields in COMPLETENESS_FIELDS.items()}
        all_fields = fields_by_format["doc"] | fields_by_format["rtf"]
        logical_fields = [name for name in schema if name in all_fields]
        groups = defaultdict(list)
        lines += ["", "### Completitud por variable y formato", "",
                  "`—` indica campo no aplicable o formato sin filas; edad agrupa años, meses y días.", "",
                  "| Indicador lógico | DOC presentes/aplicables | DOC % | RTF presentes/aplicables | RTF % |",
                  "|---|---:|---:|---:|---:|"]
        for field in logical_fields:
            groups[field.split("_", 1)[0]].append(field)
            cells = []
            for fmt in ("doc", "rtf"):
                if field in fields_by_format[fmt] and format_rows[fmt]:
                    count = indicator_counts[fmt][field]
                    cells += [fraction_text(count, format_rows[fmt]), pct(count, format_rows[fmt])]
                else:
                    cells += ["—", "—"]
            label = "pte_edad_anos (edad)" if field == "pte_edad_anos" else field
            lines.append(f"| {label} | {' | '.join(cells)} |")
        lines += ["", "### Completitud por sección", "",
                  "| Sección | DOC indicadores | DOC presentes/aplicables | DOC % | "
                  "RTF indicadores | RTF presentes/aplicables | RTF % |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for group, names in groups.items():
            cells = []
            for fmt in ("doc", "rtf"):
                applicable = [name for name in names if name in fields_by_format[fmt]]
                total = format_rows[fmt] * len(applicable)
                count = sum(indicator_counts[fmt][name] for name in applicable)
                cells += [str(len(applicable)), fraction_text(count, total), pct(count, total)]
            lines.append(f"| {group} | {' | '.join(cells)} |")
        lines += ["", "### Distribución de completitud por formato", "",
                  "Percentiles lineales sobre puntuaciones válidas; las discrepantes quedan fuera de esta tabla.", "",
                  "| Formato | Filas | Puntuaciones válidas | Mínimo % | P50 % | P90 % | Máximo % |",
                  "|---|---:|---:|---:|---:|---:|---:|"]
        for fmt in ("doc", "rtf"):
            values = scores_by_format[fmt]
            stats = ([f"{min(values):.2f}", f"{percentile(values, 0.5):.2f}",
                      f"{percentile(values, 0.9):.2f}", f"{max(values):.2f}"]
                     if values else ["—"] * 4)
            lines.append(f"| {fmt.upper()} | {format_rows[fmt]} | {len(values)} | "
                         f"{' | '.join(stats)} |")
        lines.append(f"- Formato desconocido: {format_rows['otro']} filas; "
                     "no se calcula su completitud.")
    else:
        check("Calidad de campos", "NO APLICA" if empty_batch else "NO EVALUADO",
              "Sin filas nuevas." if empty_batch else "Sin filas o esquema incompatible.")

    lines += ["", "## Trazabilidad y rechazos", ""]
    if schema_ok and rows:
        check("Trazabilidad CSV–log–archivo", status(trace_ok == len(rows)),
              f"Archivos localizados: {trace_ok}; rutas ausentes/ambiguas: {trace_missing}; "
              f"rutas inválidas o archivos ausentes: {trace_bad}; destinos reutilizados: {trace_reused}.")
    else:
        check("Trazabilidad CSV", "NO APLICA" if empty_batch else "NO EVALUADO",
              "Sin filas nuevas." if empty_batch else "Sin filas auditables.")
    check("Traslados registrados", status(sum(map(len, moves.values())) == archived + retried),
          f"Log: {sum(map(len,moves.values()))}; esperados: {archived+retried}.")
    check("Duplicados registrados", "OK" if len(duplicates) == duplicate_count else "ADVERTENCIA",
          f"Log: {len(duplicates)}; contador: {duplicate_count}. No se consultan CSV anteriores.")
    duplicate_matches = duplicate_unverified = 0
    for origin in duplicates:
        try:
            candidate = Path(origin)
            if (candidate.resolve().is_relative_to(source) and not candidate.is_symlink()
                    and candidate.is_file()):
                duplicate_matches += 1
            else:
                duplicate_unverified += 1
        except OSError:
            duplicate_unverified += 1
    lines.append(f"- Fuentes duplicadas presentes en origen: {duplicate_matches}; "
                 f"no localizadas o fuera del origen: {duplicate_unverified}. "
                 "Contenido no verificado por la auditoría.")
    lines += ["", "### Motivos de rechazo", "",
              f"Eventos: {sum(reject_codes.values())}; contador: {rejected}.", "",
              "| Código | Documentos | Motivo |", "|---|---:|---|"]
    for code, count in sorted(reject_codes.items()):
        lines.append(f"| {code} | {count} | {PSG_REJECTION_REASONS[code]} |")
    if not reject_codes:
        lines.append("| — | 0 | Sin rechazos registrados |")
    if section_warnings:
        lines += ["", "### Advertencias de sección", "",
                  "Estas incidencias no son rechazos.", "",
                  "| Sección | Avisos |", "|---|---:|"]
        for section, count in sorted(section_warnings.items()):
            lines.append(f"| {section} | {count} |")
    lines += ["", "- Unicidad histórica: NO EVALUADO; fuera del alcance."]
    if phase_times is not None:
        audit_seconds = time.perf_counter() - audit_started_at
        lines += ["", "## Tiempos de la ejecución", "",
                  "| Fase | Segundos |", "|---|---:|",
                  f"| Lectura de UUID históricos | {phase_times['historicos_s']:.3f} |",
                  f"| Procesamiento | {phase_times['procesamiento_s']:.3f} |",
                  f"| Auditoría hasta escritura del informe | {audit_seconds:.3f} |"]
        if orchestration_started_at is not None:
            lines.append("| Orquestación hasta escritura del informe | "
                         f"{time.perf_counter() - orchestration_started_at:.3f} |")
        lines.append("")
    final = ("ERROR" if "ERROR" in states else "ADVERTENCIA" if
             any(s in states for s in ("ADVERTENCIA", "NO EVALUADO")) else "OK")
    counts = Counter(states)
    action = ("Detener la continuación automática y revisar el log; el archivado no se revierte."
              if final == "ERROR" else
              "Revisar advertencias y controles no evaluados antes de una carga desatendida."
              if final == "ADVERTENCIA" else "Sin incidencias técnicas detectadas.")
    lines[2:2] = [f"**Resultado: {final}**", "", action, "",
                  f"Controles: OK={counts['OK']}; ADVERTENCIA={counts['ADVERTENCIA']}; "
                  f"ERROR={counts['ERROR']}; NO EVALUADO={counts['NO EVALUADO']}; "
                  f"NO APLICA={counts['NO APLICA']}.", ""]
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
