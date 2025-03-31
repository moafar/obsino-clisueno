import logging
from utils.texto_utils import extraer_regex

def procesar_cpap(texto_relevante: str):
    # Procesar el texto específico del examen CPAP
    print(f"Procesando examen CPAP con texto: {texto_relevante}")
    
    datos = {}
    
    VARIABLE = extraer_regex(texto_relevante, r"REGEX")
    if VARIABLE:
        logging.info(f"VARIABLE: {VARIABLE}")
        datos["VARIABLE"] = VARIABLE