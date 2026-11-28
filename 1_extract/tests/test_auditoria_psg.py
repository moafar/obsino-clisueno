import csv
import hashlib
import tempfile
import unittest
from pathlib import Path

import yaml
from extract_commons.auditoria_psg import audit_psg
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
        self.row["meta_completitud_pct"] = _completeness(self.row)
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
        state, report = self.audit()
        self.assertEqual("OK", state)
        self.assertIn("MD5 correctos: 1", report)
        self.assertNotIn(str(self.original), report)
        self.assertNotIn(str(self.archived), report)

    def test_changed_archive_and_completeness(self):
        self.archived.write_bytes(b"changed")
        self.row["meta_completitud_pct"] = "100"
        self.write_csv()
        state, report = self.audit()
        self.assertEqual("ERROR", state)
        self.assertIn("Discrepancias: 1", report)
        self.assertIn("hash incorrecto: 1", report)

    def test_empty_execution(self):
        self.log.write_text("")
        self.result.update(num_files=0, archivos_validos=0,
                           archivos_registrados=0, archivos_extraidos=0)
        state, report = self.audit()
        self.assertEqual("ADVERTENCIA", state)
        self.assertIn("No se generó CSV", report)
        self.assertFalse(self.csv.exists())

    def test_schema_mismatch(self):
        self.csv.write_text("wrong\nvalue\n")
        state, report = self.audit()
        self.assertEqual("ERROR", state)
        self.assertIn("orden exacto: False", report)


if __name__ == "__main__":
    unittest.main()
