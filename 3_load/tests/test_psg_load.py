"""Pruebas locales con XLSX sintético y BigQuery simulado; nunca escribe en BigQuery."""

import importlib.util
import io
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd
from google.cloud.bigquery import _pandas_helpers
from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("psg_load_main_test", ROOT / "3_load/main.py")
load = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = load
SPEC.loader.exec_module(load)
CONTRACT = ROOT / "0_declarations/psg.yaml"
SCHEMA = load.load_schema(CONTRACT, "schema.load.input.columns")
NAMES = list(SCHEMA)


class FakeClient:
    def __init__(self, schema, existing=()):
        self.schema = schema
        self.existing = set(existing)
        self.load_table_from_dataframe = Mock(return_value=SimpleNamespace(result=Mock(), output_rows=1))

    def get_table(self, _table):
        return SimpleNamespace(schema=self.schema)

    def query(self, _sql, job_config=None):
        if job_config is None:
            return SimpleNamespace(result=lambda: [])
        submitted = set(job_config.query_parameters[0].values)
        return SimpleNamespace(result=lambda: [{"meta_uuid": item} for item in self.existing & submitted])


class PsgLoadTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "extract_psg_synthetic_transformed.xlsx"
        self.config = load.load_runtime_config(CONTRACT, self.path, "tbl_psg_canonica_test")
        self.schema = load.build_bq_schema(SCHEMA)

    def row(self, **changes):
        row = {name: None for name in NAMES}
        row.update(pte_id="000123", meta_uuid="synthetic-uuid-1", meta_fecha_estudio=datetime(2025, 1, 2),
                   pte_edad_anos=0, arq_tiempo_sueno_min=12.5, clin_ronquido="Ronquido persistente. Acentos: niño.")
        row.update(changes)
        return row

    def write(self, rows, columns=None):
        frame = pd.DataFrame(rows, columns=columns or NAMES)
        frame.to_excel(self.path, index=False, sheet_name="procesado")

    def execute(self, client=None, expect_error=False):
        client = client or FakeClient(self.schema)
        with patch.object(load, "confirm_execution"), patch.object(load, "validate_paths"), \
             patch.object(load, "authenticate_bigquery", return_value=client), \
             patch.object(load, "move_loaded_input_file") as move, redirect_stdout(io.StringIO()):
            if expect_error:
                with self.assertRaises(RuntimeError):
                    load.run(self.config, "psg")
                client.load_table_from_dataframe.assert_not_called()
                move.assert_not_called()
                return
            load.run(self.config, "psg")
            client.load_table_from_dataframe.assert_called_once()
            move.assert_called_once()
            return client.load_table_from_dataframe.call_args.args[0]

    def test_contract_configuration_and_date_type(self):
        self.assertEqual(len(SCHEMA), 156)
        self.assertEqual(SCHEMA, load.load_schema(CONTRACT, "schema.transform.output.columns"))
        self.assertEqual((sum(kind == "INT" for kind in SCHEMA.values()),
                          sum(kind == "FLOAT" for kind in SCHEMA.values()),
                          sum(kind == "STRING" for kind in SCHEMA.values()),
                          sum(kind == "DATE" for kind in SCHEMA.values())), (31, 112, 12, 1))
        self.assertEqual(self.config.schema_yaml_path, CONTRACT)
        self.assertEqual(load.resolve_config_yaml_path("psg"), CONTRACT)
        self.assertEqual(self.config.schema_path_in_yaml, "schema.load.input.columns")
        self.assertEqual(self.config.uuid_field, "meta_uuid")
        self.assertEqual(self.config.date_field, "meta_fecha_estudio")
        self.assertIsNone(self.config.migrated_field)
        self.assertEqual(self.schema[NAMES.index("meta_fecha_estudio")].field_type, "DATE")
        self.assertEqual(
            load.load_runtime_config(CONTRACT, self.path).table_id,
            "tbl_psg_prd",
        )
        self.assertEqual(
            load.load_runtime_config(CONTRACT, self.path, "tbl_psg_prd").table_id,
            "tbl_psg_prd",
        )
        with self.assertRaises(RuntimeError):
            load.load_runtime_config(CONTRACT, self.path, "tbl_psg_legacy_prd")

    def test_valid_xlsx_preserves_values_and_types(self):
        self.write([self.row()])
        result = self.execute()
        self.assertEqual(list(result.columns), NAMES)
        self.assertEqual(result.loc[0, "pte_id"], "000123")
        self.assertEqual(result.loc[0, "meta_uuid"], "synthetic-uuid-1")
        self.assertEqual(str(result.loc[0, "meta_fecha_estudio"]), "2025-01-02")
        self.assertEqual(result.loc[0, "pte_edad_anos"], 0)
        self.assertEqual(result.loc[0, "arq_tiempo_sueno_min"], 12.5)
        self.assertIn("niño", result.loc[0, "clin_ronquido"])
        self.assertTrue(pd.isna(result.loc[0, "pte_edad_meses"]))
        arrow_table = _pandas_helpers.dataframe_to_arrow(result, self.schema)
        self.assertEqual(arrow_table.schema.field("meta_fecha_estudio").type.__str__(), "date32[day]")

    def test_reject_numeric_physical_identifier(self):
        self.write([self.row()])
        workbook = load_workbook(self.path)
        workbook["procesado"].cell(2, NAMES.index("pte_id") + 1).value = 123
        workbook.save(self.path)
        self.execute(expect_error=True)

    def test_reject_schema_errors(self):
        for columns in (NAMES[::-1], NAMES + ["unexpected"]):
            with self.subTest(columns=len(columns)):
                self.write([self.row()], columns)
                self.execute(expect_error=True)

    def test_reject_invalid_values(self):
        for changes in (
            {"arq_tiempo_sueno_min": "invalid"},
            {"pte_edad_anos": 1.5},
            {"meta_fecha_estudio": "invalid"},
            {"pte_id": None},
            {"meta_uuid": None},
            {"meta_uuid": "  "},
        ):
            with self.subTest(changes=changes):
                self.write([self.row(**changes)])
                self.execute(expect_error=True)

    def test_duplicate_uuids_and_existing(self):
        self.write([self.row(), self.row(pte_id="000124")])
        self.execute(expect_error=True)
        self.write([self.row()])
        self.execute(FakeClient(self.schema, existing={"synthetic-uuid-1"}), expect_error=True)

    def test_reject_incompatible_physical_schema_and_historical_table(self):
        self.write([self.row()])
        for incompatible in (
            self.schema[:-1],
            self.schema[::-1],
            self.schema[:1] + [load.bigquery.SchemaField(self.schema[1].name, "INT64")] + self.schema[2:],
        ):
            with self.subTest(fields=len(incompatible)):
                self.execute(FakeClient(incompatible), expect_error=True)
        self.config = replace(self.config, table_id="tbl_psg_legacy_prd")
        self.execute(expect_error=True)

    def test_xpap_shared_contract_and_legacy_cast(self):
        config = load.load_runtime_config(ROOT / "0_declarations/xpap.yaml", self.path)
        self.assertEqual(config.table_id, "tbl_xpap_prd")
        self.assertEqual(config.schema_path_in_yaml, "schema.load.input.columns")
        schema = load.load_schema(config.schema_yaml_path, config.schema_path_in_yaml)
        self.assertEqual(schema, load.load_schema(config.schema_yaml_path, "schema.transform.output.columns"))
        frame = pd.DataFrame({"xpap_edad": ["invalid"]})
        self.assertTrue(pd.isna(load.cast_dataframe(frame, {"xpap_edad": "FLOAT"}).loc[0, "xpap_edad"]))

    def test_xpap_simulated_load(self):
        config = load.load_runtime_config(ROOT / "0_declarations/xpap.yaml", self.path)
        schema = load.load_schema(config.schema_yaml_path, config.schema_path_in_yaml)
        row = {name: None for name in schema}
        row.update(xpap_uuid="synthetic-xpap-uuid", xpap_fecha_estudio=datetime(2025, 1, 2))
        pd.DataFrame([row], columns=list(schema)).to_excel(self.path, index=False, sheet_name="procesado")
        client = FakeClient(load.build_bq_schema(schema))
        with patch.object(load, "confirm_execution"), patch.object(load, "validate_paths"), \
             patch.object(load, "authenticate_bigquery", return_value=client), \
             patch.object(load, "move_loaded_input_file") as move, redirect_stdout(io.StringIO()):
            load.run(config, "xpap")
        client.load_table_from_dataframe.assert_called_once()
        move.assert_called_once()


if __name__ == "__main__":
    unittest.main()
