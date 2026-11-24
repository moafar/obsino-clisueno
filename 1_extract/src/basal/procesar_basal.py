"""Indicadores PSG leídos de catdoc/striprtf; conversiones y derivados van a transform."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

class PSGExtractionError(ValueError):
    """El documento convertido no contiene una estructura PSG legible."""


PTE_COLUMNS = (
    "pte_nombre", "pte_id", "pte_edad_anos", "pte_edad_meses",
    "pte_edad_dias", "pte_imc_kg_m2",
)
PTE_UNIT_COLUMNS = tuple(
    f"pte_{part}_{kind}"
    for part in ("peso", "talla", "cuello", "perimetro_abdominal")
    for kind in ("valor", "unidad")
)
ARQ_COLUMNS = (
    "arq_tiempo_grabacion_min", "arq_tiempo_cama_min", "arq_tiempo_sueno_min",
    "arq_eficiencia_pct", "arq_latencia_sueno_min", "arq_latencia_rem_min",
    "arq_tiempo_despierto_min", "arq_microalertamientos_total_n",
    "arq_microalertamientos_respiratorios_n", "arq_microalertamientos_plm_n",
    "arq_microalertamientos_espontaneos_n", "arq_indice_despertares_por_hora",
)
FASE_COLUMNS = tuple(
    f"fase_{phase}_{measure}"
    for phase in ("s1", "s2", "s3", "rem")
    for measure in ("episodios_n", "duracion_min", "tst_pct")
) + ("fase_despierto_episodios_n", "fase_despierto_duracion_min")
EVRESP_COLUMNS = tuple(
    f"evresp_{event}_{measure}"
    for event in ("ac", "ao", "am", "ap", "hip", "ah")
    for measure in (
        "numero_n", "duracion_max_s", "duracion_media_s",
        "duracion_total_min", "indice_evhora",
    )
) + tuple(
    f"evresp_{event}_configuracion_s" for event in ("ac", "ao", "am", "hip")
) + tuple(
    f"evresp_{event}_numero_{phase}_n"
    for event in ("ac", "ao", "am", "hip", "ah")
    for phase in ("nrem", "rem")
) + tuple(f"evresp_iah_{phase}_evhora" for phase in ("rem", "nrem", "tst"))
OXI_COLUMNS = tuple(
    f"oxi_{measure}_{phase}_{unit}"
    for phase in ("despierto", "rem", "nrem", "tst")
    for measure, unit in (("spo2_promedio", "pct"), ("indice_desat", "evhora"))
) + tuple(
    f"oxi_t{threshold}_{phase}_min"
    for threshold in (95, 90, 85, 80, 75, 70, 60, 50)
    for phase in ("despierto", "rem", "nrem", "tst")
) + (
    "oxi_t90_pct", "oxi_spo2_eventos_promedio_pct",
    "oxi_spo2_eventos_min_pct", "oxi_spo2_sueno_min_pct",
)
FC_COLUMNS = tuple(f"fc_promedio_{phase}_lpm" for phase in ("despierto", "rem", "nrem"))
MOVMI_COLUMNS = (
    "movmi_plm_total_n", "movmi_plm_indice_evhora",
    "movmi_lm_total_n", "movmi_lm_indice_evhora",
)
POS_COLUMNS = tuple(
    f"pos_{position}_{measure}"
    for position in ("supino", "derecho", "izquierdo")
    for measure in ("duracion_min", "pct", "iah_evhora")
)
CLIN_COLUMNS = (
    "clin_indicacion", "clin_epworth_puntos", "clin_interpretacion",
    "clin_conclusiones", "clin_ronquido",
)
META_COLUMNS = (
    "meta_fecha_estudio", "meta_solicita", "meta_empresa",
    "meta_fuente", "meta_uuid", "meta_version_control",
)
PSG_COLUMNS = (
    PTE_COLUMNS + PTE_UNIT_COLUMNS + ARQ_COLUMNS + FASE_COLUMNS + EVRESP_COLUMNS
    + OXI_COLUMNS + FC_COLUMNS + MOVMI_COLUMNS + POS_COLUMNS + CLIN_COLUMNS + META_COLUMNS
)

NUMBER = re.compile(r"(?<!\w)[+-]?\d+(?:[.,]\d+)?")
TITLE = re.compile(
    r"^\s*INFORME\s+DE\s+POLISOMNOGRAFIA\s+BASAL\b"
    r"(?!\s+CON\s+DISPOSITIVO\b)"
)
NEXT_REPORT = re.compile(
    r"^\s*INFORME\s+(?:DE\s+)?(?:POLISOMNOGRAFIA|POLIGRAFIA|CAPNOGRAFIA)\b"
)
SECTIONS = (
    ("procedimiento", r"^PROCEDIMIENTO\b"),
    ("indicacion", r"^INDICACION\b"),
    ("interpretacion", r"^INTERPRETACION\b"),
    ("conclusiones", r"^CONCLUSIONES\b"),
    ("arquitectura", r"^ARQUITECTURA\s+DE\s+SUENO\s*:"),
    ("fases", r"^DISTRIBUCION\s+DE\s+FASES\s+DE\s+SUENO\s*:"),
    ("respiratorios", r"^RESUMEN\s+DE\s+EVENTOS\s+RESPIRATORIOS\b"),
    ("indices", r"^RESUMEN\s+DEL\s+INDICE\s+DE\s+EVENTOS\s+RESPIRATORIOS\b"),
    ("oximetria", r"^OXIMETRIA\s*:"),
    ("frecuencia", r"^FRECUENCIA\s+CARDIACA\s*:"),
    ("movimientos", r"^MOVIMIENTOS\s+DE\s+MIEMBROS\s+INFERIORES\s*:"),
    ("posicion", r"^POSICION\s+CORPORAL\s*:"),
)


def _fold(text: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", text).upper()
        if not unicodedata.combining(char)
    )


def _text(text: str) -> str:
    return " ".join(text.replace("|", " ").replace("\t", " ").split()).strip()


def _number(cell: str) -> str | None:
    if cell.strip() in ("", "-", "--"):
        return None
    match = NUMBER.search(cell)
    return match.group(0) if match else None


def _cells(line: str, delimiter: str) -> list[str]:
    return [part.strip() for part in line.split(delimiter)]


def _row(line: str, delimiter: str) -> tuple[str, list[str]]:
    cells = _cells(line, delimiter)
    while cells and not cells[0]:
        cells.pop(0)
    if delimiter == "|" and cells and not cells[-1]:
        cells.pop()
    return (cells[0], cells[1:]) if cells else ("", [])


def _find_row(lines: list[str], pattern: str, delimiter: str) -> tuple[list[str], int | None]:
    for index, line in enumerate(lines):
        label, values = _row(line, delimiter)
        if re.search(pattern, _fold(label)):
            return values, index
    return [], None


def _check_width(values: list[str], expected: int, section: str) -> None:
    if values and len(values) != expected:
        raise PSGExtractionError(f"Fila de {section} desalineada con sus encabezados")


def _required_row(lines: list[str], pattern: str, delimiter: str,
                  width: int, section: str) -> tuple[list[str], int]:
    values, index = _find_row(lines, pattern, delimiter)
    if index is None or len(values) != width:
        raise PSGExtractionError(f"Fila obligatoria de {section} ilegible")
    return values, index


def _column_map(lines: list[str], before: int, delimiter: str,
                patterns: dict[str, str], section: str) -> dict[str, int]:
    for heading in reversed(lines[:before]):
        cells = _cells(heading, delimiter)
        if cells and not cells[0]:
            cells.pop(0)
        if delimiter == "|" and cells and not cells[-1]:
            cells.pop()
        if len(cells) != len(patterns):
            continue
        columns = {}
        matched = False
        for index, cell in enumerate(cells):
            matches = [name for name, pattern in patterns.items()
                       if re.search(pattern, _fold(cell))]
            matched |= bool(matches)
            if len(matches) > 1 or (matches and matches[0] in columns):
                raise PSGExtractionError(f"Encabezado de {section} ambiguo")
            if matches:
                columns[matches[0]] = index
        if matched:
            if set(columns) != set(patterns):
                raise PSGExtractionError(f"Encabezado de {section} incompleto")
            return columns
    raise PSGExtractionError(f"Encabezado de {section} ilegible")


def _sections(text: str) -> dict[str, list[str]]:
    # Se conserva el texto del conversor, incluidos saltos y separadores vacíos.
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    start = next((i for i, line in enumerate(lines) if TITLE.search(_fold(line))), None)
    if start is None:
        raise PSGExtractionError("Título PSG basal ilegible")
    end = next(
        (i for i in range(start + 1, len(lines)) if NEXT_REPORT.search(_fold(lines[i]))),
        len(lines),
    )
    lines = lines[start:end]
    positions = []
    for index, line in enumerate(lines):
        label = _fold(line.strip())
        for name, pattern in SECTIONS:
            if re.search(pattern, label):
                positions.append((index, name))
                break
    result = {"cabecera": lines[:positions[0][0]] if positions else lines}
    for index, (begin, name) in enumerate(positions):
        finish = positions[index + 1][0] if index + 1 < len(positions) else len(lines)
        result[name] = lines[begin:finish]
    return result


def _labeled_number(lines: list[str], pattern: str, delimiter: str,
                    *, minutes_only: bool = False) -> str | None:
    for line in lines:
        cells = _cells(line, delimiter)
        for index, cell in enumerate(cells):
            match = re.search(pattern, _fold(cell))
            if match:
                suffix = cell[match.end():].strip().lstrip(": ")
                candidate = suffix or (cells[index + 1] if index + 1 < len(cells) else "")
                if minutes_only and not re.search(r"\bmin\b", candidate, re.I):
                    return None
                # La celda de otra etiqueta no es un valor de esta etiqueta.
                return _number(candidate) if NUMBER.match(candidate) else None
    return None


def _header_cell(lines: list[str], pattern: str, delimiter: str) -> str | None:
    for line in lines:
        cells = _cells(line, delimiter)
        for index, cell in enumerate(cells[:-1]):
            if re.search(pattern, _fold(cell)):
                return _text(cells[index + 1]) or None
    return None


def _header(out: dict, lines: list[str], delimiter: str) -> None:
    out["pte_nombre"] = _header_cell(lines, r"^NOMBRE\b", delimiter)
    out["pte_id"] = _header_cell(lines, r"^(?:ID|IDENTIFICACION)\s*:?$", delimiter)
    header = "\n".join(lines)
    for part, pattern in (
        ("anos", r"\b(\d+)\s+ANOS?\b"),
        ("meses", r"\b(\d+)\s+MESES?\b"),
        ("dias", r"\b(\d+)\s+DIAS?\b"),
    ):
        match = re.search(pattern, _fold(header))
        if match:
            out[f"pte_edad_{part}"] = match.group(1)
    for name, label in (
        ("peso", "PESO"), ("talla", "TALLA"), ("cuello", "CUELLO"),
        ("perimetro_abdominal", "PERIMETRO ABDOMINAL"),
    ):
        # catdoc puede continuar la celda abdominal en la línea siguiente.
        match = re.search(
            rf"\b{label}\b\s*:?\s*[\t|\n ]*(?:\(\s*([A-Z]+)\s*\)\s*[\t|\n ]*)?([+-]?\d+(?:[.,]\d+)?)\s*([A-Z]+)?",
            _fold(header),
        )
        if match:
            out[f"pte_{name}_valor"] = match.group(2)
            unit = match.group(1) or match.group(3)
            out[f"pte_{name}_unidad"] = unit.lower() if unit else None
    out["pte_imc_kg_m2"] = _labeled_number(lines, r"\bIMC\b", delimiter)
    match = re.search(r"\bSolicita\s*:?\s*(.*?)(?=\b(?:Empresa|Eps)\s*:)", header, re.I | re.S)
    if match:
        out["meta_solicita"] = _text(match.group(1)) or None
    match = re.search(r"\b(?:Empresa|Eps)\s*:?\s*(.*?)(?=\bFecha\b)", header, re.I | re.S)
    if match:
        out["meta_empresa"] = _text(match.group(1)) or None
    match = re.search(
        r"\bFECHA(?:\s+DEL\s+ESTUDIO)?\s*:?\s*[\t|\n ]*(\d{1,4}[-/]\d{1,2}[-/]\d{2,4})",
        _fold(header),
    )
    if match:
        out["meta_fecha_estudio"] = match.group(1)


def _narrative(out: dict, sections: dict) -> None:
    for name, field in (
        ("indicacion", "clin_indicacion"),
        ("interpretacion", "clin_interpretacion"),
        ("conclusiones", "clin_conclusiones"),
    ):
        out[field] = "\n".join(
            line.strip() for line in sections.get(name, [])[1:] if line.strip()
        ) or None
    prose = " ".join(
        _text(out[field] or "")
        for field in ("clin_indicacion", "clin_interpretacion", "clin_conclusiones")
    )
    match = re.search(r"\bEpworth\s*:?\s*(\d+)\s*/\s*\d+", prose, re.I)
    if match:
        out["clin_epworth_puntos"] = match.group(1)
    interpretation = out["clin_interpretacion"] or ""
    sentences = re.split(r"(?<=[.!?;])\s+", interpretation)
    snoring = [sentence.strip() for sentence in sentences
               if re.search(r"\bronquid\w*", sentence, re.I)]
    if snoring:
        out["clin_ronquido"] = " ".join(snoring)
    match = re.search(r"\bT\s*90\s*:\s*([+-]?\d+(?:[.,]\d+)?)\s*%", prose, re.I)
    if match:
        out["oxi_t90_pct"] = match.group(1)


def _architecture(out: dict, lines: list[str], delimiter: str) -> None:
    for field, pattern in (
        ("arq_tiempo_cama_min", r"\bTIEMPO\s+EN\s+CAMA\s*:"),
        ("arq_tiempo_sueno_min", r"\bTIEMPO\s+TOTAL\s+DE\s+SUENO\s*:"),
        ("arq_eficiencia_pct", r"\bEFICIENCIA\s+DE\s+SUENO\s*:"),
        ("arq_latencia_rem_min", r"\bLATENCIA\s+DE\s+SUENO\s+REM\s*:"),
        ("arq_latencia_sueno_min", r"\bLATENCIA\s+DE\s+SUENO\b(?!\s+REM)\s*:?"),
        ("arq_tiempo_despierto_min", r"\bTIEMPO\s+DESPIERTO\s+DURANTE\s+EL\s+SUENO\s*:"),
        ("arq_indice_despertares_por_hora", r"\bINDICE\s+DESPERTARES\s*:?"),
    ):
        out[field] = _labeled_number(lines, pattern, delimiter)
    out["arq_tiempo_grabacion_min"] = _labeled_number(
        lines, r"\bTIEMPO\s+DE\s+GRABACION\s*:", delimiter, minutes_only=True
    )
    values, index = _required_row(lines, r"^MICROALERTAMIENTOS$", delimiter, 4, "microalertamientos")
    columns = _column_map(lines, index, delimiter, {
        "total": r"\bTOTAL\b", "respiratorios": r"\bRESPIRATORIOS\b",
        "plm": r"\bPLM", "espontaneos": r"\bESPONTANEOS\b",
    }, "microalertamientos")
    for name, column in columns.items():
        out[f"arq_microalertamientos_{name}_n"] = _number(values[column])


def _phases(out: dict, lines: list[str], delimiter: str) -> None:
    _, first = _find_row(lines, r"^DESPIERTO\b", delimiter)
    if first is None:
        raise PSGExtractionError("Tabla de fases ilegible")
    patterns = {"duracion": r"\bDURACION\b", "tst": r"\bTST\b"}
    if delimiter == "\t":
        patterns = {"episodios": r"\bEPISODIOS\b", **patterns}
    columns = _column_map(lines, first, delimiter, patterns, "fases")
    for phase in ("s1", "s2", "s3", "rem", "despierto"):
        values, _ = _required_row(lines, rf"^{phase.upper()}\b", delimiter, len(columns), "fases")
        if "episodios" in columns:
            out[f"fase_{phase}_episodios_n"] = _number(values[columns["episodios"]])
        out[f"fase_{phase}_duracion_min"] = _number(values[columns["duracion"]])
        if phase != "despierto":
            out[f"fase_{phase}_tst_pct"] = _number(values[columns["tst"]])


def _event(label: str) -> str | None:
    label = _fold(label)
    if label in ("AC", "AO", "AM", "HIP"):
        return label.lower()
    if "SUMA AP" in label:
        return "ap"
    if "HIPOPNEAS" in label or "EVENTOS A + H" in label:
        return "ah"
    return None


def _respiratory(out: dict, lines: list[str], delimiter: str) -> None:
    header = next(
        (_cells(line, delimiter)[1:] for line in lines[:5]
         if "AC" in _cells(line, delimiter) and "AO" in _cells(line, delimiter)),
        None,
    )
    if header and header[-1] == "":
        header.pop()
    events = [_event(cell) for cell in header] if header else []
    expected_events = {"ac", "ao", "am", "hip", "ah"}
    if delimiter == "\t":
        expected_events.add("ap")
    if set(events) != expected_events or len(events) != len(expected_events):
        raise PSGExtractionError("Columnas respiratorias ilegibles")
    for measure, pattern in (
        ("numero_n", r"^NUMERO$"),
        ("duracion_max_s", r"^(?:MAXIMA DURACION|MAX\.)"),
        ("duracion_media_s", r"^(?:DURACION MEDIA|MEDIA)"),
        ("duracion_total_min", r"^DURACION TOTAL"),
        ("indice_evhora", r"^INDICE\b"),
    ):
        values, _ = _required_row(lines, pattern, delimiter, len(events), "eventos respiratorios")
        for event, cell in zip(events, values):
            if event:
                out[f"evresp_{event}_{measure}"] = _number(cell)
    for phase in ("nrem", "rem"):
        values, _ = _find_row(lines, rf"^NUMERO EN {phase.upper()}$", delimiter)
        if delimiter == "|":
            values, _ = _required_row(lines, rf"^NUMERO EN {phase.upper()}$", delimiter,
                                      len(events), "recuentos respiratorios")
        else:
            _check_width(values, len(events), "recuentos respiratorios")
        for event, cell in zip(events, values):
            if event in ("ac", "ao", "am", "hip", "ah"):
                out[f"evresp_{event}_numero_{phase}_n"] = _number(cell)
    values, index = _find_row(lines, r"^CONFIGURACION", delimiter)
    if delimiter == "\t" and (index is None or len(values) not in (3, 4)):
        raise PSGExtractionError("Configuración respiratoria DOC ilegible")
    if values:
        numbers = [_number(cell) for cell in values]
        if len(numbers) == 3 and index is not None:
            continuation = next(
                (line for line in lines[index + 1:index + 4] if line.strip()),
                "",
            )
            if re.fullmatch(r"\s*\d+(?:[.,]\d+)?\s*", continuation):
                numbers.append(_number(continuation))
        for event, value in zip(("ac", "ao", "am", "hip"), numbers):
            out[f"evresp_{event}_configuracion_s"] = value


def _indices(out: dict, lines: list[str], delimiter: str) -> None:
    values, index = _required_row(lines, r"^IAH$", delimiter, 3, "índices respiratorios")
    columns = _column_map(lines, index, delimiter, {
        "rem": r"^REM\b", "nrem": r"^NREM\b", "tst": r"^TST\b",
    }, "índices respiratorios")
    for phase, column in columns.items():
        out[f"evresp_iah_{phase}_evhora"] = _number(values[column])


def _oximetry(out: dict, lines: list[str], delimiter: str) -> None:
    header = next(
        (_cells(line, delimiter)[1:] for line in lines[:4]
         if "DESPIERTO" in _fold(line) and "TST" in _fold(line)),
        None,
    )
    if header and header[-1] == "":
        header.pop()
    if not header or [
        "despierto" if "DESPIERTO" in _fold(cell) else
        "nrem" if "NO-REM" in _fold(cell) or "N-REM" in _fold(cell) or "NREM" in _fold(cell) else
        "rem" if _fold(cell) == "REM" else
        "tst" if "TST" in _fold(cell) else None
        for cell in header
    ] != ["despierto", "rem", "nrem", "tst"]:
        raise PSGExtractionError("Columnas de oximetría ilegibles")
    for pattern, section in (
        (r"^PROMEDIO\s*\(%\)", "promedio de oximetría"),
        (r"^INDICE DESAT", "índice de desaturación"),
        (r"^SATURACION.*MINIMA DURANTE EL SUENO", "saturación mínima del sueño"),
        (r"^SATURACION.*EVENTOS RESPIRATORIOS", "saturación en eventos"),
    ):
        width = 4 if section in ("promedio de oximetría", "índice de desaturación") else 1
        _required_row(lines, pattern, delimiter, width, section)
    thresholds = (90, 80, 70, 60, 50) if delimiter == "\t" else (95, 90, 85, 80, 75, 70, 60)
    for threshold in thresholds:
        _required_row(lines, rf"^<\s*{threshold}\s*\(MIN\)", delimiter, 4, "umbrales de oximetría")
    if delimiter == "|":
        _required_row(lines, r"^T90\s*%", delimiter, 1, "T90")
    for line in lines:
        label, values = _row(line, delimiter)
        folded = _fold(label)
        if re.match(r"^PROMEDIO\s*\(%\)", folded):
            _check_width(values, 4, "oximetría")
            for phase, cell in zip(("despierto", "rem", "nrem", "tst"), values):
                out[f"oxi_spo2_promedio_{phase}_pct"] = _number(cell)
        elif folded.startswith("INDICE DESAT"):
            _check_width(values, 4, "oximetría")
            for phase, cell in zip(("despierto", "rem", "nrem", "tst"), values):
                out[f"oxi_indice_desat_{phase}_evhora"] = _number(cell)
        else:
            threshold = re.match(r"^<\s*(95|90|85|80|75|70|60|50)\s*\(MIN\)", folded)
            if threshold:
                _check_width(values, 4, "umbrales de oximetría")
                for phase, cell in zip(("despierto", "rem", "nrem", "tst"), values):
                    out[f"oxi_t{threshold.group(1)}_{phase}_min"] = _number(cell)
        if "SATURACION" in folded and "EVENTOS RESPIRATORIOS" in folded and values:
            field = (
                "oxi_spo2_eventos_promedio_pct" if "PROMEDIO" in folded else
                "oxi_spo2_eventos_min_pct" if "MINIMA" in folded else None
            )
            if field:
                out[field] = _number(values[0])
        elif "SATURACION" in folded and "MINIMA DURANTE EL SUENO" in folded and values:
            out["oxi_spo2_sueno_min_pct"] = _number(values[0])
        elif re.match(r"^T90\s*%", folded) and values:
            out["oxi_t90_pct"] = _number(values[0])


def _heart_movement_position(out: dict, sections: dict, delimiter: str) -> None:
    heart = sections.get("frecuencia", [])
    values, index = _required_row(heart, r"^FRECUENCIA CARDIACA\s+PROMEDIO", delimiter,
                                  3, "frecuencia cardíaca")
    columns = _column_map(heart, index, delimiter, {
        "despierto": r"^DESPIERTO\b", "rem": r"^REM\b", "nrem": r"^NO-REM\b|^N-REM\b|^NREM\b",
    }, "frecuencia cardíaca")
    for phase, column in columns.items():
        out[f"fc_promedio_{phase}_lpm"] = _number(values[column])
    movement_found = False
    for line in sections.get("movimientos", []):
        cells = _cells(line, delimiter)
        if len(cells) >= 4 and "NUMERO TOTAL" in _fold(cells[0]) and "INDICE" in _fold(cells[2]):
            kind = "plm" if "PLM" in _fold(cells[0]) else "lm" if "LM" in _fold(cells[0]) else None
            if kind:
                movement_found = True
                out[f"movmi_{kind}_total_n"] = _number(cells[1])
                out[f"movmi_{kind}_indice_evhora"] = _number(cells[3])
    if not movement_found:
        raise PSGExtractionError("Tabla de movimientos ilegible")
    position = sections.get("posicion", [])
    _, first_position = _find_row(position, r"^INDICE A/H", delimiter)
    if first_position is None:
        raise PSGExtractionError("Tabla de posición ilegible")
    columns = _column_map(position, first_position, delimiter, {
        "supino": r"^SUPINO\b", "derecho": r"^DERECHO\b", "izquierdo": r"^IZQUIERDO\b",
    }, "posición")
    for measure, pattern in (
        ("iah_evhora", r"^INDICE A/H"),
        ("duracion_min", r"^DUR\.\s*SUENO"),
        ("pct", r"^SUENO\s*\(%\)"),
    ):
        values, _ = _required_row(position, pattern, delimiter, 3, "posición")
        for name, column in columns.items():
            out[f"pos_{name}_{measure}"] = _number(values[column])


def _extract(text: str, archivo: str | Path | None, delimiter: str) -> dict[str, str | None]:
    from commons.archivo_utils import generar_hash_archivo, marcar_version_extraccion

    sections = _sections(text)
    required_sections = (
        "indicacion", "interpretacion", "conclusiones", "arquitectura", "fases",
        "respiratorios", "indices", "oximetria", "frecuencia", "movimientos", "posicion",
    )
    if any(section not in sections for section in required_sections):
        raise PSGExtractionError("Informe PSG con secciones obligatorias ilegibles")
    out: dict[str, str | None] = dict.fromkeys(PSG_COLUMNS)
    _header(out, sections.get("cabecera", []), delimiter)
    _narrative(out, sections)
    _architecture(out, sections.get("arquitectura", []), delimiter)
    _phases(out, sections.get("fases", []), delimiter)
    _respiratory(out, sections.get("respiratorios", []), delimiter)
    _indices(out, sections.get("indices", []), delimiter)
    _oximetry(out, sections.get("oximetria", []), delimiter)
    _heart_movement_position(out, sections, delimiter)
    if not all(out[field] is not None for field in (
        "pte_id", "arq_tiempo_sueno_min", "fase_rem_duracion_min",
        "evresp_ah_numero_n", "evresp_iah_tst_evhora", "oxi_spo2_promedio_tst_pct",
    )):
        raise PSGExtractionError("Informe PSG con estructura obligatoria ilegible")
    if archivo is None:
        raise PSGExtractionError("Falta el archivo fuente para generar metadatos")
    out["meta_fuente"] = str(archivo)
    out["meta_uuid"] = generar_hash_archivo(str(archivo))
    if out["meta_uuid"] == "N/A":
        raise PSGExtractionError("No se pudo generar el UUID PSG")
    out["meta_version_control"] = marcar_version_extraccion()
    return out


def procesar_basal_doc(texto_relevante: str, archivo=None):
    return _extract(texto_relevante, archivo, "\t")


def procesar_basal_rtf(texto_relevante: str, archivo=None):
    return _extract(texto_relevante, archivo, "|")
