import logging
import re
from utils.texto_utils import extraer_regex

def procesar_psg_doc(texto_relevante: str):
    logging.info("Procesando examen BASAL")
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
        ("fecha_proced", r"Fecha\s*[:|]?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})(?=\s*PROCEDIMIENTO)"),
        ("escala_epworth", r"Escala\s+de\s+Epworth\s*[:|]?\s*(\d{1,2}/\d{2})"),
        ("eficiencia_sueno", r"eficiencia de sueno de\s*\(?\s*([0-9]+(?:[.,][0-9]+)?)\)?"),
        ("latencia_total", r"latencia de sueno fue(?: de)?[:\s]*([0-9]+[.,][0-9]+)\s+minutos"),
        ("latencia_rem", r"latencia de sueno REM(?: fue)?(?: de)?[:|]?\s*([0-9]+[.,][0-9]+)\s+minutos"),
        ("sueno_profundo", r"porcentaje de sueno profundo\s+\(estadio 3\)\s+de\s+([0-9]+(?:[.,][0-9]+)?)%"),
        ("indice_microalertamientos", r"indice de microalertamientos fue\s+([0-9]+(?:[.,][0-9]+)?)/hora"),
        ("iah", r"indice de apnea hipopnea \(IAH\) fue de\s+([0-9]+(?:[.,][0-9]+)?)/h(?:ora)?"),
        ("gravedad_iah", r"IAH.*?considerad[oa][:\s]*([a-zA-Z]+)"),
        ("duracion_prom_ah", r"promedio de duracion de\s+([0-9]+(?:[.,][0-9]+)?)\s+segundos"),
        ("so2_prom_vigilia", r"saturacion de oxigeno promedio en vigilia fue de\s+([0-9]+(?:[.,][0-9]+)?)"),
        ("so2_prom_sueno_nrem", r"durante el sueno el promedio fue de\s+([0-9]+(?:[.,][0-9]+)?)\s*%?\s+en sueno no[-\s]?rem"),
        ("so2_prom_sueno_rem", r"y de\s+([0-9]+(?:[.,][0-9]+)?)\s*%?\s+en sueno rem"),
        ("s02_minima_ah", r"saturacion minima durante las apneas hipopneas fue de\s+([0-9]+(?:[.,][0-9]+)?)"),
        ("indice_desaturacion", r"indice de desaturacion[:\s]*([0-9]+(?:[.,][0-9]+)?)/h"),
        ("tiempo_bajo_90so2", r"permanecio\s+([0-9]+(?:[.,][0-9]+)?)\s+minutos de sueno con saturacion menor a 90%"),
        ("t90", r"T90[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%")
    ]

    for clave, patron in campos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.warning(f"{clave}: N/A")

    return datos

def procesar_psg_rtf(texto_relevante: str):
    logging.info("Procesando examen PSG RTF")
    datos = {}

    campos = [
        ("nombre_paciente", r"Nombre del paciente:\s*[|]?(.*?)\|Edad"),
        ("edad_paciente", r"Edad:\s*(\d{1,3})\s*anos"),
        ("id_paciente", r"Identificacion:\s*[|]?(\d{6,11})\|"),
        ("peso_paciente", r"Peso:\s*(\d{2,3})\s*Kg"),
        ("talla_paciente", r"Talla:\s*(\d{2,3})\s*cm"),
        ("imc_paciente", r"IMC:\s*(\d{2}(?:[.,]\d{1,2})?)"),
        ("cuello_paciente", r"Cuello:\s*(\d{2,3})\s*cm"),
        ("perimetro_abdominal", r"Perimetro Abdominal:\s*(\d{2,3})\s*cm"),
        ("md_solicita", r"Solicita:\s*[|]?(.*?)\|Empresa"),
        ("eps_paciente", r"Empresa:\s*[|]?(.*?)\|Fecha del estudio"),
        ("fecha_proced", r"Fecha del estudio:\s*(\d{1,2}/\d{1,2}/\d{4})"),
        ("escala_epworth", r"\(Escala de Epworth\s+(\d{1,2}/\d{2})\)"),
        ("eficiencia_sueno", r"eficiencia de sueno de\s*(\d{1,3}(?:[.,]\d+)?)%"),
        ("latencia_total", r"latencia de sueno fue:\s*(\d{1,3}(?:[.,]\d+)?)\s+minutos"),
        ("latencia_rem", r"latencia de sueno REM fue\s*(?:de\s*)?(\d{1,3}(?:[.,]\d+)?)\s+minutos"),
        ("sueno_profundo", r"porcentaje de sueno profundo \(estado 3\) de\s*(\d{1,3}(?:[.,]\d+)?)"),
        ("indice_microalertamientos", r"indice de microalertamientos fue\s*(\d{1,3}(?:[.,]\d+)?)/hora"),
        ("iah", r"indice de apnea hipopnea \(IAH\) fue de\s*(\d{1,3}(?:[.,]\d+)?)/hora"),
        ("gravedad_iah", r"IAH.*?:\s*(grave|moderado|leve|normal)"),
        ("duracion_prom_ah", r"promedio de duracion de\s*(\d{1,3}(?:[.,]\d+)?)\s+segundos"),
        ("so2_prom_vigilia", r"saturacion de oxigeno promedio en vigilia fue de\s*(\d{1,3})%"),
        ("so2_prom_sueno_nrem", r"promedio fue de\s*(\d{1,3})% en sueno No-REM"),
        ("so2_prom_sueno_rem", r"y de\s*(\d{1,3})% en sueno REM"),
        ("s02_minima_ah", r"promedio a\s*(\d{1,3})%"),
        ("indice_desaturacion", r"Indice de desaturacion:\s*(\d{1,3}(?:[.,]\d+)?)/h"),
        ("tiempo_bajo_90so2", r"Permanecio\s*(\d{1,3}(?:[.,]\d+)?)\s+minutos de sueno con saturacion menor a 90%"),
        ("t90", r"T90:\s*(\d{1,3}(?:[.,]\d+)?)\s*%")
    ]

    for clave, patron in campos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.info(f"{clave}: N/A")

    return datos
