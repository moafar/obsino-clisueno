"""Recuperación remota simulada y persistencia real en directorios sintéticos."""
import errno
import io
import json
from pathlib import Path
from contextlib import redirect_stdout
from unittest.mock import Mock, patch
import unittest

from google.api_core.exceptions import NotFound
import test_psg_load as fixture
FakeClient, load = fixture.FakeClient, fixture.load
UUID1, UUID2 = fixture.UUID1, fixture.UUID2


class RecoveryLoadTest(unittest.TestCase):
    setUp = fixture.PsgLoadTest.setUp
    row = fixture.PsgLoadTest.row
    write = fixture.PsgLoadTest.write

    def execute(self, client):
        with patch.object(load, "STAGING_DIR", Path(self.temp.name)), \
             patch.object(load, "confirm_execution"), patch.object(load, "validate_paths"), \
             patch.object(load, "authenticate_bigquery", return_value=client), redirect_stdout(io.StringIO()):
            return load.run(self.config, "psg")

    def state(self):
        return json.loads(load.psg_load_state_path(self.config).read_text())

    def test_lost_response_queries_job_without_resending(self):
        self.write([self.row()])
        client = FakeClient(self.schema)
        def lost(dataframe, table, **kwargs):
            job = client._load(dataframe, table, **kwargs)
            job.result()
            raise TimeoutError("respuesta perdida")
        client.load_table_from_dataframe = Mock(side_effect=lost)
        with self.assertRaises(TimeoutError):
            self.execute(client)
        self.assertEqual("UNKNOWN", self.state()["state"])
        expected_id = self.state()["job_id"]
        result = self.execute(client)
        self.assertEqual(1, client.load_table_from_dataframe.call_count)
        self.assertEqual(expected_id, result["job_id"])
        self.assertFalse(self.path.exists())
        self.assertTrue(Path(result["loaded"]).exists())
        self.assertEqual(result, self.execute(client))
        self.assertEqual(1, client.load_table_from_dataframe.call_count)

    def test_pending_and_unknown_never_resubmit(self):
        self.write([self.row()])
        client = FakeClient(self.schema)
        def pending(dataframe, table, **kwargs):
            job = client._load(dataframe, table, **kwargs)
            job.result = lambda: None
            return job
        client.load_table_from_dataframe = Mock(side_effect=pending)
        with self.assertRaisesRegex(RuntimeError, "pendiente"):
            self.execute(client)
        self.assertEqual("PENDING", self.state()["state"])
        with self.assertRaisesRegex(RuntimeError, "pendiente"):
            self.execute(client)
        with patch.object(client, "get_job", side_effect=NotFound("no disponible")):
            with self.assertRaisesRegex(RuntimeError, "desconocido"):
                self.execute(client)
        self.assertEqual("UNKNOWN", self.state()["state"])
        self.assertEqual(1, client.load_table_from_dataframe.call_count)
        self.assertTrue(self.path.exists())

    def test_confirmed_failure_allows_new_logical_attempt(self):
        self.write([self.row()])
        client = FakeClient(self.schema)
        def failed(dataframe, table, **kwargs):
            job = client._load(dataframe, table, **kwargs)
            job.error_result = {"reason": "invalid"}
            return job
        client.load_table_from_dataframe = Mock(side_effect=failed)
        with self.assertRaisesRegex(RuntimeError, "confirmado"):
            self.execute(client)
        first = self.state()
        self.assertEqual("FAILED", first["state"])
        client.load_table_from_dataframe = Mock(side_effect=client._load)
        self.execute(client)
        self.assertEqual(2, self.state()["attempt"])
        self.assertNotEqual(first["job_id"], self.state()["job_id"])

    def test_failure_before_submission_has_no_remote_effect(self):
        self.write([self.row()])
        client = FakeClient(self.schema)
        with patch.object(load, "save", side_effect=OSError(errno.ENOSPC, "sin espacio")):
            with self.assertRaises(OSError):
                self.execute(client)
        client.load_table_from_dataframe.assert_not_called()
        self.assertTrue(self.path.exists())
        self.execute(client)
        self.assertEqual(1, client.load_table_from_dataframe.call_count)

    def test_confirmed_load_and_interrupted_link_retirement(self):
        self.write([self.row()])
        client = FakeClient(self.schema)
        from scripts import psg_state
        real_sync = psg_state.sync_dir
        def fail_once(path):
            # finish_move ya creó el enlace final; el journal CONFIRMED precede al enlace.
            raise OSError(errno.EIO, "sincronización interrumpida")
        real_move = load.finish_move
        def interrupted(*args):
            with patch.object(psg_state, "sync_dir", side_effect=fail_once):
                return real_move(*args)
        with patch.object(load, "finish_move", side_effect=interrupted):
            with self.assertRaises(OSError):
                self.execute(client)
        self.assertEqual("CONFIRMED", self.state()["state"])
        self.assertTrue(self.path.exists())
        self.assertTrue(Path(self.state()["loaded"]).exists())
        self.execute(client)
        self.assertEqual(1, client.load_table_from_dataframe.call_count)
        self.assertFalse(self.path.exists())

    def test_modified_artifact_or_foreign_job_stops_recovery(self):
        self.write([self.row()])
        client = FakeClient(self.schema)
        def lost(dataframe, table, **kwargs):
            client._load(dataframe, table, **kwargs)
            raise TimeoutError()
        client.load_table_from_dataframe = Mock(side_effect=lost)
        with self.assertRaises(TimeoutError):
            self.execute(client)
        client.jobs[self.state()["job_id"]].destination = "other.dataset.table"
        with self.assertRaisesRegex(RuntimeError, "no corresponde"):
            self.execute(client)
        self.write([self.row(pte_id="000999")])
        with self.assertRaisesRegex(RuntimeError, "Identidad"):
            self.execute(client)
        self.assertEqual(1, client.load_table_from_dataframe.call_count)

    def test_ready_checkpoint_can_submit_after_local_write_failure(self):
        self.write([self.row()])
        client = FakeClient(self.schema)
        original_save = load.save
        def before_submit(path, record):
            if record.get("state") == "SUBMITTED":
                raise OSError(errno.ENOSPC, "sin espacio antes del envío")
            original_save(path, record)
        with patch.object(load, "save", side_effect=before_submit):
            with self.assertRaises(OSError):
                self.execute(client)
        ready = self.state()
        self.assertEqual("READY", ready["state"])
        client.load_table_from_dataframe.assert_not_called()
        self.assertEqual(ready["job_id"], self.execute(client)["job_id"])
        self.assertEqual(1, client.load_table_from_dataframe.call_count)

    def test_other_uncertain_batch_blocks_new_load(self):
        self.write([self.row()])
        client = FakeClient(self.schema)
        other = Path(self.temp.name) / "extract_psg_other_transformed.load-state.json"
        other.write_text(json.dumps({"table": self.config.table_fqn, "state": "UNKNOWN"}))
        with self.assertRaisesRegex(RuntimeError, "Otra carga"):
            self.execute(client)
        client.load_table_from_dataframe.assert_not_called()
        self.assertTrue(self.path.exists())

    def test_result_exception_with_confirmed_remote_error_is_failed(self):
        self.write([self.row()])
        client = FakeClient(self.schema)
        def failed(dataframe, table, **kwargs):
            job = client._load(dataframe, table, **kwargs)
            job.state = "DONE"
            job.error_result = {"reason": "invalid"}
            job.result = Mock(side_effect=RuntimeError("fallo confirmado"))
            return job
        client.load_table_from_dataframe = Mock(side_effect=failed)
        with self.assertRaises(RuntimeError):
            self.execute(client)
        self.assertEqual("FAILED", self.state()["state"])
        self.assertTrue(self.path.exists())

    def test_source_retired_before_loaded_state_persisted_recovers(self):
        self.write([self.row()])
        client = FakeClient(self.schema)
        original_save = load.save
        def after_move(path, record):
            if record.get("state") == "LOADED":
                raise OSError(errno.ENOSPC, "sin espacio tras retirar origen")
            original_save(path, record)
        with patch.object(load, "save", side_effect=after_move):
            with self.assertRaises(OSError):
                self.execute(client)
        self.assertFalse(self.path.exists())
        self.assertEqual("CONFIRMED", self.state()["state"])
        self.execute(client)
        self.assertEqual("LOADED", self.state()["state"])
        self.assertEqual(1, client.load_table_from_dataframe.call_count)

    def test_uncertain_jobs_can_be_queried_without_mutual_blocking(self):
        self.write([self.row()])
        client = FakeClient(self.schema)
        def lost(dataframe, table, **kwargs):
            job = client._load(dataframe, table, **kwargs)
            job.result()
            raise TimeoutError()
        client.load_table_from_dataframe = Mock(side_effect=lost)
        with self.assertRaises(TimeoutError):
            self.execute(client)
        other = Path(self.temp.name) / "extract_psg_other_transformed.load-state.json"
        other.write_text(json.dumps({"table": self.config.table_fqn, "state": "UNKNOWN"}))
        result = self.execute(client)
        self.assertEqual(1, result["counts"]["inserted"])
        self.assertEqual(1, client.load_table_from_dataframe.call_count)
        self.assertEqual("UNKNOWN", json.loads(other.read_text())["state"])

    def pause_ready(self, client):
        original_save = load.save
        def before_submit(path, record):
            if record.get("state") == "SUBMITTED":
                raise OSError(errno.ENOSPC, "interrumpido en READY")
            original_save(path, record)
        with patch.object(load, "save", side_effect=before_submit):
            with self.assertRaises(OSError):
                self.execute(client)
        self.assertEqual("READY", self.state()["state"])

    def test_ready_reserves_destination_and_rechecks_existing_uuids(self):
        from dataclasses import replace
        import shutil
        self.write([self.row()])
        client = FakeClient(self.schema)
        self.pause_ready(client)
        second = self.path.with_name("extract_psg_z_transformed.parquet")
        shutil.copyfile(self.path, second)
        with patch.object(self, "config", replace(self.config, source_path=second)):
            with self.assertRaisesRegex(RuntimeError, "Otra carga"):
                self.execute(client)
        client.load_table_from_dataframe.assert_not_called()
        # Compatibilidad con un READY legado cuyo UUID ya fue cargado por otro lote.
        client.existing.add(UUID1)
        result = self.execute(client)
        self.assertEqual({"received": 1, "omitted": 1, "sent": 0, "inserted": 0}, result["counts"])
        client.load_table_from_dataframe.assert_not_called()
        self.assertTrue(second.exists())

    def test_ready_replans_partial_batch_without_changing_logical_attempt(self):
        self.write([self.row(), self.row(meta_uuid=UUID2, pte_id="000124")])
        client = FakeClient(self.schema)
        self.pause_ready(client)
        ready = self.state()
        client.existing.add(UUID1)
        result = self.execute(client)
        self.assertEqual([UUID2], client.load_table_from_dataframe.call_args.args[0]["meta_uuid"].tolist())
        self.assertEqual(1, result["counts"]["omitted"])
        self.assertEqual(ready["attempt"], self.state()["attempt"])
        self.assertNotEqual(ready["job_id"], result["job_id"])

    def test_multiple_ready_plans_have_deterministic_progress(self):
        from dataclasses import replace
        import shutil
        self.write([self.row()])
        client = FakeClient(self.schema)
        self.pause_ready(client)
        second = self.path.with_name("extract_psg_z_transformed.parquet")
        shutil.copyfile(self.path, second)
        second_config = replace(self.config, source_path=second)
        other = self.state()
        other.update(source=str(second), evidence=load.file_evidence(second),
                     loaded=str(second.with_name(second.stem + "_loaded.parquet")))
        load.psg_load_state_path(second_config).write_text(json.dumps(other))
        with patch.object(self, "config", second_config):
            with self.assertRaisesRegex(RuntimeError, "Otra carga"):
                self.execute(client)
        self.execute(client)
        with patch.object(self, "config", second_config):
            result = self.execute(client)
        self.assertEqual(1, result["counts"]["omitted"])
        self.assertEqual(1, client.load_table_from_dataframe.call_count)

    def test_invalid_journal_states_are_rejected_explicitly(self):
        self.write([self.row()])
        client = FakeClient(self.schema)
        self.pause_ready(client)
        original = self.state()
        for invalid in ("INVALID", None, []):
            for own in (True, False):
                with self.subTest(invalid=invalid, own=own):
                    load.psg_load_state_path(self.config).write_text(json.dumps(original))
                    path = (load.psg_load_state_path(self.config) if own else
                            Path(self.temp.name) / "extract_psg_other_transformed.load-state.json")
                    bad = dict(original, state=invalid)
                    path.write_text(json.dumps(bad))
                    with self.assertRaisesRegex(RuntimeError, "Estado inválido"):
                        self.execute(client)
        client.load_table_from_dataframe.assert_not_called()
