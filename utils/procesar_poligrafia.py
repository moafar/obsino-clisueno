import logging
from utils.texto_utils import extraer_regex

def procesar_poligrafia_docx(texto_relevante: str):
    logging.info("Procesando examen POLIGRAFIA (DOCX)*****************")

    datos = {}
    
    campos = [
        ("fecha_estudio", r"(?i)fecha[^\d]{1,10}(\d{1,2}(?:\/|-)\d{1,2}(?:\/|-)\d{4}|\d{1,2}(?:\s*(?:de|del)?\s*)[a-z]+\s*(?:de|del)?\d{4})\s*informacion"),        
        ("nombre_paciente", r"(?i)Nombre(?: del paciente)?\s*:\s*([^:]+?)\s*Id"),
        ("id_paciente", r"(?i)(?:nombre:.*?)(?:id|cc|ti|ce)\s*:?\s*([a-zA-Z0-9]+)(?=\D*edad)"),
        ("edad_paciente", r"(?i)Edad:\s*(\d+\s*(?:anos|meses|dias))\s*Estudio"),
        ("iah", r"(?i)IAH:\s*([\d]+[.,]?[\d]*)"),
        ("ih", r"(?i)IH:\s*([\d]+[.,]?[\d]*)"),
        ("iac", r"(?i)\s+Obstructiva:\s*([\d]+[.,]?[\d]*)"),
        ("iam", r"(?i)Mixta:\s*([\d]+[.,]?[\d]*)"),
        ("ido", r"(?i)IDO:\s*([\d]+[.,]?[\d]*)"),
        ("meq_90porc_sat", r"(?i)<=90%sat:\s*([\d]+[.,]?[\d]*)")

        
]

    for clave, patron in campos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.warning(f"{clave}: N/A")

    return datos
