class TransformError(Exception):
    """Base de errores de la capa transform."""


class ConfigError(TransformError):
    """Error en carga o validación de configuración."""


class SchemaValidationError(TransformError):
    """Error de validación de esquema de datos."""


class OperationNotFoundError(TransformError):
    """Operación declarativa no registrada en el engine."""


class InputReadError(TransformError):
    """Fallo al leer el dataset de entrada."""


class OutputWriteError(TransformError):
    """Fallo al escribir el dataset de salida."""
