import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
from extract_commons.auditoria_psg import audit_psg, percentile
from extract_commons.directorio_utils import PSG_REJECTION_REASONS
from src.basal.procesar_basal import _completeness

CONTRACT = Path(__file__).resolve().parents[2] / "0_declarations/psg.yaml"


class AuditTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.source = self.root / "source"
        self.archive = self.root / "archive"
        self.source.mkdir()
        self.archive.mkdir()
        self.csv = self.root / "extract_psg_test.csv"
        self.log = self.root / "extract_psg_test.log"
        self.log.touch()
        self.schema = yaml.safe_load(CONTRACT.read_text())["schema"]["transform"]["input"]["columns"]
        self.result = dict(num_files=1, archivos_validos=1, archivos_registrados=1,
                           archivos_extraidos=1, archivos_reintentados=0,
                           archivos_fallo_archivado=0, archivos_rechazados=0,
                           archivos_duplicados=0, errores_recorrido=0)
        self.original = self.source / "synthetic.doc"
        self.archived = self.archive / "bs_synthetic.doc"
        self.archived.write_bytes(b"synthetic")
        self.row = dict.fromkeys(self.schema, "")
        self.row.update(meta_fuente=str(self.original),
                        meta_uuid=hashlib.md5(b"synthetic").hexdigest(),
                        meta_fecha_estudio="01/02/2024", pte_id="001",
                        arq_tiempo_sueno_min="0")
        self.row["meta_completitud_pct"] = _completeness(self.row, "doc")
        self.log.write_text(f"Traslado PSG correcto: origen={self.original} destino={self.archived}\n")

    def write_csv(self):
        with self.csv.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(self.schema))
            writer.writeheader()
            writer.writerow(self.row)

    def audit(self):
        path, state = audit_psg(self.csv, self.log, CONTRACT, self.source,
                                self.archive, result=self.result)
        return state, path.read_text(encoding="utf-8")

    def test_valid_and_independent_of_previous_csv(self):
        self.write_csv()
        (self.root / "extract_psg_previous.csv").write_text("invalid")
        with patch("hashlib.file_digest", side_effect=AssertionError("rehash prohibido")):
            state, report = self.audit()
        self.assertEqual("OK", state)
        self.assertIn("Archivos localizados: 1", report)
        self.assertIn("| Encontrados | 1 |", report)
        self.assertIn("| Archivados nuevos | 1 |", report)
        self.assertIn("Válidos=1; archivados + reintentos + fallos + rechazados + "
                      "duplicados + errores técnicos=1", report)
        self.assertIn("Controles: OK=", report)
        self.assertNotIn(str(self.original), report)
        self.assertNotIn(str(self.archived), report)

    def test_missing_archive_and_bad_completeness(self):
        self.archived.unlink()
        self.row["meta_completitud_pct"] = "100"
        self.write_csv()
        state, report = self.audit()
        self.assertEqual("ERROR", state)
        self.assertIn("Discrepancias: 1", report)
        self.assertIn("archivos ausentes: 1", report)

    def test_empty_execution(self):
        self.log.write_text("")
        self.result.update(num_files=0, archivos_validos=0,
                           archivos_registrados=0, archivos_extraidos=0)
        state, report = self.audit()
        self.assertEqual("OK", state)
        self.assertIn("**Resultado: OK**", report)
        self.assertIn("NO APLICA — Esquema", report)
        self.assertIn("NO APLICA — Calidad de campos", report)
        self.assertIn("NO APLICA — Trazabilidad CSV", report)
        self.assertIn("No se generó CSV", report)
        self.assertFalse(self.csv.exists())

    def test_empty_batch_with_header_only_csv_is_ok(self):
        self.log.write_text("")
        self.result.update(num_files=0, archivos_validos=0,
                           archivos_registrados=0, archivos_extraidos=0)
        with self.csv.open("w", newline="", encoding="utf-8") as stream:
            csv.writer(stream).writerow(self.schema)
        state, report = self.audit()
        self.assertEqual("OK", state)
        self.assertIn("OK — Esquema", report)
        self.assertIn("NO APLICA — Calidad de campos", report)
        self.assertIn("NO APLICA — Trazabilidad CSV", report)

    def test_schema_mismatch(self):
        self.csv.write_text("wrong\nvalue\n")
        state, report = self.audit()
        self.assertEqual("ERROR", state)
        self.assertIn("orden exacto: False", report)

    def test_rtf_score_uses_rtf_fields_and_ignores_doc_only(self):
        self.original = self.source / "synthetic.rtf"
        self.row["meta_fuente"] = str(self.original)
        self.row["evresp_ac_numero_nrem_n"] = "0"
        self.row["fase_s1_episodios_n"] = "999"
        self.log.write_text(
            f"Traslado PSG correcto: origen={self.original} destino={self.archived}\n"
        )
        self.row["meta_completitud_pct"] = _completeness(self.row, "rtf")
        self.write_csv()
        state, report = self.audit()
        self.assertEqual("OK", state)
        self.assertIn("Discrepancias: 0", report)

        self.row["meta_completitud_pct"] = _completeness(self.row, "doc")
        self.write_csv()
        state, report = self.audit()
        self.assertEqual("ERROR", state)
        self.assertIn("Discrepancias: 1", report)

    def test_clinical_ranges_and_relations_are_not_audited(self):
        self.row.update(arq_tiempo_sueno_min="999", arq_tiempo_cama_min="1",
                        oxi_spo2_eventos_min_pct="150",
                        oxi_spo2_eventos_promedio_pct="20",
                        oxi_t90_tst_min="200", oxi_t95_tst_min="10")
        self.row["meta_completitud_pct"] = _completeness(self.row, "doc")
        self.write_csv()
        state, report = self.audit()
        self.assertEqual("OK", state)
        self.assertNotIn("Coherencia matemática", report)
        self.assertNotIn("porcentaje fuera de 0", report)

    def test_invalid_technical_type_remains_blocking(self):
        self.row["arq_tiempo_sueno_min"] = "ilegible"
        self.row["meta_completitud_pct"] = _completeness(self.row, "doc")
        self.write_csv()
        state, report = self.audit()
        self.assertEqual("ERROR", state)
        self.assertIn("ERROR — Tipos YAML", report)

    def test_rejection_codes_reconcile_without_exposing_paths(self):
        origins = [self.source / "unreadable.doc", self.source / "nohash.rtf"]
        for origin in origins:
            origin.write_bytes(b"synthetic")
        codes = ("TEXTO_ILEGIBLE", "UUID_NO_GENERADO")
        events = [dict(codigo=code, origen=str(origin),
                       motivo=PSG_REJECTION_REASONS[code])
                  for origin, code in zip(origins, codes)]
        self.log.write_text("\n".join("Rechazo PSG: " + json.dumps(event)
                                      for event in events) + "\n")
        self.result.update(num_files=2, archivos_validos=2, archivos_registrados=0,
                           archivos_extraidos=0, archivos_rechazados=2)
        state, report = self.audit()
        self.assertEqual("OK", state)
        self.assertIn("NO APLICA — Trazabilidad CSV", report)
        self.assertIn("OK — Rechazos por motivo", report)
        self.assertIn("| TEXTO_ILEGIBLE | 1 |", report)
        self.assertIn("| UUID_NO_GENERADO | 1 |", report)
        self.assertNotIn(str(origins[0]), report)

        self.result["archivos_rechazados"] = 1
        state, report = self.audit()
        self.assertEqual("ERROR", state)
        self.assertIn("ERROR — Rechazos por motivo", report)

    def test_duplicate_or_malformed_rejection_event_blocks(self):
        origin = self.source / "unreadable.doc"
        origin.write_bytes(b"synthetic")
        event = dict(codigo="TEXTO_ILEGIBLE", origen=str(origin),
                     motivo=PSG_REJECTION_REASONS["TEXTO_ILEGIBLE"])
        self.result.update(num_files=1, archivos_validos=1, archivos_registrados=0,
                           archivos_extraidos=0, archivos_rechazados=2)
        self.log.write_text(("Rechazo PSG: " + json.dumps(event) + "\n") * 2)
        state, report = self.audit()
        self.assertEqual("ERROR", state)
        self.assertIn("orígenes repetidos: 1", report)

        self.log.write_text("Rechazo PSG: {invalid-json}\n")
        state, report = self.audit()
        self.assertEqual("ERROR", state)
        self.assertIn("eventos malformados: 1", report)

    def test_rejected_source_symlink_reconciles(self):
        target = self.root / "outside.doc"
        target.write_bytes(b"synthetic")
        link = self.source / "linked.doc"
        link.symlink_to(target)
        event = dict(codigo="ENLACE_SIMBOLICO", origen=str(link),
                     motivo=PSG_REJECTION_REASONS["ENLACE_SIMBOLICO"])
        self.log.write_text("Rechazo PSG: " + json.dumps(event) + "\n")
        self.result.update(num_files=1, archivos_validos=1, archivos_registrados=0,
                           archivos_extraidos=0, archivos_rechazados=1)
        state, report = self.audit()
        self.assertEqual("OK", state)
        self.assertIn("NO APLICA — Trazabilidad CSV", report)
        self.assertIn("OK — Rechazos por motivo", report)
        self.assertIn("| ENLACE_SIMBOLICO | 1 |", report)

    def test_inaccessible_inventory_blocks(self):
        self.write_csv()
        self.source.rmdir()
        state, report = self.audit()
        self.assertEqual("ERROR", state)
        self.assertIn("ERROR — Inventario residual", report)

    def test_standalone_audit_accepts_legacy_summary_without_technical_counter(self):
        self.write_csv()
        with self.log.open("a", encoding="utf-8") as stream:
            stream.write("Resumen: archivos=1, válidos=1, filas_nuevas=1, "
                         "nuevos_archivados=1, duplicados=0, fallos_archivado=0, "
                         "reintentos=0, rechazados=0, errores_recorrido=0\n")
        path, state = audit_psg(self.csv, self.log, CONTRACT, self.source, self.archive)
        self.assertEqual("OK", state)
        self.assertIn("**Resultado: OK**", path.read_text(encoding="utf-8"))

    def test_logical_completeness_by_variable_format_and_section(self):
        self.row["pte_edad_meses"] = "0"
        self.row["meta_completitud_pct"] = _completeness(self.row, "doc")
        second_origin = self.source / "synthetic.rtf"
        second_archive = self.archive / "bs_synthetic.rtf"
        second_archive.write_bytes(b"synthetic-rtf")
        second = dict.fromkeys(self.schema, "")
        second.update(meta_fuente=str(second_origin),
                      meta_uuid=hashlib.md5(b"synthetic-rtf").hexdigest(),
                      meta_fecha_estudio="01/02/2024", pte_id="002",
                      arq_tiempo_sueno_min="0", evresp_hip_duracion_max_s="0",
                      oxi_indice_desat_despierto_evhora="0")
        second["meta_completitud_pct"] = _completeness(second, "rtf")
        with self.csv.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(self.schema))
            writer.writeheader()
            writer.writerows((self.row, second))
        self.log.write_text(
            f"Traslado PSG correcto: origen={self.original} destino={self.archived}\n"
            f"Traslado PSG correcto: origen={second_origin} destino={second_archive}\n"
        )
        self.result.update(num_files=2, archivos_validos=2,
                           archivos_registrados=2, archivos_extraidos=2)
        state, report = self.audit()
        self.assertEqual("OK", state)
        self.assertIn("| pte_edad_anos (edad) | 1/1 | 100.00 | 0/1 | 0.00 |", report)
        self.assertIn("| fase_s1_episodios_n | 0/1 | 0.00 | — | — |", report)
        self.assertIn("| evresp_hip_duracion_max_s | 0/1 | 0.00 | 1/1 | 100.00 |", report)
        self.assertIn("| oxi_indice_desat_despierto_evhora | 0/1 | 0.00 | 1/1 | 100.00 |", report)
        self.assertIn("| pte | 12 | 2/12 | 16.67 | 12 | 1/12 | 8.33 |", report)
        self.assertIn("| DOC | 1 | 1 | 2.42 | 2.42 | 2.42 | 2.42 |", report)
        self.assertIn("| RTF | 1 | 1 | 3.10 | 3.10 | 3.10 | 3.10 |", report)
        self.assertNotIn("| meta_uuid |", report)
        self.assertNotIn("| pte_edad_meses |", report)

    def test_percentile_interpolates_and_handles_one_value(self):
        self.assertEqual(90, percentile([100, 0, 50], 0.9))
        self.assertEqual(12.5, percentile([12.5], 0.9))


if __name__ == "__main__":
    unittest.main()
