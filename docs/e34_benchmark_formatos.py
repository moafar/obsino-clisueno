"""Benchmark PSG sintético; ejecutar desde la raíz con .venv/bin/python docs/e34_benchmark_formatos.py."""
from __future__ import annotations

import argparse
import hashlib
import json
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "0_declarations/psg.yaml"
SIZES = (100, 1000, 10000)
FORMATS = ("xlsx", "csv", "parquet")
REPETITIONS = 3


def typed_frame(size: int, columns: dict[str, str]) -> pd.DataFrame:
    positions = np.arange(size)
    result = {}
    for name, kind in columns.items():
        if kind == "int":
            values = pd.Series(positions % 101, dtype="Int64")
            values.loc[positions % 19 == 0] = pd.NA
        elif kind == "float":
            values = pd.Series((positions % 101) / 4.0, dtype="Float64")
            values.loc[positions % 17 == 0] = pd.NA
        elif kind == "date":
            values = pd.Series(pd.Timestamp("2025-01-01") +
                               pd.to_timedelta(positions % 365, unit="D"))
            values.loc[positions % 23 == 0] = pd.NaT
        elif name == "pte_id":
            values = pd.Series([f"{i:08d}" for i in positions], dtype="string")
            values.loc[positions % 29 == 0] = pd.NA
        elif name == "meta_uuid":
            values = pd.Series([hashlib.md5(f"psg-sintetico-{i}".encode()).hexdigest()
                                for i in positions], dtype="string")
        elif name == "meta_incidencias_calidad":
            payload = json.dumps([{"campo": "pte_edad_anos", "valor_original": "x",
                                   "error": "entero_incompatible", "accion": "convertido_a_null"}],
                                 ensure_ascii=False, separators=(",", ":"))
            values = pd.Series([payload if i % 11 == 0 else pd.NA for i in positions],
                               dtype="string")
        else:
            values = pd.Series([f"sintético_{name}_{i % 7}" for i in positions],
                               dtype="string")
            values.loc[positions % 31 == 0] = pd.NA
        result[name] = values
    return pd.DataFrame(result, columns=list(columns))


def measure(size: int, fmt: str, repetition: int) -> dict:
    columns = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))["schema"]["transform"]["output"]["columns"]
    expected = typed_frame(size, columns)
    dtypes = {name: {"int": "Int64", "float": "Float64", "string": "string"}[kind]
              for name, kind in columns.items() if kind != "date"}
    with tempfile.TemporaryDirectory(prefix="e34-psg-") as folder:
        path = Path(folder) / f"synthetic.{fmt}"
        wall = time.perf_counter()
        cpu = time.process_time()
        if fmt == "xlsx":
            expected.to_excel(path, index=False, engine="openpyxl")
        elif fmt == "csv":
            expected.to_csv(path, index=False, encoding="utf-8")
        else:
            expected.to_parquet(path, index=False, engine="pyarrow", compression="snappy")
        write_wall, write_cpu = time.perf_counter() - wall, time.process_time() - cpu
        size_bytes = path.stat().st_size
        wall = time.perf_counter()
        cpu = time.process_time()
        if fmt == "xlsx":
            actual = pd.read_excel(path, engine="openpyxl", dtype=dtypes)
        elif fmt == "csv":
            actual = pd.read_csv(path, dtype=dtypes, parse_dates=["meta_fecha_estudio"])
        else:
            actual = pd.read_parquet(path, engine="pyarrow")
        read_wall, read_cpu = time.perf_counter() - wall, time.process_time() - cpu
        try:
            pd.testing.assert_frame_equal(expected, actual, check_dtype=True, check_exact=True)
            equivalent, difference = True, None
        except AssertionError as error:
            equivalent, difference = False, str(error).splitlines()[0][:300]
        return {"rows": size, "format": fmt, "repetition": repetition,
                "write_wall_s": round(write_wall, 6), "read_wall_s": round(read_wall, 6),
                "write_cpu_s": round(write_cpu, 6), "read_cpu_s": round(read_cpu, 6),
                "bytes": size_bytes, "peak_rss_mib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2),
                "equivalent": equivalent, "difference": difference,
                "actual_rows": len(actual), "actual_columns": len(actual.columns)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--rows", type=int)
    parser.add_argument("--format", choices=FORMATS)
    parser.add_argument("--repetition", type=int)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/e34_mediciones.json")
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(measure(args.rows, args.format, args.repetition), ensure_ascii=False))
        return
    runs = []
    for size in SIZES:
        for fmt in FORMATS:
            for repetition in range(1, REPETITIONS + 1):
                command = [sys.executable, str(Path(__file__)), "--worker", "--rows", str(size),
                           "--format", fmt, "--repetition", str(repetition)]
                completed = subprocess.run(command, capture_output=True, text=True, check=True)
                run = json.loads(completed.stdout)
                runs.append(run)
                print(f"{size:>5} {fmt:<7} {repetition}: escritura={run['write_wall_s']:.3f}s "
                      f"lectura={run['read_wall_s']:.3f}s equivalencia={run['equivalent']}", flush=True)
    payload = {"contract": "0_declarations/psg.yaml", "versions": {
        "python": sys.version.split()[0], "pandas": pd.__version__,
        "pyarrow": __import__("pyarrow").__version__,
        "openpyxl": __import__("openpyxl").__version__},
        "sample_sizes": SIZES, "repetitions": REPETITIONS, "runs": runs}
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
