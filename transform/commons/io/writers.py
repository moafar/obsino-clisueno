from pathlib import Path
from typing import Any

from commons.errors import OutputWriteError

import pandas as pd


def write_dataset(dataframe, output_path: str, **kwargs: Any) -> Path:
    """Escribe un dataset procesado en disco."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    config = kwargs.get("config", {}) or {}

    try:
        output_format = config.get("format")
        if output_format == "csv" or path.suffix.lower() == ".csv":
            dataframe.to_csv(
                path,
                index=False,
                encoding=config.get("encoding", "utf-8"),
                sep=config.get("sep", ","),
            )
            return path

        if output_format == "xlsx" or path.suffix.lower() in {".xlsx", ".xls"}:
            sheet_name = config.get("sheet_name", "procesado")
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                dataframe.to_excel(writer, index=False, sheet_name=sheet_name)
            return path

        raise OutputWriteError(
            f"Formato no soportado para escritura: {path.suffix or output_format or 'desconocido'}"
        )
    except Exception as exc:  # noqa: BLE001
        raise OutputWriteError(f"Error escribiendo salida en {output_path}: {exc}") from exc
