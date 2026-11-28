"""Pruebas locales con Parquet sintético y BigQuery simulado; nunca escribe en BigQuery."""

import importlib.util
import hashlib
import io
import json
import time
import sys
import tempfile
import shutil
from uuid import uuid4
import unittest
from dataclasses import replace
from datetime import datetime
from contextlib import redirect_stdout
from threading import Thread
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd
from google.cloud.bigquery import _pandas_helpers


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "1_extract"))
sys.path.insert(0, str(ROOT / "2_transform"))
from src.basal.procesar_basal import PSG_COLUMNS
from psg.main import run as transform_psg

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
        self.jobs = {}
        self.load_table_from_dataframe = Mock(side_effect=self._load)
        self.load_table_from_file = Mock(side_effect=AssertionError("Carga desde archivo no seleccionada"))

    def _load(self, dataframe, _table, job_config=None, job_id=None, location=None):
        uuid_field = "meta_uuid" if "meta_uuid" in dataframe else "xpap_uuid"
        uuids = set(dataframe[uuid_field])
        job = SimpleNamespace(job_id=job_id, destination=_table, write_disposition="WRITE_APPEND",
                              state="RUNNING", error_result=None, output_rows=len(dataframe))
        def finish():
            job.state = "DONE"
            if not job.error_result:
                self.existing.update(uuids)
        job.result = finish
        self.jobs[job_id] = job
        return job

    def get_table(self, _table):
        return SimpleNamespace(schema=self.schema, location="EU")

    def get_job(self, job_id, **kwargs):
        return self.jobs[job_id]

    def query(self, _sql, job_config=None):
        if job_config is None:
            return SimpleNamespace(result=lambda: [])
        submitted = set(job_config.query_parameters[0].values)
        return SimpleNamespace(result=lambda: [{"meta_uuid": item} for item in self.existing & submitted])


class PsgLoadTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "extract_psg_synthetic_transformed.parquet"
        self.config = load.load_runtime_config(CONTRACT, self.path, "tbl_psg_canonica_test")
        self.schema = load.build_bq_schema(SCHEMA)

    def row(self, **changes):
        row = {name: None for name in NAMES}
        row.update(pte_id="000123", meta_uuid="synthetic-uuid-1", meta_fecha_estudio=datetime(2025, 1, 2),
                   pte_edad_anos=0, arq_tiempo_sueno_min=12.5, meta_completitud_pct=20.0, clin_ronquido="Ronquido persistente. Acentos: niño.")
        row.update(changes)
        return row

    def write(self, rows, columns=None, physical_overrides=None):
        frame = pd.DataFrame(rows, columns=columns or NAMES)
        for name in frame.columns:
            if name not in SCHEMA:
                continue
            kind = (physical_overrides or {}).get(name, SCHEMA[name])
            target = {"STRING": "string", "INT": "Int64", "FLOAT": "Float64",
                      "DATE": "datetime64[ns]"}.get(kind, kind)
            try:
                frame[name] = frame[name].astype(target)
            except (ValueError, TypeError):
                pass  # El caso inválido se escribe con su tipo físico incorrecto.
        frame.to_parquet(self.path, index=False, engine="pyarrow", compression="snappy")

    def execute(self, client=None, expect_error=False, expect_no_load=False):
        client = client or FakeClient(self.schema)
        with patch.object(load, "confirm_execution"), patch.object(load, "validate_paths"), \
             patch.object(load, "authenticate_bigquery", return_value=client), \
             patch.object(load, "finish_move", side_effect=lambda source, target, _: shutil.copyfile(source, target)) as move, \
             patch.object(load, "psg_load_state_path", return_value=Path(self.temp.name) / (uuid4().hex + ".json")), \
             patch.object(load, "STAGING_DIR", Path(self.temp.name)), redirect_stdout(io.StringIO()):
            if expect_error:
                with self.assertRaises(RuntimeError):
                    load.run(self.config, "psg")
                client.load_table_from_dataframe.assert_not_called()
                move.assert_not_called()
                return
            load.run(self.config, "psg")
            if expect_no_load:
                client.load_table_from_dataframe.assert_not_called()
                move.assert_called_once()
                return None
            client.load_table_from_dataframe.assert_called_once()
            move.assert_called_once()
            return client.load_table_from_dataframe.call_args.args[0]

    def test_contract_configuration_and_date_type(self):
        self.assertEqual(len(SCHEMA), 158)
        self.assertEqual(SCHEMA, load.load_schema(CONTRACT, "schema.transform.output.columns"))
        self.assertEqual((sum(kind == "INT" for kind in SCHEMA.values()),
                          sum(kind == "FLOAT" for kind in SCHEMA.values()),
                          sum(kind == "STRING" for kind in SCHEMA.values()),
                          sum(kind == "DATE" for kind in SCHEMA.values())), (31, 113, 13, 1))
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

    def test_valid_parquet_preserves_values_and_types(self):
        self.write([self.row()])
        result = self.execute()
        self.assertEqual(list(result.columns), NAMES)
        self.assertEqual(result.loc[0, "pte_id"], "000123")
        self.assertEqual(result.loc[0, "meta_uuid"], "synthetic-uuid-1")
        self.assertEqual(result.loc[0, "meta_fecha_estudio"], pd.Timestamp("2025-01-02"))
        self.assertEqual(result.loc[0, "pte_edad_anos"], 0)
        self.assertEqual(result.loc[0, "arq_tiempo_sueno_min"], 12.5)
        self.assertIn("niño", result.loc[0, "clin_ronquido"])
        self.assertTrue(pd.isna(result.loc[0, "pte_edad_meses"]))
        arrow_table = _pandas_helpers.dataframe_to_arrow(result, self.schema)
        self.assertEqual(arrow_table.schema.field("meta_fecha_estudio").type.__str__(), "date32[day]")

    def test_reject_numeric_physical_identifier(self):
        self.write([self.row(pte_id=123)], physical_overrides={"pte_id": "Int64"})
        self.execute(expect_error=True)

    def test_nullable_partition_date_reaches_arrow_as_null(self):
        self.write([self.row(meta_fecha_estudio=None)])
        result = self.execute()
        field = NAMES.index("meta_fecha_estudio")
        self.assertEqual("NULLABLE", self.schema[field].mode)
        self.assertTrue(pd.isna(result.loc[0, "meta_fecha_estudio"]))
        arrow = _pandas_helpers.dataframe_to_arrow(result, self.schema)
        self.assertEqual(1, arrow.column("meta_fecha_estudio").null_count)

    def test_reject_schema_errors(self):
        for columns in (NAMES[::-1], NAMES + ["unexpected"]):
            with self.subTest(columns=len(columns)):
                self.write([self.row()], columns)
                self.execute(expect_error=True)

    def test_reject_wrong_physical_types_and_legacy_formats(self):
        for name, kind, value in (("pte_id", "Int64", 123),
                                  ("pte_edad_anos", "Float64", 12.0),
                                  ("arq_tiempo_sueno_min", "Int64", 12),
                                  ("meta_fecha_estudio", "string", "2025-01-02")):
            with self.subTest(name=name):
                self.write([self.row(**{name: value})], physical_overrides={name: kind})
                self.execute(expect_error=True)
        old = self.path.with_suffix(".xlsx")
        old.touch()
        self.assertFalse(load._is_flow_transformed_file(old, "psg"))

    def test_discovery_excludes_partial_loaded_and_legacy_files(self):
        with patch.object(load, "STAGING_DIR", Path(self.temp.name)):
            self.write([self.row()])
            for name in ("extract_psg_synthetic_transformed.parquet.tmp",
                         "extract_psg_synthetic_transformed_loaded.parquet",
                         "extract_psg_synthetic_transformed_partial.parquet",
                         "extract_psg_synthetic_transformed.xlsx"):
                (Path(self.temp.name) / name).touch()
            self.assertEqual(self.path, load._discover_latest_input("psg"))
            for name in ("extract_psg_synthetic_transformed.parquet.tmp",
                         "extract_psg_synthetic_transformed_loaded.parquet",
                         "extract_psg_synthetic_transformed_partial.parquet",
                         "extract_psg_synthetic_transformed.xlsx"):
                with self.subTest(name=name):
                    self.assertFalse(load._is_flow_transformed_file(Path(self.temp.name) / name, "psg"))

    def test_cli_accepts_only_published_psg_parquet(self):
        self.write([self.row()])
        with patch.object(load, "STAGING_DIR", Path(self.temp.name)), \
             patch.object(sys, "argv", ["load", "--flow", "psg", "--input", str(self.path)]):
            self.assertEqual(("psg", self.path, None, False, None), load.parse_cli_args())
        old = self.path.with_suffix(".xlsx")
        old.touch()
        with patch.object(load, "STAGING_DIR", Path(self.temp.name)), \
             patch.object(sys, "argv", ["load", "--flow", "psg", "--input", str(old)]):
            with self.assertRaises(RuntimeError):
                load.parse_cli_args()

    def test_loaded_parquet_suffix_is_preserved(self):
        self.write([self.row()])
        with patch.object(load, "STAGING_DIR", Path(self.temp.name)):
            moved = load.move_loaded_input_file(self.path, "psg")
        self.assertEqual("extract_psg_synthetic_transformed_loaded.parquet", moved.name)
        self.assertTrue(moved.exists())
        self.assertFalse(self.path.exists())

    def test_reject_invalid_values(self):
        for changes in (
            {"arq_tiempo_sueno_min": "invalid"},
            {"meta_completitud_pct": 101},
            {"pte_edad_anos": 1.5},
            {"meta_fecha_estudio": "invalid"},
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
        self.execute(FakeClient(self.schema, existing={"synthetic-uuid-1"}), expect_no_load=True)

    def test_first_partial_and_repeated_loads_reconcile(self):
        rows = [self.row(), self.row(meta_uuid="synthetic-uuid-2", pte_id="000124")]
        self.write(rows)
        client = FakeClient(self.schema)
        self.assertEqual(2, len(self.execute(client)))
        client.load_table_from_dataframe.reset_mock()
        client.existing.remove("synthetic-uuid-2")
        with patch.object(load, "log") as log_event:
            sent = self.execute(client)
        self.assertEqual(["synthetic-uuid-2"], sent["meta_uuid"].tolist())
        self.assertTrue(any("recibidos=2, omitidos=1, enviados=1, insertados=1" in str(call)
                            for call in log_event.call_args_list))
        client.load_table_from_dataframe.reset_mock()
        self.execute(client, expect_no_load=True)
        self.assertEqual({"synthetic-uuid-1", "synthetic-uuid-2"}, client.existing)

    def test_output_rows_mismatch_and_load_failure_keep_artifact(self):
        self.write([self.row()])
        for fail_result in (False, True):
            client = FakeClient(self.schema)
            def outcome(dataframe, table, **kwargs):
                job = client._load(dataframe, table, **kwargs)
                if fail_result:
                    job.result = Mock(side_effect=RuntimeError("fallo sintético"))
                else:
                    job.output_rows = 0
                return job
            client.load_table_from_dataframe = Mock(side_effect=outcome)
            with patch.object(load, "confirm_execution"), patch.object(load, "validate_paths"), \
                 patch.object(load, "authenticate_bigquery", return_value=client), \
                 patch.object(load, "STAGING_DIR", Path(self.temp.name)), \
                 patch.object(load, "finish_move") as move, \
                 patch.object(load, "psg_load_state_path", return_value=Path(self.temp.name) / (uuid4().hex + ".json")), \
                 redirect_stdout(io.StringIO()):
                with self.assertRaises(RuntimeError):
                    load.run(self.config, "psg")
                move.assert_not_called()
                self.assertTrue(self.path.exists())

    def test_e22_json_and_null_survive_psg_load_preparation(self):
        payload = json.dumps([{"campo": "pte_edad_anos", "valor_original": "x",
                               "error": "entero_incompatible", "accion": "convertido_a_null"}],
                             ensure_ascii=False, separators=(",", ":"))
        self.write([self.row(meta_incidencias_calidad=payload),
                    self.row(meta_uuid="synthetic-uuid-2", pte_id=None,
                             meta_incidencias_calidad=None)])
        sent = self.execute()
        self.assertEqual(payload, sent.loc[0, "meta_incidencias_calidad"])
        self.assertTrue(pd.isna(sent.loc[1, "meta_incidencias_calidad"]))
        self.assertTrue(pd.isna(sent.loc[1, "pte_id"]))
        arrow = _pandas_helpers.dataframe_to_arrow(sent, self.schema)
        self.assertEqual(payload, arrow.column("meta_incidencias_calidad")[0].as_py())
        self.assertIsNone(arrow.column("meta_incidencias_calidad")[1].as_py())

    def test_csv_transform_parquet_and_simulated_load(self):
        source = Path(self.temp.name) / "extract_psg_synthetic.csv"
        original = dict.fromkeys(PSG_COLUMNS, "")
        uuid = hashlib.md5(b"psg-e36-synthetic").hexdigest()
        original.update(pte_id="000123", meta_uuid=uuid, meta_fecha_estudio="02/01/2025",
                        meta_completitud_pct="20", pte_edad_anos="12",
                        arq_tiempo_sueno_min="valor incompatible")
        pd.DataFrame([original], columns=PSG_COLUMNS).to_csv(source, index=False)
        self.assertEqual(self.path, transform_psg(str(CONTRACT), str(source), str(self.path)))
        expected = pd.read_parquet(self.path)
        sent = self.execute()
        pd.testing.assert_frame_equal(expected, sent, check_dtype=True, check_exact=True)
        self.assertEqual("000123", sent.loc[0, "pte_id"])
        self.assertEqual(uuid, sent.loc[0, "meta_uuid"])
        self.assertTrue(pd.isna(sent.loc[0, "arq_tiempo_sueno_min"]))
        self.assertEqual("valor incompatible", json.loads(sent.loc[0, "meta_incidencias_calidad"])[0]["valor_original"])
        self.assertTrue(source.exists())
        self.assertTrue(self.path.exists())  # El doble sustituye al movimiento remoto.

    def test_local_lock_serializes_query_and_load(self):
        self.write([self.row()])
        client = FakeClient(self.schema)
        def slow_load(dataframe, table, **kwargs):
            time.sleep(0.05)
            return client._load(dataframe, table, **kwargs)
        client.load_table_from_dataframe = Mock(side_effect=slow_load)
        errors = []
        def worker():
            try:
                load.run(self.config, "psg")
            except Exception as error:
                errors.append(error)
        with patch.object(load, "confirm_execution"), patch.object(load, "validate_paths"), \
             patch.object(load, "authenticate_bigquery", return_value=client), \
             patch.object(load, "STAGING_DIR", Path(self.temp.name)), \
             patch.object(load, "finish_move", side_effect=lambda source, target, _: shutil.copyfile(source, target)) as move, \
             redirect_stdout(io.StringIO()):
            threads = [Thread(target=worker) for _ in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=5)
            self.assertFalse(any(thread.is_alive() for thread in threads))
        self.assertEqual([], errors)
        self.assertEqual(1, client.load_table_from_dataframe.call_count)
        self.assertEqual(1, move.call_count)

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
        xpap_path = self.path.with_name("extract_xpap_synthetic_transformed.xlsx")
        config = load.load_runtime_config(ROOT / "0_declarations/xpap.yaml", xpap_path)
        self.assertEqual(config.table_id, "tbl_xpap_prd")
        self.assertEqual(config.schema_path_in_yaml, "schema.load.input.columns")
        schema = load.load_schema(config.schema_yaml_path, config.schema_path_in_yaml)
        self.assertEqual(schema, load.load_schema(config.schema_yaml_path, "schema.transform.output.columns"))
        frame = pd.DataFrame({"xpap_edad": ["invalid"]})
        self.assertTrue(pd.isna(load.cast_dataframe(frame, {"xpap_edad": "FLOAT"}).loc[0, "xpap_edad"]))

    def test_xpap_simulated_load(self):
        xpap_path = self.path.with_name("extract_xpap_synthetic_transformed.xlsx")
        config = load.load_runtime_config(ROOT / "0_declarations/xpap.yaml", xpap_path)
        schema = load.load_schema(config.schema_yaml_path, config.schema_path_in_yaml)
        row = {name: None for name in schema}
        row.update(xpap_uuid="synthetic-xpap-uuid", xpap_fecha_estudio=datetime(2025, 1, 2))
        pd.DataFrame([row], columns=list(schema)).to_excel(xpap_path, index=False, sheet_name="procesado")
        client = FakeClient(load.build_bq_schema(schema))
        with patch.object(load, "confirm_execution"), patch.object(load, "validate_paths"), \
             patch.object(load, "authenticate_bigquery", return_value=client), \
             patch.object(load, "move_loaded_input_file") as move, redirect_stdout(io.StringIO()):
            load.run(config, "xpap")
        client.load_table_from_dataframe.assert_called_once()
        move.assert_called_once()


if __name__ == "__main__":
    unittest.main()
