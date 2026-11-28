"""Observa la ruta de archivado PSG en un temporal sintético."""

import argparse
import errno
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from e01_perfil_extractor import archivo_utils


def observe(base):
    events = []
    with tempfile.TemporaryDirectory(prefix="e03-archive-", dir=base) as folder:
        root = Path(folder)
        source = root / "source"
        archive = root / "archive"
        source.mkdir()
        archive.mkdir()
        first = source / "synthetic.doc"
        first.write_bytes(b"synthetic-first")
        original_rename = archivo_utils._rename_noreplace
        original_link = archivo_utils.os.link
        original_unlink = archivo_utils.os.unlink

        def rename(*args, **kwargs):
            try:
                result = original_rename(*args, **kwargs)
                events.append("renameat2_ok")
                return result
            except OSError as error:
                events.append(f"renameat2_errno_{error.errno}")
                raise

        def link(*args, **kwargs):
            result = original_link(*args, **kwargs)
            events.append("link_ok")
            return result

        def unlink(*args, **kwargs):
            result = original_unlink(*args, **kwargs)
            events.append("unlink_ok")
            return result

        with patch.object(archivo_utils, "_rename_noreplace", rename), \
             patch.object(archivo_utils.os, "link", link), \
             patch.object(archivo_utils.os, "unlink", unlink):
            target = archivo_utils._move_psg_file(first, "bs", "01/02/2026", archive)
        first_ok = not first.exists() and target.read_bytes() == b"synthetic-first"
        second = source / "synthetic.doc"
        second.write_bytes(b"synthetic-different")
        with patch.object(archivo_utils, "_rename_noreplace", rename), \
             patch.object(archivo_utils.os, "link", link):
            try:
                archivo_utils._move_psg_file(second, "bs", "01/02/2026", archive)
                collision_errno = None
            except OSError as error:
                collision_errno = error.errno
        collision_safe = (second.read_bytes() == b"synthetic-different" and
                          target.read_bytes() == b"synthetic-first")
        interrupted = source / "interrupt.doc"
        interrupted.write_bytes(b"synthetic-interrupted")
        original_unlink = archivo_utils.os.unlink

        def unsupported(*_args, **_kwargs):
            raise OSError(errno.EINVAL, "fallback sintético")

        def stop_before_unlink(path, *args, **kwargs):
            if Path(path) == interrupted:
                raise PermissionError(errno.EACCES, "interrupción sintética")
            return original_unlink(path, *args, **kwargs)

        with patch.object(archivo_utils, "_rename_noreplace", unsupported), \
             patch.object(archivo_utils.os, "unlink", stop_before_unlink):
            try:
                archivo_utils._move_psg_file(interrupted, "bs", "01/02/2026", archive)
                interrupted_error = False
            except PermissionError:
                interrupted_error = True
        interrupted_target = archive / "2026/2026-02/bs_interrupt.doc"
        two_names_one_file = (interrupted.exists() and interrupted_target.exists() and
                              interrupted.samefile(interrupted_target))
        with patch.object(archivo_utils, "_rename_noreplace", unsupported):
            archivo_utils._move_psg_file(interrupted, "bs", "01/02/2026", archive,
                                         allow_complete_link=True)
        recovered = (not interrupted.exists() and
                     interrupted_target.read_bytes() == b"synthetic-interrupted")
        return {"events": events, "first_move_ok": first_ok,
                "collision_errno": collision_errno,
                "collision_safe": collision_safe,
                "collision_is_eexist": collision_errno == errno.EEXIST,
                "interrupted_error": interrupted_error,
                "two_names_one_file": two_names_one_file,
                "retry_recovered": recovered}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--temp-base", type=Path, required=True)
    options = parser.parse_args()
    result = observe(options.temp_base)
    print(json.dumps(result, sort_keys=True))
    if not all((result["first_move_ok"], result["collision_safe"],
                result["collision_is_eexist"], result["interrupted_error"],
                result["two_names_one_file"], result["retry_recovered"])):
        raise SystemExit(1)
