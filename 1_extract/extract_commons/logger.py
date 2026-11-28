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
    
    # Evitar mezclar dos ejecuciones iniciadas en el mismo segundo.
    base = log_file
    suffix = 1
    while True:
        try:
            handler = logging.FileHandler(log_file, mode='x', encoding='utf-8')
            break
        except FileExistsError:
            log_file = base.with_name(f'{base.stem}_{suffix}.log')
            suffix += 1
    resolved_level = getattr(logging, (level_name or "INFO").upper(), logging.INFO)

    logging.basicConfig(
        level=resolved_level,
        format='%(asctime)s $$ %(levelname)s $$ %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8')
        ],
        force=True,
    )
    return log_file
