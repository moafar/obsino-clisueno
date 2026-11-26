import csv
import hashlib
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

import yaml
import pandas as pd
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "1_extract"))

from psg_quality_check import _count_explicit_zeros, check_quality, main
from src.basal.procesar_basal import PSG_COLUMNS, _completeness, _is_present
from psg.core.transforms import _date, _parse_date

with (ROOT / "0_declarations" / "psg.yaml").open(encoding="utf-8") as stream:
    CONTRACT = yaml.safe_load(stream)
INPUT_COLUMNS = list(CONTRACT["schema"]["transform"]["input"]["columns"])
OUTPUT_COLUMNS = list(CONTRACT["schema"]["transform"]["output"]["columns"])


def record(index=1, **changes):
    row = dict.fromkeys(INPUT_COLUMNS, "")
    row["meta_uuid"] = hashlib.md5(f"synthetic-{index}".encode()).hexdigest()
    row["meta_fecha_estudio"] = "01/02/2025"
    row["arq_tiempo_sueno_min"] = "0"
    row.update(changes)
    row["meta_completitud_pct"] = _completeness(row)
    return row


class PSGQualityCheckTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "input.csv"
        self.rows = [record(1), record(2, clin_indicacion="N/A",
                                            meta_fecha_estudio="2024-12-31")]
        self.write_csv(self.source, self.rows)

    def write_csv(self, path, rows, columns=INPUT_COLUMNS):
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream)
            writer.writerow(columns)
            writer.writerows([row.get(column, "") for column in columns] for row in rows)

    def write_xlsx(self, rows, columns=OUTPUT_COLUMNS):
        path = self.root / "transformed.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "procesado"
        sheet.append(columns)
        for row in rows:
            sheet.append([row.get(column) for column in columns])
        workbook.save(path)
        return path

    def check(self, **kwargs):
        return check_quality(self.source, today=date(2026, 11, 26), **kwargs)

    def test_valid_csv_statistics_dates_missing_and_explicit_zero(self):
        report = self.check()
        self.assertEqual([], report["errors"])
        stats = report["statistics"]
        self.assertEqual(2, stats["records"])
        self.assertEqual(159, stats["columns"])
        self.assertEqual({"2024": 1, "2025": 1}, stats["dates"]["by_year"])
        self.assertEqual(2, stats["explicit_zeros_present"])
        self.assertEqual(2, stats["uuid"]["valid_total"])
        self.assertEqual(2, stats["uuid"]["valid_unique"])
        self.assertEqual(0, stats["uuid"]["historical_unique"])
        self.assertEqual({"count": 0, "pct": 0.0},
                         stats["missing_by_variable"]["arq_tiempo_sueno_min"])
        self.assertEqual({"count": 2, "pct": 100.0},
                         stats["missing_by_variable"]["clin_conclusiones"])
        self.assertEqual({"count": 2, "pct": 100.0},
                         stats["missing_by_variable"]["clin_indicacion"])
        self.assertIn("clin_conclusiones", stats["completely_empty_variables"])
        self.assertEqual(152, len(stats["missing_by_variable"]))
        self.assertEqual(2, stats["completeness_pct"]["valid"])
        self.assertEqual(stats["completeness_pct"]["min"],
                         stats["completeness_pct"]["p5"])
        self.assertTrue(report["warnings"])

    def test_numeric_zero_formats_exclude_text_and_invalid_numbers(self):
        row = record(1, arq_eficiencia_pct="0.0", oxi_t90_pct="0,00",
                     pte_edad_anos="-0", evresp_ac_numero_n="+0",
                     arq_tiempo_cama_min="0e0", evresp_ao_numero_n="0_0",
                     pte_nombre="0", clin_interpretacion="0.0")
        self.write_csv(self.source, [row])
        report = self.check()
        self.assertEqual([], report["errors"])
        self.assertEqual(6, report["statistics"]["explicit_zeros_present"])

    def test_vectorized_zero_count_matches_scalar_conversion(self):
        values = ["0", "0.0", "0,00", "-0", "+0", "0e0", " 0 ",
                  "0_0", "texto", "N/A", "NaN", "inf", "-", "5", ""]
        rows = [{"arq_tiempo_sueno_min": value, "arq_eficiencia_pct": value}
                for value in values]
        previous = int(sum(
            pd.to_numeric(row[column].strip().replace(",", "."), errors="coerce") == 0
            for row in rows for column in {"arq_tiempo_sueno_min", "arq_eficiencia_pct"}
        ))
        self.assertEqual(previous, _count_explicit_zeros(
            rows, {"arq_tiempo_sueno_min", "arq_eficiencia_pct"}
        ))

    def test_extractor_presence_rule_and_historical_completeness(self):
        absent = [None, "", "  ", "N/A", " na ", "NONE", "NULL", "NAN"]
        present = [0, "0", "0.0", "-0", "texto", "0_0"]
        self.assertTrue(all(not _is_present(value) for value in absent))
        self.assertTrue(all(_is_present(value) for value in present))
        row = dict.fromkeys(PSG_COLUMNS)
        clinical = [column for column in PSG_COLUMNS if not column.startswith("meta_")]
        for column, value in zip(clinical, absent + present):
            row[column] = value
        self.assertEqual(f"{100 * len(present) / len(clinical):.2f}", _completeness(row))

    def test_completeness_distribution_percentiles(self):
        rows = [record(i, **{INPUT_COLUMNS[0]: str(i)}) for i in range(1, 21)]
        for i, row in enumerate(rows):
            for column in INPUT_COLUMNS[:i]:
                row[column] = str(i)
            row["meta_completitud_pct"] = _completeness(row)
        self.write_csv(self.source, rows)
        stats = self.check()["statistics"]["completeness_pct"]
        values = sorted(float(row["meta_completitud_pct"]) for row in rows)
        self.assertEqual(values[0], stats["min"])
        self.assertEqual(values[-1], stats["max"])
        self.assertAlmostEqual(sum(values) / len(values), stats["mean"])
        self.assertEqual((values[9] + values[10]) / 2, stats["median"])
        self.assertAlmostEqual(values[0] + (values[1] - values[0]) * .95, stats["p5"])
        self.assertAlmostEqual(values[18] + (values[19] - values[18]) * .05, stats["p95"])

    def test_csv_schema_and_row_length_block(self):
        for columns in (INPUT_COLUMNS[:-1], INPUT_COLUMNS[1:] + INPUT_COLUMNS[:1],
                        INPUT_COLUMNS[:-1] + [INPUT_COLUMNS[-2]]):
            with self.subTest(columns=columns[-1]):
                self.write_csv(self.source, self.rows, columns)
                self.assertTrue(self.check()["errors"])
        self.write_csv(self.source, self.rows)
        with self.source.open("a", encoding="utf-8") as stream:
            stream.write("short,row\n")
        self.assertTrue(any("Filas CSV" in e for e in self.check()["errors"]))

    def test_empty_csv_blocks(self):
        self.write_csv(self.source, [])
        self.assertIn("CSV sin registros", self.check()["errors"])

    def test_uuid_null_empty_invalid_and_duplicate_block(self):
        rows = [record(i) for i in range(1, 7)]
        rows[0]["meta_uuid"] = "NULL"
        rows[1]["meta_uuid"] = " "
        rows[2]["meta_uuid"] = "not-an-md5"
        rows[3]["meta_uuid"] = rows[4]["meta_uuid"].upper()
        self.write_csv(self.source, rows)
        report = self.check()
        self.assertEqual({"valid_total": 3, "valid_unique": 2,
                          "historical_unique": 0, "null": 1, "empty": 1,
                          "invalid_md5": 1, "duplicate": 1, "shared_historical": 0},
                         report["statistics"]["uuid"])
        self.assertEqual(4, len([e for e in report["errors"] if e.startswith("UUID")]))
        self.assertNotIn(rows[4]["meta_uuid"], json.dumps(report))

    def test_historical_overlap_across_files_blocks(self):
        paths = [self.root / "historical1.csv", self.root / "historical2.csv"]
        self.write_csv(paths[0], [self.rows[0]], columns=["meta_uuid"])
        self.write_csv(paths[1], [self.rows[0], self.rows[1]], columns=["meta_uuid"])
        report = self.check(historical=paths)
        self.assertEqual(2, report["statistics"]["uuid"]["shared_historical"])
        self.assertEqual(2, report["statistics"]["uuid"]["historical_unique"])
        self.assertTrue(any("históricos" in e for e in report["errors"]))
        self.write_csv(paths[1], self.rows, columns=["wrong"])
        self.assertTrue(any("histórico" in e for e in self.check(historical=paths)["errors"]))
        self.write_csv(paths[1], [{"meta_uuid": "invalid"}], columns=["meta_uuid"])
        self.assertIn("UUID históricos inválidos: 1",
                      self.check(historical=paths)["errors"])

    def test_duplicate_uuid_also_present_in_historical_batch(self):
        rows = [record(1), record(2), record(1)]
        rows[2]["meta_uuid"] = rows[0]["meta_uuid"].upper()
        self.write_csv(self.source, rows)
        historical = self.root / "historical.csv"
        self.write_csv(historical, [record(1), record(3), record(1)],
                       columns=["meta_uuid"])
        report = self.check(historical=[historical])
        self.assertEqual(3, report["statistics"]["uuid"]["valid_total"])
        self.assertEqual(2, report["statistics"]["uuid"]["valid_unique"])
        self.assertEqual(2, report["statistics"]["uuid"]["historical_unique"])
        self.assertEqual(1, report["statistics"]["uuid"]["duplicate"])
        self.assertEqual(1, report["statistics"]["uuid"]["shared_historical"])
        self.assertIn("UUID duplicados: 1", report["errors"])
        self.assertIn("UUID compartidos con históricos: 1", report["errors"])

    def test_completeness_invalid_out_of_range_and_recalculation_block(self):
        rows = [record(i) for i in range(1, 6)]
        rows[0]["meta_completitud_pct"] = ""
        rows[1]["meta_completitud_pct"] = "NaN"
        rows[2]["meta_completitud_pct"] = "101"
        rows[3]["meta_completitud_pct"] = "-1"
        rows[4]["meta_completitud_pct"] = "0"
        self.write_csv(self.source, rows)
        report = self.check()
        self.assertIn("meta_completitud_pct inválido: 4", report["errors"])
        self.assertIn("meta_completitud_pct distinto del recálculo: 1", report["errors"])
        self.assertEqual(1, report["statistics"]["completeness_pct"]["valid"])

    def test_invalid_dates_block_but_missing_and_future_dates_warn(self):
        rows = [record(1, meta_fecha_estudio=""), record(2, meta_fecha_estudio="N/A"),
                record(3, meta_fecha_estudio="31/02/2025"),
                record(4, meta_fecha_estudio="27/11/2026"),
                record(5, meta_fecha_estudio="NULL")]
        self.write_csv(self.source, rows)
        report = self.check()
        self.assertIn("Fechas inválidas: 3", report["errors"])
        self.assertEqual({"by_year": {"2026": 1}, "missing": 1,
                          "invalid": 3, "future": 1}, report["statistics"]["dates"])
        self.assertEqual(2, len([w for w in report["warnings"] if "Fechas" in w]))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(1, main(["--input", str(self.source)]))

        self.write_csv(self.source, [rows[0], rows[3]])
        report = self.check()
        self.assertEqual([], report["errors"])
        self.assertEqual({"by_year": {"2026": 1}, "missing": 1,
                          "invalid": 0, "future": 1}, report["statistics"]["dates"])

    def test_validator_dates_follow_transform_parser(self):
        values = ["", "  ", "01/02/2025", "2024-12-31", "27/11/2026",
                  "N/A", "NULL", "31/02/2025"]
        text, parsed = _parse_date(pd.Series(values, dtype="string"))
        self.assertEqual(2, int(text.isna().sum()))
        self.assertEqual(3, int((text.notna() & parsed.isna()).sum()))
        with self.assertRaisesRegex(ValueError, "Fecha inválida"):
            _date(pd.Series(values, dtype="string"), "meta_fecha_estudio")
        self.assertTrue(_date(pd.Series(values[:5], dtype="string"),
                              "meta_fecha_estudio").equals(parsed.iloc[:5]))
        self.write_csv(self.source, [record(i + 1, meta_fecha_estudio=value)
                                     for i, value in enumerate(values)])
        report = self.check()
        self.assertEqual(2, report["statistics"]["dates"]["missing"])
        self.assertEqual(3, report["statistics"]["dates"]["invalid"])
        self.assertEqual(1, report["statistics"]["dates"]["future"])

    def test_xlsx_valid_and_consistency_checks(self):
        transformed = self.write_xlsx(list(reversed(self.rows)))
        self.assertEqual([], self.check(transformed=transformed)["errors"])
        changed = [dict(row) for row in self.rows]
        changed[0]["meta_completitud_pct"] = "99"
        transformed = self.write_xlsx(changed)
        self.assertTrue(any("cambiado" in e for e in
                            self.check(transformed=transformed)["errors"]))
        changed[0]["meta_uuid"] = hashlib.md5(b"extra").hexdigest()
        transformed = self.write_xlsx(changed)
        self.assertTrue(any("Conjuntos UUID" in e for e in
                            self.check(transformed=transformed)["errors"]))
        transformed = self.write_xlsx(self.rows[:1])
        self.assertTrue(any("Número de registros" in e for e in
                            self.check(transformed=transformed)["errors"]))
        transformed = self.write_xlsx(self.rows, OUTPUT_COLUMNS[:-1])
        self.assertTrue(any("Esquema XLSX" in e for e in
                            self.check(transformed=transformed)["errors"]))

    def test_xlsx_duplicate_uuid_and_missing_sheet(self):
        rows = [dict(row) for row in self.rows]
        rows[1]["meta_uuid"] = rows[0]["meta_uuid"]
        self.assertTrue(any("UUID XLSX duplicados" in e for e in
                            self.check(transformed=self.write_xlsx(rows))["errors"]))
        rows[1]["meta_uuid"] = " "
        self.assertTrue(any("UUID XLSX inválidos" in e for e in
                            self.check(transformed=self.write_xlsx(rows))["errors"]))
        workbook = Workbook()
        workbook.active.title = "wrong"
        path = self.root / "wrong.xlsx"
        workbook.save(path)
        self.assertIn("Falta la hoja XLSX declarada", self.check(transformed=path)["errors"])

    def test_cli_codes_and_no_patient_identifiers(self):
        self.rows[0]["pte_nombre"] = "NOMBRE_SINTETICO_PRIVADO"
        self.rows[0]["meta_completitud_pct"] = _completeness(self.rows[0])
        self.write_csv(self.source, self.rows)
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(0, main(["--input", str(self.source)]))
        self.assertNotIn("NOMBRE_SINTETICO_PRIVADO", output.getvalue())
        self.assertNotIn(self.rows[0]["meta_uuid"], output.getvalue())
        self.rows[0]["meta_completitud_pct"] = "101"
        self.write_csv(self.source, self.rows)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(1, main(["--input", str(self.source)]))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(2, main(["--input", str(self.root / "missing.csv")]))
        broken = self.root / "broken.xlsx"
        broken.write_text("not an xlsx", encoding="utf-8")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(2, main(["--input", str(self.source),
                                      "--transformed", str(broken)]))


if __name__ == "__main__":
    unittest.main()
