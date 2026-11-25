"""Pruebas del CLI de compatibilidad PSG v5.0.0 -> v5.0.1."""

import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from psg_csv_v501 import PSG_COLUMNS, convert_psg_csv  # noqa: E402


OLD_COLUMNS = list(PSG_COLUMNS[:-1])


def record(uuid, **values):
    row = dict.fromkeys(OLD_COLUMNS, "")
    row.update(values)
    row["meta_uuid"] = uuid
    return [row[column] for column in OLD_COLUMNS]


def write_csv(path, rows, header=None):
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(OLD_COLUMNS if header is None else header)
        writer.writerows(rows)


class PSGCsvV501Test(unittest.TestCase):
    def test_converts_without_changing_original_data_or_provenance(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "original.csv"
            target = Path(folder) / "converted.csv"
            rows = [
                record("uuid-1", pte_id="000123", arq_tiempo_sueno_min="0",
                       clin_indicacion="Texto íntegro\ncon salto de línea",
                       meta_version_control="Extraido: 2026-11-25 04:36:00"),
                record("uuid-2", pte_id="000124", arq_tiempo_sueno_min="N/A",
                       clin_indicacion="NULL"),
            ]
            write_csv(source, rows)
            original_bytes = source.read_bytes()

            summary = convert_psg_csv(source, target)
            self.assertEqual(2, summary[0])
            self.assertEqual(original_bytes, source.read_bytes())

            with target.open(encoding="utf-8", newline="") as f:
                reader = csv.reader(f)
                self.assertEqual(list(PSG_COLUMNS), next(reader))
                converted = list(reader)
            self.assertEqual([*rows[0], "1.97"], converted[0])
            self.assertEqual([*rows[1], "0.66"], converted[1])

    def test_dry_run_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "original.csv"
            target = Path(folder) / "converted.csv"
            write_csv(source, [record("uuid-1", pte_id="123")])
            count, minimum, average, maximum = convert_psg_csv(
                source, target, dry_run=True
            )
            self.assertEqual((1, 0.66, 0.66, 0.66),
                             (count, minimum, average, maximum))
            self.assertFalse(target.exists())

    def test_rejects_noncanonical_header(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "original.csv"
            target = Path(folder) / "converted.csv"
            bad_header = OLD_COLUMNS.copy()
            bad_header[0], bad_header[1] = bad_header[1], bad_header[0]
            write_csv(source, [record("uuid-1")], header=bad_header)
            with self.assertRaisesRegex(ValueError, "158 columnas"):
                convert_psg_csv(source, target)
            self.assertFalse(target.exists())

    def test_rejects_duplicate_uuid_without_partial_file(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "original.csv"
            target = Path(folder) / "converted.csv"
            write_csv(source, [record("duplicate"), record("duplicate")])
            with self.assertRaisesRegex(ValueError, "repetido"):
                convert_psg_csv(source, target)
            self.assertFalse(target.exists())
            self.assertEqual([], list(Path(folder).glob("*.tmp")))

    def test_never_overwrites_existing_destination(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "original.csv"
            target = Path(folder) / "converted.csv"
            write_csv(source, [record("uuid-1")])
            target.write_text("PROTEGIDO", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                convert_psg_csv(source, target)
            self.assertEqual("PROTEGIDO", target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
