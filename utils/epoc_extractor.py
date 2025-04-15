import os
import openpyxl
import pandas as pd
import re
from tqdm import tqdm
import sys
import warnings

"""
Este script explora una carpeta y sus subcarpetas en busca de archivos XLSX que contengan en su nombre las palabras 'EGRESO' o 'SEGUIMIENTO'.

****** Se ejecuta con 'python epoc.py <ruta_a_analizar>' ******

El script realiza las siguientes acciones:
1. Recibe una ruta como argumento.
2. Explora la ruta y sus subcarpetas en busca de archivos XLSX que contengan 'EGRESO' o 'SEGUIMIENTO' en su nombre.
3. Para cada archivo encontrado, realiza las siguientes validaciones y extracciones:
  3.1. **Validaciones:**
  - La celda G9 debe contener 'SI'.
  - La celda B7 debe contener la palabra 'EPOC' en cualquier parte de su contenido.
  -> Si no cumple alguna, se clasifica como 'No cumple criterios'.

  3.2. **Extracción de datos para archivos que cumplen los criterios:**
    - Se extraen datos generales del paciente:
      - id_paciente (G6)
      - edad_paciente (H5)
      - fecha_inicio (G7)
      - fecha_fin (G8)
      - eps (B6)
    - Se extraen datos clínicos:
      - c6m_inicial (C16), c6m_final (D16), c6m_cambio (E16)
      - mmrc_inicial (C28), mmrc_final (D28), mmrc_cambio (E28)
      - cat_inicial (C31), cat_final (D31), cat_cambio (E31)
      - exacerb_inicial (H32), exacerb_final (I32), exacerb_cambio (J32)
      - fev1_pred_porc_post (E36)
    - Se extrae información de resistencia:
      - resist_inicial (G18), resist_cambio (J18)
      - resist_final dependerá del tipo de modalidad:
        - Si en B1 aparece la palabra 'TELE', se toma de H18
        - Si no aparece 'TELE', se toma de I18
    - Se clasifica el archivo en 'TELE' o 'PRESENCIAL' según el contenido de B1.

  3.3. **Resultados:**
    - Los datos de archivos que cumplen los criterios se guardan en 'resultados_xlsx.csv'.
    - Los datos de archivos que no cumplen los criterios se guardan en 'archivos_no_cumplen_criterios.csv', incluyendo:
      - Ruta del archivo.
      - Razón por la cual no cumple los criterios.
      - Contenido de la celda B7.
"""

def explorar_archivos_xlsx(ruta_raiz):
    if not os.path.exists(ruta_raiz):
        print(f"Error: La ruta '{ruta_raiz}' no existe.")
        return
    
    ruta_raiz = os.path.abspath(ruta_raiz)
    print(f"Ruta normalizada: '{ruta_raiz}'")
    
    archivos_xlsx = []
    data = []
    no_cumplen_data = []
    
    for root, _, files in os.walk(ruta_raiz):
        for file in files:
            if ("EGRESO" in file or "SEGUIMIENTO" in file) and file.endswith(".xlsx"):
                archivos_xlsx.append(os.path.join(root, file))
    
    if archivos_xlsx:
        print("Procesando archivos...")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # Ignorar warnings
            for ruta_archivo in tqdm(archivos_xlsx, desc="Explorando archivos XLSX", unit="archivo"):
                try:
                    wb = openpyxl.load_workbook(ruta_archivo, data_only=True)
                    sheet = wb.active
                    
                    valor_g9 = sheet["G9"].value
                    valor_b7 = sheet["B7"].value
                    valor_b1 = str(sheet["B1"].value).upper() if sheet["B1"].value else ""
                    modalidad = "TELE" if "TELE" in valor_b1 else "PRESENCIAL"
                    
                    if valor_g9 == "SI" and valor_b7 and re.search(r"EPOC", str(valor_b7).upper()):
                        id_paciente = sheet["G6"].value
                        edad_paciente = sheet["H5"].value
                        fecha_inicio = sheet["G7"].value
                        fecha_fin = sheet["G8"].value
                        eps = sheet["B6"].value
                        
                        c6m_inicial = sheet["C16"].value
                        c6m_final = sheet["D16"].value
                        c6m_cambio = sheet["E16"].value
                        mmrc_inicial = sheet["C28"].value
                        mmrc_final = sheet["D28"].value
                        mmrc_cambio = sheet["E28"].value
                        cat_inicial = sheet["C31"].value
                        cat_final = sheet["D31"].value
                        cat_cambio = sheet["E31"].value
                        exacerb_inicial = sheet["H32"].value
                        exacerb_final = sheet["I32"].value
                        exacerb_cambio = sheet["J32"].value
                        fev1_pred_porc_post = sheet["E36"].value
                        resist_inicial = sheet["G18"].value
                        resist_cambio = sheet["J18"].value
                        
                        resist_final = sheet["H18"].value if modalidad == "TELE" else sheet["I18"].value
                        
                        data.append({
                            "ruta_archivo": ruta_archivo,
                            "id_paciente": id_paciente,
                            "edad_paciente": edad_paciente,
                            "fecha_inicio": fecha_inicio,
                            "fecha_fin": fecha_fin,
                            "eps": eps,
                            "c6m_inicial": c6m_inicial,
                            "c6m_final": c6m_final,
                            "c6m_cambio": c6m_cambio,
                            "mmrc_inicial": mmrc_inicial,
                            "mmrc_final": mmrc_final,
                            "mmrc_cambio": mmrc_cambio,
                            "cat_inicial": cat_inicial,
                            "cat_final": cat_final,
                            "cat_cambio": cat_cambio,
                            "exacerb_inicial": exacerb_inicial,
                            "exacerb_final": exacerb_final,
                            "exacerb_cambio": exacerb_cambio,
                            "fev1_pred_porc_post": fev1_pred_porc_post,
                            "resist_inicial": resist_inicial,
                            "resist_final": resist_final,
                            "resist_cambio": resist_cambio,
                            "modalidad": modalidad
                        })
                    else:
                        razon = []
                        if valor_g9 != "SI":
                            razon.append("No cumple con 'SI' en G9")
                        if not valor_b7 or not re.search(r"EPOC", str(valor_b7).upper()):
                            razon.append("No cumple con 'EPOC' en B7")
                        no_cumplen_data.append({
                            "ruta_archivo": ruta_archivo,
                            "razon": ", ".join(razon),
                            "contenido_B7": valor_b7
                        })
                except Exception as e:
                    print(f"Error al procesar {ruta_archivo}: {e}")
    
    if no_cumplen_data:
        df_no_cumplen = pd.DataFrame(no_cumplen_data)
        no_cumplen_csv_path = os.path.join(ruta_raiz, "archivos_no_cumplen_criterios.csv")
        df_no_cumplen.to_csv(no_cumplen_csv_path, index=False)
        print("Archivo 'archivos_no_cumplen_criterios.csv' generado correctamente.")
    
    if data:
        df = pd.DataFrame(data)
        csv_path = os.path.join(ruta_raiz, "resultados_xlsx.csv")
        df.to_csv(csv_path, index=False)
        print("Resultados extraídos y guardados en 'resultados_xlsx.csv'.")
    else:
        print("No se encontraron datos que cumplan los criterios.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python script.py <ruta_a_analizar>")
    else:
        print(f"Ruta recibida: '{sys.argv[1]}'")
        explorar_archivos_xlsx(sys.argv[1])
