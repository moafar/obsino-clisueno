import logging
from utils.texto_utils import extraer_regex

def procesar_cpap_doc(texto_relevante: str):
    logging.info("Procesando examen CPAP (DOC)")
    datos = {}

    campos = [
        ("nombre_paciente", r"(?i)nombre(?: del paciente)?\s*[:|]?\s*([\wáéíóúñ-]+(?:\s+[\wáéíóúñ-]+)*)(?=\s*[:|]?\s*edad\b)"),
        ("edad_paciente", r"(?i)edad\s*[:|]?\s*(\d+(?:[.,]\d+)?)\s*(?:años|anos)?"),
        ("id_paciente", r"(?i)id\s*[:|]?\s*([A-Z0-9]{4,20})"),
        ("fecha_proced", r"(?i)fecha\s*[:|]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})(?=\s*procedimiento)"),
        ("iah_diagnostico", r"IAH[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*/(?:hr|h|hora)\b"),
        ("mascara_marca", r"(?i)\b(?:[BC][i]?[-]?PAP?P?)\b es marca ([A-Za-z0-9\s&.\-]+?)(?=\s+y se utilizo mascara)"),
        ("mascara_tipo", r"(?i)mascara (\w+)\s+tamano"),
        ("mascara_tamano", r"(?i)mascara\b.*?\btamano\s+[“\"']\s*([A-Za-z0-9]+)\s*[”\"']"),
        ("mascara_referencia", r"(?i)(?:\bmascara\b.*?\btamano\b.*?)(?:\(ref\.\s+([^)]+)\))"),
        ("tiempo_dormido", r"(?i)interpretacion\s+arquitectura\s+del\s+sueno:.*?durmio\s+(\d+[.,]\d+)\s*minutos"),
        ("tiempo_en_cama", r"(?i)interpretacion\s+arquitectura\s+del\s+sueno:.*?durmio\s+\d+[.,]\d+\s*minutos\s+de\s*(?:los\s*)?(\d+[.,]\d+)"),
        ("eficiencia_sueno", r"(?i)interpretacion\s+.*?(?:\(|(?:,|\s)+para\s+una\s+eficiencia(?:\s+de\s+sueno)?\s+de\s+|eficiencia\s*[:(\s]+)(\d+[.,]\d+)\s*%?"),
        ("porc_sueno_rem", r"(?i)(?:se\s+observ[oó]\s+un\s+)?(?:porcentaje|%)\s+de\s+sueno\s+rem\s*(?:de\s+|[:=]\s*)(\d+[.,]\d+)\s*%?"),
        ("porc_sueno_profundo", r'(?i)porcentaje de sueno profundo\s*(?:\(estad(?:io|o)\s*3\))?\s*(?::|de)?\s*(\d{1,3}[,.]\d)\%?'),
        ("indice_microalertamientos", r"(?i)indice\s+de\s+microalertamientos\s*(?:fue|:)?\s*(\d+[.,]\d+)\s*(?:/|por\s+)?h(?:ora|r)?\b"),
        ("presion_terapeutica", r"(?i)a\s*(?:una\s+presion\s+de\s*)?(\d+)\s*cm\s*(?:de\s*(?:agua|H2O)|H2O)?\s*se\s+observo")
    ]

    for clave, patron in campos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.warning(f"{clave}: N/A")
    return datos

def procesar_cpap_docx(texto_relevante: str):
    logging.info("Procesando examen CPAP (DOCX)")

    datos = {}
    
    campos = [
        ("nombre_paciente", r"Nombre:\s*(.*?)\s*Edad"),
        ("edad_paciente", r"Edad\s*[:|]?\s*(\d{1,3})"),
        ("id_paciente", r"Id:\s*(\d+)\s*\d+\s*Adq"),
        ("fecha_proced", r"Fecha:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"),
        ("iah_diagnostico", r"IAH\s*[:=]\s*(\d+[,.]\d+|\d+)\s*(?:/?\s*hr)?"),
        ("mascara_marca", r"\b(?:[BCbc][iI]?[-]?[Pp][Aa]?[Pp])\b es marca ([A-Za-z0-9\s&.\-]+?)(?=\s+y se utilizo mascara)"),
        ("mascara_tipo", r"mascara (\w+)\s+tamano"),
        ("mascara_tamano", r"mascara\b.*?\btamano\s+[“\"']\s*([A-Za-z0-9]+)\s*[”\"']"),
        ("mascara_referencia", r"(?:\bmascara\b.*?\btamano\b.*?)(?:\([Rr]ef\.\s+([^)]+)\))"),
        ("tiempo_dormido", r"Durmio\s+(\d+\.?\d*)\s+minutos"),
        ("tiempo_en_cama", r"de\s+(\d+\.?\d*)\s+que permanecio en cama"),
        ("eficiencia_sueno", r"(?i)interpretacion\b.*?arquitectura\b.*?durmio\b.*?cama\b.*?\((\d{1,3}[.,]\d)%?\)"),
        ("porc_sueno_rem", r"Porcentaje\s+de\s+sueno\s+REM\s*[:]?\s*(\d+[,.]?\d*)\s*%"),
        ("porc_sueno_profundo", r"Porcentaje\s+de\s+sueno\s+profundo\s*\(estado\s*3\)\s*[:]?\s*(\d+[,.]?\d*)\s*%"),
        ("indice_microalertamientos", r"\s+microalertamientos\s*[:]?\s*(\d+[,.]?\d*)\s*/\s*hora"),
        ("presion_terapeutica", r"a\s+una\s+presion\s+de\s+(\d+[,.]?\d*)\s*cm\s*(?:de\s*)?agua(?:\s*de\s*agua)?\s+se\s+observo\s"),
    ]

    for clave, patron in campos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.warning(f"{clave}: N/A")

    return datos

def procesar_cpap_rtf(texto_relevante: str):
    logging.info("Procesando examen CPAP (RTF)")
    datos = {}

    campos = [
        ("nombre_paciente", r"Nombre(?: del paciente)?:?\s*[|]?(.*?)\|Edad"),
        ("edad_paciente", r"Edad[:|]?\s*(\d{1,3})\s*anos"),
        ("id_paciente", r"(?:Id|Identificacion)[:|]?\s*[|]?(\d{5,10})\b"),
        ("fecha_proced", r"Fecha(?: del estudio)?[:|]?\s*\|?(\d{1,2}[/-]\d{1,2}[/-]\d{4})"),
        ("iah_diagnostico", r"IAH[:|]?\s*([0-9]+(?:[.,][0-9]+)?)\s*/hr"),
        ("mascara_marca", r"\b(?:[BCbc][iI]?[-]?[Pp][Aa]?[Pp])\b es marca ([A-Za-z0-9\s&.\-]+?)(?=\s+y se utilizo mascara)"),
        ("mascara_tipo", r"mascara (\w+)\s+tamano"),
        ("mascara_tamano", r"mascara\b.*?\btamano\s+[“\"']\s*([A-Za-z0-9]+)\s*[”\"']"),
        ("mascara_referencia", r"(?:\bmascara\b.*?\btamano\b.*?)(?:\([Rr]ef\.\s+([^)]+)\))"),
        ("tiempo_dormido", r"Durmio\s+([0-9]+(?:[.,][0-9]+)?)\s+minutos"),
        ("tiempo_en_cama", r"minutos de(?: los)?\s+([0-9]+(?:[.,][0-9]+)?)\s+(?:minutos\s+)?que permanecio en cama"),
        ("eficiencia_sueno", r"(?i)interpretacion.*?arquitectura.*?eficiencia.*?[(:]\s*(\d{1,3}[,.]\d)\s*%?"),
        ("porc_sueno_rem", r"porcentaje de sueno REM(?: de|:)?\s*([0-9]+(?:[.,][0-9]+)?)%?"),
        ("porc_sueno_profundo", r"porcentaje de sueno profundo \(estad(?:o|io) 3\)(?: de|:)?\s*([0-9]+(?:[.,][0-9]+)?)%?"),
        ("indice_microalertamientos", r"indice de microalertamientos(?: fue)?[:\s]*([0-9]+(?:[.,][0-9]+)?)/hora"),
        ("presion_terapeutica", r"A una presion de\s+([0-9]+)\s*cm de agua se observo"),
    ]

    for clave, patron in campos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.warning(f"{clave}: N/A")

    return datos


