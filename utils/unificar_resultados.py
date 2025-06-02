import os
import pandas as pd
import glob
from IPython.display import display, HTML
import uuid

carpeta = "/home/rom/clisueno/output"

# Función que recorre la carpeta y analiza los archivos CSV para comparar estructura
def analizar_csv(carpeta):
    # Buscar todos los archivos CSV en la carpeta
    archivos_csv = glob.glob(os.path.join(carpeta, "*.csv"))
    
    if not archivos_csv:
        print("No se encontraron archivos CSV en la carpeta.")
        return
    
    print(f"Se detectaron {len(archivos_csv)} archivos CSV ")
    print("-"*50)
    
    # Diccionario para almacenar los nombres de las columnas de cada archivo
    columnas_por_archivo = {}
    
    # Recorrer cada archivo CSV
    for archivo in archivos_csv:
        # Leer el archivo CSV en un DataFrame
        df = pd.read_csv(archivo)
        
        # Guardar el nombre del archivo y la forma del DataFrame
        columnas_por_archivo[archivo] = {
            'columnas': set(df.columns),  # Convertir a set para evitar duplicados
            'forma': df.shape
        }
        
        # Imprimir la forma de cada archivo
        print(f"Archivo: {os.path.basename(archivo)} | Forma: {df.shape}")
    
    # Comparar las columnas entre todos los archivos
    todas_las_columnas = set().union(*[data['columnas'] for data in columnas_por_archivo.values()])
    
    # Preparar un resumen con las columnas faltantes o sobrantes
    resumen = {}
    
    for archivo, data in columnas_por_archivo.items():
        archivo_columnas = data['columnas']
        columnas_faltantes = todas_las_columnas - archivo_columnas
        columnas_sobrantes = archivo_columnas - todas_las_columnas
        resumen[archivo] = {
            'columnas_faltantes': list(columnas_faltantes),
            'columnas_sobrantes': list(columnas_sobrantes)
        }
    
    # Crear una tabla HTML con el resumen
    html_table = "<table border='1'><tr><th>Archivo</th><th>Columnas Faltantes</th><th>Columnas Sobrantes</th></tr>"
    
    for archivo, data in resumen.items():
        html_table += f"<tr><td>{os.path.basename(archivo)}</td>"
        html_table += f"<td>{', '.join(data['columnas_faltantes'])}</td>"
        html_table += f"<td>{', '.join(data['columnas_sobrantes'])}</td></tr>"
    
    html_table += "</table>"
    
    # Mostrar el HTML en pantalla
    display(HTML(html_table))

# Llamar a la función para analizar si las estructuras se corresponden
analizar_csv(carpeta)

archivos_csv = glob.glob(os.path.join(carpeta, "*.csv"))

# Leer el primer archivo CSV para obtener las columnas
archivo_base = os.path.join(carpeta, archivos_csv[0])
df_base = pd.read_csv(archivo_base)
columnas_base = set(df_base.columns)
print(f"Archivo base: {os.path.basename(archivo_base)}")
print()

print(f"Archivo base: {archivo_base} con forma {df_base.shape}")
print("-"*100)
dfs = []
# Comparar con los demás archivos CSV
for archivo in archivos_csv:
    archivo_actual = os.path.join(carpeta, archivo)
    df_actual = pd.read_csv(archivo_actual)
    columnas_actual = set(df_actual.columns)
    print(f"\nProcesando... {archivo} con forma {df_actual.shape}")
    
    if columnas_base != columnas_actual:
        print(f"  .... ERROR:")

        diferencias_base = columnas_base - columnas_actual
        diferencias_actual = columnas_actual - columnas_base
        
        if diferencias_base:
            print(f" - Faltan columnas: {diferencias_base}")
        if diferencias_actual:
            print(f" - Columnas adicionales: {diferencias_actual}")
    print("  .... ok")

    # Agregar la columna con el nombre del archivo de procedencia
    #df_actual['fuente'] = archivo

    # Agregar el DataFrame a la lista
    dfs.append(df_actual)
print()
print("-"*100)
print(f"Se procesaron {len(dfs)} archivos CSV con la misma estructura.")

# Concatenar todos los DataFrames en uno solo
df_unificado = pd.concat(dfs, ignore_index=True)
print("Se ha combinado el DataFrame.  EL nuevo DataFrame tiene forma: ", df_unificado.shape)
print()

archivo_salida = os.path.join(carpeta, "unificado.csv")

# Exportar el DataFrame unificado a un archivo CSV
df_unificado["uuid"] = [str(uuid.uuid4()) for _ in range(len(df_unificado))]
df_unificado.to_csv(archivo_salida, index=False)
print(f"El DataFrame unificado se ha guardado en {archivo_salida} con forma {df_unificado.shape}")