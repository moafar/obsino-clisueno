import logging
from utils.texto_utils import extraer_regex

def procesar_capnografia_doc(texto_relevante: str):
    #print(texto_relevante)
    logging.info("Procesando examen CAPNOGRAFIA DOC")
    datos = {}

    campos = [
        ("nombre_paciente", r"Nombre(?: del paciente)?:?\s*[|]?\s*([\wÁÉÍÓÚÑáéíóúñ-]+(?:\s+[\wÁÉÍÓÚÑáéíóúñ-]+)*)(?=\s*[|]?\s*Edad\b)"),
        ("edad_paciente", r"Edad\s*[:|]?\s*([\d]+(?:[.,]\d+)?)\s*(años|anos)?"),
        ("id_paciente", r"Id\s*[:|]?\s*(\d{4,10})"),
        ("peso_paciente", r"Peso\s*[:|]?\s*(?:\([kK]g\))?\s*([\d]+(?:[.,]\d+)?)"),
        ("talla_paciente", r"Talla\s*[:|]?\s*(?:\([mM]\))?\s*([\d]+(?:[.,]\d+)?)"),
        ("imc_paciente", r"IMC\s*[:|]?\s*([\d]+(?:[.,]\d+)?)"),
        ("cuello_paciente", r"Cuello\s*[:|]?\s*([\d]+(?:[.,][0-9]+)?)\s*(?:cm)?"),
        ("perimetro_abdominal", r"perimetro abdominal[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*cm"),
        ("md_solicita", r"Solicita\s*[:|]?\s*(.*?)\s+Empresa"),
        ("eps_paciente", r"Empresa\s*[:|]?\s*(.*?)\s*Fecha"),
        ("fecha_proced", r"Fecha\s*[:|]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})(?=\s*DATOS)"),
        ("media_etco2_nrem", r"Durante NREM:\s*\d+(?:[,.]\d+)?\s*Durante NREM:\s*(\d+[,.]\d+)"),
        ("media_etco2_rem", r"Durante REM:\s*\d+(?:[,.]\d+)?\s*Durante REM:\s*(\d+[,.]\d+)"),
        ("nivel_max_etco2", r'nivel mas alto de EtCO2 durante el sueno fue de (\d+)')
    ]

    for clave, patron in campos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.warning(f"{clave}: N/A")

    #print(list(datos.keys())[-1],":",datos[list(datos.keys())[-1]])
    #print(datos)
    return datos

def procesar_capnografia_rtf(texto_relevante: str):
    #print(texto_relevante)
    logging.info("Procesando examen CAPNOGRAFIA RTF")
    datos = {}

    campos = [
        ("nombre_paciente", r"Nombre(?: del paciente)?:\|([^|]+)\|Edad"),
        ("edad_paciente", r"\|Edad\|\s*(\d{1,2})\s*anos?\b"),
        ("id_paciente", r"(?:Id|Identificacion):\|(\d{4,11})\|"),
        ("peso_paciente", r"Peso:\s*\(?\s*(\d{2,3})\s*(?:Kg|kg)\s*\)?"),
        ("talla_paciente", r"Talla:\s*[|]?\s*\(?\s*(\d{1,3}(?:\.\d{1,2})?)\s*(?:cm|CM|m|mts?)\s*\)?\s*[|]?"),
        ("imc_paciente", r"IMC\s*[|:]\s*(\d{2,3}(?:[.,]\d{1,2})?)\s*[|]?"),
        ("cuello_paciente", r"Cuello:?\s*[|]?\s*\(?\s*(\d{2,3})\s*(?:cm|CM)\s*\)?\s*[|]?"),
        ("perimetro_abdominal", r"Perimetro\s+Abdominal:?\s*[|]?\s*\(?\s*(\d{2,3})\s*(?:cm|CM)\s*\)?\s*[|]?"),
        ("md_solicita", r"Solicita:\s*[|]?(.*?)\|Empresa"),
        ("eps_paciente", r"Empresa:\s*\|([^|]+)\|Fecha(?: del estudio)?"),
        ("fecha_proced", r"Fecha:\s*\|(\d{4}/\d{2}/\d{2}|\d{1,2}/\d{1,2}/\d{4})\|"),
        ("media_etco2_rem", r"EtCO2\s+(?:promedio|medio)\s+en\s+sueno\s+REM:\s*(\d{1,2})\s+y\s+NREM:\s*(\d{1,2})"),
        ("media_etco2_nrem", r"EtCO2\s+promedio\s+en\s+sueno\s+REM:\s*\d{1,2}\s+y\s+NREM:\s*(\d{1,2})"),
        ("nivel_max_etco2", r"EtCO2\s+mas\s+alta\s+durante\s+TC:\s*(\d{1,2})"),
        
    ]

    for clave, patron in campos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.warning(f"{clave}: N/A")

    #print(list(datos.keys())[-1],":",datos[list(datos.keys())[-1]])
    #print(datos)
    return datos
