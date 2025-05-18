import logging
from utils.texto_utils import extraer_regex
import re

def procesar_psg_doc(texto_relevante: str, archivo: str):
    logging.info("Procesando examen BASAL (DOC)") 
    datos = {}

    campos = [
        ("nombre", r"(?i)nombre\s*:?\s*([a-z0-9.,\s]+)(?=\s*edad)"),
        ("edad_anos", r"(?i)Edad\s*:?\s*(\d+)\s*anos?(?:(?:\s*,?\s*y?\s*\d+\s*meses?)?(?:\s*,?\s*y?\s*\d+\s*dias?)?)?.{0,100}?\s*Id"),
        ("edad_meses", r"(?i)Edad\s*:?\s*(?:\d+\s*anos?)?(?:\s*,?\s*y?\s*(\d+)\s*meses?)?(?:\s*,?\s*y?\s*\d+\s*dias?)?.{0,100}?\s*Id"),
        ("edad_dias", r"(?i)Edad\s*:?\s*(?:\d+\s*anos?)?(?:\s*,?\s*y?\s*\d+\s*meses?)?(?:\s*,?\s*y?\s*(\d+)\s*dias?)?.{0,100}?\s*Id"),
        ("id", r"(?i)\b(?:Identificacion|Id)\b\s*[:|]?\s*\|?\s*([A-Z0-9]+)\s*\|?.*?\bPeso\b"),
        ("peso", r"(?i)peso\s*:?.*?(\d+(?:[.,]\d+)?)(?:\s+.*)?\s+talla"),
        ("medida_peso", r"(?i)peso\s*:?\s*(?:\(\s*([a-z]+)\s*\)\s*\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s*\(?([a-z]+)\)?)\s+.*?talla"),
        ("talla", r"(?i)talla\s*:?\s*(?:\(\s*[a-z]+\s*\)\s*)?([\d]+(?:[.,]\d+)?)(?:\s*\(?[a-z]+\)?)?\s+.*?imc"),
        ("medida_talla", r"(?i)talla\s*:?\s*(?:\(\s*([a-z]+)\s*\)\s*[\d]+(?:[.,]\d+)?|[\d]+(?:[.,]\d+)?\s*\(?([a-z]+)\)?)\s+.*?imc"),
        ("imc", r"(?i)imc\s*:?\s*([\d]+(?:[.,]\d+)?)\s*cuello"),
        ("cuello", r"(?i)cuello\s*:?\s*([\d]+(?:[.,]\d+)?)\s*[a-zA-Z]*\s*perimetro"),
        ("medida_cuello", r"(?i)cuello\s*:?\s*[\d]+(?:[.,]\d+)?\s*([^\d\s]+)\s*perimetro"),
        ("perimetro_abdominal", r"Perimetro\s+Abdominal\s*:?\s*([\d]+(?:[.,]\d+)?)\s*(?:cm|m)?\s*Solicita"),
        ("medida_perimetro_abdominal", r"Perimetro\s+Abdominal\s*:?\s*[\d]+(?:[.,]\d+)?\s*([^\d\s]+)\s*Solicita"),
        ("solicita", r"(?i)Solicita\s*:?\s*(.*?)\s*(?:Empresa|Eps)"),
        ("empresa", r"(?i)(?:Empresa|Eps)\s*:?\s*(.{1,50}?)(?=\s*(Fecha|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|$))"),
        ("fecha_estudio", r"(?i)Fecha\s*:?\s*(\d{1,4}[-/]\d{2}[-/]\d{2,4})\s*PROCEDIMIENTO"),
        ("epworth", r"(?i)Epworth\s*:?\s*(\d+)\s*/24"),
        ("tiempo_en_cama", r"(?i)ARQUITECTURA DE SUENO:.*?Tiempo en Cama:\s*([\d]+(?:[.,]\d+)?)"),
        ("tiempo_sueno", r"(?i)ARQUITECTURA DE SUENO:.*?Tiempo Total de Sueno:\s*([\d]+(?:[.,]\d+)?)"),
        ("eficiencia_sueno", r"(?i)ARQUITECTURA DE SUENO:.*?Eficiencia de Sueno:\s*([\d]+(?:[.,]\d+)?)%"),
        ("latencia_sueno_total", r"(?i)ARQUITECTURA DE SUENO:.*?Latencia de Sueno\s*:?\s*([\d]+(?:[.,]\d+)?)"),
        ("latencia_sueno_rem", r"(?i)ARQUITECTURA DE SUENO:.*?Latencia de sueno REM\s*:?\s*([\d]+(?:[.,]\d+)?)"), 
        ("indice_microalertamientos", r"(?i)Microalertamientos.*?Indice Despertares\s*:?\s*([\d]+(?:[.,]\d+)?)\s*/Hr\.\s*DISTRIBUCION DE FASES DE SUENO"),
        ("porcentaje_sueno_rem", r"(?i)DISTRIBUCION DE FASES DE SUENO:.*?REM\s+\d+\s+[\d]+(?:[.,]\d+)?\s+([\d]+(?:[.,]\d+)?)"),
        ("porcentaje_sueno_profundo", r"(?i)DISTRIBUCION DE FASES DE SUENO:.*?S3\s+\d+\s+[\d]+(?:[.,]\d+)?\s+([\d]+(?:[.,]\d+)?)"),
        ("iac", r"(?i)Resumen de eventos respiratorios.*?Indice \(nº/h TST\)\s+([\d]+(?:[.,]\d+)?)"),
        ("iao", r"(?i)Resumen de eventos respiratorios.*?Indice \(nº/h TST\)\s+[\d]+(?:[.,]\d+)?\s+([\d]+(?:[.,]\d+)?)"),
        ("iam", r"(?i)Resumen de eventos respiratorios.*?Indice \(nº/h TST\)\s+(?:[\d]+(?:[.,]\d+)?\s+){2}([\d]+(?:[.,]\d+)?)"),
        ("ih", r"(?i)Resumen de eventos respiratorios.*?Indice \(nº/h TST\)\s+(?:[\d]+(?:[.,]\d+)?\s+){4}([\d]+(?:[.,]\d+)?)"),
        ("iah", r"(?i)Resumen de eventos respiratorios.*?Indice \(nº/h TST\)\s+(?:[\d]+(?:[.,]\d+)?\s+){5}([\d]+(?:[.,]\d+)?)"),
        ("indice_desat_rem", r"(?i)OXIMETRIA:.*?Indice Desat \(#/hour\)\s+[\d]+(?:[.,]\d+)?\s+([\d]+(?:[.,]\d+)?)"),
        ("indice_desat_nrem", r"(?i)OXIMETRIA:.*?Indice Desat \(#/hour\)\s+(?:[\d]+(?:[.,]\d+)?\s+){2}([\d]+(?:[.,]\d+)?)"),
        ("indice_desat_total", r"(?i)OXIMETRIA:.*?Indice Desat \(#/hour\)\s+(?:[\d]+(?:[.,]\d+)?\s+){3}([\d]+(?:[.,]\d+)?)"),
        ("oxim_menor90_total", r"(?i)OXIMETRIA:.*?<90 \(min\)\s+(?:[\d]+(?:[.,]\d+)?\s+){3}([\d]+(?:[.,]\d+)?)"),
        ("oxim_menor80_total", r"(?i)OXIMETRIA:.*?<80 \(min\)\s+(?:[\d]+(?:[.,]\d+)?\s+){3}([\d]+(?:[.,]\d+)?)"),
        ("oxim_menor70_total", r"(?i)OXIMETRIA:.*?<70 \(min\)\s+(?:[\d]+(?:[.,]\d+)?\s+){3}([\d]+(?:[.,]\d+)?)"),
        ("oxim_menor60_total", r"(?i)OXIMETRIA:.*?<60 \(min\)\s+(?:[\d]+(?:[.,]\d+)?\s+){3}([\d]+(?:[.,]\d+)?)"),
        ("t90", r"INTERPRETACION.*?T90\s*[:|]?\s*([\d.,]+)\s*%")
    ]

    # Tipo 1 es la tabla con "Suma AP" 
    campos_tipo1 = [
        ("numero_eventos_ah", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?Numero\s+(?:[\d.,]+\s+){5}([\d.,]+)"),
    ]

    # Tipo 2 es la tabla con "Suma AP" y "RERA"
    campos_tipo2 = [
        ("numero_eventos_ah", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?Numero(?:\s+[\d.,]+){7}\s+([\d.,]+)"),
    ]

    # Tipo 3 es la tabla sencilla, que NO tiene "Suma AP" ni RERA (No he encontrado ejemplos de este caso en DOC)
    campos_tipo3 = [
        ("numero_eventos_ah", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?Numero\s*\|(?:[^\|\n]*\|){4}([^\|\n]*)"),
    ]

    # Extraer REGEX para patrones comunes

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

    # Extraer REGEX para patrones específicos 
    for clave, patron in patrones_especificos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.warning(f"{clave}: N/A")

    # Agregar el nombre del archivo a los datos
    datos['fuente'] = archivo

    return datos

def procesar_psg_rtf(texto_relevante: str, archivo: str):
    logging.info("Procesando examen PSG (RTF)")
    datos = {}

    campos_comunes = [
        ("nombre", r"(?i)Nombre\s*(?:del\s*paciente)?\s*[:|]?\s*\|?\s*([a-z0-9.,\s]+)(?=\s*\|?\s*(Edad|$))"),
        ("edad_anos", r"(?i)Edad\s*[:|]?\s*(\d+)\s*anos?.{0,100}?(Identificacion|Id)"),
        ("edad_meses", r"(?i)Edad.{0,100}?(\d+)\s*meses?.{0,100}?(Identificacion|Id)"),
        ("edad_dias", r"(?i)Edad.{0,100}?(\d+)\s*dias?.{0,100}?(Identificacion|Id)"),
        ("id", r"(?i)\b(?:Identificacion|Id)\b\s*[:|]?\s*\|?\s*([A-Z0-9]+)\s*\|?.*?\bPeso\b"),
        ("peso", r"(?i)peso\s*[:|]?\s*\|?\s*(?:\(\s*[a-z]+\s*\)\s*\|?)?\s*(\d+(?:[.,]\d+)?)\s*\|?.*?talla"),
        ("medida_peso", r"(?i)peso\s*[:|]?\s*\|?\s*(?:\(\s*([a-z]+)\s*\)\s*\|?\s*\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s*\|?\s*\(?([a-z]+)\)?)\s*\|?.*?talla"),
        ("talla", r"(?i)talla\s*[:|]?\s*\|?\s*(?:\(\s*[a-z]+\s*\)\s*\|?)?\s*(\d+(?:[.,]\d+)?)\s*\|?.*?imc"),
        ("medida_talla", r"(?i)talla\s*[:|]?\s*\|?\s*(?:\(\s*([a-z]+)\s*\)\s*\|?\s*\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s*\|?\s*\(?([a-z]+)\)?)\s*\|?.*?imc"),
        ("imc", r"(?i)IMC\s*[:|]?\s*\|?\s*([\d.,]+)\s*\|?\s*Cuello"),
        ("cuello", r"(?i)Cuello\s*[:|]?\s*\|?\s*(\d+)\s*[a-zA-Z]+\s*\|?\s*Perimetro"),
        ("medida_cuello", r"(?i)Cuello\s*[:|]?\s*\|?\s*\d+\s*([a-zA-Z]+)\s*\|?\s*Perimetro"),
        ("perimetro_abdominal", r"(?i)Perimetro\s*Abdominal\s*[:|]?\s*\|?\s*(\d+)\s*[a-zA-Z]+\s*\|?\s*Solicita"),
        ("medida_perimetro_abdominal", r"(?i)Perimetro\s*Abdominal\s*[:|]?\s*\|?\s*\d+\s*([a-zA-Z]+)\s*\|?\s*Solicita"),
        ("solicita", r"(?i)Solicita\s*[:|]?\s*\|?\s*(.+?)\s*\|?\s*Empresa"),
        ("empresa", r"(?i)(?:Empresa|Eps)\s*[:|]?\s*\|?\s*(.{1,50}?)(?=\s*\|?\s*(Fecha|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|$))"),
        ("fecha_estudio", r"(?i)Fecha(?:\s+del\s+estudio)?\s*[:|]?\s*\|?\s*([\d]{1,2}/[\d]{1,2}/[\d]{2,4})\s*\|(?:\s*\|*)*\s*PROCEDIMIENTO"),
        ("epworth", r"(?i)Escala\s*de\s*Epworth\s+(\d+)\s*/\s*\d+"),
        ("tiempo_en_cama", r"(?i)ARQUITECTURA\s+DE\s+SUENO:.*?Tiempo\s+en\s+Cama\s*[:|]?\s*\|?\s*([\d.]+)"),
        ("tiempo_sueno", r"(?i)ARQUITECTURA\s+DE\s+SUENO:.*?Tiempo\s+Total\s+de\s+Sueno\s*[:|]?\s*\|?\s*([\d.]+)"),
        ("eficiencia_sueno", r"(?i)ARQUITECTURA\s+DE\s+SUENO:.*?Eficiencia\s+de\s+Sueno\s*[:|]?\s*\|?\s*([\d.]+)"),
        ("latencia_sueno_total", r"(?i)ARQUITECTURA\s+DE\s+SUENO:.*?Latencia\s+de\s+Sueno\s*[:|]?\s*\|?\s*([\d.]+)"),
        ("latencia_sueno_rem", r"(?i)ARQUITECTURA\s+DE\s+SUENO:.*?Latencia\s+de\s+sueno\s+REM\s*[:|]?\s*\|?\s*([\d.]+)"),
        ("indice_microalertamientos", r"(?i)Microalertamientos.*?Indice\s+Despertares\s*[:|]?\s*\|?\s*([\d.,]+)"),
        ("porcentaje_sueno_rem", r"(?i)DISTRIBUCION\s+DE\s+FASES\s+DE\s+SUENO:.*?REM\s*\|\s*[\d.,]+\s*\|\s*([\d.,]+)"),
        ("porcentaje_sueno_profundo", r"(?i)DISTRIBUCION\s+DE\s+FASES\s+DE\s+SUENO:.*?S3\s*\|\s*[\d.,]+\s*\|\s*([\d.,]+)"),
        ("iac", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?(?:Indice\s+\(nº/h\s+TST\)|Indice\s+\[nº/h\])\|([\d.,]+)"),
        ("iao", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?(?:Indice\s+\(nº/h\s+TST\)|Indice\s+\[nº/h\])\|[\d.,]+\|([\d.,]+)"),
        ("iam", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?(?:Indice\s+\(nº/h\s+TST\)|Indice\s+\[nº/h\])\|[\d.,]+\|[\d.,]+\|([\d.,]+)"),
        ("indice_desat_rem", r"(?i)OXIMETRIA.*?Indice\s+Desat\s+\(#/hour\)\|(?:[\d.,]*\|){1}([\d.,]+)"),
        ("indice_desat_nrem", r"(?i)OXIMETRIA.*?Indice\s+Desat\s+\(#/hour\)\|(?:[\d.,]*\|){2}([\d.,]+)"),
        ("indice_desat_total", r"(?i)OXIMETRIA.*?Indice\s+Desat\s+\(#/hour\)\|(?:[\d.,]*\|){3}([\d.,]+)"),
        ("oxim_menor90_total", r"(?i)OXIMETRIA.*?<90\s*\(min\)\|(?:[\d.,]*\|){3}([\d.,]+)"),
        ("oxim_menor80_total", r"(?i)OXIMETRIA.*?<80\s*\(min\)\|(?:[\d.,]*\|){3}([\d.,]+)"),
        ("oxim_menor70_total", r"(?i)OXIMETRIA.*?<70\s*\(min\)\|(?:[\d.,]*\|){3}([\d.,]+)"),
        ("oxim_menor60_total", r"(?i)OXIMETRIA.*?<60\s*\(min\)\|(?:[\d.,]*\|){3}([\d.,]+)"),
        ("t90", r"(?i)INTERPRETACION.*?T90\s*[:|]?\s*([\d.,]+)\s*%")    
    ]

    # Tipo 1 es la tabla con "Suma AP" (No he encontrado ejemplos de este caso en RTF)
    campos_tipo1 = [
        ("numero_eventos_ah", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?Numero\|(?:[^\|\n]*\|){5}([^\|\n]*)"),
        ("ih", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?(?:Indice\s+\(nº/h\s+TST\)|Indice\s+\[nº/h\])\|(?:[\d.,]+\|){3}([\d.,]+)"),
        ("iah", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?(?:Indice\s+\(nº/h\s+TST\)|Indice\s+\[nº/h\])\|(?:[\d.,]+\|){4}([\d.,]+)"),
    ]

    # Tipo 2 es la tabla con "Suma AP" y "RERA"
    campos_tipo2 = [
        ("numero_eventos_ah", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?Numero\s*\|(?:[\d.,]+\|){7}([\d.,]+)"),
        ("ih", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?(?:Indice\s+\(nº/h\s+TST\)|Indice\s+\[nº/h\])\|(?:[\d.,]+\|){4}([\d.,]+)"),
        ("iah", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?(?:Indice\s+\(nº/h\s+TST\)|Indice\s+\[nº/h\])\|(?:[\d.,]+\|){5}([\d.,]+)"),
    ]

    # Tipo 3 es la tabla sencilla, que NO tiene "Suma AP" ni RERA
    campos_tipo3 = [
        ("numero_eventos_ah", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?Numero\s*\|(?:[^\|\n]*\|){4}([^\|\n]*)"),
        ("ih", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?(?:Indice\s+\(nº/h\s+TST\)|Indice\s+\[nº/h\])\|(?:[\d.,]+\|){3}([\d.,]+)"),
        ("iah", r"(?i)Resumen\s+de\s+eventos\s+respiratorios\s+\(Tiempo\s+de\s+sueno\s+total\).*?(?:Indice\s+\(nº/h\s+TST\)|Indice\s+\[nº/h\])\|(?:[\d.,]+\|){4}([\d.,]+)"),
    ]

    # Extraer REGEX para patrones comunes
    for clave, patron in campos_comunes:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.warning(f"{clave}: N/A")

    # Detectar tipo de resumen
    tiene_suma_ap = re.search(r"\|\s*Suma\s+AP\s*\|", texto_relevante, re.IGNORECASE)
    tiene_rera = re.search(r"\|\s*RERA\s*\|", texto_relevante, re.IGNORECASE)

    # Extraer REGEX para patrones específicos según el tipo de resumen
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
    
    # Agregar el nombre del archivo a los datos
    datos['fuente'] = archivo
    
    return datos
