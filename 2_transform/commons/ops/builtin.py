from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd


def _normalize_numeric_series(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip()
    text = text.str.replace(",", ".", regex=False)
    text = text.replace({"": pd.NA, "N/A": pd.NA, "n/a": pd.NA, "NA": pd.NA, "nan": pd.NA})
    return text


def _op_rename_columns(dataframe: pd.DataFrame, mappings: dict[str, str], **_: Any) -> pd.DataFrame:
    return dataframe.rename(columns=mappings)


def _op_cast_types(dataframe: pd.DataFrame, dtypes: dict[str, str], **_: Any) -> pd.DataFrame:
    result = dataframe.copy()
    for column, target_type in dtypes.items():
        if column not in result.columns:
            continue

        normalized = str(target_type).strip().lower()
        if normalized in {"string", "str"}:
            result[column] = result[column].astype("string")
        elif normalized in {"int", "int64", "integer"}:
            result[column] = pd.to_numeric(
                _normalize_numeric_series(result[column]), errors="coerce"
            ).astype("Int64")
        elif normalized in {"float", "float64", "number", "numeric"}:
            result[column] = pd.to_numeric(
                _normalize_numeric_series(result[column]), errors="coerce"
            )
        elif normalized in {"datetime", "datetime64", "date"}:
            result[column] = pd.to_datetime(
                result[column],
                errors="coerce",
                dayfirst=True,
                format="mixed",
            )
        elif normalized in {"bool", "boolean"}:
            result[column] = result[column].astype("boolean")
    return result


def _parse_ternary(expression: str) -> tuple[str, str, str] | None:
    match = re.match(
        r"^\s*(?P<cond>.+?)\s*\?\s*(?P<true>.+?)\s*:\s*(?P<false>.+?)\s*$",
        expression,
    )
    if not match:
        return None
    return match.group("cond"), match.group("true"), match.group("false")


def _strip_quotes(raw: str) -> str:
    value = raw.strip()
    if (value.startswith("'") and value.endswith("'")) or (
        value.startswith('"') and value.endswith('"')
    ):
        return value[1:-1]
    return value


def _op_derive_columns(dataframe: pd.DataFrame, expressions: dict[str, str], **_: Any) -> pd.DataFrame:
    result = dataframe.copy()

    for new_column, expression in expressions.items():
        ternary = _parse_ternary(expression)
        if ternary:
            condition_expr, true_value_raw, false_value_raw = ternary
            mask = result.eval(condition_expr)
            true_value = _strip_quotes(true_value_raw)
            false_value = _strip_quotes(false_value_raw)
            result[new_column] = np.where(mask, true_value, false_value)
            continue

        result[new_column] = result.eval(expression)

    return result


def _op_select_columns(dataframe: pd.DataFrame, columns: list[str], **_: Any) -> pd.DataFrame:
    return dataframe.loc[:, columns].copy()


def _op_filter_rows(dataframe: pd.DataFrame, query: str, **_: Any) -> pd.DataFrame:
    return dataframe.query(query).copy()


def _op_drop_duplicates(
    dataframe: pd.DataFrame,
    subset: list[str] | None = None,
    keep: str = "first",
    **_: Any,
) -> pd.DataFrame:
    return dataframe.drop_duplicates(subset=subset, keep=keep).copy()


def _op_sort(dataframe: pd.DataFrame, by: list[str], ascending: bool = True, **_: Any) -> pd.DataFrame:
    return dataframe.sort_values(by=by, ascending=ascending).copy()


def register_builtin_operations(registry) -> None:
    """Registra operaciones base del motor declarativo."""
    registry.register("rename_columns", _op_rename_columns)
    registry.register("cast_types", _op_cast_types)
    registry.register("derive_columns", _op_derive_columns)
    registry.register("select_columns", _op_select_columns)
    registry.register("filter_rows", _op_filter_rows)
    registry.register("drop_duplicates", _op_drop_duplicates)
    registry.register("sort", _op_sort)
