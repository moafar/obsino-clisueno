import re
import logging

def determinar_tipos_examenes(texto: str) -> list:
    tipos_examen = {
        "BASAL": [r"INFORME\s+DE\s+POLISOMNOGRAFIA\s+BASAL"],
        "CPAP": [r"INFORME\s+DE\s+POLISOMNOGRAFIA\s+EN\s+TITULACION\s+DE\s+CPAP"],
        "DAM": [r"INFORME\s+DE\s+POLISOMNOGRAFIA\s+BASAL\s+CON\s+DISPOSITIVO(\s+DE\s+AVANCE)?\s+MANDIBULAR"],
        "BPAP": [r"INFORME\s+DE\s+POLISOMNOGRAFIA\s+EN\s+TITULACION\s+DE\s+B[I]?PAP"],
        "ACTIGRAFIA": [r"INFORME\s+ACTIGRAFIA"],
        "CAPNOGRAFIA": [r"INFORME\s+DE\s+CAPNOGRAFIA"],
        "AUTOCPAP": [r"INFORME\s+DE\s+TITULACION\s+CON\s+AUTO\s+CPAP"],
        "POLIGRAFIA": [r"INFORME\s+POLIGRAFIA\s+RESPIRATORIA"]
    }
    tipos_detectados = []
    for tipo, patrones in tipos_examen.items():
        for patron in patrones:
            if re.search(patron, texto, re.IGNORECASE):
                tipos_detectados.append(tipo)
                break
    if not tipos_detectados:
        tipos_detectados.append("DESCONOCIDO")
    return tipos_detectados


def extraer_regex(texto, patron, grupo=1):
    """
    Extrae el primer grupo de coincidencia de un patrón regex en un texto dado.

    :param texto: El texto en el que buscar el patrón.
    :param patron: La expresión regular a buscar.
    :param grupo: El grupo de coincidencia a devolver (por defecto es 1).
    :return: La coincidencia encontrada o None si no se encuentra.
    """
    match = re.search(patron, texto, re.IGNORECASE)
    if match:
        return match.group(grupo).strip()
    return None

def procesar_basal(texto_relevante: str):
    # Procesar el texto específico del examen basal
    logging.info("Procesando examen BASAL")
    #print(texto_relevante)
    datos = {}
        
    nombre_paciente = extraer_regex(texto_relevante, r"Nombre(?: del paciente)?:?\s*[|]?\s*([\wÁÉÍÓÚÑáéíóúñ-]+(?:\s+[\wÁÉÍÓÚÑáéíóúñ-]+)*)(?=\s*[|]?\s*Edad\b)")
    if nombre_paciente:
        logging.info(f"nombre_paciente: {nombre_paciente}")
        datos["nombre_paciente"] = nombre_paciente
        
    edad_paciente = extraer_regex(texto_relevante, r"Edad\s*[:|]?\s*([\d]+(?:[.,]\d+)?)\s*(años|anos)?")
    if edad_paciente:
        logging.info(f"edad_paciente: {edad_paciente}")
        datos["edad_paciente"] = edad_paciente
        
    id_paciente = extraer_regex(texto_relevante, r"Id\s*[:|]?\s*(\d{7,10})")
    if id_paciente:
        logging.info(f"id_paciente: {id_paciente}")
        datos["id_paciente"] = id_paciente
        
    peso_paciente = extraer_regex(texto_relevante, r"Peso\s*[:|]?\s*([\d]+(?:[.,]\d+)?)\s*kg")
    if peso_paciente:
        logging.info(f"peso_paciente: {peso_paciente}")
        datos["peso_paciente"] = peso_paciente
        
    talla_paciente = extraer_regex(texto_relevante, r"Talla\s*[:|]?\s*([\d]+(?:[.,]\d+)?)\s*cm")
    if talla_paciente:
        logging.info(f"talla_paciente: {talla_paciente}")
        datos["talla_paciente"] = talla_paciente
        
    imc_paciente = extraer_regex(texto_relevante, r"IMC\s*[:|]?\s*([\d]+(?:[.,]\d+)?)")
    if imc_paciente:
        logging.info(f"imc_paciente: {imc_paciente}")
        datos["imc_paciente"] = imc_paciente
        
    cuello_paciente = extraer_regex(texto_relevante, r"Cuello\s*[:|]?\s*([\d]+(?:[.,]\d+)?)\s*cm")
    if cuello_paciente:
        logging.info(f"cuello_paciente: {cuello_paciente}")
        datos["cuello_paciente"] = cuello_paciente
        
    md_solicita = extraer_regex(texto_relevante, r"Solicita\s*[:|]?\s*(Dra\.\s*[\w\sÁÉÍÓÚÑáéíóúñ.]+-\s*[\w\sÁÉÍÓÚÑáéíóúñ]+)\s*Empresa")
    if md_solicita:
        logging.info(f"md_solicita: {md_solicita}")
        datos["md_solicita"] = md_solicita
        
    eps_paciente = extraer_regex(texto_relevante, r"Empresa\s*[:|]?\s*(.*?)\s*Fecha")
    if eps_paciente:
        logging.info(f"eps_paciente: {eps_paciente}")
        datos["eps_paciente"] = eps_paciente
        
    fecha_proced = extraer_regex(texto_relevante, r"Fecha\s*[:|]?\s*(\d{2}[/-]\d{2}[/-]\d{4}|\d{4}[/-]\d{2}[/-]\d{2})(?=\s*PROCEDIMIENTO)")
    if fecha_proced:
        logging.info(f"fecha_proced: {fecha_proced}")
        datos["fecha_proced"] = fecha_proced
        
    escala_epworth = extraer_regex(texto_relevante, r"Escala\s+de\s+Epworth\s*[:|]?\s*(\d{1,2}\/\d{2})")
    if escala_epworth:
        logging.info(f"escala_epworth: {escala_epworth}")
        datos["escala_epworth"] = escala_epworth
        
    eficiencia_sueno = extraer_regex(texto_relevante, r"eficiencia de sueno de (\d{1,3}(?:[.,]\d{1})?)\s*%")
    if eficiencia_sueno:
        logging.info(f"eficiencia_sueno: {eficiencia_sueno}")
    datos["eficiencia_sueno"] = eficiencia_sueno
        
    latencia_total = extraer_regex(texto_relevante, r"latencia de sueno fue(?: de)?[:\s]*([0-9]+[.,][0-9]+)\s+minutos")
    if latencia_total:
        logging.info(f"latencia_total: {latencia_total}")
        datos["latencia_total"] = latencia_total
        
    latencia_rem = extraer_regex(texto_relevante, r"latencia de sueno REM(?: fue)?(?: de)?[:|]?\s*([0-9]+[.,][0-9]+)\s+minutos")
    if latencia_rem:
        logging.info(f"latencia_rem: {latencia_rem}")
        datos["latencia_rem"] = latencia_rem
        
    sueno_profundo = extraer_regex(texto_relevante, r"porcentaje de sueno profundo\s+\(estadio 3\)\s+de\s+([0-9]+(?:[.,][0-9]+)?)%")
    if sueno_profundo:
        logging.info(f"sueno_profundo: {sueno_profundo}")
        datos["sueno_profundo"] = sueno_profundo
        
    indice_microalertamientos = extraer_regex(texto_relevante, r"indice de microalertamientos fue\s+([0-9]+(?:[.,][0-9]+)?)/hora")
    if indice_microalertamientos:
        logging.info(f"indice_microalertamientos: {indice_microalertamientos}")
        datos["indice_microalertamientos"] = indice_microalertamientos
        
    iah = extraer_regex(texto_relevante, r"indice de apnea hipopnea \(IAH\) fue de\s+([0-9]+(?:[.,][0-9]+)?)/h[ora]?")
    if iah:
        logging.info(f"iah: {iah}")
        datos["iah"] = iah
        
    gravedad_iah = extraer_regex(texto_relevante, r"IAH\) fue de \d+(?:[.,]\d+)?/(?:h|hora) considerado[:\s]*([a-z]+)")
    if gravedad_iah:
        logging.info(f"gravedad_iah: {gravedad_iah}")
        datos["gravedad_iah"] = gravedad_iah
        
    duracion_prom_ah = extraer_regex(texto_relevante, r"promedio de duracion de\s+([0-9]+(?:[.,][0-9]+)?)\s+segundos")
    if duracion_prom_ah:
        logging.info(f"duracion_prom_ah: {duracion_prom_ah}")
        datos["duracion_prom_ah"] = duracion_prom_ah
        
    so2_prom_vigilia = extraer_regex(texto_relevante, r"saturacion de oxigeno promedio en vigilia fue de\s+([0-9]+(?:[.,][0-9]+)?)")
    if so2_prom_vigilia:
        logging.info(f"so2_prom_vigilia: {so2_prom_vigilia}")
        datos["so2_prom_vigilia"] = so2_prom_vigilia
        
    so2_prom_sueno_nrem = extraer_regex(texto_relevante, r"durante el sueno el promedio fue de\s+([0-9]+(?:[.,][0-9]+)?)\s*%?\s+en sueno no[-\s]?rem")
    if so2_prom_sueno_nrem:
        logging.info(f"so2_prom_sueno_nrem: {so2_prom_sueno_nrem}")
        datos["so2_prom_sueno_nrem"] = so2_prom_sueno_nrem
        
    so2_prom_sueno_rem = extraer_regex(texto_relevante, r"y de\s+([0-9]+(?:[.,][0-9]+)?)\s*%?\s+en sueno rem")
    if so2_prom_sueno_rem:
        logging.info(f"so2_prom_sueno_rem: {so2_prom_sueno_rem}")
        datos["so2_prom_sueno_rem"] = so2_prom_sueno_rem
        
    s02_minima_ah = extraer_regex(texto_relevante, r"saturacion minima durante las apneas hipopneas fue de\s+([0-9]+(?:[.,][0-9]+)?)")
    if s02_minima_ah:
        logging.info(f"s02_minima_ah: {s02_minima_ah}")
        datos["s02_minima_ah"] = s02_minima_ah
        
    indice_desaturacion = extraer_regex(texto_relevante, r"indice de desaturacion[:\s]*([0-9]+(?:[.,][0-9]+)?)/h")
    if indice_desaturacion:
        logging.info(f"indice_desaturacion: {indice_desaturacion}")
        datos["indice_desaturacion"] = indice_desaturacion
        
    tiempo_bajo_90so2 = extraer_regex(texto_relevante, r"permanecio\s+([0-9]+(?:[.,][0-9]+)?)\s+minutos de sueno con saturacion menor a 90%")
    if tiempo_bajo_90so2:
        logging.info(f"tiempo_bajo_90so2: {tiempo_bajo_90so2}")
        datos["tiempo_bajo_90so2"] = tiempo_bajo_90so2
        
    t90 = extraer_regex(texto_relevante, r"T90[:\s]*([0-9]+(?:[.,][0-9]+)?)\s*%")
    if t90:
        logging.info(f"t90: {t90}")
        datos["t90"] = t90
        
    return datos
    
def procesar_cpap(texto_relevante: str):
    # Procesar el texto específico del examen CPAP
    print(f"Procesando examen CPAP con texto: {texto_relevante}")
    
    datos = {}
    
    VARIABLE = extraer_regex(texto_relevante, r"REGEX")
    if VARIABLE:
        logging.info(f"VARIABLE: {VARIABLE}")
        datos["VARIABLE"] = VARIABLE
    
def procesar_dam(texto_relevante: str):
    # Procesar el texto específico del examen DAM
    print(f"Procesando examen DAM con texto: {texto_relevante}")
    
    datos = {}
    
    VARIABLE = extraer_regex(texto_relevante, r"REGEX")
    if VARIABLE:
        logging.info(f"VARIABLE: {VARIABLE}")
        datos["VARIABLE"] = VARIABLE
    
def procesar_bpap(texto_relevante: str):
    # Procesar el texto específico del examen BPAP
    print(f"Procesando examen BPAP con texto: {texto_relevante}")
    
    datos = {}
    
    VARIABLE = extraer_regex(texto_relevante, r"REGEX")
    if VARIABLE:
        logging.info(f"VARIABLE: {VARIABLE}")
        datos["VARIABLE"] = VARIABLE
    
def procesar_actigrafia(texto_relevante: str):
    # Procesar el texto específico del examen de actigrafía
    print(f"Procesando examen de actigrafía con texto: {texto_relevante}")
    
    datos = {}
    
    VARIABLE = extraer_regex(texto_relevante, r"REGEX")
    if VARIABLE:
        logging.info(f"VARIABLE: {VARIABLE}")
        datos["VARIABLE"] = VARIABLE
    
def procesar_capnografia(texto_relevante: str):
    # Procesar el texto específico del examen de capnografía
    print(f"Procesando examen de capnografía con texto: {texto_relevante}")
    
    datos = {}
    
    VARIABLE = extraer_regex(texto_relevante, r"REGEX")
    if VARIABLE:
        logging.info(f"VARIABLE: {VARIABLE}")
        datos["VARIABLE"] = VARIABLE
    
def procesar_autocpap(texto_relevante: str):
    # Procesar el texto específico del examen de auto CPAP
    print(f"Procesando examen de auto CPAP con texto: {texto_relevante}")
    
    datos = {}
    
    VARIABLE = extraer_regex(texto_relevante, r"REGEX")
    if VARIABLE:
        logging.info(f"VARIABLE: {VARIABLE}")
        datos["VARIABLE"] = VARIABLE
    
    
def procesar_poligrafia(texto_relevante: str):
    # Procesar el texto específico del examen de poligrafía
    print(f"Procesando examen de poligrafía con texto: {texto_relevante}")
    
    datos = {}
    
    VARIABLE = extraer_regex(texto_relevante, r"REGEX")
    if VARIABLE:
        logging.info(f"VARIABLE: {VARIABLE}")
        datos["VARIABLE"] = VARIABLE
    
    