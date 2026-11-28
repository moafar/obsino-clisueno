"""Medición aislada de E01 sobre informes PSG RTF sintéticos.

Uso: .venv/bin/python docs/e01_perfil_extractor.py --count 30
Solo crea archivos en TemporaryDirectory bajo /tmp y no cambia código funcional.
"""

import argparse
import contextlib
import csv
import functools
import hashlib
import importlib.util
import io
import json
import resource
import shutil
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "1_extract"), str(ROOT / "1_extract" / "tests")]

from extract_commons import archivo_utils, auditoria_psg  # noqa: E402
from test_psg_extractor import synthetic_report  # noqa: E402

spec = importlib.util.spec_from_file_location("e01_extract_main", ROOT / "1_extract" / "main.py")
main = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = main
spec.loader.exec_module(main)


def as_rtf(text):
    def escape(char):
        if char == "\n":
            return "\\par\n"
        if char in "\\{}":
            return "\\" + char
        if ord(char) > 127:
            return f"\\u{ord(char)}?"
        return char

    return ("{\\rtf1\\ansi\n" + "".join(map(escape, text)) + "}").encode("ascii")


def measured(totals, name, function):
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return function(*args, **kwargs)
        finally:
            totals[name] += time.perf_counter() - start
    return wrapper


def run(count, prior_rows=0, *, temp_base=None, fixture_dir=None):
    totals = defaultdict(float)
    with tempfile.TemporaryDirectory(prefix="e01-psg-", dir=temp_base) as folder:
        root = Path(folder)
        (root / ".psg-test-root").touch()
        source, archive, output = (root / name for name in ("source", "archive", "csv"))
        for directory in (source, archive, output):
            directory.mkdir()
        if fixture_dir is None:
            suffix = ".rtf"
            for number in range(count):
                report = synthetic_report("rtf").replace("000123", f"{number + 1:06d}")
                (source / f"synthetic_{number:04d}.rtf").write_bytes(as_rtf(report))
        else:
            fixtures = sorted(Path(fixture_dir).iterdir())
            suffixes = {path.suffix.lower() for path in fixtures}
            if len(fixtures) != count or len(suffixes) != 1 or not suffixes <= {".rtf", ".doc"}:
                raise ValueError("La muestra debe tener count archivos DOC o RTF del mismo formato")
            suffix = suffixes.pop()
            for path in fixtures:
                if not path.is_file() or path.is_symlink():
                    raise ValueError("La muestra debe contener solo archivos regulares")
                shutil.copyfile(path, source / path.name)
        if prior_rows:
            with (output / "extract_psg_prior.csv").open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=archivo_utils.PSG_COLUMNS)
                writer.writeheader()
                for number in range(prior_rows):
                    writer.writerow({"meta_uuid": f"{number + 1:032x}",
                                     "meta_fuente": f"/tmp/synthetic_previous_{number:05d}.rtf"})

        args = argparse.Namespace(
            flow="psg", config=None, input=str(source), input_posicional=None,
            archive_dest=str(archive), output_dir=str(output), test_root=str(root),
            mode="test", dry_run=False, no_process=False, no_unify=False,
            verbose=False,
        )
        patches = [
            patch.object(main, "parse_args", return_value=args),
            patch("builtins.input", return_value="s"),
            patch.object(main, "load_known_psg_uuids", measured(totals, "csv_previos", main.load_known_psg_uuids)),
            patch.object(main, "run_processing", measured(totals, "procesamiento", main.run_processing)),
            patch.object(main, "audit_psg", measured(totals, "auditoria", main.audit_psg)),
            patch.object(archivo_utils, "_extract_text", measured(totals, "lectura_" + suffix[1:], archivo_utils._extract_text)),
            patch.object(archivo_utils, "generar_hash_archivo", measured(totals, "hash_inicial", archivo_utils.generar_hash_archivo)),
            patch.object(archivo_utils, "_append_psg_row", measured(totals, "csv_append", archivo_utils._append_psg_row)),
            patch.object(archivo_utils.os, "fsync", measured(totals, "csv_fsync", archivo_utils.os.fsync)),
            patch.object(archivo_utils, "_move_psg_file", measured(totals, "archivado", archivo_utils._move_psg_file)),
            patch.object(auditoria_psg, "digest", measured(totals, "auditoria_hash", auditoria_psg.digest)),
            patch.object(auditoria_psg, "residual_count", measured(totals, "auditoria_inventario", auditoria_psg.residual_count)),
        ]
        processor = archivo_utils.EXAMS["BASAL"].processors[suffix]
        with contextlib.ExitStack() as stack:
            for item in patches:
                stack.enter_context(item)
            archivo_utils.EXAMS["BASAL"].processors[suffix] = measured(totals, "parseo", processor)
            try:
                start_wall, start_cpu = time.perf_counter(), time.process_time()
                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    exit_code = main.orchestrate()
                wall = time.perf_counter() - start_wall
                cpu = time.process_time() - start_cpu
            finally:
                archivo_utils.EXAMS["BASAL"].processors[suffix] = processor

        csv_files = [path for path in output.glob("extract_psg_*.csv")
                     if path.name != "extract_psg_prior.csv"]
        rows = 0
        row_digest = None
        if len(csv_files) == 1:
            with csv_files[0].open(newline="", encoding="utf-8") as stream:
                records = list(csv.DictReader(stream))
                rows = len(records)
            if fixture_dir is not None:
                for record in records:
                    record.pop("meta_fuente", None)
                    record.pop("meta_version_control", None)
                records.sort(key=lambda record: record["meta_uuid"])
                row_digest = hashlib.sha256(json.dumps(records, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
        archive_files = sorted(archive.rglob("*"))
        archive_files = [path for path in archive_files if path.is_file()]
        archived = sum(path.suffix.lower() == suffix for path in archive_files)
        archive_digest = None
        if fixture_dir is not None:
            pairs = [(path.name, hashlib.sha256(path.read_bytes()).hexdigest()) for path in archive_files]
            archive_digest = hashlib.sha256(json.dumps(pairs).encode("ascii")).hexdigest()
        audit_files = list((root / "logs").glob("*_auditoria.md"))
        audit_state = (audit_files[0].read_text(encoding="utf-8").split("**Resultado: ", 1)[1].split("**", 1)[0]
                       if len(audit_files) == 1 else None)
        return {
            "count": count, "prior_rows": prior_rows,
            "input_bytes": sum(path.stat().st_size for path in archive_files),
            "exit_code": exit_code, "csv_rows": rows, "archived": archived,
            "format": suffix[1:], "row_digest": row_digest, "archive_digest": archive_digest,
            "audit_state": audit_state, "wall_s": round(wall, 6), "cpu_s": round(cpu, 6),
            "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "phases_s": {name: round(value, 6) for name, value in sorted(totals.items())},
        }


def run_generic(rows):
    """Aísla el append usado por XPAP; no simula extracción ni archivado."""
    with tempfile.TemporaryDirectory(prefix="e01-generic-csv-") as folder:
        outfile = Path(folder) / "synthetic.csv"
        start_wall, start_cpu = time.perf_counter(), time.process_time()
        for number in range(rows):
            row = {f"field_{column}": f"synthetic_{number}_{column}"
                   for column in range(20)}
            archivo_utils._append_row_unified(row, outfile)
        wall = time.perf_counter() - start_wall
        cpu = time.process_time() - start_cpu
        with outfile.open(newline="", encoding="utf-8") as stream:
            written = sum(1 for _ in csv.DictReader(stream))
        return {"generic_rows": rows, "csv_rows": written,
                "wall_s": round(wall, 6), "cpu_s": round(cpu, 6),
                "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int)
    parser.add_argument("--prior-rows", type=int, default=0)
    parser.add_argument("--generic-rows", type=int)
    parser.add_argument("--temp-base", type=Path)
    parser.add_argument("--fixture-dir", type=Path)
    options = parser.parse_args()
    if options.generic_rows is not None:
        if options.generic_rows < 1 or options.count is not None or options.prior_rows:
            parser.error("--generic-rows positivo no admite --count ni --prior-rows")
        result = run_generic(options.generic_rows)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        if result["csv_rows"] != options.generic_rows:
            raise SystemExit(1)
        raise SystemExit(0)
    if options.count is None or options.count < 1 or options.prior_rows < 0:
        parser.error("--count debe ser positivo y --prior-rows no negativo")
    result = run(options.count, options.prior_rows,
                 temp_base=options.temp_base, fixture_dir=options.fixture_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if (result["exit_code"] or result["csv_rows"] != options.count or
            result["archived"] != options.count or result["audit_state"] != "OK"):
        raise SystemExit(1)
