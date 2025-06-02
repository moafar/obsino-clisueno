import pandas as pd
import numpy as np
from datetime import datetime
import warnings

df = pd.read_csv("/home/rom/clisueno/output/unificado.csv", quoting=1)
print(f"Cargado dataframe con {df.shape[0]} filas")
print(f"El dataframe tiene {len(df.columns)} columnas: \n {df.columns}")

variables_str = [
    'nombre',
    'id',
    'medida_peso',
    'medida_talla',
    'medida_cuello',
    'medida_perimetro_abdominal',
    'solicita',
    'empresa',
    'fuente',
    'uuid'


]

variables_int = [


]

variables_float = [
    'edad_anos',
    'edad_meses',
    'edad_dias',
    'epworth',
    'peso',
    'talla',
    'imc',
    'cuello',
    'perimetro_abdominal',
    'tiempo_en_cama',
    'tiempo_sueno',
    'eficiencia_sueno',
    'latencia_sueno_total',
    'latencia_sueno_rem',
    'indice_microalertamientos',
    'porcentaje_sueno_rem',
    'porcentaje_sueno_profundo',
    'iac',
    'iao',
    'iam',
    'indice_desat_rem',
    'indice_desat_nrem',
    'indice_desat_total',
    'oxim_menor90_total',
    'oxim_menor80_total',
    'oxim_menor70_total',
    'oxim_menor60_total',
    't90',
    'ih',
    'iah',
    'numero_eventos_ah'


]

variables_datetime = ['fecha_estudio']

# Variables DATETIME ***********************************

import pandas as pd
from datetime import datetime

def validar_transformar_datetime(df, variables):

    # Inicializar listas de resultados
    variables_no_encontradas = []
    variables_transformadas = []
    variables_no_transformadas = []

    def convertir_fecha(fecha_str):
        try:
            return pd.to_datetime(str(fecha_str).strip(), dayfirst=True, errors='coerce')
        except Exception:
            return pd.NaT

    for variable in variables:
        if variable not in df.columns:
            variables_no_encontradas.append(variable)
        else:
            # Aplicar conversión
            df[variable] = df[variable].apply(convertir_fecha)
            df[variable] = df[variable].dt.floor("D")  # elimina la hora, conserva datetime64[ns]

            # Verificar si se transformó exitosamente
            if df[variable].isna().all():
                variables_no_transformadas.append(variable)
            else:
                variables_transformadas.append(variable)

    # Reporte
    print("\n************ Resultado de la transformación DATETIME **************\n")
    print(f"{len(variables_no_encontradas)} Variables no encontradas: {variables_no_encontradas}")
    print(f"{len(variables_no_transformadas)} Variables no transformadas: {variables_no_transformadas}")
    print(f"{len(variables_transformadas)} Variables transformadas exitosamente: {variables_transformadas}")

    return {
        "no_encontradas": variables_no_encontradas,
        "no_transformadas": variables_no_transformadas,
        "transformadas": variables_transformadas
    }


# Validación y transformación a INT *****************************

import pandas as pd

def validar_transformar_int(df, variables):

    variables_no_encontradas = []
    variables_transformadas = []
    variables_no_transformadas = []

    for var in variables:
        if var not in df.columns:
            variables_no_encontradas.append(var)
            print(f"La columna '{var}' no se encuentra en el DataFrame.")
        else:
            try:
                # Reemplazar comas por puntos y convertir a número
                df[var] = df[var].astype(str).str.replace(',', '.', regex=False)
                df[var] = pd.to_numeric(df[var], errors='coerce').astype('Int64')

                if df[var].isna().all():
                    variables_no_transformadas.append(var)
                else:
                    variables_transformadas.append(var)

            except Exception as e:
                variables_no_transformadas.append(var)
                print(f"Error al transformar la columna '{var}' a enteros: {e}")

    print("\n************ Resultado de la transformación INT **************\n")
    print(f"{len(variables_no_encontradas)} Variables no encontradas: {variables_no_encontradas}")
    print(f"{len(variables_no_transformadas)} Variables no transformadas: {variables_no_transformadas}")
    print(f"{len(variables_transformadas)} Variables transformadas exitosamente: {variables_transformadas}")

    return {
        "no_encontradas": variables_no_encontradas,
        "no_transformadas": variables_no_transformadas,
        "transformadas": variables_transformadas
    }


# Validación y transformación a FLOAT ************************************************

import pandas as pd

def validar_transformar_float(df, variables):
    
    variables_no_encontradas = []
    variables_transformadas = []
    variables_no_transformadas = []

    for var in variables:
        if var not in df.columns:
            variables_no_encontradas.append(var)
            print(f"La columna '{var}' no se encuentra en el DataFrame.")
        else:
            try:
                # Estandarizar separadores decimales
                df[var] = df[var].astype(str).str.replace(',', '.', regex=False)
                df[var] = pd.to_numeric(df[var], errors='coerce').astype(float)

                if df[var].isna().all():
                    variables_no_transformadas.append(var)
                else:
                    variables_transformadas.append(var)

            except Exception as e:
                variables_no_transformadas.append(var)
                print(f"Error al transformar la columna '{var}' a flotante: {e}")

    print("\n************ Resultado de la transformación FLOAT **************\n")
    print(f"{len(variables_no_encontradas)} Variables no encontradas: {variables_no_encontradas}")
    print(f"{len(variables_no_transformadas)} Variables no transformadas: {variables_no_transformadas}")
    print(f"{len(variables_transformadas)} Variables transformadas exitosamente: {variables_transformadas}")

    return {
        "no_encontradas": variables_no_encontradas,
        "no_transformadas": variables_no_transformadas,
        "transformadas": variables_transformadas
    }


# Validación y transformación a STRING ****************************************

def validar_transformar_str(df, variables):

    import warnings
    import pandas as pd

    variables_no_encontradas = []
    variables_transformadas = []
    variables_no_transformadas = []
    variables_con_warnings = []

    for var in variables:
        if var not in df.columns:
            variables_no_encontradas.append(var)
            print(f"La columna '{var}' no se encuentra en el DataFrame.")
        else:
            try:
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always", UserWarning)

                    df[var] = df[var].astype("string")  # usa tipo string (acepta pd.NA)

                    if len(w) > 0:
                        variables_con_warnings.append(var)

                    if df[var].isna().all():
                        variables_no_transformadas.append(var)
                    else:
                        variables_transformadas.append(var)

            except Exception as e:
                variables_no_transformadas.append(var)
                print(f"Error al transformar la columna '{var}' a cadena: {e}")

    print("\n************ Resultado de la transformación STR **************\n")
    print(f"{len(variables_no_encontradas)} Variables no encontradas: {variables_no_encontradas}")
    print(f"{len(variables_no_transformadas)} Variables no transformadas: {variables_no_transformadas}")
    print(f"{len(variables_con_warnings)} Variables transformadas con warnings: {variables_con_warnings}")
    print(f"{len(variables_transformadas)} Variables transformadas exitosamente: {variables_transformadas}")

print("Finalizado ")

validar_transformar_int(df,variables_int)
validar_transformar_float(df,variables_float)
validar_transformar_datetime(df,variables_datetime)
validar_transformar_str(df,variables_str)

df["edad_anos_decimal"] = (
    df["edad_anos"].fillna(0) +
    df["edad_meses"].fillna(0) / 12 +
    df["edad_dias"].fillna(0) / 365.25
)

# Unificación de unidades: todo a minúsculas y sin espacios
df["medida_peso"] = df["medida_peso"].str.lower().str.strip()

# Definimos sets de unidades por tipo
unidades_kg = {"kg", "kgs", "kgr", "kl"}
unidades_g = {"g", "gr", "grs"}

# Cálculo de peso en kilogramos
df["peso_kg"] = df.apply(
    lambda row: row["peso"] / 1000 if row["medida_peso"] in unidades_g # type: ignore
    else row["peso"] if row["medida_peso"] in unidades_kg
    else None,  # o np.nan
    axis=1
)

# Verificación de que no hay unidades no contempladas
print("\nUnidades de peso no contempladas: \n")
print(df[~df["medida_peso"].isin(unidades_kg.union(unidades_g))]["medida_peso"].value_counts())


# Limpieza de texto
df["medida_talla"] = df["medida_talla"].str.lower().str.strip()

# Definir sets de unidades
unidades_metros = {"m", "mts", "metros"}
unidades_centimetros = {"c", "cm", "cms", "a"}

# Reemplazar nulos por 0 (si lo consideras seguro)
df["talla"] = df["talla"].fillna(0)

# Calcular talla en cm
df["talla_cm"] = df.apply(
    lambda row: row["talla"] * 100 if row["medida_talla"] in unidades_metros # type: ignore
    else row["talla"] if row["medida_talla"] in unidades_centimetros
    else None,
    axis=1
)

# Verificación de que no hay unidades no contempladas
print("\nUnidades de talla no contempladas: \n")
print(df[~df["medida_talla"].isin(["cm", "m"])]["medida_talla"].value_counts())

# Limpieza del texto
df["medida_cuello"] = df["medida_cuello"].str.lower().str.strip()

# Definir unidades válidas
unidades_metros = {"m", "mts", "metros"}
unidades_centimetros = {"c", "cm", "cms"}
unidades_cuello_validas = unidades_metros.union(unidades_centimetros)

# Rellenar nulos si aplica
df["cuello"] = df["cuello"].fillna(0)

# Calcular cuello en cm
df["cuello_cm"] = df.apply(
    lambda row: row["cuello"] * 100 if row["medida_cuello"] in unidades_metros # type: ignore
    else row["cuello"] if row["medida_cuello"] in unidades_centimetros
    else None,
    axis=1
)

# Verificación de que no hay unidades no contempladas
print("\nUnidades de cuello no contempladas: \n")
print(df[~df["medida_cuello"].isin(unidades_cuello_validas)]["medida_cuello"].value_counts())

# Limpieza del texto
df["medida_perimetro_abdominal"] = df["medida_perimetro_abdominal"].str.lower().str.strip()

# Definir unidades válidas
unidades_metros = {"m", "ms", "mts"}
unidades_centimetros = {"cm", "cms", "cm.", ".cm", ".ccm", "ccm"}
unidades_abdominal_validas = unidades_metros.union(unidades_centimetros)

# Reemplazar nulos si aplica
df["perimetro_abdominal"] = df["perimetro_abdominal"].fillna(0)

# Calcular perímetro abdominal en cm
df["perimetro_abdominal_cm"] = df.apply(
    lambda row: row["perimetro_abdominal"] * 100 if row["medida_perimetro_abdominal"] in unidades_metros # type: ignore
    else row["perimetro_abdominal"] if row["medida_perimetro_abdominal"] in unidades_centimetros
    else None,
    axis=1
)

# Verificación de que no hay unidades no contempladas
print("\nUnidades de perímetro abdominal no contempladas: \n")
print(df[~df["medida_perimetro_abdominal"].isin(unidades_abdominal_validas)]["medida_perimetro_abdominal"].value_counts())

columnas_finales = [
    'nombre','id', 'imc', 'solicita', 'empresa', 'fecha_estudio', 'epworth', 
    'tiempo_en_cama', 'tiempo_sueno', 'eficiencia_sueno', 'latencia_sueno_total',
    'latencia_sueno_rem', 'indice_microalertamientos', 'porcentaje_sueno_rem', 
    'porcentaje_sueno_profundo', 'iac', 'iao', 'iam', 'indice_desat_rem',
    'indice_desat_nrem', 'indice_desat_total', 'oxim_menor90_total', 
    'oxim_menor80_total', 'oxim_menor70_total', 'oxim_menor60_total', 't90',
    'numero_eventos_ah', 'ih', 'iah', 'fuente', 'uuid', 'edad_anos_decimal', 
    'peso_kg', 'talla_cm', 'cuello_cm', 'perimetro_abdominal_cm'
]

df = df[columnas_finales]

# Agrega la columna de version control
ahora = datetime.today().strftime('%Y-%m-%d : %H:%M:%S')
df['version_control'] = 'Extraido en: ' + ahora

# Carga a zona cruda (Google Sheets)
import pandas as pd
import gspread
from gspread_dataframe import set_with_dataframe
from google.oauth2.service_account import Credentials

def exportar_df_a_google_sheets(
    df: pd.DataFrame,
    spreadsheet_id: str,
    hoja: str,
    creds_path: str,
    variables_str: list,
    variables_int: list,
    variables_float: list,
    variables_percent: list,
    variables_datetime: list
):
    # 1. Autenticación
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/spreadsheets"
    ]
    creds = Credentials.from_service_account_file(creds_path, scopes=scope)
    client = gspread.authorize(creds)

    # 2. Validación de coherencia
    percent_not_in_float = [col for col in variables_percent if col not in variables_float]
    if percent_not_in_float:
        raise ValueError(f"Las siguientes columnas están en variables_percent pero no en variables_float: {percent_not_in_float}")

    # 3. Convertir columnas de porcentaje a decimal
    for col in variables_percent:
        if col in df:
            df[col] = df[col] / 100

    # 4. Abrir hoja y limpiar
    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.worksheet(hoja)
    worksheet.clear()

    # 5. Escribir DataFrame
    set_with_dataframe(worksheet, df)

    # 6. Construir diccionario de formatos por columna
    column_formats = {}
    for i, col in enumerate(df.columns):
        if col in variables_str:
            column_formats[i] = {"numberFormat": {"type": "TEXT", "pattern": "@"}}
        elif col in variables_int:
            column_formats[i] = {"numberFormat": {"type": "NUMBER", "pattern": "0"}}
        elif col in variables_percent:
            column_formats[i] = {"numberFormat": {"type": "PERCENT", "pattern": "0.00%"}}
        elif col in variables_float:
            column_formats[i] = {"numberFormat": {"type": "NUMBER", "pattern": "0.00"}}
        elif col in variables_datetime:
            column_formats[i] = {"numberFormat": {"type": "DATE", "pattern": "yyyy-mm-dd"}}

    # 7. Preparar batch_update con repeatCell
    requests = []
    for col_index, format_options in column_formats.items():
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": worksheet._properties["sheetId"],
                    "startRowIndex": 1,  # desde fila 2 (excluye encabezado)
                    "startColumnIndex": col_index,
                    "endColumnIndex": col_index + 1
                },
                "cell": {
                    "userEnteredFormat": format_options
                },
                "fields": "userEnteredFormat.numberFormat"
            }
        })

    # 8. Ejecutar actualización de formatos
    if requests:
        response = spreadsheet.batch_update({"requests": requests})
        print(f"Formatos aplicados: {response}")
    else:
        print("No se definieron formatos para aplicar.")

variables_percent = ['eficiencia_sueno', 'porcentaje_sueno_rem', 'porcentaje_sueno_profundo', 't90']

spreadsheet_id="1KI8_Df7G9RUco-0FLPqTiFsyLC1r98T_pR3CsHZAu0s"
hoja="Data"
creds_path="/home/rom/clisueno/secrets/observatorio-ino-1-78cfc246d28f-key.json"

exportar_df_a_google_sheets(
    df=df,
    spreadsheet_id = spreadsheet_id,
    hoja = hoja,
    creds_path = creds_path,
    variables_str=variables_str,
    variables_int=variables_int,
    variables_float=variables_float,
    variables_percent=variables_percent,
    variables_datetime=variables_datetime
)