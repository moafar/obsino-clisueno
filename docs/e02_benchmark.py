"""Benchmark E02 con corpus sintético idéntico sobre ext4 y DrvFs/NTFS.

La generación de DOC usa LibreOffice solo antes de medir. Todos los documentos
y resultados intermedios viven en temporales; el JSON final carece de datos
personales y rutas de la muestra.
"""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from e01_perfil_extractor import ROOT, as_rtf, synthetic_report


def generate_corpus(root, maximum, include_doc):
    rtf_dir = root / "master_rtf"
    rtf_dir.mkdir()
    doc_source = root / "doc_source"
    if include_doc:
        doc_source.mkdir()
    for number in range(maximum):
        name = f"synthetic_{number:04d}"
        token = f"{number + 1:06d}"
        (rtf_dir / (name + ".rtf")).write_bytes(
            as_rtf(synthetic_report("rtf").replace("000123", token)))
        if include_doc:
            # El control RTF \tab conserva los tabuladores que usa el parser DOC.
            source = as_rtf(synthetic_report("doc").replace("000123", token))
            (doc_source / (name + ".rtf")).write_bytes(source.replace(b"\t", b"\\tab "))
    if include_doc:
        doc_dir = root / "master_doc"
        doc_dir.mkdir()
        profile = root / "lo_profile"
        command = ["libreoffice", f"-env:UserInstallation={profile.as_uri()}",
                   "--headless", "--convert-to", "doc:MS Word 97",
                   "--outdir", str(doc_dir)]
        command += [str(path) for path in sorted(doc_source.glob("*.rtf"))]
        result = subprocess.run(command, capture_output=True, text=True, timeout=180)
        if result.returncode or len(list(doc_dir.glob("*.doc"))) != maximum:
            raise RuntimeError(f"Conversión DOC fallida: rc={result.returncode}; "
                               f"salida={result.stdout[-300:]!r}; error={result.stderr[-300:]!r}")
    return {"rtf": rtf_dir, **({"doc": root / "master_doc"} if include_doc else {})}


def subset(root, source, count, kind):
    target = root / f"{kind}_{count}"
    target.mkdir()
    for path in sorted(source.iterdir())[:count]:
        shutil.copyfile(path, target / path.name)
    return target


def corpus_digest(folder):
    digest = hashlib.sha256()
    for path in sorted(folder.iterdir()):
        digest.update(path.name.encode("ascii"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def benchmark(fixture, base, count):
    command = [sys.executable, str(ROOT / "docs/e01_perfil_extractor.py"),
               "--count", str(count), "--fixture-dir", str(fixture),
               "--temp-base", str(base)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=300,
                            cwd=ROOT)
    if result.returncode:
        raise RuntimeError(f"Medición fallida: rc={result.returncode}; "
                           f"salida={result.stdout[-500:]!r}; error={result.stderr[-500:]!r}")
    return json.loads(result.stdout)


def run(args):
    with tempfile.TemporaryDirectory(prefix="e02-corpus-", dir="/tmp") as folder:
        root = Path(folder)
        master = generate_corpus(root, 1 if args.probe_doc else max(args.sizes), args.doc)
        if args.probe_doc:
            fixture = subset(root, master["doc"], 1, "doc_probe")
            trial = benchmark(fixture, Path("/tmp"), 1)
            return {"probe_doc": trial}
        fixtures = {(kind, count): subset(root, source, count, kind)
                    for kind, source in master.items() for count in args.sizes}
        digests = {f"{kind}_{count}": corpus_digest(folder)
                   for (kind, count), folder in fixtures.items()}
        trials = []
        bases = {"ext4": Path("/tmp"), "ntfs_drvfs": args.ntfs_base}
        for kind in master:
            for count in args.sizes:
                fixture = fixtures[(kind, count)]
                for repeat in range(args.repeats):
                    # Alternar orden para reducir el sesgo de caché y carga.
                    environments = list(bases.items())
                    if repeat % 2:
                        environments.reverse()
                    for environment, base in environments:
                        trial = benchmark(fixture, base, count)
                        trials.append({"environment": environment, "repeat": repeat + 1,
                                       **trial})
        for kind in master:
            for count in args.sizes:
                same = [trial for trial in trials if trial["format"] == kind and trial["count"] == count]
                if (len({trial["row_digest"] for trial in same}) != 1 or
                        len({trial["archive_digest"] for trial in same}) != 1 or
                        any(trial["csv_rows"] != count or trial["archived"] != count or
                            trial["audit_state"] != "OK" for trial in same)):
                    raise RuntimeError(f"Resultados no equivalentes: {kind}/{count}")
        revision = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                           cwd=ROOT, text=True).strip()
        output = {"revision": revision, "sizes": args.sizes, "repeats": args.repeats,
                  "corpus_sha256": digests, "trials": trials}
        args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
        return {"output": str(args.output), "trial_count": len(trials),
                "formats": list(master), "sizes": args.sizes,
                "all_equivalent": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-doc", action="store_true")
    parser.add_argument("--doc", action="store_true")
    parser.add_argument("--ntfs-base", type=Path)
    parser.add_argument("--sizes", type=int, nargs="+", default=[30, 120])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/e02_mediciones.json")
    options = parser.parse_args()
    if options.probe_doc:
        options.doc = True
    if any(size < 1 for size in options.sizes) or options.repeats < 2:
        parser.error("Tamaños positivos y al menos dos repeticiones")
    if not options.probe_doc and (options.ntfs_base is None or not options.ntfs_base.is_dir()):
        parser.error("Se requiere --ntfs-base existente")
    print(json.dumps(run(options), ensure_ascii=False, sort_keys=True))
