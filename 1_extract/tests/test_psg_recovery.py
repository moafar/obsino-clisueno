"""Reconciliación documental sin releer contenido ni recalcular MD5."""
import csv
import errno
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from extract_commons import archivo_utils as files
from src.basal.procesar_basal import PSG_COLUMNS


class DocumentRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, self.archive, self.output = (self.root / name for name in ("source", "archive", "output"))
        for path in (self.source, self.archive, self.output):
            path.mkdir()
        self.document = self.source / "synthetic.doc"
        self.document.write_bytes(b"synthetic-document")
        self.log = self.root / "extract.log"
        self.log.touch()
        self.uuid = "a" * 32
        with (self.output / "extract_psg_synthetic.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=PSG_COLUMNS)
            writer.writeheader()
            writer.writerow({"meta_uuid": self.uuid, "meta_fuente": str(self.document)})
        self.addCleanup(patch.stopall)
        patch.object(files, "PSG_RECOVERY_DIR", self.output / ".psg-moves").start()
        patch.object(files, "PSG_RECOVERY_LOG", self.log).start()
        patch.object(files, "generar_hash_archivo", side_effect=AssertionError("No recalcular MD5")).start()

    def recover(self):
        files.recover_psg_moves(self.source, self.archive, self.output)

    def test_moved_document_without_log_is_reconstructed_once(self):
        with patch.object(files.logging, "info", side_effect=OSError("interrupción antes del log")):
            with self.assertRaises(OSError):
                files._move_psg_file(self.document, "bs", None, self.archive, initial_uuid=self.uuid)
        self.assertFalse(self.document.exists())
        self.recover()
        self.recover()
        self.assertEqual(1, self.log.read_text().count("Traslado PSG correcto:"))
        state = json.loads(next((self.output / ".psg-moves").glob("*.json")).read_text())
        self.assertEqual("LOGGED", state["state"])
        self.assertEqual(self.uuid, state["uuid"])

    def test_link_created_before_source_retired(self):
        original_unlink = files.os.unlink
        def fail_source(path, *args, **kwargs):
            if Path(path) == self.document:
                raise OSError(errno.EIO, "interrupción")
            return original_unlink(path, *args, **kwargs)
        with patch.object(files, "_rename_noreplace", side_effect=OSError(errno.ENOSYS, "sin renameat2")), \
             patch.object(files.os, "unlink", side_effect=fail_source):
            with self.assertRaises(OSError):
                files._move_psg_file(self.document, "bs", None, self.archive, initial_uuid=self.uuid)
        target = self.archive / "sin_fecha/bs_synthetic.doc"
        self.assertTrue(target.samefile(self.document))
        self.recover()
        self.assertFalse(self.document.exists())
        self.assertTrue(target.exists())

    def test_missing_or_replaced_destination_stops(self):
        with patch.object(files.logging, "info", side_effect=OSError("sin confirmar log")):
            with self.assertRaises(OSError):
                files._move_psg_file(self.document, "bs", None, self.archive, initial_uuid=self.uuid)
        target = self.archive / "sin_fecha/bs_synthetic.doc"
        target.unlink()
        with self.assertRaises(RuntimeError):
            self.recover()
        target.write_bytes(b"other-document")
        with self.assertRaises(RuntimeError):
            self.recover()

    def test_logged_history_does_not_revalidate_or_block_new_roots(self):
        files._move_psg_file(self.document, "bs", None, self.archive, initial_uuid=self.uuid)
        journal = next((self.output / ".psg-moves").glob("*.json"))
        self.assertEqual("LOGGED", json.loads(journal.read_text())["state"])
        original = journal.read_bytes()
        with patch.object(files, "load_known_psg_uuids", side_effect=AssertionError("Sin lectura histórica")), \
             patch.object(files, "file_evidence", side_effect=AssertionError("Sin revalidar confirmados")):
            files.recover_psg_moves(self.root / "other-source", self.root / "other-archive", self.output)
        self.assertEqual(original, journal.read_bytes())

    def test_pending_incompatible_roots_are_not_ignored(self):
        with patch.object(files.logging, "info", side_effect=OSError("sin confirmar log")):
            with self.assertRaises(OSError):
                files._move_psg_file(self.document, "bs", None, self.archive, initial_uuid=self.uuid)
        with self.assertRaisesRegex(RuntimeError, "fuera de las rutas"):
            files.recover_psg_moves(self.root / "other-source", self.root / "other-archive", self.output)

    def test_recovery_reuses_provided_uuid_dictionary(self):
        with patch.object(files.logging, "info", side_effect=OSError("sin confirmar log")):
            with self.assertRaises(OSError):
                files._move_psg_file(self.document, "bs", None, self.archive, initial_uuid=self.uuid)
        with patch.object(files, "load_known_psg_uuids", side_effect=AssertionError("No releer CSV")):
            files.recover_psg_moves(self.source, self.archive, self.output,
                                    known={self.uuid: str(self.document)})
