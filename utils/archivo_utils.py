from pathlib import Path
import os
import logging
from utils.texto_utils import extraer_texto_docx, extraer_texto_pdf, extraer_texto_rtf, extraer_texto_doc, normalizar_texto, extraer_subcadenas, determinar_tipos_examenes
from utils.procesar_psg import procesar_psg_doc, procesar_psg_rtf
import csv

def procesar_archivo(archivo: Path) -> None:
    """Lee el contenido de un archivo y retorna el texto extraído o None si hay un error."""
    
    _, extension = os.path.splitext(archivo)
    texto = ""

    try:
        extension = extension.lower()

        if extension == ".docx":
            texto = extraer_texto_docx(archivo)
        elif extension == ".pdf":
            texto = extraer_texto_pdf(archivo)
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

    texto_normalizado = normalizar_texto(texto)  # Normalizar el texto extraído
    
    tipos_examenes = determinar_tipos_examenes(texto_normalizado)  # <-- Llamada a la función para determinar el tipo de examen ***
    
    if not tipos_examenes:
        logging.warning(f"No se encontraron tipos de examen en el archivo {archivo}.")
        return

    cadenas_busqueda = {
        "BASAL": (r"INFORME\s+DE\s+POLISOMNOGRAFIA\s+BASAL", r"CONCLUSION(?:ES)?"),
        "CPAP": (r"INFORME\s+DE\s+POLISOMNOGRAFIA\s+EN\s+TITULACION\s+DE\s+CPAP", r"CONCLUSION(?:ES)?"),
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
                
                if tipo == "BASAL":
                    if extension == ".rtf":
                        resultados_basal = procesar_psg_rtf(texto_relevante)
                        ruta = "resultados_psg_rtf.csv"
                    elif extension == ".doc":
                        resultados_basal = procesar_psg_doc(texto_relevante)
                        ruta = "resultados_psg_doc.csv"
                    else:
                        logging.warning(f"Extensión no reconocida para archivo: {archivo}")
                        continue
                        
                    es_nuevo = not os.path.isfile(ruta) # Escribir encabezado si el archivo no existe
                    with open(ruta, mode='a', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=resultados_basal.keys()) 
                        if es_nuevo:
                            writer.writeheader()
                        writer.writerow(resultados_basal)
                    logging.info(f"** FIN ** Procesamiento Basal terminado para {archivo}")

                '''elif tipo == "CPAP":
                    procesar_cpap(texto_relevante)
                elif tipo == "DAM":
                    procesar_dam(texto_relevante)
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