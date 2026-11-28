"""Orquestación y reanudación explícita PSG mediante las CLI de cada capa."""
from __future__ import annotations

import argparse
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.psg_state import save, psg_lock, fingerprint, sync_dir

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "staging"
CONTRACT = ROOT / "0_declarations/psg.yaml"


def now():
    return datetime.now(timezone.utc).isoformat()




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


def run(source: Path | None = None, archive: Path | None = None, mount: Path | None = None,
        table_id: str | None = None, resume_id: str | None = None) -> Path:
    staging = STAGING.resolve(strict=True)
    with psg_lock(staging, blocking=False) as descriptor:
        if resume_id:
            if not re.fullmatch(r"[A-Za-z0-9_-]+", resume_id):
                raise ValueError("Identificador de ejecución inválido")
            folder = staging / "psg_runs" / resume_id
            state_path = folder / "run.json"
            record = json.loads(state_path.read_text())
            if record.get("recovery_blocked"):
                raise RuntimeError("Reanudación bloqueada por una inconsistencia previamente confirmada")
            if record["id"] != resume_id:
                raise RuntimeError("Identidad de ejecución inconsistente")
            source, archive, mount = (Path(record["paths"][key]) for key in ("source", "archive", "mount"))
            table_id = record["destination"].split(".")[-1]
            execution = resume_id
            csv = staging / f"extract_psg_{execution}.csv"
            parquet = csv.with_name(csv.stem + "_transformed.parquet")
            if record["paths"]["csv"] != str(csv) or record["paths"]["parquet"] != str(parquet):
                raise RuntimeError("Rutas de ejecución inconsistentes")
            record["resume_count"] = record.get("resume_count", 0) + 1
            record.update(state="RUNNING", error=None)
        else:
            if not all((source, archive, mount, table_id)):
                raise ValueError("Una ejecución nueva requiere input, archive-dest, mount y table-id")
            source, archive, mount = (p.resolve() for p in (source, archive, mount))
            execution = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "_" + uuid4().hex
            folder = staging / "psg_runs" / execution
            folder.mkdir(parents=True, exist_ok=False)
            sync_dir(folder.parent)
            sync_dir(staging)
            state_path = folder / "run.json"
            csv = staging / f"extract_psg_{execution}.csv"
            parquet = csv.with_name(csv.stem + "_transformed.parquet")
            record = {"id": execution, "state": "RUNNING", "started_at": now(),
                      "paths": {"source": str(source), "archive": str(archive), "mount": str(mount),
                                "csv": str(csv), "parquet": str(parquet)},
                      "digests": {}, "stages": {}, "error": None}
        record["paths"]["load_state"] = str(parquet.with_suffix(".load-state.json"))
        started = time.perf_counter()
        save(state_path, record)

        def stage(name, command, result_path=None, validate=None):
            previous = record["stages"].get(name)
            if previous and previous["state"] == "OK":
                try:
                    validate(previous["result"])
                except Exception as error:
                    previous.update(state="ERROR", error=type(error).__name__)
                    record["recovery_blocked"] = {"stage": name, "error": type(error).__name__}
                    save(state_path, record)
                    raise
                return previous["result"]
            attempt = (previous or {}).get("attempt", 0) + 1
            entry = {"state": "RUNNING", "started_at": now(), "attempt": attempt,
                     "log": str(folder / f"{name}.{attempt}.log")}
            record["stages"][name] = entry
            save(state_path, record)
            tick = time.perf_counter()
            try:
                cached = result_path and result_path.exists()
                if cached and previous and name == "extract_audit":
                    cached = json.loads(result_path.read_text())["audit_state"] in ("OK", "ADVERTENCIA")
                if not cached:
                    if previous and name == "load" and not parquet.with_suffix(".load-state.json").is_file():
                        raise RuntimeError("No existe el journal de la carga interrumpida; requiere revisión")
                    if previous and name == "extract_audit":
                        command = [*command, "--resume-extraction"]
                    if previous and name == "transform":
                        command = [*command, "--recover-publication"]
                    with Path(entry["log"]).open("xb") as log:
                        subprocess.run([sys.executable, *map(str, command)], cwd=ROOT,
                                       stdin=subprocess.DEVNULL, stdout=log,
                                       stderr=subprocess.STDOUT, check=True,
                                       pass_fds=(descriptor,),
                                       env={**os.environ, "PSG_LOCK_FD": str(descriptor)})
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
            destination = f"{config['project_id']}.{config['dataset_id']}.{table_id}"
            if resume_id and record["destination"] != destination:
                raise RuntimeError("El contrato ha cambiado de destino")
            record["destination"] = destination
            preflight(source, archive, mount, staging, ROOT / config["service_account_json"])
            logs = ROOT / "logs"
            logs.mkdir(exist_ok=True)
            with tempfile.TemporaryFile(dir=logs):
                pass
            def verify_artifact(key, path):
                actual = fingerprint(path)
                expected = record.setdefault("digests", {}).get(key)
                if expected is not None and actual != expected:
                    raise RuntimeError("El artefacto ha cambiado desde su confirmación")
                if resume_id and record["stages"].get(key, {}).get("state") == "OK" and expected is None:
                    raise RuntimeError("Registro anterior sin huella de artefacto; requiere revisión")
                record["digests"][key] = actual

            def validate_extraction(result):
                record["audit"] = {"state": result["audit_state"], "report": result.get("audit")}
                if result["audit_state"] not in ("OK", "ADVERTENCIA") or result["csv"] != str(csv):
                    raise RuntimeError("Extracción/auditoría no conciliada")
                rows = result["counts"]["archivos_registrados"]
                if rows and not csv.is_file():
                    raise RuntimeError("No existe el CSV declarado por extracción")
                if rows:
                    verify_artifact("extract_audit", csv)
                record.setdefault("counts", {})["extracted"] = rows

            def validate_transform(_result):
                actual = parquet
                if not actual.exists():
                    state = json.loads(parquet.with_suffix(".load-state.json").read_text())
                    if state["state"] not in ("CONFIRMED", "LOADED"):
                        raise RuntimeError("Parquet ausente sin carga confirmada")
                    actual = Path(state["loaded"])
                transformed = pq.read_metadata(actual).num_rows
                verify_artifact("transform", actual)
                if transformed != record["counts"]["extracted"]:
                    raise RuntimeError("No concilian extracción y transformación")
                record["counts"]["transformed"] = transformed

            def validate_load(result):
                expected_loaded = parquet.with_name(parquet.stem + "_loaded.parquet")
                if Path(result["loaded"]) != expected_loaded:
                    raise RuntimeError("Ruta del artefacto cargado inconsistente")
                if (result["counts"]["received"] != record["counts"]["transformed"]
                        or not Path(result["loaded"]).is_file()):
                    raise RuntimeError("Carga no conciliada con el artefacto local")
                verify_artifact("load", Path(result["loaded"]))
                if record["digests"]["load"] != record["digests"]["transform"]:
                    raise RuntimeError("El artefacto cargado no coincide con el transformado")

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
    parser.add_argument("--input", type=Path)
    parser.add_argument("--archive-dest", type=Path)
    parser.add_argument("--mount", type=Path, help="Montaje documental real, por ejemplo /mnt/e")
    parser.add_argument("--table-id", help="Tabla canónica de destino explícita")
    parser.add_argument("--resume", help="Identificador de ejecución a reanudar")
    args = parser.parse_args()
    if args.resume and any((args.input, args.archive_dest, args.mount, args.table_id)):
        parser.error("--resume reutiliza las rutas y el destino registrados")
    try:
        run(args.input, args.archive_dest, args.mount, args.table_id, resume_id=args.resume)
        return 0
    except (Exception, KeyboardInterrupt) as error:
        print(f"Orquestación PSG detenida: {type(error).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
