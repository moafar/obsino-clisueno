from pathlib import Path
import os
import logging
from commons.texto_utils import extraer_texto_docx, extraer_texto_rtf, extraer_texto_doc, normalizar_texto, extraer_subcadenas, determinar_tipos_examenes
from src.basal.procesar_basal import procesar_basal_doc, procesar_basal_rtf
from src.xpap.procesar_xpap import procesar_xpap_doc, procesar_xpap_rtf, procesar_xpap_docx
# from dam.procesar_dam import procesar_dam_doc, procesar_dam_rtf
# from basal.xpap.procesar_bpap import procesar_bpap_doc, procesar_bpap_rtf
# from actigrafia.procesar_actigrafia import procesar_actigrafia_doc
# from capnografia.procesar_capnografia import procesar_capnografia_doc, procesar_capnografia_rtf
# from autocpap.procesar_autocpap import procesar_autocpap_docx
# from poligrafia.procesar_poligrafia import procesar_poligrafia_docx
import csv

def procesar_archivo(archivo: Path) -> None:
    """Lee el contenido de un archivo y retorna el texto extraído o None si hay un error."""

    # Excluir examenes con OXIGENO
    nombre = archivo.name.upper()
    patrones_excluir = ["O2", "OXIG", "OXÍG", "OXIGENO", "OXÍGENO"]
    if any(pat in nombre for pat in patrones_excluir):
        logging.info(f"Archivo excluido por patrón OXIGENO en filename: {archivo.name}")
        return None
    
    _, extension = os.path.splitext(archivo)
    texto = ""

    try:
        extension = extension.lower()

        if extension == ".docx":
            texto = extraer_texto_docx(archivo)
        elif extension == ".rtf":
            texto = extraer_texto_rtf(archivo)
        elif extension == ".doc":
            texto = extraer_texto_doc(archivo)
        else:
            logging.error(f"Extensión de archivo no soportada: {extension}")
            return None        
        
    except Exception as e:
        logging.error(f"Error inesperado al leer {archivo} $$ {e}")
        return None

    #print(texto)  # Para verificar el texto extraído
    #logging.debug(f"Texto extraído: {texto}")

    texto_normalizado = normalizar_texto(texto)  # Normalizar el texto extraído
    #print(texto_normalizado)  # Para verificar el texto normalizado
    logging.debug(f"Texto normalizado: {texto_normalizado}")
    
    tipos_examenes = determinar_tipos_examenes(texto_normalizado)  # <-- Llamada a la función para determinar el tipo de examen ***
    #print(tipos_examenes)  # Para verificar los tipos de examen encontrados
    
    if not tipos_examenes:
        logging.warning(f"No se encontraron tipos de examen en el archivo {archivo}.")
        return

    # Cadenas para extraer subcadenas (texto relevante) según el tipo de examen
    cadenas_busqueda = {
        "BASAL": (r"INFORME\s+DE\s+POLISOMNOGRAFIA\s+BASAL", r"Saturacion\s+O2\s+Minima\s+durante\s+el\s+sueno"),
        "CPAP": (r"^", r"$"),
        "DAM": (r"INFORME\s+DE\s+POLISOMNOGRAFIA\s+BASAL\s+CON\s+DISPOSITIVO\s+(?:DE\s+AVANCE\s+)?MANDIBULAR", r"CONCLUSION(?:ES)?"),
        "BPAP": (r"^", r"$"),
        "ACTIGRAFIA": (r"Fecha", r"ESTADISTICAS DIARIAS"),
        "CAPNOGRAFIA": (r"INFORME\s+DE\s+CAPNOGRAFIA", r"CONCLUSION(?:ES)?"),
        "AUTOCPAP": (r"^", r"Informe\s+de\s+cumplimiento"),
        "POLIGRAFIA": (r"^", r"Indicacion\s+del\s+estudio")
    }

    for tipo in tipos_examenes:
        logging.info(f"Procesando examen de {tipo}")
        if tipo in cadenas_busqueda:
            inicio, fin = cadenas_busqueda[tipo]
            logging.debug(f"Buscando subcadenas para {tipo}: Inicio: {inicio}, Fin: {fin}")
            texto_relevante = extraer_subcadenas(texto_normalizado, inicio, fin) # <-- Llamada a la función para extraer SUBCADENAS ***
            if texto_relevante:
                logging.info(f"Subcadena encontrada para {tipo}: {texto_relevante}")
                
                if tipo == "BASAL":
                    logging.info(f"** INICIO ** Procesando archivo BASAL válido: {archivo}")

                    if extension == ".rtf":
                        resultados_basal = procesar_basal_rtf(texto_relevante, archivo)
                        nombre_archivo = "resultados_basal_rtf.csv"
                    elif extension == ".doc":
                        resultados_basal = procesar_basal_doc(texto_relevante, archivo)
                        nombre_archivo = "resultados_basal_doc.csv"
                    else:
                        logging.warning(f"Extensión no reconocida para archivo: {archivo}")
                        continue

                    directorio_salida = "output"
                    os.makedirs(directorio_salida, exist_ok=True)
                    ruta = os.path.join(directorio_salida, nombre_archivo)

                    es_nuevo = not os.path.isfile(ruta)
                    with open(ruta, mode='a', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=resultados_basal.keys())
                        if es_nuevo:
                            writer.writeheader()
                        writer.writerow(resultados_basal)

                    logging.info(f"** FIN ** Procesamiento Basal terminado para {archivo}")
                    
                
                if tipo == "CPAP" or tipo == "BPAP":
                    logging.info(f"** INICIO ** Procesando archivo XPAP válido: {archivo}")
                    
                    if extension == ".rtf":
                        resultados_xpap = procesar_xpap_rtf(texto_relevante, archivo)
                        nombre_archivo = "resultados_xpap_rtf.csv"
                    elif extension == ".doc":
                        resultados_xpap = procesar_xpap_doc(texto_relevante, archivo)
                        nombre_archivo = "resultados_xpap_doc.csv"
                    elif extension == ".docx":
                        resultados_xpap = procesar_xpap_docx(texto_relevante, archivo)
                        nombre_archivo = "resultados_xpap_docx.csv"
                    else:
                        logging.warning(f"Extensión no reconocida para archivo: {archivo}")
                        continue

                    directorio_salida = "output"
                    os.makedirs(directorio_salida, exist_ok=True)
                    ruta = os.path.join(directorio_salida, nombre_archivo)
                    
                    es_nuevo = not os.path.isfile(ruta)
                    with open(ruta, mode='a', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=resultados_xpap.keys()) 
                        if es_nuevo:
                            writer.writeheader()
                        writer.writerow(resultados_xpap)
                    logging.info(f"** FIN ** Procesamiento XPAP terminado para {archivo}")

                '''
                elif tipo == "DAM": 
                    logging.info(f"** INICIO ** Procesando archivo DAM válido: {archivo}")
                    if extension == ".rtf":
                        resultados_dam = procesar_dam_rtf(texto_relevante)
                        ruta = "resultados_dam_rtf.csv"
                    elif extension == ".doc":   
                        resultados_dam = procesar_dam_doc(texto_relevante)
                        ruta = "resultados_dam_doc.csv"
                    else:
                        logging.warning(f"Extensión no reconocida para archivo: {archivo}")
                        continue
                    es_nuevo = not os.path.isfile(ruta)
                    with open(ruta, mode='a', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=resultados_dam.keys()) 
                        if es_nuevo:
                            writer.writeheader()
                        writer.writerow(resultados_dam)
                    logging.info(f"** FIN ** Procesamiento DAM terminado para {archivo}")

                elif tipo == "BPAP": 
                    logging.info(f"** INICIO ** Procesando archivo BPAP válido: {archivo}")
                    if extension == ".rtf":
                        resultados_bpap = procesar_bpap_rtf(texto_relevante)
                        ruta = "resultados_bpap_rtf.csv"
                    elif extension == ".doc":
                        resultados_bpap = procesar_bpap_doc(texto_relevante)
                        ruta = "resultados_bpap_doc.csv"
                    else:
                        logging.warning(f"Extensión no reconocida para archivo: {archivo}")
                        continue
                    es_nuevo = not os.path.isfile(ruta)
                    with open(ruta, mode='a', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=resultados_bpap.keys()) 
                        if es_nuevo:
                            writer.writeheader()
                        writer.writerow(resultados_bpap)
                    logging.info(f"** FIN ** Procesamiento BPAP terminado para {archivo}")

                elif tipo == "ACTIGRAFIA":
                    logging.info(f"** INICIO ** Procesando archivo ACTIGRAFIA válido: {archivo}")
                    if extension == ".doc":
                        resultados_actigrafia = procesar_actigrafia_doc(texto_relevante)
                        ruta = "resultados_actigrafia_doc.csv"
                    else:
                        logging.warning(f"Extensión no reconocida para archivo: {archivo}")
                        continue
                    es_nuevo = not os.path.isfile(ruta)
                    with open(ruta, mode='a', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=resultados_actigrafia.keys()) 
                        if es_nuevo:
                            writer.writeheader()
                        writer.writerow(resultados_actigrafia)
                    logging.info(f"** FIN ** Procesamiento BPAP terminado para {archivo}")

                elif tipo == "CAPNOGRAFIA":
                    logging.info(f"** INICIO ** Procesando archivo CAPNOGRAFIA válido: {archivo}")
                    if extension == ".rtf":
                        resultados_capnografia = procesar_capnografia_rtf(texto_relevante)
                        ruta = "resultados_capnografia_rtf.csv"
                    elif extension == ".doc":
                        resultados_capnografia = procesar_capnografia_doc(texto_relevante)
                        ruta = "resultados_capnografia_doc.csv"
                    else:
                        logging.warning(f"Extensión no reconocida para archivo: {archivo}")
                        continue
                    es_nuevo = not os.path.isfile(ruta)
                    with open(ruta, mode='a', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=resultados_capnografia.keys()) 
                        if es_nuevo:
                            writer.writeheader()
                        writer.writerow(resultados_capnografia)
                    logging.info(f"** FIN ** Procesamiento BPAP terminado para {archivo}")

                                
                elif tipo == "AUTOCPAP":
                    logging.info(f"** INICIO ** Procesando archivo AUTOCPAP válido: {archivo}")
                    if extension == ".docx":
                        resultados_autocpap = procesar_autocpap_docx(texto_relevante)
                        ruta = "resultados_autocpap_docx.csv"
                    else:
                        logging.warning(f"Extensión no reconocida para archivo: {archivo}")
                        continue
                    es_nuevo = not os.path.isfile(ruta)
                    with open(ruta, mode='a', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=resultados_autocpap.keys()) 
                        if es_nuevo:
                            writer.writeheader()
                        writer.writerow(resultados_autocpap)
                    logging.info(f"** FIN ** Procesamiento AUTOCPAP terminado para {archivo}")

                
                elif tipo == "POLIGRAFIA":
                    logging.info(f"** INICIO ** Procesando archivo POLIGRAFIA válido: {archivo}")
                    if extension == ".docx":
                        resultados_poligrafia = procesar_poligrafia_docx(texto_relevante)
                        ruta = "resultados_poligrafia_docx.csv"
                    else:
                        logging.warning(f"Extensión no reconocida para archivo: {archivo}")
                        continue
                    es_nuevo = not os.path.isfile(ruta)
                    with open(ruta, mode='a', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=resultados_poligrafia.keys()) 
                        if es_nuevo:
                            writer.writeheader()
                        writer.writerow(resultados_poligrafia)
                    logging.info(f"** FIN ** Procesamiento POLIGRAFIA terminado para {archivo}")
                
                else:
                    logging.warning(f"Tipo de examen no manejado: {tipo}")
                    continue
                '''
            else:
                logging.error(f"No se encontraron subcadenas para {tipo} en el archivo {archivo}.")