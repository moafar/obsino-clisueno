"""Orquestación aislada con CLI simuladas; sin documentos ni servicios remotos."""
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
from threading import Event, Thread
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout

import pandas as pd

SPEC = importlib.util.spec_from_file_location("run_psg", Path(__file__).resolve().parents[1] / "run_psg.py")
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class RunPsgTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, self.archive = self.root / "source", self.root / "archive"
        self.source.mkdir()
        self.archive.mkdir()
        self.calls = []
        self.rows, self.warning, self.failure = 2, False, None
        self.entered, self.release = Event(), Event()
        self.block = False

    def cli(self, command, **options):
        self.assertEqual(subprocess.DEVNULL, options["stdin"])
        self.assertTrue(options["check"])
        self.assertIn("--yes", command)
        name = Path(command[1]).parent.name
        self.calls.append(name)
        if self.block and name == "1_extract":
            self.entered.set()
            self.release.wait(5)
        if self.failure == name:
            raise subprocess.CalledProcessError(3, command)
        def value(flag):
            return Path(command[command.index(flag) + 1])
        if name == "1_extract":
            csv = value("--output-dir") / value("--output-file")
            if self.rows:
                csv.write_text("synthetic CSV")
            value("--result-json").write_text(json.dumps({"csv": str(csv),
                "audit_state": "ADVERTENCIA" if self.warning else "OK",
                "counts": {"archivos_registrados": self.rows}}))
        elif name == "2_transform":
            self.assertTrue(value("--input").is_file())
            pd.DataFrame({"synthetic": range(self.rows)}).to_parquet(value("--output"))
        else:
            source = value("--input")
            self.assertTrue(source.is_file())
            loaded = source.with_name(source.stem + "_loaded.parquet")
            source.rename(loaded)
            value("--result-json").write_text(json.dumps({"loaded": str(loaded),
                "job_id": "simulated-job", "counts": {"received": self.rows,
                "omitted": 0, "sent": self.rows, "inserted": self.rows}}))

    def execute(self):
        with patch.object(runner, "STAGING", self.root), patch.object(runner, "preflight"), \
             patch.object(runner.subprocess, "run", side_effect=self.cli), redirect_stdout(io.StringIO()):
            return runner.run(self.source, self.archive, self.root, "synthetic_test")

    def record(self):
        return json.loads(next(self.root.glob("psg_runs/*/run.json")).read_text())

    def test_success_and_warnings(self):
        for warning in (False, True):
            self.warning = warning
            record = json.loads(self.execute().read_text())
            self.assertEqual("WARNING" if warning else "OK", record["state"])
            self.assertEqual(2, record["counts"]["inserted"])
            self.assertEqual("simulated-job", record["job_id"])
            self.assertTrue(Path(record["paths"]["loaded"]).exists())
            self.assertTrue(all(stage["elapsed_s"] >= 0 for stage in record["stages"].values()))
        self.assertEqual(["1_extract", "2_transform", "3_load"] * 2, self.calls)
        self.assertEqual(2, len(list(self.root.glob("psg_runs/*/run.json"))))

    def test_empty_skips_transform_and_load(self):
        self.rows = 0
        for warning in (False, True):
            self.warning = warning
            record = json.loads(self.execute().read_text())
            self.assertEqual("EMPTY", record["state"])
            self.assertEqual("ADVERTENCIA" if warning else "OK", record["audit"]["state"])
            self.assertEqual(record["audit"]["state"],
                             record["stages"]["extract_audit"]["result"]["audit_state"])
            self.assertEqual("SKIPPED", record["stages"]["load"]["state"])
        self.assertEqual(["1_extract", "1_extract"], self.calls)

    def test_conciliation_errors_mark_responsible_stage_as_error(self):
        cases = (("1_extract", "audit_state", "ERROR", "extract_audit"),
                 ("1_extract", "csv", "/incorrect.csv", "extract_audit"),
                 ("2_transform", "rows", 1, "transform"),
                 ("2_transform", "rows", 3, "transform"),
                 ("3_load", "received", 1, "load"),
                 ("3_load", "loaded", "/missing.parquet", "load"))
        original_cli = self.cli
        for cli_name, field, value, stage_name in cases:
            with self.subTest(stage=stage_name, field=field, value=value), \
                 tempfile.TemporaryDirectory() as root:
                self.root = Path(root)
                self.calls = []
                def altered_cli(command, **options):
                    original_cli(command, **options)
                    if Path(command[1]).parent.name != cli_name:
                        return
                    if field == "rows":
                        target = Path(command[command.index("--output") + 1])
                        pd.DataFrame({"synthetic": range(value)}).to_parquet(target)
                    else:
                        target = Path(command[command.index("--result-json") + 1])
                        result = json.loads(target.read_text())
                        if field == "received":
                            result["counts"][field] = value
                        else:
                            result[field] = value
                        target.write_text(json.dumps(result))
                with patch.object(self, "cli", side_effect=altered_cli):
                    with self.assertRaises(RuntimeError):
                        self.execute()
                record = self.record()
                self.assertEqual("ERROR", record["state"])
                self.assertEqual("ERROR", record["stages"][stage_name]["state"])
                self.assertEqual(stage_name, list(record["stages"])[-1])

    def test_preflight_requires_disjoint_document_directories(self):
        mount = self.root / "documents"
        source, archive = mount / "source", mount / "archive"
        nested = source / "nested"
        nested.mkdir(parents=True)
        archive.mkdir()
        staging = self.root / "staging"
        staging.mkdir()
        credentials = self.root / "synthetic-key.json"
        credentials.write_text("{}")
        with patch.object(runner.os.path, "ismount", return_value=True):
            for origin, destination in ((source, nested), (nested, source), (source, source)):
                with self.subTest(source=origin, archive=destination):
                    with self.assertRaisesRegex(ValueError, "incompatibles"):
                        runner.preflight(origin, destination, mount, staging, credentials)
            runner.preflight(source, archive, mount, staging, credentials)

    def test_empty_with_real_extraction_cli_and_integrated_auditor(self):
        # Directorios sintéticos vacíos: no se mueven documentos ni se invoca carga.
        with patch.object(runner, "STAGING", self.root), patch.object(runner, "preflight"), \
             redirect_stdout(io.StringIO()):
            state = runner.run(self.source, self.archive, self.root, "synthetic_test")
        record = json.loads(state.read_text())
        self.assertEqual("EMPTY", record["state"])
        self.assertEqual("OK", record["stages"]["extract_audit"]["result"]["audit_state"])
        self.assertTrue(Path(record["stages"]["extract_audit"]["result"]["audit"]).is_file())

    def test_failure_stops_each_stage_and_records_error(self):
        for index, stage in enumerate(("1_extract", "2_transform", "3_load")):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as root:
                self.root = Path(root)
                self.calls = []
                self.failure = stage
                with self.assertRaises(subprocess.CalledProcessError):
                    self.execute()
                record = self.record()
                self.assertEqual("ERROR", record["state"])
                self.assertEqual(index + 1, len(self.calls))
                self.assertEqual("ERROR", list(record["stages"].values())[-1]["state"])
                if index:
                    self.assertTrue(Path(record["paths"]["csv"]).exists())
                if index == 2:
                    self.assertTrue(Path(record["paths"]["parquet"]).exists())

    def test_global_exclusion(self):
        self.block = True
        errors = []
        def work():
            try:
                self.execute()
            except Exception as error:
                errors.append(error)
        worker = Thread(target=work)
        worker.start()
        try:
            self.assertTrue(self.entered.wait(5))
            with patch.object(runner, "STAGING", self.root):
                with self.assertRaisesRegex(RuntimeError, "activo"):
                    runner.run(self.source, self.archive, self.root, "synthetic_test")
        finally:
            self.release.set()
            worker.join(10)
        self.assertFalse(worker.is_alive())
        self.assertEqual([], errors)
        self.assertEqual(3, len(self.calls))

    def test_preflight_requires_real_mount_and_readable_credentials(self):
        credentials = self.root / "synthetic-key.json"
        credentials.write_text("{}")
        stage = self.root / "staging"
        stage.mkdir()
        with patch.object(runner.os.path, "ismount", return_value=False):
            with self.assertRaises(ValueError):
                runner.preflight(self.source, self.archive, self.root, stage, credentials)
        with patch.object(runner.os.path, "ismount", return_value=True):
            with self.assertRaises(ValueError):
                runner.preflight(self.source, self.archive, self.root, stage, credentials)


if __name__ == "__main__":
    unittest.main()
