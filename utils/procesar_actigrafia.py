import logging
from utils.texto_utils import extraer_regex

def procesar_actigrafia_doc(texto_relevante: str):
    logging.info("Procesando examen ACTIGRAFIA")
    datos = {}

    campos = [
        ("nombre_paciente", r"Nombre\s*:\s*\*{0,2}([A-ZÑÁÉÍÓÚÜ\s]+?)\s*(?=\*{2}|TI\s*:)"),
        ("edad_paciente", r"Edad\s*:\s*(\d+)\s*anos\b"),
        ("id_paciente", r"TI:\s*(\d+)"),
        ("fecha_proced", r"Fecha:\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})"),
        ("iah", r"(?i)AOS\b[^(]*\(IAH\s*([\d]+[.,]?\d*)\s*(?:\/h|\/hora|\/ hora)?\)"),
        ("fecha_inicio_grabacion", r"Periodo de grabaci[óo]n:\s*de\s*(\d{1,2}/\d{2}/\d{4})"),
        ("fecha_fin_grabacion", r"Periodo de grabaci[óo]n:\s*de\s*\d{1,2}/\d{2}/\d{4}\s*a\s*(\d{1,2}/\d{2}/\d{4})"),
        ("hora_acostarse_prom", r"promedio\s+(\d{1,2}:\d{2}:\d{2})"),
        ("hora_levantarse_prom", r"promedio\s+\d{1,2}:\d{2}:\d{2}\s+(\d{1,2}:\d{2}:\d{2})"),
        ("tiempo_sueno", r"promedio\s+(?:\d{1,2}:){2}\d{2}\s+(?:\d{1,2}:){2}\d{2}\s+([\d,]+)"),
        ("latencia_prom", r"promedio\s+(?:\d{1,2}:){2}\d{2}\s+(?:\d{1,2}:){2}\d{2}\s+[\d,]+\s+([\d,]+)"),
        ("dtis", r"promedio\s+(?:\S+\s+){4}(\d{1,2}:\d{2})"),
        ("porcentaje_dtis", r"promedio\s+(?:\S+\s+){5}([\d,]+)")
    ]


    for clave, patron in campos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.warning(f"{clave}: N/A")

    #print(texto_relevante)
    #print(datos["iah"])
    return datos

