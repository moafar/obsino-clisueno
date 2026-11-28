"""Verifica las CLI PSG sin ejecutar procesamiento ni autenticación remota."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class PsgCliLockTest(unittest.TestCase):
    def test_all_pipeline_cli_entries_reach_shared_lock_before_processing(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            (directory / ".psg-test-root").touch()
            source, archive, output = (directory / name for name in ("source", "archive", "output"))
            for path in (source, archive, output):
                path.mkdir()
            log = directory / "synthetic.log"
            log.touch()
            with tempfile.NamedTemporaryFile(dir=ROOT / "staging", prefix="extract_psg_locktest_",
                                             suffix="_transformed.parquet") as artifact:
                cases = (
                    ("1_extract/main.py", ["--flow", "psg", "--mode", "test", "--test-root", root,
                        "--input", str(source), "--archive-dest", str(archive), "--output-dir", str(output), "--protected-root", str(directory.parent / (directory.name + "-protected")), "--yes"]),
                    ("1_extract/extract_commons/auditoria_psg.py", ["--input", artifact.name,
                        "--log", str(log), "--source", str(source), "--archive", str(archive)]),
                    ("2_transform/main.py", ["--flow", "psg", "--input", str(output / "extract_psg_locktest.csv"), "--dry-run"]),
                    ("2_transform/psg/main.py", ["--input", str(output / "extract_psg_locktest.csv"), "--dry-run"]),
                    ("3_load/main.py", ["--flow", "psg", "--input", artifact.name, "--table-id", "synthetic_test", "--yes"]),
                    ("scripts/run_psg.py", ["--input", str(source), "--archive-dest", str(archive),
                        "--mount", root, "--table-id", "synthetic_test"]),
                )
                for entry, args in cases:
                    with self.subTest(entry=entry):
                        code = '''import sys,runpy
from contextlib import contextmanager
from scripts import psg_state
class LockReached(BaseException): pass
@contextmanager
def lock(*args, **kwargs):
    raise LockReached()
    yield
psg_state.psg_lock = lock
sys.argv = %r
try:
    runpy.run_path(%r, run_name="__main__")
except LockReached:
    sys.exit(75)
''' % ([entry, *args], str(ROOT / entry))
                        result = subprocess.run([sys.executable, "-c", code], cwd=ROOT,
                            env={**os.environ, "PYTHONPATH": os.pathsep.join(map(str,
                                 (ROOT, ROOT / "1_extract", ROOT / "2_transform")))},
                            capture_output=True, text=True, timeout=15)
                        self.assertEqual(75, result.returncode, result.stderr[-1200:])
