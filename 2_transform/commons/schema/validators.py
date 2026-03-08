from typing import Any, Mapping

from commons.errors import SchemaValidationError

import pandas as pd


def _normalize_text_series(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip()


def _prepare_numeric_series(series: pd.Series) -> pd.Series:
    text = _normalize_text_series(series)
    text = text.str.replace(",", ".", regex=False)
    text = text.replace(
        {
            "": pd.NA,
            "N/A": pd.NA,
            "n/a": pd.NA,
            "NA": pd.NA,
            "nan": pd.NA,
            "null": pd.NA,
            "none": pd.NA,
        }
    )
    # Algunos extractores exportan "vacío" como signos de puntuación sueltos (por ejemplo, ".").
    text = text.where(~text.str.fullmatch(r"[.\-]+", na=False), pd.NA)
    return text


def _normalize_dtype(dtype_name: str) -> str:
    return dtype_name.strip().lower()


def _validate_required_columns(dataframe, required_columns: list[str]) -> None:
    missing = [column for column in required_columns if column not in dataframe.columns]
    if missing:
        raise SchemaValidationError(
            f"Faltan columnas requeridas: {missing}. Disponibles: {list(dataframe.columns)}"
        )


def _is_coercible(series: pd.Series, target_dtype: str) -> bool:
    normalized = _normalize_dtype(target_dtype)

    try:
        if normalized in {"string", "str"}:
            series.astype("string")
            return True

        if normalized in {"int", "int64", "integer"}:
            numeric_series = _prepare_numeric_series(series)
            pd.to_numeric(numeric_series, errors="raise").astype("Int64")
            return True

        if normalized in {"float", "float64", "number", "numeric"}:
            numeric_series = _prepare_numeric_series(series)
            pd.to_numeric(numeric_series, errors="raise")
            return True

        if normalized in {"datetime", "datetime64", "date"}:
            datetime_series = _normalize_text_series(series)
            datetime_series = datetime_series.replace(
                {"": pd.NA, "N/A": pd.NA, "n/a": pd.NA, "NA": pd.NA, "nan": pd.NA}
            )
            parsed = pd.to_datetime(
                datetime_series,
                errors="coerce",
                dayfirst=True,
                format="mixed",
            )
            invalid_mask = datetime_series.notna() & parsed.isna()
            if invalid_mask.any():
                return False
            return True

        if normalized in {"bool", "boolean"}:
            series.astype("boolean")
            return True
    except Exception:  # noqa: BLE001
        return False

    return False


def _validate_dtypes(dataframe, dtypes: Mapping[str, str]) -> None:
    for column, dtype_name in dtypes.items():
        if column not in dataframe.columns:
            continue
        if not _is_coercible(dataframe[column], dtype_name):
            sample_value = dataframe[column].dropna().astype("string").head(1)
            sample_suffix = ""
            if not sample_value.empty:
                sample_suffix = f" Valor de muestra: {sample_value.iloc[0]!r}."
            raise SchemaValidationError(
                f"La columna '{column}' no puede convertirse a tipo '{dtype_name}'.{sample_suffix}"
            )


def _resolve_schema_config(schema_config: Mapping[str, Any]) -> tuple[list[str], dict[str, str]]:
    columns_map = schema_config.get("columns")
    if isinstance(columns_map, Mapping):
        dtypes = {str(column): str(dtype_name) for column, dtype_name in columns_map.items()}
        required_columns = list(dtypes.keys())
        return required_columns, dtypes

    required_columns = list(schema_config.get("required_columns", []))
    dtypes = {str(column): str(dtype_name) for column, dtype_name in (schema_config.get("dtypes", {}) or {}).items()}
    return required_columns, dtypes


def validate_input_schema(dataframe, schema_config: Mapping[str, Any]) -> None:
    """Valida el esquema de entrada según configuración declarativa."""
    required_columns, dtypes = _resolve_schema_config(schema_config)

    _validate_required_columns(dataframe, required_columns)
    _validate_dtypes(dataframe, dtypes)


def validate_output_schema(dataframe, schema_config: Mapping[str, Any]) -> None:
    """Valida el esquema de salida según configuración declarativa."""
    required_columns, dtypes = _resolve_schema_config(schema_config)

    _validate_required_columns(dataframe, required_columns)
    _validate_dtypes(dataframe, dtypes)
