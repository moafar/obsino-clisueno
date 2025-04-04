import logging
from utils.texto_utils import extraer_regex

def procesar_cpap_doc(texto_relevante: str):
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
        ("presion_inicial", r"inicio a una presion de\s*([0-9]+)\s*cm de agua"),
        ("presion_terapeutica", r"a una presion de\s*([0-9]+)\s*cm de agua se observo"),
        ("so2_prom_sueno", r"saturacion de oxigeno promedio durante el sueno.*?fue de\s*([0-9]+(?:[.,][0-9]+)?)%")
    ]

    for clave, patron in campos:
        valor = extraer_regex(texto_relevante, patron)
        datos[clave] = valor if valor else "N/A"
        if datos[clave] == "N/A":
            logging.info(f"{clave}: N/A")
    return datos

def procesar_cpap_docx(texto_relevante: str):
    logging.info("Procesando examen CPAP - formato DOC")
    
    def eliminar_cadenas_duplicadas(texto: str) -> str | None:
        
        texto = texto.strip()

        if not texto:
            return None
        
        # Primero intentar por frases completas (para casos como "Solicita:")
        palabras = texto.split()
        if len(palabras) > 5:  # Solo si es suficientemente largo para ser una frase
            # Buscar el patrón de frase completa
            for tam in range(len(palabras)//2, 0, -1):  # De mayor a menor
                patron = ' '.join(palabras[:tam])
                repeticiones = texto.count(patron)
                if repeticiones > 1 and patron * repeticiones in texto:
                    return patron
        
        # Luego la lógica original para palabras individuales
        for tam in range(1, len(palabras)//2 + 1):
            patron = palabras[:tam]
            repeticiones = len(palabras) // tam
            if patron * repeticiones == palabras[:tam*repeticiones]:
                return ' '.join(patron)
        
        # Eliminar duplicados consecutivos como último recurso
        resultado = []
        for palabra in palabras:
            if not resultado or palabra != resultado[-1]:
                resultado.append(palabra)
                
        return ' '.join(resultado)

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
            logging.info(f"{clave}: N/A")
    
    # Eliminar cadenas duplicadas en el nombre del paciente
    datos["nombre_paciente"] = eliminar_cadenas_duplicadas(datos["nombre_paciente"])
    datos["edad_paciente"] = eliminar_cadenas_duplicadas(datos["edad_paciente"])
    datos["md_solicita"] = eliminar_cadenas_duplicadas(datos["md_solicita"]) # No funciona pero lo dejo para no perder datos
    #datos["empresa"] = eliminar_cadenas_duplicadas(datos["empresa"]) # No funciona pero lo dejo para no perder datos

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
            logging.info(f"{clave}: N/A")
    return datos


