import logging
from utils.texto_utils import extraer_regex

def procesar_capnografia_doc(texto_relevante: str):
    logging.info("Procesando examen CAPNOGRAFIA DOC")
    datos = {}

    campos = [
        ("nombre_paciente", r"Nombre(?: del paciente)?:?\s*[|]?\s*([\wÁÉÍÓÚÑáéíóúñ-]+(?:\s+[\wÁÉÍÓÚÑáéíóúñ-]+)*)(?=\s*[|]?\s*Edad\b)"),
        ("edad_paciente", r"(?i)Edad\s*[:|]?\s*([\d]+(?:[.,]\d+)?)\s*"),
        ("medida_edad_paciente", r"(?i)(?:Edad\s*[:|]?\s*\d+(?:[.,]\d+)?\s*)([a-záéíóúüñ]+)\b(?:\s*y\s*\d+\s*[a-záéíóúüñ]+)?\s*Id"),
        ("id_paciente", r"Id\s*[:|]?\s*([A-Za-z]?\d{4,10})"),
        ("eps_paciente", r"Empresa\s*[:|]?\s*(.*?)\s*Fecha"),
        ("fecha_proced", r"Fecha\s*[:|]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})(?=\s*DATOS)"),
        ("media_etco2_sueno",r"(?i)durante\s+(?:el\s+)?sueno[^\d]*\d+[^\d]*durante\s+(?:el\s+)?sueno[^\d]*(\d+[,.]\d+)"),
        ("media_etco2_rem", r"Durante REM:\s*\d+(?:[,.]\d+)?\s*Durante REM:\s*(\d+[,.]\d+)"),
        ("media_etco2_nrem", r"Durante NREM:\s*\d+(?:[,.]\d+)?\s*Durante NREM:\s*(\d+[,.]\d+)"),
        ("nivel_max_etco2", r'nivel mas alto de EtCO2 durante el sueno fue de (\d+)')
    ]

    for clave, patron in campos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.warning(f"{clave}: N/A")

    return datos

def procesar_capnografia_rtf(texto_relevante: str):
    logging.info("Procesando examen CAPNOGRAFIA RTF")
    datos = {}

    campos = [
        ("nombre_paciente", r"Nombre(?: del paciente)?:\|([^|]+)\|Edad"),
        ("edad_paciente", r"\|Edad\|\s*(\d{1,2})\s*anos?\b"),
        ("medida_edad_paciente", r"(?i)(?:Edad\|?\s*\d+\s*)(\w+)\|?\s*Id"),
        ("id_paciente", r"Id:\s*\|?\s*([A-Za-z]?\d{6,10})\|?"),
        ("eps_paciente", r"Empresa:\s*\|([^|]+)\|Fecha(?: del estudio)?"),
        ("fecha_proced", r"Fecha:\s*\|(\d{4}/\d{2}/\d{2}|\d{1,2}/\d{1,2}/\d{4})\|"),
        ("media_etco2_sueno",r"Distribucion de EtCO2.*?Media\|[^|]+\|[^|]+\|[^|]+\|(\d+)"),
        ("media_etco2_rem", r"Distribucion de EtCO2.*?Media\|[^|]+\|(\d+)"),
        ("media_etco2_nrem", r"Distribucion de EtCO2.*?Media\|[^|]+\|[^|]+\|(\d+)"),
        ("nivel_max_etco2", r"EtCO2\s+mas\s+alta\s+durante\s+TC:\s*(\d{1,2})"),

    ]

    for clave, patron in campos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.warning(f"{clave}: N/A")

    return datos
