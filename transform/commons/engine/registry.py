from collections.abc import Callable

from commons.errors import OperationNotFoundError


class OperationRegistry:
    """Registro de operaciones declarativas disponibles."""

    def __init__(self) -> None:
        self._operations: dict[str, Callable] = {}

    def register(self, name: str, operation: Callable) -> None:
        self._operations[name] = operation

    def get(self, name: str) -> Callable:
        if name not in self._operations:
            raise OperationNotFoundError(f"Operación no registrada: {name}")
        return self._operations[name]
