from __future__ import annotations

from pathlib import Path
from typing import Mapping


def resolve_existing_path(path_value: str, search_bases: list[Path]) -> Path:
    candidate = Path(path_value).expanduser()
    if candidate.is_absolute():
        return candidate

    for base in search_bases:
        resolved = (base / candidate).resolve()
        if resolved.exists():
            return resolved

    return (search_bases[0] / candidate).resolve()


def resolve_output_path(path_value: str, search_bases: list[Path]) -> Path:
    candidate = Path(path_value).expanduser()
    if candidate.is_absolute():
        return candidate

    for base in search_bases:
        resolved = (base / candidate).resolve()
        if resolved.parent.exists():
            return resolved

    return (search_bases[0] / candidate).resolve()


def output_extension_from_config(pipeline_config: Mapping[str, object]) -> str:
    output_config = pipeline_config.get("output", {})
    if not isinstance(output_config, Mapping):
        return ".xlsx"

    configured_format = str(output_config.get("format", "")).strip().lower()
    if configured_format == "xlsx":
        return ".xlsx"
    if configured_format == "csv":
        return ".csv"
    return ".xlsx"


def build_default_output_path(
    input_path: Path,
    pipeline_output_dir: Path,
    pipeline_config: Mapping[str, object],
    suffix: str = "_transformed",
) -> Path:
    extension = output_extension_from_config(pipeline_config)
    file_name = f"{input_path.stem}{suffix}{extension}"
    return (pipeline_output_dir / file_name).resolve()
