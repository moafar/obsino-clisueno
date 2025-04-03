import logging
from utils.texto_utils import extraer_regex

def procesar_bpap_doc(texto_relevante: str):
    logging.info("Procesando examen CPAP - formato DOC")
    datos = {}

    campos = [
        ("nombre_paciente", r"Nombre\s*[:|]?\s*([\wÁÉÍÓÚÑáéíóúñ\-]+(?:\s+[\wÁÉÍÓÚÑáéíóúñ\-]+)+)(?=\s+Edad)"),
        ("edad_paciente", r"Edad\s*[:|]?\s*(\d{1,3})\s*(años|anos)?"),
        ("id_paciente", r"Id\s*[:|]?\s*(\d{5,12})"),
        ("peso_paciente", r"Peso\s*[:|]?\s*(\d{2,3}(?:[.,]\d+)?)\s*kg"),
        ("talla_paciente", r"Talla\s*[:|]?\s*(\d{2,3}(?:[.,]\d+)?)\s*cm"),
        ("imc_paciente", r"IMC\s*[:|]?\s*(\d{2}(?:[.,]\d+)?)"),
        ("cuello_paciente", r"Cuello\s*[:|]?\s*(\d{2,3}(?:[.,]\d+)?)\s*cm"),
        ("perimetro_abdominal", r"Perimetro Abdominal\s*[:|]?\s*(\d{2,3}(?:[.,]\d+)?)\s*cm"),
        ("md_solicita", r"Solicita\s*[:|]?\s*(.*?)\s+Empresa"),
        ("eps_paciente", r"Empresa\s*[:|]?\s*(.*?)\s+Fecha"),
        ("fecha_proced", r"Fecha\s*[:|]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4})"),
        ("iah_diagnostico", r"IAH[:\s]*([0-9]+(?:[.,][0-9]+)?)/hr"),
        ("tiempo_de_sueno(eficiencia)", r"Durmio\s+([0-9]+(?:[.,][0-9]+)?)\s+minutos"),
        ("tiempo_en_cama(eficiencia)", r"minutos de(?: los)?\s+([0-9]+(?:[.,][0-9]+)?)\s+(?:minutos\s+)?que permanecio en cama"),
        ("latencia_total", r"latencia de sueno fue[:\s]*([0-9]+(?:[.,][0-9]+)?)\s+minutos"),
        ("latencia_rem", r"latencia de sueno REM fue[:\s]*([0-9]+(?:[.,][0-9]+)?)\s+minutos"),
        ("sueno_rem", r"sueno REM de\s*([0-9]+(?:[.,][0-9]+)?)%"),
        ("sueno_profundo", r"sueno profundo.*?de\s*([0-9]+(?:[.,][0-9]+)?)"),
        ("indice_microalertamientos", r"indice de microalertamientos fue\s*([0-9]+(?:[.,][0-9]+)?)/hora"),
        ("presion_inicial", r"inicio (?:a una|con) presion de\s*([0-9]+(?:/[0-9]+)?)\s*cm\s*(?:de\s*[aA]gua|de\s*H2O|H2O|[aA]gua)\b"),
        ("presion_terapeutica", r"(?i)a una presion de\s+(\d{2}/\d{2})\s*cm\s*(?:de\s*)?(?:agua|H2O)\b"),
        ("so2_prom_sueno", r"saturacion de oxigeno promedio durante el sueno.*?fue de\s*([0-9]+(?:[.,][0-9]+)?)%")
    ]

    for clave, patron in campos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.info(f"{clave}: N/A")
    return datos

def procesar_bpap_rtf(texto_relevante: str):
    logging.info("Procesando examen CPAP (RTF)")
    datos = {}

    campos = [
        ("nombre_paciente", r"Nombre(?: del paciente)?:?\s*[|]?(.*?)\|Edad"),
        ("edad_paciente", r"Edad[:|]?\s*(\d{1,3})\s*anos"),
        ("id_paciente", r"(?:Id|Identificacion)[:|]?\s*[|]?(\d{5,10})\b"),
        ("peso_paciente", r"Peso[:|]?\s*\(?(?:Kg)?\)?\s*[:|]?\s*([0-9]+(?:[.,][0-9]+)?)"),
        ("talla_paciente", r"Talla[:|]?\s*\(?(?:cm|m)?\)?\s*[:|]?\s*([0-9]+(?:[.,][0-9]+)?)"),
        ("imc_paciente", r"IMC[:|]?\s*([0-9]+(?:[.,][0-9]+)?)"),
        ("cuello_paciente", r"Cuello[:|]?\s*\|?([0-9]+(?:[.,][0-9]+)?)\s*cm"),
        ("perimetro_abdominal", r"Perimetro Abdominal[:|]?\s*([0-9]+(?:[.,][0-9]+)?)\s*cm"),
        ("md_solicita", r"Solicita[:|]?\s*\|?(.*?)\s*\|Empresa"),
        ("eps_paciente", r"Empresa[:|]?\s*\|?(.*?)\s*\|Fecha"),
        ("fecha_proced", r"Fecha(?: del estudio)?[:|]?\s*\|?(\d{1,2}[/-]\d{1,2}[/-]\d{4})"),
        ("iah_diagnostico", r"IAH[:|]?\s*([0-9]+(?:[.,][0-9]+)?)\s*/hr"),
        ("tiempo_de_sueno(eficiencia)", r"Durmio\s+([0-9]+(?:[.,][0-9]+)?)\s+minutos"),
        ("tiempo_en_cama(eficiencia)", r"minutos de(?: los)?\s+([0-9]+(?:[.,][0-9]+)?)\s+(?:minutos\s+)?que permanecio en cama"),
        ("latencia_total", r"latencia de sueno(?: fue)?:?\s*([0-9]+(?:[.,][0-9]+)?)\s+minutos"),
        ("latencia_rem", r"latencia de sueno REM(?: fue)?:?\s*([0-9]+(?:[.,][0-9]+)?)\s+minutos"),
        ("sueno_rem", r"porcentaje de sueno REM(?: de|:)?\s*([0-9]+(?:[.,][0-9]+)?)%?"),
        ("sueno_profundo", r"porcentaje de sueno profundo \(estad(?:o|io) 3\)(?: de|:)?\s*([0-9]+(?:[.,][0-9]+)?)%?"),
        ("indice_microalertamientos", r"indice de microalertamientos(?: fue)?[:\s]*([0-9]+(?:[.,][0-9]+)?)/hora"),
        ("presion_inicial", r"inicio (?:a una|con) presion de\s*([0-9]+(?:/[0-9]+)?)\s*cm\s*(?:de\s*[aA]gua|de\s*H2O|H2O|[aA]gua)\b"),
        ("presion_terapeutica", r"(?i)a una presion de\s+(\d{2}/\d{2})\s*cm\s*(?:de\s*)?(?:agua|H2O)\b"),
        ("so2_prom_sueno_terapeutica", r"una vez alcanzada la presion terapeutica.*?fue de\s+([0-9]+(?:[.,][0-9]+)?)%")
    ]

    for clave, patron in campos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.info(f"{clave}: N/A")
    return datos


