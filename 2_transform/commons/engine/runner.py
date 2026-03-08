from typing import Any, Mapping

from commons.errors import ConfigError
from commons.logging import get_logger


logger = get_logger(__name__)


def _drop_rows_with_duplicated_uuid(dataframe):
    uuid_column = next(
        (column for column in dataframe.columns if str(column).strip().upper() == "UUID"),
        None,
    )
    if uuid_column is None:
        return dataframe

    normalized_uuid = dataframe[uuid_column].astype("string").str.strip()
    has_uuid = normalized_uuid.notna() & (normalized_uuid != "")
    duplicated_after_first = normalized_uuid.duplicated(keep="first")

    # Mantiene la primera ocurrencia por UUID y elimina duplicados reales (no vacíos).
    rows_to_drop = has_uuid & duplicated_after_first
    if not rows_to_drop.any():
        return dataframe

    removed_rows = int(rows_to_drop.sum())
    logger.info(
        "Deduplicacion por UUID aplicada: %s filas eliminadas (keep=first)",
        removed_rows,
    )

    return dataframe.loc[~rows_to_drop].copy()


def run_pipeline(pipeline_config: Mapping[str, Any], registry, dataframe):
    """Ejecuta un pipeline declarativo sobre un dataframe."""
    steps = pipeline_config.get("steps", [])
    if not isinstance(steps, list):
        raise ConfigError("La clave 'steps' del pipeline debe ser una lista.")

    current = dataframe
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            raise ConfigError(f"El step #{index} no es un objeto válido.")

        op_name = step.get("op")
        if not op_name:
            raise ConfigError(f"El step #{index} no define la clave obligatoria 'op'.")

        params = step.get("params", {}) or {}
        operation = registry.get(op_name)
        current = operation(current, **params)

    current = _drop_rows_with_duplicated_uuid(current)
    return current
