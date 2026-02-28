from __future__ import annotations

from pathlib import Path

from psg.main import run


def run_default(dry_run: bool = False) -> Path | None:
    base_dir = Path(__file__).resolve().parents[1]
    config_path = base_dir / "config.yaml"
    input_path = base_dir / "input" / "input.xlsx"
    output_path = base_dir / "output" / "processed.xlsx"
    return run(
        config_path=str(config_path),
        input_path=str(input_path),
        output_path=str(output_path),
        dry_run=dry_run,
    )
