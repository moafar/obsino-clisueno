"""Archivado PSG con documentos y rutas exclusivamente sintéticos."""

import argparse
import csv
import json
import errno
import hashlib
import io
import importlib.util
import os
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from threading import Thread
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "1_extract"))

from extract_commons import archivo_utils
from extract_commons.directorio_utils import procesar_directorio
from test_psg_extractor import synthetic_report

SPEC = importlib.util.spec_from_file_location("psg_extract_main_test", ROOT / "1_extract/main.py")
extract_main = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = extract_main
SPEC.loader.exec_module(extract_main)


class PSGArchivingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="psg-archive-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / ".psg-test-root").touch()
        self.source = self.root / "source"
        self.destination = self.root / "archive"
        self.output = self.root / "csv"
        for directory in (self.source, self.destination, self.output):
            directory.mkdir()
        self.config = extract_main.load_config(str(ROOT / "0_declarations/psg.yaml"))

    def test_yaml_resolves_production_defaults_without_writing(self):
        self.assertEqual(Path("/mnt/e/RESULTADOS"), self.config.entrada_ruta)
        self.assertEqual(Path("/mnt/e/RESULTADOS/RESULTADOS_OBSERVATORIO"),
                         self.config.archivo_destino)
        self.assertEqual(ROOT / "staging", self.config.carpeta_csv)

    def args(self, **changes):
        values = dict(flow="psg", config=None, input=str(self.source), input_posicional=None,
                      archive_dest=str(self.destination), output_dir=str(self.output),
                      test_root=str(self.root), mode="test", dry_run=False, no_process=False,
                      no_unify=False, verbose=False)
        values.update(changes)
        return argparse.Namespace(**values)

    def run_cli(self, answer="s", **changes):
        with patch.object(extract_main, "parse_args", return_value=self.args(**changes)), \
             patch("builtins.input", return_value=answer), \
             patch.dict(archivo_utils.TEXT_EXTRACTORS, {".doc": lambda _: synthetic_report("doc"),
                                                       ".rtf": lambda _: synthetic_report("rtf")}), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return extract_main.orchestrate()

    def csv_rows(self):
        rows = []
        for path in self.output.glob("extract_psg_*.csv"):
            with path.open(encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                if reader.fieldnames == list(archivo_utils.PSG_COLUMNS):
                    rows.extend(reader)
        return rows

    def test_dates_and_invalid_dates(self):
        for original, expected in (("01/02/2026", "2026/2026-02"),
                                   ("2024-02-29", "2024/2024-02"),
                                   ("2023-13-01", "sin_fecha"),
                                   ("2023-02-29", "sin_fecha"),
                                   (None, "sin_fecha"), ("illegible", "sin_fecha")):
            with self.subTest(original=original):
                self.assertEqual(expected, str(archivo_utils._psg_date_path(original)))

    def test_atomic_move_collision_and_prefixes(self):
        first = self.source / "report.doc"
        first.write_bytes(b"one")
        moved = archivo_utils._move_psg_file(first, "bs", "01/02/2026", self.destination)
        self.assertEqual(self.destination / "2026/2026-02/bs_report.doc", moved)
        self.assertFalse(first.exists())
        self.assertEqual(b"one", moved.read_bytes())
        first.write_bytes(b"two")
        with self.assertRaises(FileExistsError):
            archivo_utils._move_psg_file(first, "bs", "01/02/2026", self.destination)
        self.assertEqual(b"two", first.read_bytes())
        self.assertEqual(b"one", moved.read_bytes())
        prefixed = self.source / "bs_report.doc"
        prefixed.write_bytes(b"prefixed")
        twice = archivo_utils._move_psg_file(prefixed, "bs", "01/02/2026", self.destination)
        self.assertEqual("bs_bs_report.doc", twice.name)
        twice_named = self.source / twice.name
        twice_named.write_bytes(b"twice")
        third = archivo_utils._move_psg_file(twice_named, "bs", "01/02/2026", self.destination)
        self.assertEqual("bs_bs_bs_report.doc", third.name)

    def test_rename_success_does_not_use_link_fallback(self):
        source = self.source / "synthetic.doc"
        source.write_bytes(b"synthetic")
        with patch.object(archivo_utils, "_rename_noreplace",
                          side_effect=lambda src, dst, **kwargs: os.rename(src, dst)):
            with patch.object(archivo_utils.os, "link", side_effect=AssertionError("unexpected link")):
                archivo_utils._move_psg_file(source, "bs", "01/02/2026", self.destination)
        self.assertFalse(source.exists())

    def test_drvfs_fallback_links_then_unlinks_without_copy(self):
        source = self.source / "synthetic.doc"
        source.write_bytes(b"synthetic")
        unsupported = OSError(errno.EINVAL, "RENAME_NOREPLACE unsupported")
        with patch.object(archivo_utils, "_rename_noreplace", side_effect=unsupported):
            destination = archivo_utils._move_psg_file(
                source, "bs", "01/02/2026", self.destination)
        self.assertFalse(source.exists())
        self.assertEqual(b"synthetic", destination.read_bytes())

    def test_link_failure_preserves_source(self):
        source = self.source / "synthetic.doc"
        source.write_bytes(b"synthetic")
        with patch.object(archivo_utils, "_rename_noreplace",
                          side_effect=OSError(errno.EINVAL, "unsupported")), \
             patch.object(archivo_utils.os, "link",
                          side_effect=PermissionError(errno.EACCES, "denied")):
            with self.assertRaises(PermissionError):
                archivo_utils._move_psg_file(source, "bs", "01/02/2026", self.destination)
        self.assertEqual(b"synthetic", source.read_bytes())
        self.assertFalse((self.destination / "2026/2026-02/bs_synthetic.doc").exists())

    def test_link_fallback_never_replaces_different_content(self):
        source = self.source / "synthetic.doc"
        source.write_bytes(b"synthetic")
        destination_dir = self.destination / "2026/2026-02"
        destination_dir.mkdir(parents=True)
        destination = destination_dir / "bs_synthetic.doc"
        destination.write_bytes(b"different")
        with patch.object(archivo_utils, "_rename_noreplace",
                          side_effect=OSError(errno.EINVAL, "unsupported")):
            with self.assertRaises(FileExistsError):
                archivo_utils._move_psg_file(source, "bs", "01/02/2026",
                                             self.destination, allow_complete_link=True)
        self.assertEqual(b"synthetic", source.read_bytes())
        self.assertEqual(b"different", destination.read_bytes())

    def test_same_file_collision_requires_registered_retry(self):
        source = self.source / "synthetic.doc"
        source.write_bytes(b"synthetic")
        destination_dir = self.destination / "2026/2026-02"
        destination_dir.mkdir(parents=True)
        destination = destination_dir / "bs_synthetic.doc"
        os.link(source, destination)
        with patch.object(archivo_utils, "_rename_noreplace",
                          side_effect=OSError(errno.EINVAL, "unsupported")):
            with self.assertRaises(FileExistsError):
                archivo_utils._move_psg_file(source, "bs", "01/02/2026", self.destination)
        self.assertTrue(source.exists())
        self.assertTrue(os.path.samefile(source, destination))

    def test_registered_same_file_can_finish_when_rename_is_supported(self):
        source = self.source / "synthetic.doc"
        source.write_bytes(b"synthetic")
        destination_dir = self.destination / "2026/2026-02"
        destination_dir.mkdir(parents=True)
        destination = destination_dir / "bs_synthetic.doc"
        os.link(source, destination)
        archivo_utils._move_psg_file(source, "bs", "01/02/2026", self.destination,
                                     allow_complete_link=True)
        self.assertFalse(source.exists())
        self.assertEqual(b"synthetic", destination.read_bytes())

    def test_destination_symlinks_cannot_create_or_move_outside_archive(self):
        outside = self.root / "outside"
        outside.mkdir()
        source = self.source / "synthetic.doc"
        source.write_bytes(b"synthetic")
        year = self.destination / "2026"
        year.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(OSError):
            archivo_utils._move_psg_file(source, "bs", "01/02/2026", self.destination)
        self.assertFalse((outside / "2026-02").exists())
        year.unlink()
        year.mkdir()
        (year / "2026-02").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(OSError):
            archivo_utils._move_psg_file(source, "bs", "01/02/2026", self.destination)
        self.assertFalse((outside / "bs_synthetic.doc").exists())
        self.assertEqual(b"synthetic", source.read_bytes())

    def test_concurrent_collision_does_not_overwrite(self):
        other = self.root / "other"
        other.mkdir()
        sources = [self.source / "same.doc", other / "same.doc"]
        sources[0].write_bytes(b"first")
        sources[1].write_bytes(b"second")
        results = []
        def move(source):
            try:
                archivo_utils._move_psg_file(source, "bs", "", self.destination)
                results.append("moved")
            except FileExistsError:
                results.append("collision")
        threads = [Thread(target=move, args=(source,)) for source in sources]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertCountEqual(["moved", "collision"], results)
        self.assertEqual(1, sum(source.exists() for source in sources))
        self.assertIn((self.destination / "sin_fecha/bs_same.doc").read_bytes(),
                      (b"first", b"second"))

    def test_recursive_exclusion_uses_resolved_destination(self):
        nested = self.source / "another_name"
        nested.mkdir()
        (nested / "old.doc").write_bytes(b"old")
        (self.source / "new.doc").write_bytes(b"new")
        with patch("extract_commons.directorio_utils.procesar_archivo", return_value="new") as process:
            result = procesar_directorio(self.source, barra_progreso=False,
                                         psg_archive_dir=nested, known_psg={})
        self.assertEqual(1, result["num_files"])
        self.assertEqual(1, process.call_count)

    def test_dry_run_and_denial_have_no_side_effects(self):
        source = self.source / "synthetic.doc"
        source.write_bytes(b"synthetic")
        with patch.object(extract_main, "parse_args", return_value=self.args(dry_run=True)), \
             patch("builtins.input", side_effect=AssertionError("no prompt")), \
             patch.object(extract_main, "run_processing", side_effect=AssertionError("no extraction")), \
             redirect_stdout(io.StringIO()):
            self.assertEqual(0, extract_main.orchestrate())
        self.assertEqual(0, self.run_cli(answer="n"))
        with patch("builtins.input", side_effect=EOFError), \
             patch.object(extract_main, "parse_args", return_value=self.args()), \
             redirect_stdout(io.StringIO()):
            self.assertEqual(0, extract_main.orchestrate())
        self.assertTrue(source.exists())
        self.assertFalse((self.root / "logs").exists())
        self.assertFalse((self.output / ".psg-archive.lock").exists())
        self.assertEqual([], list(self.output.glob("*.csv")))

    def test_test_mode_rejects_paths_outside_root(self):
        with tempfile.TemporaryDirectory(prefix="other-psg-test-") as outside:
            with self.assertRaises(ValueError):
                extract_main._psg_runtime(self.args(input=outside), self.config)
        (self.root / ".psg-test-root").unlink()
        with self.assertRaises(ValueError):
            extract_main._psg_runtime(self.args(), self.config)

    def test_test_mode_rejects_protected_clinical_root(self):
        official = replace(self.config, rutas_clinicas_protegidas=[self.root])
        with patch.object(extract_main, "load_config", return_value=official):
            with self.assertRaises(ValueError):
                extract_main._psg_runtime(self.args(), self.config)

    def test_psg_rejects_additional_subflows_in_test_mode(self):
        unsafe = replace(self.config, subflujos_salida_unificada={
            "BASAL": "extract_psg_{timestamp}.csv", "CPAP": "extract_xpap_test.csv"})
        with self.assertRaises(ValueError):
            extract_main._psg_runtime(self.args(), unsafe)

    def test_missing_archive_destination_has_no_fallback(self):
        nonexistent = self.root / "missing"
        with self.assertRaises(FileNotFoundError):
            extract_main._psg_runtime(self.args(archive_dest=str(nonexistent)), self.config)
        self.assertFalse(nonexistent.exists())

    def test_directory_counts_all_psg_outcomes(self):
        for name in ("a.doc", "b.doc", "c.doc", "d.doc"):
            (self.source / name).write_bytes(b"synthetic")
        with patch("extract_commons.directorio_utils.procesar_archivo",
                   side_effect=["new", "duplicate", "new_archive_failed", "retried"]):
            result = procesar_directorio(self.source, barra_progreso=False,
                                         psg_archive_dir=self.destination, known_psg={})
        self.assertEqual(1, result["archivos_extraidos"])
        self.assertEqual(1, result["archivos_duplicados"])
        self.assertEqual(1, result["archivos_fallo_archivado"])
        self.assertEqual(1, result["archivos_reintentados"])
        self.assertEqual(2, result["archivos_registrados"])

    def test_audit_automatically_written_after_extraction(self):
        source = self.source / "synthetic.doc"
        source.write_bytes(b"synthetic")
        self.assertEqual(0, self.run_cli())
        reports = list((self.root / "logs").glob("extract_psg_*_auditoria.md"))
        self.assertEqual(1, len(reports))
        report_text = reports[0].read_text(encoding="utf-8")
        self.assertIn("Archivos localizados: 1", report_text)
        self.assertIn("## Tiempos de la ejecución", report_text)
        for phase in ("Lectura de UUID históricos", "Procesamiento",
                      "Auditoría hasta escritura del informe",
                      "Orquestación hasta escritura del informe"):
            self.assertIn(f"| {phase} |", report_text)
        logs = list((self.root / "logs").glob("extract_psg_*.log"))
        self.assertEqual(1, len(logs))
        log_text = logs[0].read_text(encoding="utf-8")
        for step in ("1/3", "2/3", "3/3"):
            self.assertIn(f"Progreso PSG {step}", log_text)
        self.assertRegex(log_text, r"orquestacion_total_s=\d+\.\d{3}")
        self.assertFalse(source.exists())
        self.assertEqual(1, len(self.csv_rows()))

    def test_each_rejected_document_has_one_coded_log_event(self):
        for name in ("unreadable.doc", "other.doc", "nohash.doc", "OXIGENO.doc"):
            (self.source / name).write_bytes(b"synthetic")

        def converted(path):
            return (None if path.name == "unreadable.doc" else
                    "Documento sintético ajeno a PSG" if path.name == "other.doc" else
                    synthetic_report("doc"))

        with patch("extract_commons.archivo_utils._extract_text", side_effect=converted), \
             patch("extract_commons.archivo_utils.generar_hash_archivo", return_value="N/A"), \
             self.assertLogs(level="WARNING") as captured:
            result = procesar_directorio(self.source, barra_progreso=False,
                                         psg_archive_dir=self.destination, known_psg={})
        events = [json.loads(line.split("Rechazo PSG: ", 1)[1])
                  for line in captured.output if "Rechazo PSG: " in line]
        self.assertEqual(4, result["archivos_rechazados"])
        self.assertEqual(4, len(events))
        self.assertEqual(4, len({event["origen"] for event in events}))
        self.assertEqual({
            "unreadable.doc": "TEXTO_ILEGIBLE", "other.doc": "NO_PSG_BASAL",
            "nohash.doc": "UUID_NO_GENERADO", "OXIGENO.doc": "EXCLUIDO_OXIGENO",
        }, {Path(event["origen"]).name: event["codigo"] for event in events})
        self.assertTrue(all(event["motivo"] for event in events))

    def test_csv_write_failure_blocks_without_counting_rejection(self):
        source = self.source / "synthetic.doc"
        source.write_bytes(b"synthetic")
        with patch("extract_commons.archivo_utils._append_psg_row",
                   side_effect=OSError("fallo sintético de escritura")):
            self.assertEqual(extract_main.EXIT_PROCESS, self.run_cli())
        self.assertTrue(source.exists())
        logs = list((self.root / "logs").glob("extract_psg_*.log"))
        self.assertEqual(1, len(logs))
        log_text = logs[0].read_text(encoding="utf-8")
        self.assertIn("errores_procesamiento=1", log_text)
        self.assertIn("rechazados=0", log_text)
        self.assertNotIn("Rechazo PSG:", log_text)
        reports = list((self.root / "logs").glob("extract_psg_*_auditoria.md"))
        self.assertEqual(1, len(reports))
        report_text = reports[0].read_text(encoding="utf-8")
        self.assertIn("**Resultado: ERROR**", report_text)
        self.assertIn("| Errores técnicos de procesamiento | 1 |", report_text)

    def test_unexpected_basal_parser_failure_blocks_without_rejection(self):
        source = self.source / "synthetic.doc"
        source.write_bytes(b"synthetic")

        def unexpected_parser(*_):
            raise RuntimeError("fallo sintético")

        with patch.dict(archivo_utils.EXAMS["BASAL"].processors,
                        {".doc": unexpected_parser}):
            self.assertEqual(extract_main.EXIT_PROCESS, self.run_cli())
        self.assertTrue(source.exists())
        log = next((self.root / "logs").glob("extract_psg_*.log"))
        log_text = log.read_text(encoding="utf-8")
        self.assertIn("errores_procesamiento=1", log_text)
        self.assertIn("rechazados=0", log_text)
        self.assertNotIn("Rechazo PSG:", log_text)
        report = next((self.root / "logs").glob("extract_psg_*_auditoria.md"))
        self.assertIn("**Resultado: ERROR**", report.read_text(encoding="utf-8"))

    def test_normal_mode_accepts_alternate_origin(self):
        source, destination, output, _ = extract_main._psg_runtime(
            self.args(mode="normal", test_root=None), self.config)
        self.assertEqual((self.source, self.destination, self.output),
                         (source, destination, output))
        source_file = self.source / "synthetic.doc"
        source_file.write_bytes(b"synthetic")
        self.assertEqual(0, self.run_cli(mode="normal", test_root=None))
        self.assertFalse(source_file.exists())

    def test_success_and_retry_after_archiving_failure(self):
        source = self.source / "synthetic.doc"
        source.write_bytes(b"synthetic")
        with patch.object(archivo_utils, "_rename_noreplace", side_effect=OSError("synthetic")):
            self.assertEqual(extract_main.EXIT_PROCESS, self.run_cli())
        self.assertTrue(source.exists())
        csv_files = list(self.output.glob("extract_psg_*.csv"))
        self.assertEqual(1, len(csv_files))
        with csv_files[0].open(encoding="utf-8", newline="") as stream:
            self.assertEqual(1, len(list(csv.DictReader(stream))))
        with patch.object(extract_main, "build_timestamped_output_map",
                          return_value={"BASAL": "extract_psg_retry.csv"}):
            self.assertEqual(0, self.run_cli())
        self.assertFalse(source.exists())
        self.assertTrue((self.destination / "2026/2026-02/bs_synthetic.doc").exists())
        self.assertEqual(1, len(self.csv_rows()))

    def test_unlink_failure_is_recovered_without_duplicate_csv_row(self):
        source = self.source / "synthetic.doc"
        source.write_bytes(b"synthetic")
        real_unlink = os.unlink
        def fail_source_unlink(path, *args, **kwargs):
            if Path(path) == source:
                raise PermissionError(errno.EACCES, "synthetic unlink failure")
            return real_unlink(path, *args, **kwargs)
        with patch.object(archivo_utils, "_rename_noreplace",
                          side_effect=OSError(errno.EINVAL, "unsupported")), \
             patch.object(archivo_utils.os, "unlink", side_effect=fail_source_unlink):
            self.assertEqual(extract_main.EXIT_PROCESS, self.run_cli())
        destination = self.destination / "2026/2026-02/bs_synthetic.doc"
        self.assertTrue(source.exists())
        self.assertTrue(os.path.samefile(source, destination))
        self.assertEqual(1, len(self.csv_rows()))
        with patch.object(archivo_utils, "_rename_noreplace",
                          side_effect=OSError(errno.EINVAL, "unsupported")):
            self.assertEqual(0, self.run_cli())
        self.assertFalse(source.exists())
        self.assertEqual(b"synthetic", destination.read_bytes())
        self.assertEqual(1, len(self.csv_rows()))

    def test_uuid_duplicate_from_other_source_is_not_moved(self):
        first = self.source / "first.doc"
        first.write_bytes(b"same-content")
        self.assertEqual(0, self.run_cli())
        second = self.source / "second.doc"
        second.write_bytes(b"same-content")
        self.assertEqual(0, self.run_cli())
        self.assertTrue(second.exists())
        self.assertFalse((self.destination / "2026/2026-02/bs_second.doc").exists())
        self.assertEqual(1, len(self.csv_rows()))

    def test_resume_checkpoint_reconciles_recovered_archive_failure(self):
        source = self.source / "synthetic.doc"
        source.write_bytes(b"synthetic")
        summary = self.root / "extract.json"
        with patch.object(archivo_utils, "_rename_noreplace", side_effect=OSError(errno.EIO, "interrumpido")):
            self.assertEqual(extract_main.EXIT_PROCESS, self.run_cli(result_json=str(summary)))
        self.assertTrue(source.exists())
        self.assertEqual(0, self.run_cli(result_json=str(summary), resume_extraction=True))
        self.assertFalse(source.exists())
        import json
        result = json.loads(summary.read_text())
        self.assertEqual(0, result["counts"]["archivos_fallo_archivado"])
        self.assertEqual(1, result["counts"]["archivos_extraidos"])
        self.assertEqual(1, len(self.csv_rows()))

    def test_source_change_and_single_history_read(self):
        (self.source / "first.doc").write_bytes(b"first-synthetic")
        self.assertEqual(0, self.run_cli())
        new_source, new_archive = self.root / "source2", self.root / "archive2"
        new_source.mkdir()
        new_archive.mkdir()
        (new_source / "second.doc").write_bytes(b"second-synthetic")
        history_reader = extract_main.load_known_psg_uuids
        with patch.object(extract_main, "load_known_psg_uuids", wraps=history_reader) as history, \
             patch.object(archivo_utils, "load_known_psg_uuids", side_effect=AssertionError("No duplicar lectura")):
            self.assertEqual(0, self.run_cli(input=str(new_source), archive_dest=str(new_archive)))
        history.assert_called_once_with(self.output)
        self.assertEqual(2, len(self.csv_rows()))

    def test_existing_archive_name_survives_retry(self):
        source = self.source / "synthetic.doc"
        source.write_bytes(b"synthetic")
        archive_dir = self.destination / "2026/2026-02"
        archive_dir.mkdir(parents=True)
        existing = archive_dir / "bs_synthetic.doc"
        existing.write_bytes(b"existing")
        self.assertEqual(extract_main.EXIT_PROCESS, self.run_cli())
        self.assertEqual(extract_main.EXIT_PROCESS, self.run_cli())
        self.assertEqual(b"synthetic", source.read_bytes())
        self.assertEqual(b"existing", existing.read_bytes())
        self.assertEqual(1, len(self.csv_rows()))

    def test_archive_failure_continues_other_documents_and_returns_error(self):
        blocked = self.source / "blocked.doc"
        accepted = self.source / "accepted.doc"
        blocked.write_bytes(b"blocked")
        accepted.write_bytes(b"accepted")
        archive_dir = self.destination / "2026/2026-02"
        archive_dir.mkdir(parents=True)
        (archive_dir / "bs_blocked.doc").write_bytes(b"existing")
        self.assertEqual(extract_main.EXIT_PROCESS, self.run_cli())
        self.assertTrue(blocked.exists())
        self.assertFalse(accepted.exists())
        self.assertTrue((archive_dir / "bs_accepted.doc").exists())
        self.assertEqual(2, len(self.csv_rows()))

    def test_walk_error_returns_nonzero_after_summary(self):
        result = dict(num_files=0, num_dirs=0, archivos_validos=0,
                      archivos_extraidos=0, archivos_registrados=0,
                      archivos_rechazados=0, archivos_duplicados=0,
                      archivos_fallo_archivado=0, archivos_reintentados=0,
                      errores_recorrido=1)
        with patch.object(extract_main, "run_processing", return_value=(result, 0.01)), \
             patch.object(extract_main, "report") as summary:
            self.assertEqual(extract_main.EXIT_PROCESS, self.run_cli())
        summary.assert_called_once()

    def test_walk_error_does_not_stop_other_documents(self):
        source = self.source / "synthetic.doc"
        source.write_bytes(b"synthetic")
        def walk(_root, *, onerror, **_kwargs):
            onerror(OSError("synthetic unreadable directory"))
            yield str(self.source), [], [source.name]
        with patch("extract_commons.directorio_utils.os.walk", side_effect=walk), \
             patch("extract_commons.directorio_utils.procesar_archivo", return_value="new"):
            result = procesar_directorio(self.source, barra_progreso=False,
                                         psg_archive_dir=self.destination, known_psg={})
        self.assertEqual(1, result["errores_recorrido"])
        self.assertEqual(1, result["archivos_extraidos"])

    def test_legacy_csv_does_not_block_canonical_reprocessing(self):
        source = self.source / "synthetic.doc"
        source.write_bytes(b"synthetic")
        legacy = self.output / "extract_psg_legacy.csv"
        legacy.write_text("basal_uuid,basal_fuente\n" +
                          hashlib.md5(b"synthetic").hexdigest() + ",old-source\n",
                          encoding="utf-8")
        self.assertEqual(0, self.run_cli())
        self.assertFalse(source.exists())
        self.assertEqual(1, len(self.csv_rows()))

    def test_rtf_without_study_date_archives_in_sin_fecha(self):
        source = self.source / "synthetic.rtf"
        source.write_bytes(b"synthetic-rtf")
        original = synthetic_report("rtf")
        text = original.replace("01/02/2026", "fecha ilegible")
        with patch.dict(archivo_utils.TEXT_EXTRACTORS, {".rtf": lambda _: text}), \
             patch.object(extract_main, "parse_args", return_value=self.args()), \
             patch("builtins.input", return_value="s"), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(0, extract_main.orchestrate())
        self.assertTrue((self.destination / "sin_fecha/bs_synthetic.rtf").exists())

    def test_xpap_cli_keeps_legacy_output_configuration(self):
        xpap_config = extract_main.load_config(str(ROOT / "0_declarations/xpap.yaml"))
        args = self.args(flow="xpap", dry_run=True, mode="normal", test_root=None,
                         archive_dest=None, output_dir=None)
        with patch.object(extract_main, "parse_args", return_value=args), \
             patch.object(extract_main, "setup_logging_from_config"), \
             patch.object(extract_main, "configure_subflows") as configure, \
             redirect_stdout(io.StringIO()):
            self.assertEqual(0, extract_main.orchestrate())
        self.assertEqual(xpap_config.carpeta_csv, configure.call_args.kwargs["output_dir"])


if __name__ == "__main__":
    unittest.main()
