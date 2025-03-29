import logging
from pathlib import Path
import datetime

def setup_logger(log_directory: str):
    """
    Configura el logger para el proyecto.
    
    Args:
        log_directory: Directorio donde se guardarán los logs.
    """
    log_path = Path(log_directory)
    log_path.mkdir(parents=True, exist_ok=True)
    
    # Crear un nombre de archivo de log único usando la fecha y hora actual
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    log_file = log_path / f'log_{timestamp}.log'
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file)
        ]
    )