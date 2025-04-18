import logging
from utils.texto_utils import extraer_regex

def procesar_actigrafia_doc(texto_relevante: str):
    logging.info("Procesando examen ACTIGRAFIA")
    logging.debug(f"Texto relevante: {texto_relevante}")
    datos = {}

    campos = [
        ("nombre_paciente", r"Nombre\s*:\s*\*{0,2}([A-ZÑÁÉÍÓÚÜ\s]+?)\s*(?=\*{2}|TI\s*[:]|ID\s*[:]|CC\s*[:])"),
        ("id_paciente", r"[ID|TI]:\s*(\d+)"),
        ("edad_paciente", r"Edad\s*:\s*(\d+)\s*anos\b"),
        ("fecha_proced", r":\s*(\d{1,2}\s+(?:de\s+)?[A-Za-z]+\s+\d{4})(?=\s+Informacion\s+de\s+paciente)"),
        ("latencia_prom", r"Estadisticas\s+de\s+resumen(?:.|\n)*?promedio\s+\d{1,2}:\d{2}:\d{2}\s+\d{1,2}:\d{2}:\d{2}\s+(?:\d+\s*h\s*\d+min|\d+,\d+\s*h)\s+([\d,]+)")
    ]


    for clave, patron in campos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.warning(f"{clave}: N/A")

    return datos

