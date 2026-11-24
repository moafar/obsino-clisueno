from __future__ import annotations

from pathlib import Path

from psg.main import _discover_input_files, run


def run_default(dry_run: bool = False) -> Path | None:
    base_dir = Path(__file__).resolve().parents[1]
    config_path = base_dir.parents[1] / "0_declarations" / "psg.yaml"
    input_files = _discover_input_files()
    if len(input_files) != 1:
        raise ValueError("run_default requiere un único CSV PSG en staging; usa --input")
    return run(
        config_path=str(config_path),
        input_path=str(input_files[0]),
        output_path=None,
        dry_run=dry_run,
    )
