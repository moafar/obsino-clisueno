import logging
from utils.texto_utils import extraer_regex

def procesar_cpap_doc(texto_relevante: str):
    logging.info("Procesando examen CPAP (DOC)")
    datos = {}

    campos = [
        ("nombre_paciente", r"(?i)nombre(?: del paciente)?\s*[:|]?\s*([\wáéíóúñ-]+(?:\s+[\wáéíóúñ-]+)*)(?=\s*[:|]?\s*edad\b)"),
        ("edad_paciente", r"(?i)edad\s*[:|]?\s*(\d+(?:[.,]\d+)?)\s*(?:años|anos)?"),
        ("id_paciente", r"(?i)id\s*[:|]?\s*([A-Z0-9]{4,20})"),
        ("eps_paciente", r"(?i)empresa\s*[:|]?\s*(.*?)\s*fecha"),
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
        ("peso_paciente", r"Peso[:\s]*\(?Kg\)?\s*[:)]?\s*(\d+\.?\d*)"),
        ("talla_paciente", r"Talla[:\s]*\(?m\)?\s*[:)]?\s*(\d+\.?\d+)"),
        ("imc_paciente", r"IMC\s*[:=]?\s*(\d+\.?\d*)\s*(kg/m²)?"),
        ("cuello_paciente", r"(?i)cuello\D*(\d+\.?\d*)\s*(?:cm|\(cm\))?"),
        ("perimetro_abdominal", r"(?i)(?:abdominal|perimetro\s*abdominal)\D*(\d+\.?\d*)\s*(?:cm|\(cm\))?"),
        ("md_solicita", r"Solicita:\s*(.*?)(?=\s*Empresa:)"),
        ("eps_paciente", r"Empresa:\s*([^\n]*?)\s*(?=Fecha:|$)"),
        ("fecha_proced", r"Fecha:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"),
        ("mascara_marca", r"\b(?:[BCbc][iI]?[-]?[Pp][Aa]?[Pp])\b es marca ([A-Za-z0-9\s&.\-]+?)(?=\s+y se utilizo mascara)"),
        ("mascara_tipo", r"mascara (\w+)\s+tamano"),
        ("mascara_tamano", r"mascara\b.*?\btamano\s+[“\"']\s*([A-Za-z0-9]+)\s*[”\"']"),
        ("mascara_referencia", r"(?:\bmascara\b.*?\btamano\b.*?)(?:\([Rr]ef\.\s+([^)]+)\))"),
        ("iah_diagnostico", r"IAH\s*[:=]\s*(\d+[,.]\d+|\d+)\s*(?:/?\s*hr)?"),
        ("tiempo_de_sueno(eficiencia)", r"Durmio\s+(\d+\.?\d*)\s+minutos"),
        ("tiempo_en_cama(eficiencia)", r"de\s+(\d+\.?\d*)\s+que permanecio en cama"),
        ("latencia_total", r"Latencia\s+de\s+sueno\s*[:]?\s*(\d+[,.]?\d*)\s*min\w*"),
        ("latencia_rem", r"Latencia\s+de\s+sueno\s+REM\s*[:]?\s*(\d+[,.]?\d*)\s*min\w*"),
        ("sueno_rem", r"Porcentaje\s+de\s+sueno\s+REM\s*[:]?\s*(\d+[,.]?\d*)\s*%"),
        ("sueno_profundo", r"Porcentaje\s+de\s+sueno\s+profundo\s*\(estado\s*3\)\s*[:]?\s*(\d+[,.]?\d*)\s*%"),
        ("indice_microalertamientos", r"\s+microalertamientos\s*[:]?\s*(\d+[,.]?\d*)\s*/\s*hora"),
        ("presion_inicial", r"(?i)inicio\s+a\s+una\s+presion\s+de\s+(\d+[,.]?\d*)\s*cm\s*(?:de\s*(?:agua|h2o)|(?:agua|h2o))?"),
        ("presion_terapeutica", r"a\s+una\s+presion\s+de\s+(\d+[,.]?\d*)\s*cm\s*(?:de\s*)?agua(?:\s*de\s*agua)?\s+se\s+observo\s"),
        ("so2_prom_sueno_terapeutica", r"saturacion de oxigeno promedio durante el sueno.*?fue de\s*(\d+)%")
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
        ("peso_paciente", r"Peso[:|]?\s*\(?(?:Kg)?\)?\s*[:|]?\s*([0-9]+(?:[.,][0-9]+)?)"),
        ("talla_paciente", r"Talla[:|]?\s*\(?(?:cm|m)?\)?\s*[:|]?\s*([0-9]+(?:[.,][0-9]+)?)"),
        ("imc_paciente", r"IMC[:|]?\s*([0-9]+(?:[.,][0-9]+)?)"),
        ("cuello_paciente", r"Cuello[:|]?\s*\|?([0-9]+(?:[.,][0-9]+)?)\s*cm"),
        ("perimetro_abdominal", r"Perimetro Abdominal[:|]?\s*([0-9]+(?:[.,][0-9]+)?)\s*cm"),
        ("md_solicita", r"Solicita[:|]?\s*\|?(.*?)\s*\|Empresa"),
        ("eps_paciente", r"Empresa[:|]?\s*\|?(.*?)\s*\|Fecha"),
        ("fecha_proced", r"Fecha(?: del estudio)?[:|]?\s*\|?(\d{1,2}[/-]\d{1,2}[/-]\d{4})"),
        ("mascara_marca", r"\b(?:[BCbc][iI]?[-]?[Pp][Aa]?[Pp])\b es marca ([A-Za-z0-9\s&.\-]+?)(?=\s+y se utilizo mascara)"),
        ("mascara_tipo", r"mascara (\w+)\s+tamano"),
        ("mascara_tamano", r"mascara\b.*?\btamano\s+[“\"']\s*([A-Za-z0-9]+)\s*[”\"']"),
        ("mascara_referencia", r"(?:\bmascara\b.*?\btamano\b.*?)(?:\([Rr]ef\.\s+([^)]+)\))"),
        ("iah_diagnostico", r"IAH[:|]?\s*([0-9]+(?:[.,][0-9]+)?)\s*/hr"),
        ("tiempo_de_sueno(eficiencia)", r"Durmio\s+([0-9]+(?:[.,][0-9]+)?)\s+minutos"),
        ("tiempo_en_cama(eficiencia)", r"minutos de(?: los)?\s+([0-9]+(?:[.,][0-9]+)?)\s+(?:minutos\s+)?que permanecio en cama"),
        ("latencia_total", r"latencia de sueno(?: fue)?:?\s*([0-9]+(?:[.,][0-9]+)?)\s+minutos"),
        ("latencia_rem", r"latencia de sueno REM(?: fue)?:?\s*([0-9]+(?:[.,][0-9]+)?)\s+minutos"),
        ("sueno_rem", r"porcentaje de sueno REM(?: de|:)?\s*([0-9]+(?:[.,][0-9]+)?)%?"),
        ("sueno_profundo", r"porcentaje de sueno profundo \(estad(?:o|io) 3\)(?: de|:)?\s*([0-9]+(?:[.,][0-9]+)?)%?"),
        ("indice_microalertamientos", r"indice de microalertamientos(?: fue)?[:\s]*([0-9]+(?:[.,][0-9]+)?)/hora"),
        ("presion_inicial", r"Se inicio a una presion de\s+([0-9]+)\s*cm de agua"),
        ("presion_terapeutica", r"A una presion de\s+([0-9]+)\s*cm de agua se observo"),
        ("so2_prom_sueno_terapeutica", r"una vez alcanzada la presion terapeutica.*?fue de\s+([0-9]+(?:[.,][0-9]+)?)%")
    ]

    for clave, patron in campos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.warning(f"{clave}: N/A")
    return datos


