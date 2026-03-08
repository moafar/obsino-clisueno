import logging
from datetime import datetime
from pathlib import Path


_FILE_HANDLER: logging.Handler | None = None
_FLOW_NAME = "transform"


def configure_flow_logging(flow_name: str) -> None:
    """Configura el nombre de flow para el archivo de log compartido."""
    global _FLOW_NAME, _FILE_HANDLER

    normalized_flow = (flow_name or "transform").strip().lower().replace(" ", "_")
    if normalized_flow == _FLOW_NAME:
        return

    _FLOW_NAME = normalized_flow
    if _FILE_HANDLER is not None:
        _FILE_HANDLER.close()
        _FILE_HANDLER = None


def _get_shared_file_handler() -> logging.Handler:
    global _FILE_HANDLER
    if _FILE_HANDLER is not None:
        return _FILE_HANDLER

    project_root = Path(__file__).resolve().parents[3]
    logs_dir = project_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    file_path = logs_dir / f"transform_{_FLOW_NAME}_{timestamp}.log"
    file_handler = logging.FileHandler(file_path, encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    _FILE_HANDLER = file_handler
    return _FILE_HANDLER


def get_logger(name: str) -> logging.Logger:
    """Retorna un logger estándar para la capa transform."""
    logger = logging.getLogger(name)
    if not any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        )
        logger.addHandler(stream_handler)

    shared_file_handler = _get_shared_file_handler()
    if shared_file_handler not in logger.handlers:
        logger.addHandler(shared_file_handler)

    logger.setLevel(logging.INFO)
    return logger
