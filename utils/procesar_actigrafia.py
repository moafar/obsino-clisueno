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
        ("tiempo_total_sueno", r"Promedio\s+\d+:\d+:\d+\s+[ap]\.\s*m\.\s+\d+:\d+:\d+\s+[ap]\.\s*m\.\s+\d+:\d+:\d+\s+(\d+:\d+:\d+)"),
        ("latencia_prom", r"Promedio(?:\s+\d+:\d+:\d+\s*(?:[ap]\.\s*m\.)?\s*){4}(\d+,\d+)")
    ]

    for clave, patron in campos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.warning(f"{clave}: N/A")

    return datos

