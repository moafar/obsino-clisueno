import csv
import hashlib
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from commons.archivo_utils import _append_psg_row, procesar_archivo
from commons.directorio_utils import procesar_directorio
from commons.texto_utils import determinar_tipos_examenes, normalizar_texto
from src.basal.procesar_basal import (
    PSG_COLUMNS, PSGExtractionError, procesar_basal_doc, procesar_basal_rtf,
)


def synthetic_report(kind):
    sep = "\t" if kind == "doc" else "|"

    def row(label, *values):
        return sep.join((label, *map(str, values))) + ("|" if kind == "rtf" else "")

    def heading(*values):
        return sep + sep.join(values) + ("|" if kind == "rtf" else "")

    doc = kind == "doc"
    parts = [
        "INFORME DE POLISOMNOGRAFÍA BASAL",
        row("Nombre:", "Paciente Sintético", "Edad:", "12 años", "Id:" if doc else "Identificación:", "000123"),
        row("Peso:", "70 kg", "Talla:", "170 cm", "IMC:", "24", "Cuello:", "38 cm", "Perímetro Abdominal:"),
        "90 cm",
        row("Solicita:", "Servicio sintético", "Empresa:", "Entidad sintética", "Fecha:", "01/02/2026"),
        "PROCEDIMIENTO",
        "INDICACIÓN DEL ESTUDIO",
        "Motivo íntegro con acento. Epworth 0/24.",
        "INTERPRETACIÓN",
        "Primera frase clínica íntegra. El ronquido fue frecuente durante el sueño.",
        "CONCLUSIONES",
        "Conclusión íntegra con puntuación y acentos.",
        "ARQUITECTURA DE SUEÑO:",
        row("Tiempo de Grabación:", "500 min") if not doc else row("Tiempo de Grabación:", "01/02/2026 20:00"),
        row("Tiempo en Cama:", "480 min"),
        row("Tiempo Total de Sueño:", "400 min"),
        row("Eficiencia de Sueño:", "83%"),
        row("Latencia de Sueño:", "10 min"),
        row("Latencia de sueño REM:", "80 min"),
        row("Tiempo despierto durante el sueño:", "30 min"),
        heading("Nº Total", "Nº Eventos Respiratorios", "Nº PLMs", "Espontáneos"),
        "",
        row("Microalertamientos", 11, 12, 13, 14),
        row("Indice Despertares", "2,5"),
        "DISTRIBUCIÓN DE FASES DE SUEÑO:",
        heading("Episodios", "Duración", "TST") if doc else heading("Duración", "TST"),
    ]
    for i, phase in enumerate(("Despierto (SPT)", "REM", "S1", "S2", "S3")):
        values = [str(20 + i)] if doc else []
        values += [str(35 if i == 0 else 30 + i), "-" if i == 0 else str(40 + i)]
        parts.append(row(phase, *values))
    events = ("AC", "AO", "AM", "Suma AP", "hip", "Eventos A + H") if doc else (
        "AC", "AO", "AM", "HIP", "Apneas + Hipopneas",
    )
    parts += [
        "Resumen de eventos respiratorios (Tiempo de sueño total)",
        heading(*events),
    ]
    if doc:
        parts += [row("Configuración (s)", 91, 92, 93), "", "94"]
    parts.append(row("Número", *(10 + i for i in range(len(events)))))
    parts.append(row("Máx. (s)" if doc else "Máxima duración", *(
        (31 + i if doc else "--" if i < 3 else 31 + i if i == 3 else "")
        for i in range(len(events))
    )))
    parts.append(row("Media (s)" if doc else "Duración media (seg)", *(40 + i for i in range(len(events)))))
    parts.append(row("Duración total (min)", *(50 + i for i in range(len(events)))))
    parts.append(row("Índice (nº/h TST)" if doc else "Índice [nº/h]", *(60 + i for i in range(len(events)))))
    if not doc:
        parts.append(row("Numero en NREM", *(70 + i for i in range(len(events)))))
        parts.append(row("Numero en REM", *(80 + i for i in range(len(events)))))
    parts += [
        "Resumen del índice de eventos respiratorios (Tiempo de sueño total)",
        heading("REM nº/h (REM)", "NREM nº/h (NREM)", "TST nº/h (sueño)"),
        row("IAH", 101, 102, 103),
        "OXIMETRÍA:",
        heading("Despierto", "REM", "No-REM", "TST"),
        row("Promedio (%)", 90, 91, 92, 93),
        row("Indice Desat (#/hour)", "" if not doc else 1, 2, 3, 4),
    ]
    thresholds = (90, 80, 70, 60, 50) if doc else (95, 90, 85, 80, 75, 70, 60)
    for threshold in thresholds:
        parts.append(row(f"<{threshold} (min)", 0, threshold + 1, threshold + 2, threshold + 3))
    parts += [
        row("Saturación O2 Mínima durante los Eventos Respiratorios [%] :" if doc else
            "Saturación O2 Promedio durante los Eventos Respiratorios [%] :", 88),
        row("Saturación O2 Mínima durante el sueño [%] :", 77),
    ]
    if not doc:
        parts.append(row("T90%", "5,5%"))
    else:
        parts[parts.index("Primera frase clínica íntegra. El ronquido fue frecuente durante el sueño.")] += " T90: 5,5%."
    parts += [
        "FRECUENCIA CARDIACA:",
        heading("Despierto", "REM", "No-REM"),
        row("Frecuencia Cardiaca Promedio (l/min)", 61, 62, 63),
        "MOVIMIENTOS DE MIEMBROS INFERIORES:",
        row("Número Total de LMs" if doc else "Número Total de PLMs", 30,
            "Índice de LMs (#/hr)" if doc else "Índice de PLMs (#/hr)", "3,2"),
        "POSICION CORPORAL:",
        heading("Supino", "Derecho", "Izquierdo"),
        row("Índice A/H (#/hr)", 11, 12, 13),
        row("Dur. sueño (m)", 21, 22, 23),
        row("Sueño (%)", 31, 32, 33),
        "INFORME DE POLISOMNOGRAFÍA EN TITULACIÓN DE CPAP",
        row("T90%", 999),
    ]
    return "\n".join(parts)


class PSGExtractorTest(unittest.TestCase):
    def test_columns_match_direct_dictionary_fields(self):
        dictionary = Path(__file__).resolve().parents[2] / "docs" / "diccionario_datos_psg.md"
        fields = re.findall(r"^\|\s*\d+\s*\|\s*`([a-z0-9_]+)`", dictionary.read_text(), re.M)
        derived = {
            "pte_edad_decimal_anos", "pte_grupo_edad", "pte_peso_kg",
            "pte_talla_cm", "pte_cuello_cm", "pte_perimetro_abdominal_cm",
        }
        self.assertEqual(156, len(fields))
        self.assertEqual(set(fields) - derived, set(PSG_COLUMNS) - {
            f"pte_{part}_{kind}"
            for part in ("peso", "talla", "cuello", "perimetro_abdominal")
            for kind in ("valor", "unidad")
        })
        self.assertEqual(158, len(PSG_COLUMNS))
        self.assertEqual(158, len(set(PSG_COLUMNS)))
        self.assertEqual(
            [field for field in fields if field not in derived],
            [field for field in PSG_COLUMNS if field in fields],
        )

    def test_tables_map_to_distinct_cells_in_both_formats(self):
        for kind, processor in (("doc", procesar_basal_doc), ("rtf", procesar_basal_rtf)):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as folder:
                source = Path(folder) / "synthetic"
                source.write_bytes(b"contenido sintetico")
                row = processor(synthetic_report(kind), source)
                self.assertEqual(list(PSG_COLUMNS), list(row))
                self.assertEqual(130, sum(value is not None for value in row.values()))
                self.assertEqual("000123", row["pte_id"])
                self.assertEqual("Paciente Sintético", row["pte_nombre"])
                self.assertIsNone(row["pte_edad_meses"])
                self.assertEqual("70", row["pte_peso_valor"])
                self.assertEqual("kg", row["pte_peso_unidad"])
                self.assertEqual("90", row["pte_perimetro_abdominal_valor"])
                self.assertEqual("cm", row["pte_perimetro_abdominal_unidad"])
                self.assertEqual("Servicio sintético", row["meta_solicita"])
                self.assertEqual("Entidad sintética", row["meta_empresa"])
                self.assertEqual("0", row["clin_epworth_puntos"])
                self.assertEqual("30", row["arq_tiempo_despierto_min"])
                self.assertEqual("35", row["fase_despierto_duracion_min"])
                self.assertEqual("11", row["arq_microalertamientos_total_n"])
                self.assertEqual("12", row["arq_microalertamientos_respiratorios_n"])
                self.assertEqual("13", row["arq_microalertamientos_plm_n"])
                self.assertEqual("14", row["arq_microalertamientos_espontaneos_n"])
                self.assertEqual("65" if kind == "doc" else "64", row["evresp_ah_indice_evhora"])
                self.assertEqual("103", row["evresp_iah_tst_evhora"])
                self.assertEqual("0", row["oxi_t90_despierto_min"])
                self.assertEqual("5,5", row["oxi_t90_pct"])
                self.assertEqual("77", row["oxi_spo2_sueno_min_pct"])
                self.assertEqual("61", row["fc_promedio_despierto_lpm"])
                self.assertEqual("22", row["pos_derecho_duracion_min"])
                self.assertEqual("13", row["pos_izquierdo_iah_evhora"])
                self.assertIn("íntegra", row["clin_interpretacion"])
                self.assertIn("íntegro", row["clin_indicacion"])
                self.assertIn("íntegra", row["clin_conclusiones"])
                self.assertIn("ronquido fue frecuente", row["clin_ronquido"])
                self.assertNotIn("999", str(row))
                self.assertEqual(hashlib.md5(source.read_bytes()).hexdigest(), row["meta_uuid"])
                for event, index in (("ac", 0), ("ao", 1), ("am", 2), ("hip", 4 if kind == "doc" else 3), ("ah", 5 if kind == "doc" else 4)):
                    self.assertEqual(str(10 + index), row[f"evresp_{event}_numero_n"])
                    self.assertEqual(str(40 + index), row[f"evresp_{event}_duracion_media_s"])
                    self.assertEqual(str(60 + index), row[f"evresp_{event}_indice_evhora"])
                for threshold in ((90, 80, 70, 60, 50) if kind == "doc" else (95, 90, 85, 80, 75, 70, 60)):
                    for stage, offset in (("despierto", 0), ("rem", 1), ("nrem", 2), ("tst", 3)):
                        self.assertEqual(str(threshold + offset) if offset else "0",
                                         row[f"oxi_t{threshold}_{stage}_min"])
                if kind == "doc":
                    self.assertEqual("94", row["evresp_hip_configuracion_s"])
                    self.assertEqual("91", row["evresp_ac_configuracion_s"])
                    self.assertEqual("30", row["movmi_lm_total_n"])
                    self.assertIsNone(row["movmi_plm_total_n"])
                    self.assertIsNone(row["evresp_ac_numero_nrem_n"])
                    self.assertEqual("20", row["fase_despierto_episodios_n"])
                    self.assertIsNone(row["arq_tiempo_grabacion_min"])
                else:
                    self.assertEqual("70", row["evresp_ac_numero_nrem_n"])
                    self.assertEqual("84", row["evresp_ah_numero_rem_n"])
                    self.assertEqual("30", row["movmi_plm_total_n"])
                    self.assertIsNone(row["movmi_lm_total_n"])
                    self.assertIsNone(row["evresp_ac_duracion_max_s"])
                    self.assertIsNone(row["fase_despierto_episodios_n"])
                    self.assertIsNone(row["oxi_indice_desat_despierto_evhora"])

    def test_format_specific_fields_by_name(self):
        doc_only = (
            [f"fase_{phase}_episodios_n" for phase in ("s1", "s2", "s3", "rem", "despierto")]
            + [f"evresp_{event}_configuracion_s" for event in ("ac", "ao", "am", "hip")]
            + [f"evresp_ap_{measure}" for measure in (
                "numero_n", "duracion_max_s", "duracion_media_s", "duracion_total_min", "indice_evhora")]
            + [f"oxi_t50_{phase}_min" for phase in ("despierto", "rem", "nrem", "tst")]
            + ["oxi_spo2_eventos_min_pct", "movmi_lm_total_n", "movmi_lm_indice_evhora"]
        )
        rtf_only = (
            [f"evresp_{event}_numero_{phase}_n"
             for event in ("ac", "ao", "am", "hip", "ah") for phase in ("nrem", "rem")]
            + [f"oxi_t{threshold}_{phase}_min"
               for threshold in (95, 85, 75) for phase in ("despierto", "rem", "nrem", "tst")]
            + ["oxi_spo2_eventos_promedio_pct", "movmi_plm_total_n",
               "movmi_plm_indice_evhora", "arq_tiempo_grabacion_min"]
        )
        self.assertEqual((21, 26), (len(doc_only), len(rtf_only)))
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "synthetic"
            source.write_bytes(b"synthetic")
            for kind, processor, present, absent in (
                ("doc", procesar_basal_doc, doc_only, rtf_only),
                ("rtf", procesar_basal_rtf, rtf_only, doc_only),
            ):
                row = processor(synthetic_report(kind), source)
                for field in present:
                    with self.subTest(kind=kind, field=field):
                        self.assertIsNotNone(row[field])
                for field in absent:
                    with self.subTest(kind=kind, field=field):
                        self.assertIsNone(row[field])

    def test_csv_header_null_zero_utf8_and_incompatible_header(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "synthetic"
            source.write_bytes(b"synthetic")
            doc_source = Path(folder) / "synthetic-doc"
            doc_source.write_bytes(b"different synthetic document")
            row = procesar_basal_rtf(synthetic_report("rtf"), source)
            doc_row = procesar_basal_doc(synthetic_report("doc"), doc_source)
            csv_path = Path(folder) / "psg.csv"
            self.assertTrue(_append_psg_row(row, csv_path))
            self.assertFalse(_append_psg_row(row, csv_path))
            before_failure = csv_path.read_bytes()
            with patch("commons.archivo_utils.os.fsync", side_effect=OSError("synthetic")):
                with self.assertRaises(OSError):
                    _append_psg_row(doc_row, csv_path)
            self.assertEqual(before_failure, csv_path.read_bytes())
            self.assertTrue(_append_psg_row(doc_row, csv_path))
            with csv_path.open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                self.assertEqual(list(PSG_COLUMNS), reader.fieldnames)
                records = list(reader)
            self.assertEqual(2, len(records))
            self.assertEqual("", records[0]["evresp_ac_duracion_max_s"])
            self.assertEqual("0", records[0]["oxi_t90_despierto_min"])
            self.assertIn("íntegra", records[0]["clin_conclusiones"])
            self.assertEqual("31", records[1]["evresp_ac_duracion_max_s"])
            self.assertEqual("", records[1]["evresp_ac_numero_nrem_n"])
            csv_path.write_text("legacy,columns\nkeep,this\n", encoding="utf-8")
            with self.assertRaises(PSGExtractionError):
                _append_psg_row(row, csv_path)
            self.assertEqual("legacy,columns\nkeep,this\n", csv_path.read_text(encoding="utf-8"))
            csv_path.write_text(",".join(PSG_COLUMNS) + "\npartial", encoding="utf-8")
            with self.assertRaises(PSGExtractionError):
                _append_psg_row(row, csv_path)

    def test_unreadable_tables_rejected_without_affecting_shared_normalization(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "synthetic"
            source.write_bytes(b"synthetic")
            broken = synthetic_report("doc").replace("\tEpisodios\tDuración\tTST", "")
            with self.assertRaises(PSGExtractionError):
                procesar_basal_doc(broken, source)
            misaligned = synthetic_report("doc").replace(
                "Número\t10\t11\t12\t13\t14\t15",
                "Número\t10\t11\t12\t13\t14\t15\t16",
            )
            with self.assertRaises(PSGExtractionError):
                procesar_basal_doc(misaligned, source)
        self.assertEqual("a b c", normalizar_texto("á\tb\nc"))

    def test_unit_before_value_is_preserved_for_later_transform(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "synthetic"
            source.write_bytes(b"synthetic")
            text = synthetic_report("doc").replace("Peso:\t70 kg", "Peso:\t(kg) 70")
            row = procesar_basal_doc(text, source)
            self.assertEqual("70", row["pte_peso_valor"])
            self.assertEqual("kg", row["pte_peso_unidad"])

    def test_empty_labeled_cell_and_distinct_sleep_latencies(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "synthetic"
            source.write_bytes(b"synthetic")
            for kind, processor, sep in (
                ("doc", procesar_basal_doc, "\t"),
                ("rtf", procesar_basal_rtf, "|"),
            ):
                with self.subTest(kind=kind):
                    report = synthetic_report(kind).replace(
                        f"Tiempo en Cama:{sep}480 min",
                        f"Tiempo en Cama:{sep}{sep}Eficiencia de Sueño:{sep}83%",
                    ).replace(f"Latencia de Sueño:{sep}10 min{'|' if kind == 'rtf' else ''}\n", "")
                    row = processor(report, source)
                    self.assertIsNone(row["arq_tiempo_cama_min"])
                    self.assertIsNone(row["arq_latencia_sueno_min"])
                    self.assertEqual("80", row["arq_latencia_rem_min"])

    def test_reordered_table_headers_map_to_their_own_cells(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "synthetic"
            source.write_bytes(b"synthetic")
            for kind, processor, sep in (
                ("doc", procesar_basal_doc, "\t"),
                ("rtf", procesar_basal_rtf, "|"),
            ):
                with self.subTest(kind=kind):
                    report = synthetic_report(kind)
                    report = report.replace(
                        f"Nº Total{sep}Nº Eventos Respiratorios",
                        f"Nº Eventos Respiratorios{sep}Nº Total",
                    ).replace(
                        f"REM nº/h (REM){sep}NREM nº/h (NREM)",
                        f"NREM nº/h (NREM){sep}REM nº/h (REM)",
                    ).replace(
                        f"Despierto{sep}REM{sep}No-REM{'|' if kind == 'rtf' else ''}\n",
                        f"REM{sep}Despierto{sep}No-REM{'|' if kind == 'rtf' else ''}\n",
                    ).replace(
                        f"Supino{sep}Derecho{sep}Izquierdo",
                        f"Derecho{sep}Supino{sep}Izquierdo",
                    )
                    row = processor(report, source)
                    self.assertEqual("12", row["arq_microalertamientos_total_n"])
                    self.assertEqual("11", row["arq_microalertamientos_respiratorios_n"])
                    self.assertEqual("102", row["evresp_iah_rem_evhora"])
                    self.assertEqual("101", row["evresp_iah_nrem_evhora"])
                    self.assertEqual("62", row["fc_promedio_despierto_lpm"])
                    self.assertEqual("61", row["fc_promedio_rem_lpm"])
                    self.assertEqual("22", row["pos_supino_duracion_min"])
                    self.assertEqual("21", row["pos_derecho_duracion_min"])

    def test_missing_required_rows_and_sections_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "synthetic"
            source.write_bytes(b"synthetic")
            for kind, processor, sep in (
                ("doc", procesar_basal_doc, "\t"),
                ("rtf", procesar_basal_rtf, "|"),
            ):
                base = synthetic_report(kind)
                for broken in (
                    base.replace(f"S3{sep}{'24' + sep if kind == 'doc' else ''}34{sep}44{'|' if kind == 'rtf' else ''}\n", ""),
                    base.replace("FRECUENCIA CARDIACA:\n", ""),
                    base.replace(f"<90 (min){sep}0{sep}91{sep}92{sep}93{'|' if kind == 'rtf' else ''}\n", ""),
                    base.replace(f"Número{sep}" + sep.join(str(10 + i) for i in range(6 if kind == "doc" else 5)),
                                 f"Nro{sep}" + sep.join(str(10 + i) for i in range(6 if kind == "doc" else 5))),
                    base.replace("MOVIMIENTOS DE MIEMBROS INFERIORES:\n", ""),
                ):
                    with self.subTest(kind=kind, removed=len(base) - len(broken)):
                        self.assertNotEqual(base, broken)
                        with self.assertRaises(PSGExtractionError):
                            processor(broken, source)

    def test_ambiguous_table_header_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "synthetic"
            source.write_bytes(b"synthetic")
            for kind, processor, sep in (
                ("doc", procesar_basal_doc, "\t"),
                ("rtf", procesar_basal_rtf, "|"),
            ):
                report = synthetic_report(kind).replace(
                    f"Nº Total{sep}Nº Eventos Respiratorios",
                    f"Nº Total{sep}Nº Total",
                )
                with self.subTest(kind=kind), self.assertRaises(PSGExtractionError):
                    processor(report, source)

    def test_dam_is_not_psg_basal(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "synthetic"
            source.write_bytes(b"synthetic")
            dam = synthetic_report("doc").replace(
                "POLISOMNOGRAFÍA BASAL", "POLISOMNOGRAFÍA BASAL CON DISPOSITIVO MANDIBULAR", 1,
            )
            dam = dam.split("INFORME DE POLISOMNOGRAFÍA EN TITULACIÓN DE CPAP")[0]
            with self.assertRaises(PSGExtractionError):
                procesar_basal_doc(dam, source)
            kinds = determinar_tipos_examenes(normalizar_texto(dam))
            self.assertIn("DAM", kinds)
            self.assertNotIn("BASAL", kinds)
            with patch("commons.archivo_utils._extract_text", return_value=dam), \
                 patch("commons.archivo_utils._append_psg_row") as append, \
                 patch("commons.archivo_utils._move_processed_file") as move:
                self.assertFalse(procesar_archivo(source.with_suffix(".doc")))
                append.assert_not_called()
                move.assert_not_called()
            both = determinar_tipos_examenes(normalizar_texto(
                "INFORME DE POLISOMNOGRAFÍA BASAL\n"
                "INFORME DE POLISOMNOGRAFÍA BASAL CON DISPOSITIVO MANDIBULAR"
            ))
            self.assertIn("BASAL", both)
            self.assertIn("DAM", both)

    def test_ronquido_preserves_full_original_paragraph(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "synthetic"
            source.write_bytes(b"synthetic")
            paragraph = (
                "Primera frase clínica íntegra. El ronquido fue frecuente durante el sueño. "
                "En REM, el ronquido continuó con intensidad variable."
            )
            report = synthetic_report("rtf").replace(
                "Primera frase clínica íntegra. El ronquido fue frecuente durante el sueño.",
                paragraph,
            )
            self.assertEqual(paragraph, procesar_basal_rtf(report, source)["clin_ronquido"])

    def test_directory_counts_extracted_and_rejected_separately(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in ("a.doc", "b.doc", "c.rtf"):
                (Path(folder) / name).write_bytes(b"synthetic")
            with patch("commons.directorio_utils.procesar_archivo",
                       side_effect=[True, False, RuntimeError("synthetic")]):
                with self.assertLogs(level="CRITICAL"):
                    result = procesar_directorio(Path(folder), barra_progreso=False)
            self.assertEqual(3, result["archivos_validos"])
            self.assertEqual(1, result["archivos_extraidos"])
            self.assertEqual(2, result["archivos_rechazados"])


if __name__ == "__main__":
    unittest.main()
