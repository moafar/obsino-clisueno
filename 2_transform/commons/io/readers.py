from pathlib import Path
from typing import Any

from commons.errors import InputReadError

import pandas as pd


def read_dataset(input_path: str, **kwargs: Any):
    """Lee un dataset desde archivo (csv/xlsx)."""
    path = Path(input_path)
    if not path.exists():
        raise InputReadError(f"No existe el archivo de entrada: {input_path}")
    config = kwargs.get("config", {}) or {}

    try:
        if path.suffix.lower() == ".csv" or config.get("format") == "csv":
            return pd.read_csv(
                path,
                encoding=config.get("encoding", "utf-8"),
                sep=config.get("sep", ","),
                header=config.get("header", 0),
            )

        if path.suffix.lower() in {".xlsx", ".xls"} or config.get("format") == "xlsx":
            return pd.read_excel(
                path,
                sheet_name=config.get("sheet_name", 0),
                header=config.get("header", 0),
            )

        raise InputReadError(
            f"Formato no soportado para lectura: {path.suffix or 'sin extensión'}"
        )
    except Exception as exc:  # noqa: BLE001
        raise InputReadError(f"Error leyendo archivo de entrada {input_path}: {exc}") from exc
