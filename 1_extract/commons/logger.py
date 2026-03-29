import logging
from pathlib import Path
import datetime

def setup_logger(log_directory: str, flow_name: str = "extract", level_name: str = "INFO"):
    """
    Configura el logger para el proyecto.
    
    Args:
        log_directory: Directorio donde se guardarán los logs.
    """
    log_path = Path(log_directory)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Cada flujo escribe a un archivo dedicado para trazabilidad por ejecución.
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    safe_flow_name = (flow_name or "extract").strip().lower().replace(" ", "_")
    log_file = log_path / f'extract_{safe_flow_name}_{timestamp}.log'
    
    resolved_level = getattr(logging, (level_name or "INFO").upper(), logging.INFO)

    logging.basicConfig(
        level=resolved_level,
        format='%(asctime)s $$ %(levelname)s $$ %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8')
        ],
        force=True,
    )