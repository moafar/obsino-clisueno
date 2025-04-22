import logging
from utils.texto_utils import extraer_regex

def procesar_psg_doc(texto_relevante: str):
    logging.info("Procesando examen BASAL (DOC)") 
    datos = {}

    campos = [
        ("nombre_paciente", r"(?i)nombre(?: del paciente)?\s*[:|]?\s*([\wáéíóúñ-]+(?:\s+[\wáéíóúñ-]+)*)(?=\s*[:|]?\s*edad\b)"),
        ("edad_paciente", r"(?i)edad\s*[:|]?\s*(\d+(?:[.,]\d+)?)"),
        ("medida_edad_paciente", r"(?:edad\s*[:|]?\s*\d+\s*)(anos|meses)\b"),
        ("id_paciente", r"(?i)(?<!\w)(?:id|identificacion)\s*[:|]?\s*([A-Z0-9]{4,20})(?!\w)"),
        ("eps_paciente", r"(?i)empresa\s*[:|]?\s*(.*?)\s*fecha"),
        ("fecha_proced", r"(?i)fecha\s*[:|]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})(?=\s*procedimiento)"),
        ("escala_epworth", r"(?i)escala\s+de\s+epworth\s*[:|]?\s*(\d{1,2})(?=\s*/\s*24)"),
        ("tiempo_dormido", r"(?i)arquitectura\s+del\s+sueno:\s*durmio\D*(\d+[.,]\d+|\d+)\s*(?:min(?:utos?|s)?)?"),
        ("tiempo_en_cama", r"(?i)arquitectura\s+del\s+sueno:\s*durmio\s*\d+[.,]\d*\s*min(?:utos?)?\s*de\s*(?:los\s*)?(\d+[.,]\d+)\s*min(?:utos?)?\s*"),
        ("eficiencia_sueno", r"(?i)interpretacion\s+.*?(?:\(|(?:,|\s)+para\s+una\s+eficiencia(?:\s+de\s+sueno)?\s+de\s+|eficiencia\s*[:(\s]+)(\d+[.,]\d+)\s*%?"),
        ("porc_sueno_rem", r"(?i)(?:porcentaje\s+de\s+)?sueno\s+rem\s+(?:de\s+|del?\s+)?(\d+[.,]\d+)\s*%?"),
        ("porcentaje_sueno_profundo", r"(?i)(?:porcentaje|%)\s*(?:del?\s+)?sueno\s+profundo\s*(?:\(?\s*estadio\s*3\s*\)?)?\s*(?:de\s+|:?\s*)(\d+[.,]\d+)\s*%?"),
        ("indice_microalertamientos", r"(?i)indice\s+de\s+microalertamientos\s*(?:fue|:)?\s*(\d+[.,]\d+)\s*(?:/|por\s+)?h(?:ora|r)?\b"),
        ("iah", r"(?i)indice\s+de\s+apnea\s+hipopnea\s*\(?\s*iah\s*\)?\s*fue\s+de\s+(\d+[.,]\d+)\s*(?:/?(?:h(?:ora)?|hr)\b)?"),
        ("gravedad_iah", r"(?i)iah.*?considerad[oa][\s:]*([a-záéíóúñ]+)"),
        ("ido", r"(?i)(?:indice\s+de\s+)?desaturacion\s*[:=]?\s*(\d+[.,]\d+)\s*(?:/?(?:h(?:ora)?|hr)\b)?"),
        ("tiempo_bajo_90so2", r"(?i)permanecio\s+(\d+[.,]\d+)\s*min(?:utos?|s)?\s+de\s+sueno\s+con\s+saturacion\s+menor\s+a\s+90\s*%?"),
        ("ct90", r"(?i)\(?\s*t90\s*[:=]?\s*(\d+[.,]\d+)\s*%?\s*\)?"),
        ("iac", r"(?i)indice\s*\([^)]+\)\s*([\d,.]+)"),
        ("iao", r"(?i)indice\s*\([^)]+\)(?:\s*[\d,.]+){1}\s*([\d,.]+)"),
        ("iam", r"(?i)indice\s*\([^)]+\)(?:\s*[\d,.]+){2}\s*([\d,.]+)"),
        ("ih", r"(?i)indice\s*\([^)]+\)(?:\s*[\d,.]+){4}\s*([\d,.]+)")
    ]

    for clave, patron in campos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.warning(f"{clave}: N/A")

    return datos

def procesar_psg_rtf(texto_relevante: str):
    logging.info("Procesando examen PSG (RTF)")
    datos = {}

    campos = [
        ("nombre_paciente", r"(?i)nombre\s*(?:del\s*paciente\s*|paciente\s*|)\s*[:|]?\s*\|\s*([^|]+)\|"),
        #("edad_paciente", r"(?i)(?:edad\D*)(\d+)(?=\D*(?:\bidentificacion\b|\bid\b|\|))"),
        #("medida_edad_paciente", r"(?i)(?:edad\s*[:|]?\s*\d+\s*)(anos|meses)(?=\s*[\|]?\s*|$)"),
        #("id_paciente", r"(?i)(?:id|identificacion)\s*:?\s*\|?\s*([A-Za-z0-9]+)(?=\s*\||\s*$)"),
        #("eps_paciente", r"Empresa\s*:\s*\|([^|]+)\|(?:Fecha|Fecha del estudio)\s*:"),
        #("fecha_proced", r"Fecha\s*(?:del\s+estudio)?\s*:\s*\|?\s*(\d{1,2}/\d{1,2}/\d{4})(?=\s|\||$)"),
        #("escala_epworth", r"(?i)(?:\bEscala\s+(?:de\s+)?)?Epworth\b\s*[:|]?\s*(\d{1,2})(?=\s*/\d{2})\b"),
        #("tiempo_dormido", r"(?i)arquitectura\s+del\s+sueno:\s*durmio\D*(\d+[.,]?\d*)\s*(?:min(?:utos?|s)?)?"),
        #("tiempo_en_cama", r"(?i)arquitectura\s+del\s+sueno:\s*durmio\s*\d+[.,]?\d*\s*min(?:utos?)?\s*de\s*(?:los\s*)?(\d+[.,]?\d*)\s*min(?:utos?)?\s*"),
        #("eficiencia_sueno", r"(?i)interpretacion\s+.*?(?:\(|(?:,|\s)+para\s+una\s+eficiencia(?:\s+de\s+sueno)?\s+de\s+|eficiencia\s*[:(\s]+)(\d+[.,]\d+)\s*%?"),        
        #("porc_sueno_rem", r"(?i)(?:porcentaje\s+de\s+)?sueno\s+rem\s+(?:de\s+|del?\s+)?(\d+[.,]\d+)\s*%?"),
        #("porcentaje_sueno_profundo", r"(?i)(?:porcentaje|%)\s*(?:del?\s+)?sueno\s+profundo\s*(?:\(?\s*estad[i]?o\s*3\s*\)?)?\s*(?:de\s+|:?\s*)(\d+[.,]\d+)\s*%?"),
        #("indice_microalertamientos", r"(?i)indice de micro\s?alertamientos fue\s*(\d{1,3}(?:[.,]\d+)?)/(?:hora|h|hr)"),
        #("iah", r"(?i)indice de apnea hipopnea \(IAH\) fue de\s*(\d{1,3}(?:[.,]\d+)?)/(?:hora|h|hr)"),
        #("gravedad_iah", r"(?i)iah.*?:\s*([^.]+)"),
        #("ido", r"(?i)indice de desaturacion:\s*(\d{1,3}(?:[.,]\d+)?)/(?:hora|h|hr)"),
        #("tiempo_bajo_90so2", r"Permanecio\s*(\d{1,3}(?:[.,]\d+)?)\s*(?:minutos\s+de\s+sueno\s+con\s+saturacion\s+menor\s+a\s*)?90%?"),
        ("ct90", r"(?i)\(?\s*t90\s*[:=]?\s*(\d+[.,]\d+)\s*%?\s*\)?"),
        ("iac", r"Resumen de eventos respiratorios \(Tiempo de sueno total\).*?Indice \[nº\/h\]\|([\d\.]+)"),
        ("iao", r"Resumen de eventos respiratorios \(Tiempo de sueno total\).*?Indice \[nº\/h\]\|[\d\.]+\|([\d\.]+)"),
        ("iam", r"Resumen de eventos respiratorios \(Tiempo de sueno total\).*?Indice \[nº\/h\]\|[\d\.]+\|[\d\.]+\|([\d\.]+)"),
        ("ih", r"Resumen de eventos respiratorios \(Tiempo de sueno total\).*?Indice \[nº\/h\]\|[\d\.]+\|[\d\.]+\|[\d\.]+\|([\d\.]+)")
    ]

    for clave, patron in campos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.warning(f"{clave}: N/A")
            
    return datos
