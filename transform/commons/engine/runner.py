from typing import Any, Mapping

from commons.errors import ConfigError


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

    return current
