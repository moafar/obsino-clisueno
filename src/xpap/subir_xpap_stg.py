# -*- coding: utf-8 -*-
import os
import re
import pandas as pd
import numpy as np
import yaml
from datetime import datetime
import gspread
from gspread_dataframe import set_with_dataframe
from google.oauth2.service_account import Credentials

# ============================
# 1) Config
# ============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config_basal.yaml")

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

csv_path       = config["input"]["csv_path"]
spreadsheet_id = config["output"]["spreadsheet_id"]
hoja           = config["output"]["hoja"]
unidades       = config.get("unidades", {})

# Cargar variables desde el nuevo YAML (ordenadas)
vars_list = config.get("variables", [])
column_names = [list(item.keys())[0] for item in vars_list]
column_types = {list(item.keys())[0]: list(item.values())[0] for item in vars_list}


# ============================
# 2) Leer CSV sin encabezados
# ============================
df = pd.read_csv(
    csv_path,
    header=0,
    names=column_names,
    dtype=str,
    keep_default_na=False
)

# Limpieza básica de espacios
df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

# ============================
# 3) Tipado según YAML
# ============================
def _to_float(s: str):
    if s is None:
        return np.nan
    t = str(s).strip()
    if t == "":
        return np.nan
    t = re.sub(r"[^\d,.\-]", "", t)
    if "," in t and "." in t:
        t = t.replace(".", "").replace(",", ".")
    elif "," in t:
        t = t.replace(",", ".")
    try:
        return float(t)
    except:
        return np.nan

def _to_int(s: str):
    v = _to_float(s)
    if np.isnan(v):
        return pd.NA
    try:
        return int(round(v))
    except:
        return pd.NA

def _to_fraction(s: str):
    """
    Convierte porcentajes (p.ej., '45' o '45,3') a fracción (0.45, 0.453).
    Devuelve np.nan si no es convertible.
    """
    v = _to_float(s)
    if np.isnan(v):
        return np.nan
    return np.float64(v / 100.0)

for col, typ in column_types.items():
    if col not in df.columns:
        df[col] = ""

    if typ == "str":
        df[col] = df[col].astype(str).str.strip()

    elif typ == "int":
        df[col] = df[col].map(_to_int).astype("Int64")

    elif typ == "float":
        df[col] = df[col].map(_to_float).astype("Float64")

    elif typ == "percent":
        df[col] = df[col].map(_to_fraction).astype("Float64")

    elif typ == "datetime":
        s = (
            df[col].astype("string")
            .str.replace(r"[\u200B\u00A0]", "", regex=True)
            .str.strip()
            .str.replace(r"[.\-]", "/", regex=True)
            .str.extract(r"(\d{1,2}/\d{1,2}/\d{2,4})")[0]
        )
        df[col] = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce").dt.floor("D")


# ============================
# 4) Normalizaciones
# ============================
def _anos_decimales(row):
    y = 0 if pd.isna(row["pte_edad_anos"]) else int(row["pte_edad_anos"])
    m = 0 if pd.isna(row["pte_edad_meses"]) else int(row["pte_edad_meses"])
    d = 0 if pd.isna(row["pte_edad_dias"]) else int(row["pte_edad_dias"])
    return round(y + m / 12.0 + d / 365.25, 4)


df["pte_anos_decimales"] = df.apply(_anos_decimales, axis=1).astype("Float64")

for col in ["pte_medida_peso","pte_medida_talla","pte_medida_cuello","pte_medida_perimetro_abdominal"]:
    if col in df.columns:
        df[col] = df[col].astype(str).str.lower().str.strip()

peso_kg_cfg = set(unidades.get("peso", {}).get("kg", []))
peso_g_cfg = set(unidades.get("peso", {}).get("g", []))
t_m_cfg = set(unidades.get("talla", {}).get("metros", []))
t_cm_cfg = set(unidades.get("talla", {}).get("centimetros", []))
c_m_cfg = set(unidades.get("cuello", {}).get("metros", []))
c_cm_cfg = set(unidades.get("cuello", {}).get("centimetros", []))
p_m_cfg = set(unidades.get("perimetro_abdominal", {}).get("metros", []))
p_cm_cfg = set(unidades.get("perimetro_abdominal", {}).get("centimetros", []))

df["pte_peso_kg"] = pd.Series(pd.NA, index=df.index, dtype="Float64")
mask_kg = df["pte_medida_peso"].isin(peso_kg_cfg)
mask_g  = df["pte_medida_peso"].isin(peso_g_cfg)
df.loc[mask_kg, "pte_peso_kg"] = df.loc[mask_kg, "pte_peso"].map(_to_float)
df.loc[mask_g,  "pte_peso_kg"] = df.loc[mask_g,  "pte_peso"].map(_to_float) / 1000.0

df["pte_talla_cm"] = pd.Series(pd.NA, index=df.index, dtype="Float64")
mask_tm = df["pte_medida_talla"].isin(t_m_cfg)
mask_tc = df["pte_medida_talla"].isin(t_cm_cfg)
df.loc[mask_tm, "pte_talla_cm"] = df.loc[mask_tm, "pte_talla"].map(_to_float) * 100.0
df.loc[mask_tc, "pte_talla_cm"] = df.loc[mask_tc, "pte_talla"].map(_to_float)

df["pte_cuello_cm"] = pd.Series(pd.NA, index=df.index, dtype="Float64")
mask_cm = df["pte_medida_cuello"].isin(c_m_cfg)
mask_cc = df["pte_medida_cuello"].isin(c_cm_cfg)
df.loc[mask_cm, "pte_cuello_cm"] = df.loc[mask_cm, "pte_cuello"].map(_to_float) * 100.0
df.loc[mask_cc, "pte_cuello_cm"] = df.loc[mask_cc, "pte_cuello"].map(_to_float)

df["pte_perimetro_abdominal_cm"] = pd.Series(pd.NA, index=df.index, dtype="Float64")
mask_pm = df["pte_medida_perimetro_abdominal"].isin(p_m_cfg)
mask_pc = df["pte_medida_perimetro_abdominal"].isin(p_cm_cfg)
df.loc[mask_pm, "pte_perimetro_abdominal_cm"] = df.loc[mask_pm, "pte_perimetro_abdominal"].map(_to_float) * 100.0
df.loc[mask_pc, "pte_perimetro_abdominal_cm"] = df.loc[mask_pc, "pte_perimetro_abdominal"].map(_to_float)


# ============================
# 5) t90, t80, t70 (% del tiempo de sueño)
# ============================
def _txx(rem_col, nrem_col, total_col, target_name):
    rem  = df[rem_col].astype("Float64")
    nrem = df[nrem_col].astype("Float64")
    tot  = df[total_col].astype("Float64")
    out = (rem.fillna(0) + nrem.fillna(0)) / tot
    out = out.where(tot > 0)
    df[target_name] = out.astype("Float64")


_txx("basal_tiempo_desat_90_rem","basal_tiempo_desat_90_nrem","basal_tiempo_sueno","basal_t90")
_txx("basal_tiempo_desat_80_rem","basal_tiempo_desat_80_nrem","basal_tiempo_sueno","basal_t80")
_txx("basal_tiempo_desat_70_rem","basal_tiempo_desat_70_nrem","basal_tiempo_sueno","basal_t70")


# ============================
# 6) Renombrado final y exportación
# ============================

if "basal_version_control" not in df.columns:
    df["basal_version_control"] = pd.NA

# Ahora sí el orden final
columnas_finales = [
    "pte_nombre",
    "pte_id",
    "pte_imc",
    "basal_solicita",
    "basal_empresa",
    "basal_fecha_estudio",
    "basal_epworth",
    "basal_tiempo_en_cama",
    "basal_tiempo_sueno",
    "basal_eficiencia_sueno",
    "basal_latencia_sueno_total",
    "basal_latencia_sueno_rem",
    "basal_indice_microalertamientos",
    "basal_porcentaje_sueno_rem",
    "basal_porcentaje_sueno_profundo",
    "basal_iac",
    "basal_iao",
    "basal_iam",
    "basal_ih",
    "basal_iah",
    "basal_indice_desat_rem",
    "basal_indice_desat_nrem",
    "basal_indice_desat_total",
    "basal_numero_eventos_ah",
    "basal_fuente",
    "basal_uuid",
    "pte_anos_decimales",
    "pte_peso_kg",
    "pte_talla_cm",
    "pte_cuello_cm",
    "pte_perimetro_abdominal_cm",
    "basal_t90",
    "basal_t80",
    "basal_t70",
    "basal_version_control",
]

df = df[columnas_finales]
#df.to_csv("exported.csv", index=False)


creds_path = config["output"]["creds_path"]
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]
creds = Credentials.from_service_account_file(creds_path, scopes=scope)

client = gspread.authorize(creds)
spreadsheet = client.open_by_key(spreadsheet_id)
worksheet = spreadsheet.worksheet(hoja)
worksheet.clear()
set_with_dataframe(worksheet, df)

print("Datos exportados correctamente.")