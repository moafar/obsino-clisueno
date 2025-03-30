from pathlib import Path
import os
import logging
from utils.texto_utils import extraer_texto_docx, extraer_texto_pdf, extraer_texto_rtf, extraer_texto_doc, normalizar_texto, extraer_subcadenas
from utils.examen_utils import determinar_tipos_examenes

def procesar_archivo(archivo: Path) -> None:
    """Lee el contenido de un archivo y retorna el texto extraído o None si hay un error."""
    
    _, extension = os.path.splitext(archivo)
    texto = ""

    try:
        extension = extension.lower()

        if extension == ".docx":
            texto = extraer_texto_docx(archivo)
        elif extension == ".pdf":
            texto = extraer_texto_pdf(archivo)
        elif extension == ".rtf":
            texto = extraer_texto_rtf(archivo)
        elif extension == ".doc":
            texto = extraer_texto_doc(archivo)
        else:
            logging.error(f"Extensión de archivo no soportada: {extension}")
            return None        
        
    except Exception as e:
        logging.error(f"Error inesperado al leer {archivo}: {e}")
        return None

    texto_normalizado = normalizar_texto(texto)  # Normalizar el texto extraído
    
    tipos_examenes = determinar_tipos_examenes(texto_normalizado)  # <-- Llamada a la función para determinar el tipo de examen ***
    if not tipos_examenes:
        logging.warning(f"No se encontraron tipos de examen en el archivo {archivo}.")
        return
    
    cadenas_busqueda = {
        "BASAL": (r"INFORME\s+DE\s+POLISOMNOGRAFIA\s+BASAL", r"CONCLUSION(?:ES)?"),
        "CPAP": (r"INFORME\s+DE\s+POLISOMNOGRAFIA\s+EN\s+TITULACION\s+DE\s+CPAP", r"CONCLUSION(?:ES)?"),
        "DAM": (r"INFORME\s+DE\s+POLISOMNOGRAFIA\s+BASAL\s+CON\s+DISPOSITIVO\s+(?:DE\s+AVANCE\s+)?MANDIBULAR", r"CONCLUSION(?:ES)?"),
        "BPAP": (r"INFORME\s+DE\s+POLISOMNOGRAFIA\s+EN\s+TITULACION\s+DE\s+B[I]?PAP", r"CONCLUSION(?:ES)?"),
        "ACTIGRAFIA": (r"^", r"CONCLUSION(?:ES)?"),
        "CAPNOGRAFIA": (r"INFORME\s+DE\s+CAPNOGRAFIA", r"CONCLUSION(?:ES)?"),
        "AUTOCPAP": (r"INFORME\s+DE\s+TITULACION\s+CON\s+AUTO\s+CPAP", r"CONCLUSION(?:ES)?"),
        "POLIGRAFIA": (r"INFORME\s+POLIGRAFIA\s+RESPIRATORIA", r"GRAFICOS")
    }

    for tipo in tipos_examenes:
        logging.info(f"Procesando examen de {tipo}")
        if tipo in cadenas_busqueda:
            inicio, fin = cadenas_busqueda[tipo]
            texto_relevante = extraer_subcadenas(texto_normalizado, inicio, fin) # <-- Llamada a la función para extraer subcadenas ***
            if texto_relevante:
                logging.info(f"Subcadena encontradas para {tipo}")
                # procesar_examen(tipo, texto_relevante)
                # TODO(Dev): Implementar las funciones para procesar el examen
            else:
                logging.error(f"No se encontraron subcadenas para {tipo} en el archivo {archivo}.")