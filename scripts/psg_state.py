"""Primitivas locales PSG: persistencia, exclusión y evidencia de archivos."""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile


def sync_dir(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def save(path, record):
    path = Path(path)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                     prefix=".state-", delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(record, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
            os.replace(temporary, path)
            sync_dir(path.parent)
        finally:
            temporary.unlink(missing_ok=True)


def fingerprint(path):
    path = Path(path)
    if not stat.S_ISREG(path.lstat().st_mode):
        raise RuntimeError("El artefacto PSG no es un archivo regular")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@contextmanager
def psg_lock(staging, blocking=True):
    path = Path(staging) / ".psg-run.lock"
    inherited = os.environ.get("PSG_LOCK_FD")
    if inherited is not None:
        descriptor = os.dup(int(inherited))
        if (os.fstat(descriptor).st_dev, os.fstat(descriptor).st_ino) != (path.stat().st_dev, path.stat().st_ino):
            os.close(descriptor)
            raise RuntimeError("Descriptor de bloqueo PSG incompatible")
    else:
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        except BlockingIOError:
            raise RuntimeError("Ya hay un proceso PSG activo") from None
        yield descriptor
    finally:
        # Cerrar sin LOCK_UN: un hijo superviviente conserva la misma exclusión.
        os.close(descriptor)


def finish_move(source, destination, evidence):
    """Completa enlace/retirada sin reemplazo usando evidencia persistida antes."""
    source, destination = Path(source), Path(destination)
    def matches(path):
        info = path.lstat()
        return stat.S_ISREG(info.st_mode) and [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns] == evidence
    if destination.exists():
        if not matches(destination):
            raise RuntimeError("Destino de recuperación incompatible")
        if os.path.lexists(source) and (not matches(source) or not os.path.samefile(source, destination)):
            raise RuntimeError("Origen y destino de recuperación distintos")
    else:
        if not source.exists() or not matches(source):
            raise RuntimeError("No hay evidencia suficiente para completar el traslado")
        os.link(source, destination, follow_symlinks=False)
    sync_dir(destination.parent)
    if source.exists():
        source.unlink()
        sync_dir(source.parent)
    return destination


def file_evidence(path):
    info = Path(path).lstat()
    if not stat.S_ISREG(info.st_mode):
        raise RuntimeError("Origen de recuperación no regular")
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns]
