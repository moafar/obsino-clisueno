"""Orquestación PSG mediante las CLI de cada capa; sin reanudación automática."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from uuid import uuid4

import pyarrow.parquet as pq
import yaml

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "staging"
CONTRACT = ROOT / "0_declarations/psg.yaml"


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, record):
    """Reemplazo atómico y sincronizado en el mismo directorio."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix=".state-", delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(record, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def preflight(source, archive, mount, staging, credentials):
    for path, access in ((source, os.R_OK | os.W_OK | os.X_OK),
                         (archive, os.R_OK | os.W_OK | os.X_OK),
                         (staging, os.R_OK | os.W_OK | os.X_OK)):
        if not path.is_dir() or not os.access(path, access):
            raise ValueError(f"Directorio operativo no accesible: {path}")
    if not os.path.ismount(mount) or mount == Path("/"):
        raise ValueError("Debe indicar el montaje documental real mediante --mount")
    if not all(path.is_relative_to(mount) for path in (source, archive)):
        raise ValueError("Origen y archivo deben pertenecer al montaje indicado")
    if source.is_relative_to(archive) or archive.is_relative_to(source):
        raise ValueError("Origen y archivo incompatibles")
    if source.stat().st_dev != archive.stat().st_dev:
        raise ValueError("Origen y archivo deben estar en el mismo dispositivo")
    if staging.is_relative_to(source) or staging.is_relative_to(archive) or staging.is_relative_to(mount):
        raise ValueError("Staging debe estar fuera del almacenamiento documental")
    if not credentials.is_file() or not os.access(credentials, os.R_OK):
        raise ValueError("Credencial de carga no disponible o no legible")
    # Verifica escritura efectiva antes de que extracción mueva documentos.
    for directory in (source, archive, staging):
        with tempfile.TemporaryFile(dir=directory) as stream:
            stream.write(b"psg-preflight")
            stream.flush()
            os.fsync(stream.fileno())


def run(source: Path, archive: Path, mount: Path, table_id: str) -> Path:
    staging = STAGING.resolve(strict=True)
    source, archive, mount = (p.resolve() for p in (source, archive, mount))
    with (staging / ".psg-run.lock").open("a+b") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Ya hay un orquestador PSG activo") from None
        execution = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "_" + uuid4().hex
        folder = staging / "psg_runs" / execution
        folder.mkdir(parents=True, exist_ok=False)
        state_path = folder / "run.json"
        csv = staging / f"extract_psg_{execution}.csv"
        parquet = csv.with_name(csv.stem + "_transformed.parquet")
        record = {"id": execution, "state": "RUNNING", "started_at": now(),
                  "paths": {"source": str(source), "archive": str(archive),
                            "csv": str(csv), "parquet": str(parquet)},
                  "stages": {}, "error": None}
        started = time.perf_counter()
        save(state_path, record)

        def stage(name, command, result_path=None, validate=None):
            entry = {"state": "RUNNING", "started_at": now(),
                     "log": str(folder / f"{name}.log")}
            record["stages"][name] = entry
            save(state_path, record)
            tick = time.perf_counter()
            try:
                with Path(entry["log"]).open("xb") as log:
                    subprocess.run([sys.executable, *map(str, command)], cwd=ROOT,
                                   stdin=subprocess.DEVNULL, stdout=log,
                                   stderr=subprocess.STDOUT, check=True)
                result = json.loads(result_path.read_text()) if result_path else {}
                entry["result"] = result
                if validate is not None:
                    validate(result)
                entry["state"] = "OK"
                return result
            except BaseException as error:
                entry.update(state="ERROR", error=type(error).__name__)
                raise
            finally:
                entry.update(finished_at=now(), elapsed_s=time.perf_counter() - tick)
                save(state_path, record)

        try:
            config = yaml.safe_load(CONTRACT.read_text())["load"]
            if not table_id or table_id.lower() == "tbl_psg_legacy_prd":
                raise ValueError("Debe indicar una tabla canónica explícita")
            if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table_id):
                raise ValueError("Tabla no válida")
            record["destination"] = f"{config['project_id']}.{config['dataset_id']}.{table_id}"
            preflight(source, archive, mount, staging, ROOT / config["service_account_json"])
            logs = ROOT / "logs"
            logs.mkdir(exist_ok=True)
            with tempfile.TemporaryFile(dir=logs):
                pass
            def validate_extraction(result):
                record["audit"] = {"state": result["audit_state"], "report": result.get("audit")}
                if result["audit_state"] not in ("OK", "ADVERTENCIA") or result["csv"] != str(csv):
                    raise RuntimeError("Extracción/auditoría no conciliada")
                rows = result["counts"]["archivos_registrados"]
                if rows and not csv.is_file():
                    raise RuntimeError("No existe el CSV declarado por extracción")
                record["counts"] = {"extracted": rows}

            def validate_transform(_result):
                transformed = pq.read_metadata(parquet).num_rows
                if transformed != record["counts"]["extracted"]:
                    raise RuntimeError("No concilian extracción y transformación")
                record["counts"]["transformed"] = transformed

            def validate_load(result):
                if (result["counts"]["received"] != record["counts"]["transformed"]
                        or not Path(result["loaded"]).is_file()):
                    raise RuntimeError("Carga no conciliada con el artefacto local")

            extraction = stage("extract_audit", [ROOT / "1_extract/main.py", "--flow", "psg",
                "--input", source, "--archive-dest", archive, "--output-dir", staging,
                "--output-file", csv.name, "--yes", "--result-json", folder / "extract.json"],
                folder / "extract.json", validate=validate_extraction)
            rows = record["counts"]["extracted"]
            if rows == 0:
                record["state"] = "EMPTY"
                record["stages"].update(transform={"state": "SKIPPED"}, load={"state": "SKIPPED"})
            else:
                stage("transform", [ROOT / "2_transform/main.py", "--flow", "psg",
                      "--input", csv, "--output", parquet, "--yes"], validate=validate_transform)
                loaded = stage("load", [ROOT / "3_load/main.py", "--flow", "psg", "--input", parquet,
                    "--table-id", table_id, "--yes", "--result-json", folder / "load.json"],
                    folder / "load.json", validate=validate_load)
                record["paths"]["loaded"] = loaded["loaded"]
                record["counts"].update(loaded["counts"])
                record["job_id"] = loaded["job_id"]
                record["state"] = "WARNING" if extraction["audit_state"] == "ADVERTENCIA" else "OK"
        except BaseException as error:
            record.update(state="ERROR", error={"type": type(error).__name__, "message": str(error)})
            raise
        finally:
            record.update(finished_at=now(), elapsed_s=time.perf_counter() - started)
            save(state_path, record)
            print(f"PSG {record['state']}: {state_path}", flush=True)
        return state_path


def main():
    parser = argparse.ArgumentParser(description="Ejecutar PSG con auditoría integrada y registro persistente")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--archive-dest", type=Path, required=True)
    parser.add_argument("--mount", type=Path, required=True, help="Montaje documental real, por ejemplo /mnt/e")
    parser.add_argument("--table-id", required=True, help="Tabla canónica de destino explícita")
    args = parser.parse_args()
    try:
        run(args.input, args.archive_dest, args.mount, args.table_id)
        return 0
    except (Exception, KeyboardInterrupt) as error:
        print(f"Orquestación PSG detenida: {type(error).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
