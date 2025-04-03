from pathlib import Path
import os
import logging
from utils.texto_utils import extraer_texto_docx, extraer_texto_rtf, extraer_texto_doc, normalizar_texto, extraer_subcadenas, determinar_tipos_examenes
from utils.procesar_psg import procesar_psg_doc, procesar_psg_rtf
from utils.procesar_cpap import procesar_cpap_doc, procesar_cpap_rtf, procesar_cpap_docx
from utils.procesar_dam import procesar_dam_doc, procesar_dam_rtf
import csv

def procesar_archivo(archivo: Path) -> None:
    """Lee el contenido de un archivo y retorna el texto extraído o None si hay un error."""
    
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
        logging.error(f"Error inesperado al leer {archivo}: {e}")
        return None

    #print(texto)  # Para verificar el texto extraído
    texto_normalizado = normalizar_texto(texto)  # Normalizar el texto extraído
    
    #print(texto_normalizado)  # Para verificar el texto normalizado
    tipos_examenes = determinar_tipos_examenes(texto_normalizado)  # <-- Llamada a la función para determinar el tipo de examen ***

    if not tipos_examenes:
        logging.warning(f"No se encontraron tipos de examen en el archivo {archivo}.")
        return

    # Cadenas para extraer subcadenas (texto relevante) según el tipo de examen
    cadenas_busqueda = {
        "BASAL": (r"INFORME\s+DE\s+POLISOMNOGRAFIA\s+BASAL", r"CONCLUSION(?:ES)?"),
        "CPAP": (r"^", r"CONCLUSION(?:ES)?"),
        "DAM": (r"INFORME\s+DE\s+POLISOMNOGRAFIA\s+BASAL\s+CON\s+DISPOSITIVO\s+(?:DE\s+AVANCE\s+)?MANDIBULAR", r"CONCLUSION(?:ES)?"),
        "BPAP": (r"INFORME\s+DE\s+POLISOMNOGRAFIA\s+EN\s+TITULACION\s+DE\s+B[I]?PAP", r"CONCLUSION(?:ES)?"),
        "ACTIGRAFIA": (r"^", r"CONCLUSION(?:ES)?"),
        "CAPNOGRAFIA": (r"INFORME\s+DE\s+CAPNOGRAFIA", r"CONCLUSION(?:ES)?"),
        "AUTOCPAP": (r"INFORME\s+DE\s+TITULACION\s+CON\s+AUTO\s+CPAP", r"CONCLUSION(?:ES)?"),
        "POLIGRAFIA": (r"INFORME\s+POLIGRAFIA\s+RESPIRATORIA", r"GRAFICOS")
    }

    for tipo in tipos_examenes:
        logging.info(f"Procesando examen de {tipo}")
        if tipo in cadenas_busqueda:
            inicio, fin = cadenas_busqueda[tipo]
            texto_relevante = extraer_subcadenas(texto_normalizado, inicio, fin) # <-- Llamada a la función para extraer subcadenas ***
            if texto_relevante:
                logging.info(f"Subcadena encontrada para {tipo}: {texto_relevante}")
                #print(texto_relevante)  # Para verificar el texto relevante extraído
                '''
                if tipo == "BASAL":
                    if extension == ".rtf":
                        resultados_psg = procesar_psg_rtf(texto_relevante)
                        ruta = "resultados_psg_rtf.csv"
                    elif extension == ".doc":
                        resultados_psg = procesar_psg_doc(texto_relevante)
                        ruta = "resultados_psg_doc.csv"
                    else:
                        logging.warning(f"Extensión no reconocida para archivo: {archivo}")
                        continue
                    
                    es_nuevo = not os.path.isfile(ruta) # Escribir encabezado si el archivo no existe
                    with open(ruta, mode='a', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=resultados_psg.keys()) 
                        if es_nuevo:
                            writer.writeheader()
                        writer.writerow(resultados_psg)
                    logging.info(f"** FIN ** Procesamiento Basal terminado para {archivo}")
                    
                elif tipo == "CPAP":
                    logging.info(f"** INICIO ** Procesando archivo CPAP válido: {archivo}")
                    
                    if extension == ".rtf":
                        resultados_cpap = procesar_cpap_rtf(texto_relevante)
                        ruta = "resultados_cpap_rtf.csv"
                    elif extension == ".doc":
                        resultados_cpap = procesar_cpap_doc(texto_relevante)
                        ruta = "resultados_cpap_doc.csv"
                    elif extension == ".docx":
                        resultados_cpap = procesar_cpap_docx(texto_relevante)
                        ruta = "resultados_cpap_docx.csv"
                    else:
                        logging.warning(f"Extensión no reconocida para archivo: {archivo}")
                        continue
                    
                    es_nuevo = not os.path.isfile(ruta)
                    with open(ruta, mode='a', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=resultados_cpap.keys()) 
                        if es_nuevo:
                            writer.writeheader()
                        writer.writerow(resultados_cpap)
                    logging.info(f"** FIN ** Procesamiento CPAP terminado para {archivo}")
                '''
                    
                
                if tipo == "DAM": # Cambiar a elif cuando esté terminado DAM para encadenar con PSG y CPAP
                    logging.info(f"** INICIO ** Procesando archivo DAM válido: {archivo}")
                    if extension == ".rtf":
                        resultados_dam = procesar_dam_rtf(texto_relevante)
                        print("\n",resultados_dam)
                        ruta = "resultados_dam_rtf.csv"
                    elif extension == ".doc":   
                        resultados_dam = procesar_dam_doc(texto_relevante)
                        print("\n",resultados_dam)
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
                    
                    
                '''
                elif tipo == "BPAP":
                    procesar_bpap(texto_relevante)
                elif tipo == "ACTIGRAFIA":
                    procesar_actigrafia(texto_relevante)
                elif tipo == "CAPNOGRAFIA":
                    procesar_capnografia(texto_relevante)
                elif tipo == "AUTOCPAP":
                    procesar_autocpap(texto_relevante)
                elif tipo == "POLIGRAFIA":
                    procesar_poligrafia(texto_relevante)'''
            else:
                logging.error(f"No se encontraron subcadenas para {tipo} en el archivo {archivo}.")