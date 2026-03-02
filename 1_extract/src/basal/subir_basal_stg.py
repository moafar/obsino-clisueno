#!/usr/bin/env python3
"""
ETL CSV básico: lee un CSV, aplica transformaciones y exporta el resultado
a una hoja de Google Sheets.
"""

from __future__ import annotations
import argparse
import logging
from pathlib import Path
import sys
import re
import pandas as pd
 
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe

# --- Configuración de salida a Google Sheets ---
SPREADSHEET_ID = "1KI8_Df7G9RUco-0FLPqTiFsyLC1r98T_pR3CsHZAu0s"
HOJA_NAME = "Data_basal"
EXTRACT_ROOT = Path(__file__).resolve().parents[2]
CREDS_PATH = EXTRACT_ROOT / "secrets" / "obsino_clisueno_key.json"

# --- Diccionario de tipos de ENTRADA (data dictionary para BASAL) ---
DATA_TYPES: dict[str, str] = {
    'nombre':'str',
    'edad_anos':'float',
    'edad_meses':'float',
    'edad_dias':'float',
    'id':'str',
    'peso':'float',
    'medida_peso':'str',
    'talla':'float',
    'medida_talla':'str',
    'imc':'float',
    'cuello':'float',
    'medida_cuello':'str',
    'perimetro_abdominal':'float',
    'medida_perimetro_abdominal':'str',
    'solicita':'str',
    'empresa':'str',
    'fecha_estudio':'datetime',
    'epworth':'float',
    'tiempo_en_cama':'float',
    'tiempo_sueno':'float',
    'eficiencia_sueno':'float',
    'latencia_sueno_total':'float',
    'latencia_sueno_rem':'float',
    'indice_microalertamientos':'float',
    'porcentaje_sueno_rem':'float',
    'porcentaje_sueno_profundo':'float',
    'iac':'float',
    'iao':'float',
    'iam':'float',
    'indice_desat_rem':'float',
    'indice_desat_nrem':'float',
    'indice_desat_total':'float',
    'tiempo_desat_90_rem':'float',
    'tiempo_desat_90_nrem':'float',
    'tiempo_desat_80_rem':'float',
    'tiempo_desat_80_nrem':'float',
    'tiempo_desat_70_rem':'float',
    'tiempo_desat_70_nrem':'float',
    'numero_eventos_ah':'float',
    'ih':'float',
    'iah':'float',
    'fuente':'str',
    'uuid':'str',
    'version_control':'str'
}





FLOAT_COLS = [c for c, t in DATA_TYPES.items() if t == "float"]
STR_COLS = [c for c, t in DATA_TYPES.items() if t == "str"]
DATETIME_COLS = [c for c, t in DATA_TYPES.items() if t == "datetime"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Aplica transformaciones a un CSV.")
    p.add_argument("input", type=Path, nargs="?", help="Ruta del CSV de entrada")
    p.add_argument(
        "--input",
        dest="input_flag",
        type=Path,
        help="Ruta del CSV de entrada (alternativa con bandera)",
    )
    p.add_argument("--verbose", action="store_true", help="Más logs")
    args = p.parse_args()

    input_path = args.input_flag or args.input
    if not input_path:
        p.error("Debe indicar la ruta del CSV de entrada (posicional o con --input).")

    args.input = input_path
    return args


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _clean_float_series(s: pd.Series) -> pd.Series:
    """
    Limpia una serie que debería ser numérica:
    - trata nulos y textos vacíos
    - normaliza coma/punto
    - elimina caracteres no numéricos
    - convierte a Float64 (nullable)
    """
    # pasar a string para limpiar homogéneo
    s_str = s.astype(str).str.strip()

    # marcar como nulos algunos textos "vacíos"
    null_mask = s_str.str.lower().isin({"", "na", "nan", "null", "none"})
    s_str = s_str.where(~null_mask, None)

    # si todo quedó nulo, devolver directamente
    if s_str.isna().all():
        return pd.Series(pd.NA, index=s.index, dtype="Float64")

    # reemplazar coma por punto
    s_str = s_str.str.replace(",", ".", regex=False)

    # quitar cualquier cosa que no sea dígito, punto o signo
    s_str = s_str.str.replace(r"[^0-9\.\-]", "", regex=True)

    # strings vacíos -> nulos
    s_str = s_str.where(~s_str.eq(""), None)

    # convertir a numérico
    s_num = pd.to_numeric(s_str, errors="coerce").astype("Float64")

    return s_num


def normalize_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza columnas según DATA_TYPES:
    - columnas float: limpia coma/punto y convierte a Float64
    - columnas datetime: to_datetime (day-first)
    - columnas str: las deja como están (ya vienen como str)
    """
    # floats
    for col in FLOAT_COLS:
        if col in df.columns:
            try:
                df[col] = _clean_float_series(df[col])
                logging.debug("Columna numérica normalizada: %s", col)
            except Exception as e:
                logging.exception("Error normalizando columna float %s: %s", col, e)

    # datetime
    for col in DATETIME_COLS:
        if col in df.columns:
            try:
                # --- Limpieza previa para evitar NaT ---
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.strip()
                    .str.replace("\u00a0", " ", regex=False)      # NBSP → espacio normal
                    .str.replace("-", "/", regex=False)          # guiones → barras
                    .str.replace(r"[^\d/]", "", regex=True)      # solo dígitos y /
                )

                # --- Conversión a datetime ---
                df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)

                logging.debug("Columna datetime normalizada: %s", col)
            except Exception as e:
                logging.exception("Error normalizando columna datetime %s: %s", col, e)

    return df


def apply_transformations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforma el DataFrame:
      - anos_decimales (desde edad_*)
      - Normaliza y crea: peso_kg, talla_cm, cuello_cm, perimetro_abdominal_cm
      - Crea t90, t80, t70 (proporción tiempo desaturado)
      - Elimina columnas de entrada usadas
      - Renombra y reordena columnas al patrón final solicitado
    """

    # --- helpers ---
    def _to_float(x):
        if pd.isna(x):
            return pd.NA
        s = str(x).strip().lower()
        if s in {"", "na", "nan", "null"}:
            return pd.NA
        s = s.replace(",", ".")
        s = re.sub(r"[^0-9\.\-]", "", s)
        if s in {"", ".", "-", "-.", ".-"}:
            return pd.NA
        try:
            return float(s)
        except Exception:
            return pd.NA

    def _to_int_or_zero(x):
        val = _to_float(x)
        if pd.isna(val):
            return 0
        try:
            return int(val)
        except Exception:
            return 0

    def _anos_decimales(row):
        y = _to_int_or_zero(row.get("edad_anos"))
        m = _to_int_or_zero(row.get("edad_meses"))
        d = _to_int_or_zero(row.get("edad_dias"))
        return round(y + m / 12.0 + d / 365.25, 4)

    # --- unidades embebidas ---
    unidades = {
        "peso": {"kg": ["kg", "kgs", "kgr", "kl"], "g": ["g", "gr", "grs"]},
        "talla": {
            "metros": ["m", "mts", "metros"],
            "centimetros": ["c", "cm", "cms", "a"],
        },
        "cuello": {
            "metros": ["m", "mts", "metros"],
            "centimetros": ["c", "cm", "cms"],
        },
        "perimetro_abdominal": {
            "metros": ["m", "ms", "mts"],
            "centimetros": ["cm", "cms", "cm.", ".cm", ".ccm", "ccm"],
        },
    }

    # 1) anos_decimales
    if {"edad_anos", "edad_meses", "edad_dias"}.issubset(df.columns):
        df["anos_decimales"] = df.apply(_anos_decimales, axis=1).astype("Float64")
        logging.info("Agregada columna anos_decimales.")
    else:
        logging.warning("No se encontraron columnas de edad (edad_anos/meses/dias).")

    # 2) normalizar textos de unidad
    for col in [
        "medida_peso",
        "medida_talla",
        "medida_cuello",
        "medida_perimetro_abdominal",
    ]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.lower().str.strip()

    # sets desde config
    peso_kg_cfg = set(map(str.lower, unidades["peso"]["kg"]))
    peso_g_cfg = set(map(str.lower, unidades["peso"]["g"]))
    t_m_cfg = set(map(str.lower, unidades["talla"]["metros"]))
    t_cm_cfg = set(map(str.lower, unidades["talla"]["centimetros"]))
    c_m_cfg = set(map(str.lower, unidades["cuello"]["metros"]))
    c_cm_cfg = set(map(str.lower, unidades["cuello"]["centimetros"]))
    p_m_cfg = set(map(str.lower, unidades["perimetro_abdominal"]["metros"]))
    p_cm_cfg = set(map(str.lower, unidades["perimetro_abdominal"]["centimetros"]))

    # 3) peso_kg
    if {"peso", "medida_peso"}.issubset(df.columns):
        df["peso_kg"] = pd.Series(pd.NA, index=df.index, dtype="Float64")
        mask_kg = df["medida_peso"].isin(peso_kg_cfg)
        mask_g = df["medida_peso"].isin(peso_g_cfg)
        df.loc[mask_kg, "peso_kg"] = df.loc[mask_kg, "peso"].map(_to_float)
        df.loc[mask_g, "peso_kg"] = df.loc[mask_g, "peso"].map(_to_float) / 1000.0
        logging.info("Agregada columna peso_kg.")
    else:
        logging.warning("Faltan columnas para peso (peso y/o medida_peso).")

    # 4) talla_cm
    if {"talla", "medida_talla"}.issubset(df.columns):
        df["talla_cm"] = pd.Series(pd.NA, index=df.index, dtype="Float64")
        mask_tm = df["medida_talla"].isin(t_m_cfg)
        mask_tc = df["medida_talla"].isin(t_cm_cfg)
        df.loc[mask_tm, "talla_cm"] = df.loc[mask_tm, "talla"].map(_to_float) * 100.0
        df.loc[mask_tc, "talla_cm"] = df.loc[mask_tc, "talla"].map(_to_float)
        logging.info("Agregada columna talla_cm.")
    else:
        logging.warning("Faltan columnas para talla (talla y/o medida_talla).")

    # 5) cuello_cm
    if {"cuello", "medida_cuello"}.issubset(df.columns):
        df["cuello_cm"] = pd.Series(pd.NA, index=df.index, dtype="Float64")
        mask_cm = df["medida_cuello"].isin(c_m_cfg)
        mask_cc = df["medida_cuello"].isin(c_cm_cfg)
        df.loc[mask_cm, "cuello_cm"] = df.loc[mask_cm, "cuello"].map(_to_float) * 100.0
        df.loc[mask_cc, "cuello_cm"] = df.loc[mask_cc, "cuello"].map(_to_float)
        logging.info("Agregada columna cuello_cm.")
    else:
        logging.warning("Faltan columnas para cuello (cuello y/o medida_cuello).")

    # 6) perimetro_abdominal_cm
    if {"perimetro_abdominal", "medida_perimetro_abdominal"}.issubset(df.columns):
        df["perimetro_abdominal_cm"] = pd.Series(
            pd.NA, index=df.index, dtype="Float64"
        )
        mask_pm = df["medida_perimetro_abdominal"].isin(p_m_cfg)
        mask_pc = df["medida_perimetro_abdominal"].isin(p_cm_cfg)
        df.loc[mask_pm, "perimetro_abdominal_cm"] = (
            df.loc[mask_pm, "perimetro_abdominal"].map(_to_float) * 100.0
        )
        df.loc[mask_pc, "perimetro_abdominal_cm"] = df.loc[
            mask_pc, "perimetro_abdominal"
        ].map(_to_float)
        logging.info("Agregada columna perimetro_abdominal_cm.")
    else:
        logging.warning(
            "Faltan columnas para perímetro abdominal "
            "(perimetro_abdominal y/o medida_perimetro_abdominal)."
        )

    # 7) proporciones de tiempo desaturación (t90, t80, t70)
    def _txx(rem_col: str, nrem_col: str, total_col: str, target_name: str):
        if not {rem_col, nrem_col, total_col}.issubset(df.columns):
            logging.warning(
                f"No se encontraron columnas requeridas para {target_name}."
            )
            return
        try:
            rem = df[rem_col].map(_to_float).astype("Float64")
            nrem = df[nrem_col].map(_to_float).astype("Float64")
            tot = df[total_col].map(_to_float).astype("Float64")

            out = (rem.fillna(0) + nrem.fillna(0)) / tot
            out = out.where(tot > 0)
            out = out.round(2)

            df[target_name] = out.astype("Float64")
            logging.info(f"Agregada columna {target_name}.")
        except Exception as e:
            logging.exception(f"Error calculando {target_name}: {e}")

    _txx("tiempo_desat_90_rem", "tiempo_desat_90_nrem", "tiempo_sueno", "t90")
    _txx("tiempo_desat_80_rem", "tiempo_desat_80_nrem", "tiempo_sueno", "t80")
    _txx("tiempo_desat_70_rem", "tiempo_desat_70_nrem", "tiempo_sueno", "t70")

    # 8) eliminar columnas de entrada usadas
    cols_a_eliminar = [
        "edad_anos",
        "edad_meses",
        "edad_dias",
        "peso",
        "medida_peso",
        "talla",
        "medida_talla",
        "cuello",
        "medida_cuello",
        "perimetro_abdominal",
        "medida_perimetro_abdominal",
        "tiempo_desat_90_rem",
        "tiempo_desat_90_nrem",
        "tiempo_desat_80_rem",
        "tiempo_desat_80_nrem",
        "tiempo_desat_70_rem",
        "tiempo_desat_70_nrem",
    ]
    existentes = [c for c in cols_a_eliminar if c in df.columns]
    if existentes:
        df = df.drop(columns=existentes)
        logging.info("Eliminadas columnas de entrada usadas: %s", existentes)

    # 9) renombrar columnas al patrón final
    rename_map = {
        "nombre": "pte_nombre",
        "id": "pte_id",
        "imc": "pte_imc",
        "solicita": "basal_solicita",
        "empresa": "basal_empresa",
        "fecha_estudio": "basal_fecha_estudio",
        "epworth": "basal_epworth",
        "tiempo_en_cama": "basal_tiempo_en_cama",
        "tiempo_sueno": "basal_tiempo_sueno",
        "eficiencia_sueno": "basal_eficiencia_sueno",
        "latencia_sueno_total": "basal_latencia_sueno_total",
        "latencia_sueno_rem": "basal_latencia_sueno_rem",
        "indice_microalertamientos": "basal_indice_microalertamientos",
        "porcentaje_sueno_rem": "basal_porcentaje_sueno_rem",
        "porcentaje_sueno_profundo": "basal_porcentaje_sueno_profundo",
        "iac": "basal_iac",
        "iao": "basal_iao",
        "iam": "basal_iam",
        "ih": "basal_ih",
        "iah": "basal_iah",
        "indice_desat_rem": "basal_indice_desat_rem",
        "indice_desat_nrem": "basal_indice_desat_nrem",
        "indice_desat_total": "basal_indice_desat_total",
        "numero_eventos_ah": "basal_numero_eventos_ah",
        "fuente": "basal_fuente",
        "uuid": "basal_uuid",
        "anos_decimales": "pte_anos_decimales",
        "peso_kg": "pte_peso_kg",
        "talla_cm": "pte_talla_cm",
        "cuello_cm": "pte_cuello_cm",
        "perimetro_abdominal_cm": "pte_perimetro_abdominal_cm",
        "t90": "basal_t90",
        "t80": "basal_t80",
        "t70": "basal_t70",
        "version_control": "basal_version_control"
    }





    df = df.rename(columns=rename_map)


    # 10) normalizar porcentajes a decimal (85 -> 0.85 ; 0.85 -> 0.85)
    PERCENT_OUT_COLS = [
        "basal_eficiencia_sueno",
        "basal_porcentaje_sueno_rem",
        "basal_porcentaje_sueno_profundo",
        "basal_t90",
        "basal_t80",
        "basal_t70",
    ]

    def _ensure_percent_decimal(series: pd.Series) -> pd.Series:
        s = _clean_float_series(series)  # ya existe y devuelve Float64 nullable
        # 85 -> 0.85 ; 0.85 -> 0.85
        return (s / 100).where(s > 1, s)

    # dentro de apply_transformations, justo después del rename:
    for col in PERCENT_OUT_COLS:
        if col in df.columns:
            df[col] = _ensure_percent_decimal(df[col])
            logging.info("Porcentaje normalizado a decimal: %s", col)

    # 11) reordenar y asegurar columnas finales
    final_cols = [
        "pte_nombre",
        "pte_id",
        "pte_imc",
        "pte_anos_decimales",
        "pte_peso_kg",
        "pte_talla_cm",
        "pte_cuello_cm",
        "pte_perimetro_abdominal_cm",
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
        "basal_t90",
        "basal_t80",
        "basal_t70",



        
        "basal_fuente",
        "basal_uuid",
        "basal_version_control"
    ]

    for col in final_cols:
        if col not in df.columns:
            df[col] = pd.NA

    df = df[final_cols]
    logging.info("Columnas finales: %s", df.columns.tolist())

    return df


def main() -> int:
    args = parse_args()
    setup_logging(args.verbose)

    if not args.input.exists():
        logging.error("No existe el archivo de entrada: %s", args.input)
        return 2

    try:
        logging.info("Leyendo: %s", args.input)
        df = pd.read_csv(args.input, dtype=str) # leemos todo como texto para controlar coma/punto después
        logging.info("Shape inicial (raw): %s", df.shape)
        logging.info("Columnas iniciales: %s", df.columns.tolist())
    except Exception as e:
        logging.exception("Error leyendo el CSV: %s", e)
        return 3

    # normalizar tipos según DATA_TYPES (coma/punto y fechas)
    try:
        df = normalize_dtypes(df)
        logging.info("Tipos normalizados según DATA_TYPES.")
    except Exception as e:
        logging.exception("Error al normalizar tipos: %s", e)
        return 4

    try:
        df_out = apply_transformations(df)
        logging.info("Shape final: %s", df_out.shape)
    except Exception as e:
        logging.exception("Error al transformar datos: %s", e)
        return 5

    # Exportar directamente a Google Sheets
    try:
        logging.info("Iniciando exportación a Google Sheets...")
        # df_out.to_excel("basal_stg_output.xlsx", index=False)  # debug local

        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/spreadsheets",
        ]
        creds = Credentials.from_service_account_file(CREDS_PATH, scopes=scope)

        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = spreadsheet.worksheet(HOJA_NAME)

        worksheet.clear()
        set_with_dataframe(worksheet, df_out)

        logging.info("Datos exportados correctamente a Google Sheets.")
        print("✅ Datos exportados correctamente a Google Sheets.")
    except Exception as e:
        logging.exception("Error exportando a Google Sheets: %s", e)
        print("❌ Error exportando a Google Sheets. Revisa el log.")
        return 6

    return 0


if __name__ == "__main__":
    sys.exit(main())