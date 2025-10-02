import os
import pandas as pd
import yaml
from datetime import datetime
import gspread
from gspread_dataframe import set_with_dataframe
from google.oauth2.service_account import Credentials

# ============================
# 1) Cargar configuración (ruta robusta)
# ============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config_procesar_resultados_basal.yaml")

with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

csv_path       = config["input"]["csv_path"]
spreadsheet_id = config["output"]["spreadsheet_id"]
hoja           = config["output"]["hoja"]
creds_path     = config["output"]["creds_path"]

variables_str      = config["variables"]["str"]
variables_int      = config["variables"]["int"]
variables_float    = config["variables"]["float"]
variables_datetime = config["variables"]["datetime"]
variables_percent  = config["variables"]["percent"]
unidades           = config["unidades"]

# ============================
# 2) Leer CSV
# ============================
df = pd.read_csv(csv_path, decimal=",")
print(f"Procesando dataframe con {df.shape[0]} filas y {df.shape[1]} columnas...")

# ============================
# 3) Transformaciones
# ============================

print("\n Iniciando transpormaciones...")
# --- Convertir tipos numéricos (una pasada) ---
num_cols = set(variables_float + [
    "peso", "talla", "cuello", "perimetro_abdominal"
])
for c in num_cols.intersection(df.columns):
    df[c] = pd.to_numeric(df[c], errors="coerce")

# --- Parseo de fecha_estudio ---
if "fecha_estudio" in df.columns:
    df["fecha_estudio"] = pd.to_datetime(
        df["fecha_estudio"], dayfirst=True, errors="coerce"
    ).dt.floor("D")

# --- Edad decimal (ya con numéricos) ---
df["edad_anos_decimal"] = (
    df.get("edad_anos", 0).fillna(0)
    + df.get("edad_meses", 0).fillna(0) / 12
    + df.get("edad_dias", 0).fillna(0) / 365.25
)

# --- Normalizar texto en medidas ---
for col in ["medida_peso","medida_talla","medida_cuello","medida_perimetro_abdominal"]:
    if col in df.columns:
        df[col] = df[col].astype("string").str.lower().str.strip()

# --- PESO en kg ---
if "medida_peso" in df.columns and "peso" in df.columns:
    m_kg = df["medida_peso"].isin(unidades["peso"]["kg"])
    m_g  = df["medida_peso"].isin(unidades["peso"]["g"])
    df["peso_kg"] = pd.Series(pd.NA, index=df.index, dtype="Float64")
    df.loc[m_kg, "peso_kg"] = df.loc[m_kg, "peso"]
    df.loc[m_g,  "peso_kg"] = df.loc[m_g,  "peso"] / 1000

# --- TALLA en cm ---
if "medida_talla" in df.columns and "talla" in df.columns:
    tm = df["medida_talla"].isin(unidades["talla"]["metros"])
    tc = df["medida_talla"].isin(unidades["talla"]["centimetros"])
    df["talla_cm"] = pd.Series(pd.NA, index=df.index, dtype="Float64")
    df.loc[tm, "talla_cm"] = df.loc[tm, "talla"] * 100
    df.loc[tc, "talla_cm"] = df.loc[tc, "talla"]

# --- CUELLO en cm ---
if "medida_cuello" in df.columns and "cuello" in df.columns:
    cm = df["medida_cuello"].isin(unidades["cuello"]["metros"])
    cc = df["medida_cuello"].isin(unidades["cuello"]["centimetros"])
    df["cuello_cm"] = pd.Series(pd.NA, index=df.index, dtype="Float64")
    df.loc[cm, "cuello_cm"] = df.loc[cm, "cuello"] * 100
    df.loc[cc, "cuello_cm"] = df.loc[cc, "cuello"]

# --- PERÍMETRO ABDOMINAL en cm ---
if "medida_perimetro_abdominal" in df.columns and "perimetro_abdominal" in df.columns:
    pm = df["medida_perimetro_abdominal"].isin(unidades["perimetro_abdominal"]["metros"])
    pc = df["medida_perimetro_abdominal"].isin(unidades["perimetro_abdominal"]["centimetros"])
    df["perimetro_abdominal_cm"] = pd.Series(pd.NA, index=df.index, dtype="Float64")
    df.loc[pm, "perimetro_abdominal_cm"] = df.loc[pm, "perimetro_abdominal"] * 100
    df.loc[pc, "perimetro_abdominal_cm"] = df.loc[pc, "perimetro_abdominal"]

# --- T90, T80, T70 ---
def txx(rem, nrem, total):
    out = (rem.fillna(0) + nrem.fillna(0)).div(total).mul(100)
    return out.where(total > 0)

req = {"tiempo_desat_90_rem","tiempo_desat_90_nrem",
       "tiempo_desat_80_rem","tiempo_desat_80_nrem",
       "tiempo_desat_70_rem","tiempo_desat_70_nrem","tiempo_sueno"}
if req.issubset(df.columns):
    df['t90'] = txx(df['tiempo_desat_90_rem'], df['tiempo_desat_90_nrem'], df['tiempo_sueno'])
    df['t80'] = txx(df['tiempo_desat_80_rem'], df['tiempo_desat_80_nrem'], df['tiempo_sueno'])
    df['t70'] = txx(df['tiempo_desat_70_rem'], df['tiempo_desat_70_nrem'], df['tiempo_sueno'])

print("\n Transformaciones finalizadas.  Configurando tabla final...")

# --- Columnas finales ---
columnas_finales = [
    'nombre','id','imc','solicita','empresa','fecha_estudio','epworth',
    'tiempo_en_cama','tiempo_sueno','eficiencia_sueno','latencia_sueno_total',
    'latencia_sueno_rem','indice_microalertamientos','porcentaje_sueno_rem',
    'porcentaje_sueno_profundo','iac','iao','iam','indice_desat_rem',
    'indice_desat_nrem','indice_desat_total','t90','t80','t70',
    'numero_eventos_ah','ih','iah','fuente','uuid','edad_anos_decimal',
    'peso_kg','talla_cm','cuello_cm','perimetro_abdominal_cm'
]
df = df.reindex(columns=columnas_finales)

# --- Version control ---
ahora = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
df['version_control'] = 'Extraido en: ' + ahora

# --- Porcentajes a decimal ---
for col in variables_percent:
    if col in df.columns:
        df[col] = df[col] / 100

print("\n Tabla final lista.  Iniciando envío a Google Sheets...")

# ============================
# 4) Exportar a Google Sheets
# ============================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets"
]
creds = Credentials.from_service_account_file(creds_path, scopes=scope)
client = gspread.authorize(creds)

spreadsheet = client.open_by_key(spreadsheet_id)
worksheet = spreadsheet.worksheet(hoja)
worksheet.clear()

set_with_dataframe(worksheet, df)

print("\nDatos exportados a Google Sheets correctamente.")