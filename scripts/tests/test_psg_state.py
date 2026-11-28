import errno
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts import psg_state as state


class PsgStateTest(unittest.TestCase):
    def test_atomic_write_failure_preserves_last_confirmed_state(self):
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / "state.json"
            state.save(target, {"state": "CONFIRMED"})
            with patch.object(state.os, "replace", side_effect=OSError(errno.ENOSPC, "sin espacio")):
                with self.assertRaises(OSError):
                    state.save(target, {"state": "LOADED"})
            self.assertEqual({"state": "CONFIRMED"}, json.loads(target.read_text()))

    def test_manual_and_orchestrator_lock_and_inherited_child_after_sigkill(self):
        with tempfile.TemporaryDirectory() as root:
            directory = Path(root)
            read_fd, write_fd = os.pipe()
            child_code = ('import os,sys; from pathlib import Path; '
                'from scripts.psg_state import psg_lock; '
                f'ctx=psg_lock(Path({root!r})); ctx.__enter__(); '
                f'os.read({read_fd},1); ctx.__exit__(None,None,None)')
            parent_code = ('import os,subprocess,sys,time; from pathlib import Path; '
                'from scripts.psg_state import psg_lock; '
                f'ctx=psg_lock(Path({root!r})); fd=ctx.__enter__(); '
                f'p=subprocess.Popen([sys.executable,"-c",{child_code!r}], '
                f'pass_fds=(fd,{read_fd}),env={{**os.environ,"PSG_LOCK_FD":str(fd)}}); '
                'print(p.pid,flush=True); time.sleep(60)')
            parent = subprocess.Popen([sys.executable, "-c", parent_code], cwd=ROOT,
                                      pass_fds=(read_fd,), stdout=subprocess.PIPE, text=True)
            try:
                child_pid = int(parent.stdout.readline())
                parent.kill()
                parent.wait(timeout=5)
                with self.assertRaisesRegex(RuntimeError, "activo"):
                    with state.psg_lock(directory, blocking=False):
                        pass
                os.write(write_fd, b"x")
                deadline = time.monotonic() + 5
                while True:
                    try:
                        with state.psg_lock(directory, blocking=False):
                            break
                    except RuntimeError:
                        if time.monotonic() > deadline:
                            self.fail("El hijo no liberó el bloqueo")
                        time.sleep(0.02)
            finally:
                if parent.poll() is None:
                    parent.kill()
                    parent.wait()
                parent.stdout.close()
                os.close(read_fd)
                os.close(write_fd)

    def test_replaced_source_symlink_is_not_retired(self):
        with tempfile.TemporaryDirectory() as root:
            source, target = Path(root) / "source", Path(root) / "target"
            source.write_bytes(b"synthetic")
            evidence = state.file_evidence(source)
            os.link(source, target)
            source.unlink()
            source.symlink_to(target)
            with self.assertRaises(RuntimeError):
                state.finish_move(source, target, evidence)
            self.assertTrue(source.is_symlink())
            self.assertEqual(b"synthetic", target.read_bytes())
