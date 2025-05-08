import logging
from utils.texto_utils import extraer_regex
import re

def procesar_psg_doc(texto_relevante: str):
    logging.info("Procesando examen BASAL (DOC)") 
    datos = {}

    campos = [
        ("pte_nombre", r"(?i)nombre\s*:?\s*([a-z0-9.,\s]+)(?=\s*edad)"),
        ("pte_edad_anos", r"(?i)Edad\s*:?\s*(\d+)\s*anos?(?:(?:\s*,?\s*y?\s*\d+\s*meses?)?(?:\s*,?\s*y?\s*\d+\s*dias?)?)?.{0,100}?\s*Id"),
        ("pte_edad_meses", r"(?i)Edad\s*:?\s*(?:\d+\s*anos?)?(?:\s*,?\s*y?\s*(\d+)\s*meses?)?(?:\s*,?\s*y?\s*\d+\s*dias?)?.{0,100}?\s*Id"),
        ("pte_edad_dias", r"(?i)Edad\s*:?\s*(?:\d+\s*anos?)?(?:\s*,?\s*y?\s*\d+\s*meses?)?(?:\s*,?\s*y?\s*(\d+)\s*dias?)?.{0,100}?\s*Id"),
        ("pte_id", r"(?i)\b(?:Identificacion|Id)\b\s*[:|]?\s*\|?\s*([A-Z0-9]+)\s*\|?.*?\bPeso\b"),
        ("pte_peso", r"(?i)peso\s*:?.*?(\d+(?:[.,]\d+)?)(?:\s+.*)?\s+talla"),
        ("pte_medida_peso", r"(?i)peso\s*:?\s*(?:\(\s*([a-z]+)\s*\)\s*\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s*\(?([a-z]+)\)?)\s+.*?talla"),
        ("pte_talla", r"(?i)talla\s*:?\s*(?:\(\s*[a-z]+\s*\)\s*)?([\d]+(?:[.,]\d+)?)(?:\s*\(?[a-z]+\)?)?\s+.*?imc"),
        ("pte_medida_talla", r"(?i)talla\s*:?\s*(?:\(\s*([a-z]+)\s*\)\s*[\d]+(?:[.,]\d+)?|[\d]+(?:[.,]\d+)?\s*\(?([a-z]+)\)?)\s+.*?imc"),
        ("pte_imc", r"(?i)imc\s*:?\s*([\d]+(?:[.,]\d+)?)\s*cuello"),
        ("pte_cuello", r"(?i)cuello\s*:?\s*([\d]+(?:[.,]\d+)?)\s*[a-zA-Z]*\s*perimetro"),
        ("pte_medida_cuello", r"(?i)cuello\s*:?\s*[\d]+(?:[.,]\d+)?\s*([^\d\s]+)\s*perimetro"),
        ("pte_perimetro_abdominal", r"Perimetro\s+Abdominal\s*:?\s*([\d]+(?:[.,]\d+)?)\s*(?:cm|m)?\s*Solicita"),
        ("pte_medida_perimetro_abdominal", r"Perimetro\s+Abdominal\s*:?\s*[\d]+(?:[.,]\d+)?\s*([^\d\s]+)\s*Solicita"),
        ("proced_solicita", r"(?i)Solicita\s*:?\s*(.*?)\s*(?:Empresa|Eps)"),
        ("proced_empresa", r"(?i)(?:Empresa|Eps)\s*:?\s*(.{1,50}?)(?=\s*(Fecha|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|$))"),
        ("proced_fecha", r"(?i)Fecha\s*:?\s*(\d{2,4}[-/]\d{2}[-/]\d{2,4})\s*PROCEDIMIENTO"),
        ("proced_epworth", r"(?i)Epworth\s*:?\s*(\d+)\s*/24"),
        ("proced_tiempo_en_cama", r"(?i)ARQUITECTURA DE SUENO:.*?Tiempo en Cama:\s*([\d]+(?:[.,]\d+)?)"),
        ("proced_tiempo_sueno", r"(?i)ARQUITECTURA DE SUENO:.*?Tiempo Total de Sueno:\s*([\d]+(?:[.,]\d+)?)"),
        ("proced_eficiencia_sueno", r"(?i)ARQUITECTURA DE SUENO:.*?Eficiencia de Sueno:\s*([\d]+(?:[.,]\d+)?)%"),
        ("proced_latencia_sueno_total", r"(?i)ARQUITECTURA DE SUENO:.*?Latencia de Sueno\s*:?\s*([\d]+(?:[.,]\d+)?)"),
        ("proced_latencia_sueno_rem", r"(?i)ARQUITECTURA DE SUENO:.*?Latencia de sueno REM\s*:?\s*([\d]+(?:[.,]\d+)?)"), 
        ("proced_indice_microalertamientos", r"(?i)Microalertamientos.*?Indice Despertares\s*:?\s*([\d]+(?:[.,]\d+)?)\s*/Hr\.\s*DISTRIBUCION DE FASES DE SUENO"),
        ("proced_porcentaje_sueno_rem", r"(?i)DISTRIBUCION DE FASES DE SUENO:.*?REM\s+\d+\s+[\d]+(?:[.,]\d+)?\s+([\d]+(?:[.,]\d+)?)"),
        ("proced_porcentaje_sueno_profundo", r"(?i)DISTRIBUCION DE FASES DE SUENO:.*?S3\s+\d+\s+[\d]+(?:[.,]\d+)?\s+([\d]+(?:[.,]\d+)?)"),
        ("proced_iac", r"(?i)Resumen de eventos respiratorios.*?Indice \(nº/h TST\)\s+([\d]+(?:[.,]\d+)?)"),
        ("proced_iao", r"(?i)Resumen de eventos respiratorios.*?Indice \(nº/h TST\)\s+[\d]+(?:[.,]\d+)?\s+([\d]+(?:[.,]\d+)?)"),
        ("proced_iam", r"(?i)Resumen de eventos respiratorios.*?Indice \(nº/h TST\)\s+(?:[\d]+(?:[.,]\d+)?\s+){2}([\d]+(?:[.,]\d+)?)"),
        ("proced_ih", r"(?i)Resumen de eventos respiratorios.*?Indice \(nº/h TST\)\s+(?:[\d]+(?:[.,]\d+)?\s+){4}([\d]+(?:[.,]\d+)?)"),
        ("proced_iah", r"(?i)Resumen de eventos respiratorios.*?Indice \(nº/h TST\)\s+(?:[\d]+(?:[.,]\d+)?\s+){5}([\d]+(?:[.,]\d+)?)"),
        ("proced_indice_desat_rem", r"(?i)OXIMETRIA:.*?Indice Desat \(#/hour\)\s+[\d]+(?:[.,]\d+)?\s+([\d]+(?:[.,]\d+)?)"),
        ("proced_indice_desat_nrem", r"(?i)OXIMETRIA:.*?Indice Desat \(#/hour\)\s+(?:[\d]+(?:[.,]\d+)?\s+){2}([\d]+(?:[.,]\d+)?)"),
        ("proced_indice_desat_total", r"(?i)OXIMETRIA:.*?Indice Desat \(#/hour\)\s+(?:[\d]+(?:[.,]\d+)?\s+){3}([\d]+(?:[.,]\d+)?)"),
        ("proced_oxim_menor90_total", r"(?i)OXIMETRIA:.*?<90 \(min\)\s+(?:[\d]+(?:[.,]\d+)?\s+){3}([\d]+(?:[.,]\d+)?)"),
        ("proced_oxim_menor80_total", r"(?i)OXIMETRIA:.*?<80 \(min\)\s+(?:[\d]+(?:[.,]\d+)?\s+){3}([\d]+(?:[.,]\d+)?)"),
        ("proced_oxim_menor70_total", r"(?i)OXIMETRIA:.*?<70 \(min\)\s+(?:[\d]+(?:[.,]\d+)?\s+){3}([\d]+(?:[.,]\d+)?)"),
        ("proced_oxim_menor60_total", r"(?i)OXIMETRIA:.*?<60 \(min\)\s+(?:[\d]+(?:[.,]\d+)?\s+){3}([\d]+(?:[.,]\d+)?)"),
        ("proced_t90", r"INTERPRETACION.*?T90\s*[:|]?\s*([\d.,]+)\s*%")
    ]

    # Tipo 1 es la tabla con "Suma AP" 
    campos_tipo1 = [
        ("proced_numero_eventos_ah", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?Numero\s+(?:[\d.,]+\s+){5}([\d.,]+)"),
    ]

    # Tipo 2 es la tabla con "Suma AP" y "RERA"
    campos_tipo2 = [
        ("proced_numero_eventos_ah", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?Numero(?:\s+[\d.,]+){7}\s+([\d.,]+)"),
    ]

    # Tipo 3 es la tabla sencilla, que NO tiene "Suma AP" ni RERA (No he encontrado ejemplos de este caso en DOC)
    campos_tipo3 = [
        ("proced_numero_eventos_ah", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?Numero\s*\|(?:[^\|\n]*\|){4}([^\|\n]*)"),
    ]

    # Extraer patrones comunes

    for clave, patron in campos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.warning(f"{clave}: N/A")

    # Detectar tipo de resumen
    tiene_suma_ap = re.search(r"\bSuma\s+AP\b", texto_relevante, re.IGNORECASE)
    tiene_rera = re.search(r"\bRERA\b", texto_relevante, re.IGNORECASE)
    # Extraer patrones específicos según el tipo de resumen
    if tiene_suma_ap and tiene_rera:
        patrones_especificos = campos_tipo2  # Tipo 2: Suma AP + RERA
    elif tiene_suma_ap:
        patrones_especificos = campos_tipo1  # Tipo 1: solo Suma AP
    else:
        patrones_especificos = campos_tipo3  # Tipo 3: sin Suma AP
    # Extraer patrones específicos
    for clave, patron in patrones_especificos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.warning(f"{clave}: N/A")

    return datos

def procesar_psg_rtf(texto_relevante: str):
    logging.info("Procesando examen PSG (RTF)")
    datos = {}

    campos_comunes = [
        ("pte_nombre", r"(?i)Nombre\s*(?:del\s*paciente)?\s*[:|]?\s*\|?\s*([a-z0-9.,\s]+)(?=\s*\|?\s*(Edad|$))"),
        ("pte_edad_anos", r"(?i)Edad\s*[:|]?\s*(\d+)\s*anos?.{0,100}?(Identificacion|Id)"),
        ("pte_edad_meses", r"(?i)Edad.{0,100}?(\d+)\s*meses?.{0,100}?(Identificacion|Id)"),
        ("pte_edad_dias", r"(?i)Edad.{0,100}?(\d+)\s*dias?.{0,100}?(Identificacion|Id)"),
        ("pte_id", r"(?i)\b(?:Identificacion|Id)\b\s*[:|]?\s*\|?\s*([A-Z0-9]+)\s*\|?.*?\bPeso\b"),
        ("pte_peso", r"(?i)peso\s*[:|]?\s*\|?\s*(?:\(\s*[a-z]+\s*\)\s*\|?)?\s*(\d+(?:[.,]\d+)?)\s*\|?.*?talla"),
        ("pte_medida_peso", r"(?i)peso\s*[:|]?\s*\|?\s*(?:\(\s*([a-z]+)\s*\)\s*\|?\s*\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s*\|?\s*\(?([a-z]+)\)?)\s*\|?.*?talla"),
        ("pte_talla", r"(?i)talla\s*[:|]?\s*\|?\s*(?:\(\s*[a-z]+\s*\)\s*\|?)?\s*(\d+(?:[.,]\d+)?)\s*\|?.*?imc"),
        ("pte_medida_talla", r"(?i)talla\s*[:|]?\s*\|?\s*(?:\(\s*([a-z]+)\s*\)\s*\|?\s*\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s*\|?\s*\(?([a-z]+)\)?)\s*\|?.*?imc"),
        ("pte_imc", r"(?i)IMC\s*[:|]?\s*\|?\s*([\d.,]+)\s*\|?\s*Cuello"),
        ("pte_cuello", r"(?i)Cuello\s*[:|]?\s*\|?\s*(\d+)\s*[a-zA-Z]+\s*\|?\s*Perimetro"),
        ("pte_medida_cuello", r"(?i)Cuello\s*[:|]?\s*\|?\s*\d+\s*([a-zA-Z]+)\s*\|?\s*Perimetro"),
        ("pte_perimetro_abdominal", r"(?i)Perimetro\s*Abdominal\s*[:|]?\s*\|?\s*(\d+)\s*[a-zA-Z]+\s*\|?\s*Solicita"),
        ("pte_medida_perimetro_abdominal", r"(?i)Perimetro\s*Abdominal\s*[:|]?\s*\|?\s*\d+\s*([a-zA-Z]+)\s*\|?\s*Solicita"),
        ("proced_solicita", r"(?i)Solicita\s*[:|]?\s*\|?\s*(.+?)\s*\|?\s*Empresa"),
        ("proced_empresa", r"(?i)(?:Empresa|Eps)\s*[:|]?\s*\|?\s*(.{1,50}?)(?=\s*\|?\s*(Fecha|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|$))"),
        ("proced_fecha", r"(?i)Fecha\s*del\s*estudio\s*[:|]?\s*\|?\s*([\d/]+)\s*\|(?=\s*PROCEDIMIENTO)"),
        ("proced_epworth", r"(?i)Escala\s*de\s*Epworth\s+(\d+)\s*/\s*\d+"),
        ("proced_tiempo_en_cama", r"(?i)ARQUITECTURA\s+DE\s+SUENO:.*?Tiempo\s+en\s+Cama\s*[:|]?\s*\|?\s*([\d.]+)"),
        ("proced_tiempo_sueno", r"(?i)ARQUITECTURA\s+DE\s+SUENO:.*?Tiempo\s+Total\s+de\s+Sueno\s*[:|]?\s*\|?\s*([\d.]+)"),
        ("proced_eficiencia_sueno", r"(?i)ARQUITECTURA\s+DE\s+SUENO:.*?Eficiencia\s+de\s+Sueno\s*[:|]?\s*\|?\s*([\d.]+)"),
        ("proced_latencia_sueno_total", r"(?i)ARQUITECTURA\s+DE\s+SUENO:.*?Latencia\s+de\s+Sueno\s*[:|]?\s*\|?\s*([\d.]+)"),
        ("proced_latencia_sueno_rem", r"(?i)ARQUITECTURA\s+DE\s+SUENO:.*?Latencia\s+de\s+sueno\s+REM\s*[:|]?\s*\|?\s*([\d.]+)"),
        ("proced_indice_microalertamientos", r"(?i)Microalertamientos.*?Indice\s+Despertares\s*[:|]?\s*\|?\s*([\d.,]+)"),
        ("proced_porcentaje_sueno_rem", r"(?i)DISTRIBUCION\s+DE\s+FASES\s+DE\s+SUENO:.*?REM\s*\|\s*[\d.,]+\s*\|\s*([\d.,]+)"),
        ("proced_porcentaje_sueno_profundo", r"(?i)DISTRIBUCION\s+DE\s+FASES\s+DE\s+SUENO:.*?S3\s*\|\s*[\d.,]+\s*\|\s*([\d.,]+)"),
        ("proced_iac", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?(?:Indice\s+\(nº/h\s+TST\)|Indice\s+\[nº/h\])\|([\d.,]+)"),
        ("proced_iao", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?(?:Indice\s+\(nº/h\s+TST\)|Indice\s+\[nº/h\])\|[\d.,]+\|([\d.,]+)"),
        ("proced_iam", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?(?:Indice\s+\(nº/h\s+TST\)|Indice\s+\[nº/h\])\|[\d.,]+\|[\d.,]+\|([\d.,]+)"),
        ("proced_indice_desat_rem", r"(?i)OXIMETRIA.*?Indice\s+Desat\s+\(#/hour\)\|(?:[\d.,]*\|){1}([\d.,]+)"),
        ("proced_indice_desat_nrem", r"(?i)OXIMETRIA.*?Indice\s+Desat\s+\(#/hour\)\|(?:[\d.,]*\|){2}([\d.,]+)"),
        ("proced_indice_desat_total", r"(?i)OXIMETRIA.*?Indice\s+Desat\s+\(#/hour\)\|(?:[\d.,]*\|){3}([\d.,]+)"),
        ("proced_oxim_menor90_total", r"(?i)OXIMETRIA.*?<90\s*\(min\)\|(?:[\d.,]*\|){3}([\d.,]+)"),
        ("proced_oxim_menor80_total", r"(?i)OXIMETRIA.*?<80\s*\(min\)\|(?:[\d.,]*\|){3}([\d.,]+)"),
        ("proced_oxim_menor70_total", r"(?i)OXIMETRIA.*?<70\s*\(min\)\|(?:[\d.,]*\|){3}([\d.,]+)"),
        ("proced_oxim_menor60_total", r"(?i)OXIMETRIA.*?<60\s*\(min\)\|(?:[\d.,]*\|){3}([\d.,]+)"),
        ("proced_t90", r"(?i)INTERPRETACION.*?T90\s*[:|]?\s*([\d.,]+)\s*%")    
    ]

    # Tipo 1 es la tabla con "Suma AP" (No he encontrado ejemplos de este caso en RTF)
    campos_tipo1 = [
        ("proced_numero_eventos_ah", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?Numero\|(?:[^\|\n]*\|){5}([^\|\n]*)"),
        ("proced_ih", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?(?:Indice\s+\(nº/h\s+TST\)|Indice\s+\[nº/h\])\|(?:[\d.,]+\|){3}([\d.,]+)"),
        ("proced_iah", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?(?:Indice\s+\(nº/h\s+TST\)|Indice\s+\[nº/h\])\|(?:[\d.,]+\|){4}([\d.,]+)"),
    ]

    # Tipo 2 es la tabla con "Suma AP" y "RERA"
    campos_tipo2 = [
        ("proced_numero_eventos_ah", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?Numero\s*\|(?:[\d.,]+\|){7}([\d.,]+)"),
        ("proced_ih", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?(?:Indice\s+\(nº/h\s+TST\)|Indice\s+\[nº/h\])\|(?:[\d.,]+\|){4}([\d.,]+)"),
        ("proced_iah", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?(?:Indice\s+\(nº/h\s+TST\)|Indice\s+\[nº/h\])\|(?:[\d.,]+\|){5}([\d.,]+)"),
    ]

    # Tipo 3 es la tabla sencilla, que NO tiene "Suma AP" ni RERA
    campos_tipo3 = [
        ("proced_numero_eventos_ah", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?Numero\s*\|(?:[^\|\n]*\|){4}([^\|\n]*)"),
        ("proced_ih", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?(?:Indice\s+\(nº/h\s+TST\)|Indice\s+\[nº/h\])\|(?:[\d.,]+\|){3}([\d.,]+)"),
        ("proced_iah", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?(?:Indice\s+\(nº/h\s+TST\)|Indice\s+\[nº/h\])\|(?:[\d.,]+\|){4}([\d.,]+)"),
    ]

    # Extraer patrones comunes
    for clave, patron in campos_comunes:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.warning(f"{clave}: N/A")

    # Detectar tipo de resumen
    tiene_suma_ap = re.search(r"\|\s*Suma\s+AP\s*\|", texto_relevante, re.IGNORECASE)
    tiene_rera = re.search(r"\|\s*RERA\s*\|", texto_relevante, re.IGNORECASE)

    # Extraer patrones específicos según el tipo de resumen
    if tiene_suma_ap and tiene_rera:
        patrones_especificos = campos_tipo2  # Tipo 2: Suma AP + RERA
    elif tiene_suma_ap:
        patrones_especificos = campos_tipo1  # Tipo 1: solo Suma AP
    else:
        patrones_especificos = campos_tipo3  # Tipo 3: sin Suma AP
            
    # Extraer patrones específicos
    for clave, patron in patrones_especificos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.warning(f"{clave}: N/A")
    
    return datos
