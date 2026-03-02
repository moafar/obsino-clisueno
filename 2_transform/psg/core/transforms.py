from __future__ import annotations

import re
from typing import Any

import pandas as pd

DATA_TYPES: dict[str, str] = {
    "nombre": "str",
    "edad_anos": "float",
    "edad_meses": "float",
    "edad_dias": "float",
    "id": "str",
    "peso": "float",
    "medida_peso": "str",
    "talla": "float",
    "medida_talla": "str",
    "imc": "float",
    "cuello": "float",
    "medida_cuello": "str",
    "perimetro_abdominal": "float",
    "medida_perimetro_abdominal": "str",
    "solicita": "str",
    "empresa": "str",
    "fecha_estudio": "datetime",
    "epworth": "float",
    "tiempo_en_cama": "float",
    "tiempo_sueno": "float",
    "eficiencia_sueno": "float",
    "latencia_sueno_total": "float",
    "latencia_sueno_rem": "float",
    "indice_microalertamientos": "float",
    "porcentaje_sueno_rem": "float",
    "porcentaje_sueno_profundo": "float",
    "iac": "float",
    "iao": "float",
    "iam": "float",
    "indice_desat_rem": "float",
    "indice_desat_nrem": "float",
    "indice_desat_total": "float",
    "tiempo_desat_90_rem": "float",
    "tiempo_desat_90_nrem": "float",
    "tiempo_desat_80_rem": "float",
    "tiempo_desat_80_nrem": "float",
    "tiempo_desat_70_rem": "float",
    "tiempo_desat_70_nrem": "float",
    "numero_eventos_ah": "float",
    "ih": "float",
    "iah": "float",
    "fuente": "str",
    "uuid": "str",
    "version_control": "str",
}

FLOAT_COLS = [column for column, dtype_name in DATA_TYPES.items() if dtype_name == "float"]
STR_COLS = [column for column, dtype_name in DATA_TYPES.items() if dtype_name == "str"]
DATETIME_COLS = [column for column, dtype_name in DATA_TYPES.items() if dtype_name == "datetime"]


FINAL_COLS = [
    "pte_nombre",
    "pte_id",
    "pte_imc",
    "pte_anos_decimales",
    "pte_grupo_edad",
    "pte_peso_kg",
    "pte_talla_cm",
    "pte_cuello_cm",
    "pte_perimetro_abdominal_cm",
    "basal_solicita",
    "basal_empresa",
    "basal_fecha_estudio",
    "basal_epworth",
    "cat_epworth",
    "basal_tiempo_en_cama",
    "basal_tiempo_sueno",
    "basal_eficiencia_sueno",
    "cat_efic_sueno",
    "basal_latencia_sueno_total",
    "basal_latencia_sueno_rem",
    "basal_indice_microalertamientos",
    "cat_indice_microalertamientos",
    "basal_porcentaje_sueno_rem",
    "cat_porc_sueno_rem",
    "basal_porcentaje_sueno_profundo",
    "cat_porc_sueno_profundo",
    "basal_iac",
    "basal_iao",
    "basal_iam",
    "basal_ih",
    "basal_iah",
    "cat_iah",
    "basal_indice_desat_rem",
    "basal_indice_desat_nrem",
    "basal_indice_desat_total",
    "basal_numero_eventos_ah",
    "basal_t90",
    "basal_t80",
    "basal_t70",
    "basal_fuente",
    "basal_uuid",
    "basal_version_control",
]


def _clean_float_series(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip().str.lower()
    text = text.replace({"": pd.NA, "na": pd.NA, "nan": pd.NA, "null": pd.NA, "none": pd.NA})
    text = text.str.replace(",", ".", regex=False)
    text = text.str.replace(r"[^0-9\.\-]", "", regex=True)
    text = text.where(~text.eq(""), pd.NA)
    return pd.to_numeric(text, errors="coerce").astype("Float64")


def _to_percent_scale(series: pd.Series) -> pd.Series:
    values = _clean_float_series(series)
    return (values * 100).where(values <= 1, values).astype("Float64")


def _normalize_dtypes(dataframe: pd.DataFrame) -> pd.DataFrame:
    result = dataframe.copy()

    for column in STR_COLS:
        if column in result.columns:
            result[column] = result[column].astype("string").str.strip()

    for column in FLOAT_COLS:
        if column in result.columns:
            result[column] = _clean_float_series(result[column])

    for column in DATETIME_COLS:
        if column in result.columns:
            cleaned = (
                result[column]
                .astype("string")
                .str.strip()
                .str.replace("\u00a0", " ", regex=False)
                .str.replace("-", "/", regex=False)
                .str.replace(r"[^\d/]", "", regex=True)
            )
            cleaned = cleaned.replace({"": pd.NA, "N/A": pd.NA, "n/a": pd.NA, "NA": pd.NA, "nan": pd.NA})
            result[column] = pd.to_datetime(
                cleaned,
                errors="coerce",
                dayfirst=True,
                format="mixed",
            )

    return result


def _op_psg_basal_transform(dataframe: pd.DataFrame, **_: Any) -> pd.DataFrame:
    df = _normalize_dtypes(dataframe)

    years = _clean_float_series(df.get("edad_anos", pd.Series(pd.NA, index=df.index))).fillna(0)
    months = _clean_float_series(df.get("edad_meses", pd.Series(pd.NA, index=df.index))).fillna(0)
    days = _clean_float_series(df.get("edad_dias", pd.Series(pd.NA, index=df.index))).fillna(0)
    df["anos_decimales"] = (years + (months / 12.0) + (days / 365.25)).round(4).astype("Float64")

    for unit_column in [
        "medida_peso",
        "medida_talla",
        "medida_cuello",
        "medida_perimetro_abdominal",
    ]:
        if unit_column in df.columns:
            df[unit_column] = df[unit_column].astype("string").str.lower().str.strip()

    units = {
        "peso": {"kg": {"kg", "kgs", "kgr", "kl"}, "g": {"g", "gr", "grs"}},
        "talla": {"metros": {"m", "mts", "metros"}, "centimetros": {"c", "cm", "cms", "a"}},
        "cuello": {"metros": {"m", "mts", "metros"}, "centimetros": {"c", "cm", "cms"}},
        "perimetro_abdominal": {
            "metros": {"m", "ms", "mts"},
            "centimetros": {"cm", "cms", "cm.", ".cm", ".ccm", "ccm"},
        },
    }

    if {"peso", "medida_peso"}.issubset(df.columns):
        df["peso_kg"] = pd.Series(pd.NA, index=df.index, dtype="Float64")
        peso = _clean_float_series(df["peso"])
        mask_kg = df["medida_peso"].isin(units["peso"]["kg"])
        mask_g = df["medida_peso"].isin(units["peso"]["g"])
        df.loc[mask_kg, "peso_kg"] = peso[mask_kg]
        df.loc[mask_g, "peso_kg"] = (peso[mask_g] / 1000.0).astype("Float64")

    if {"talla", "medida_talla"}.issubset(df.columns):
        df["talla_cm"] = pd.Series(pd.NA, index=df.index, dtype="Float64")
        talla = _clean_float_series(df["talla"])
        mask_m = df["medida_talla"].isin(units["talla"]["metros"])
        mask_cm = df["medida_talla"].isin(units["talla"]["centimetros"])
        df.loc[mask_m, "talla_cm"] = (talla[mask_m] * 100.0).astype("Float64")
        df.loc[mask_cm, "talla_cm"] = talla[mask_cm]

    if {"cuello", "medida_cuello"}.issubset(df.columns):
        df["cuello_cm"] = pd.Series(pd.NA, index=df.index, dtype="Float64")
        cuello = _clean_float_series(df["cuello"])
        mask_m = df["medida_cuello"].isin(units["cuello"]["metros"])
        mask_cm = df["medida_cuello"].isin(units["cuello"]["centimetros"])
        df.loc[mask_m, "cuello_cm"] = (cuello[mask_m] * 100.0).astype("Float64")
        df.loc[mask_cm, "cuello_cm"] = cuello[mask_cm]

    if {"perimetro_abdominal", "medida_perimetro_abdominal"}.issubset(df.columns):
        df["perimetro_abdominal_cm"] = pd.Series(pd.NA, index=df.index, dtype="Float64")
        perimetro = _clean_float_series(df["perimetro_abdominal"])
        mask_m = df["medida_perimetro_abdominal"].isin(units["perimetro_abdominal"]["metros"])
        mask_cm = df["medida_perimetro_abdominal"].isin(units["perimetro_abdominal"]["centimetros"])
        df.loc[mask_m, "perimetro_abdominal_cm"] = (perimetro[mask_m] * 100.0).astype("Float64")
        df.loc[mask_cm, "perimetro_abdominal_cm"] = perimetro[mask_cm]

    def _calc_txx(rem_col: str, nrem_col: str, total_col: str, target_col: str) -> None:
        if not {rem_col, nrem_col, total_col}.issubset(df.columns):
            return
        rem = _clean_float_series(df[rem_col]).fillna(0)
        nrem = _clean_float_series(df[nrem_col]).fillna(0)
        total = _clean_float_series(df[total_col])
        value = (rem + nrem) / total
        value = value.where(total > 0).round(2)
        df[target_col] = value.astype("Float64")

    _calc_txx("tiempo_desat_90_rem", "tiempo_desat_90_nrem", "tiempo_sueno", "t90")
    _calc_txx("tiempo_desat_80_rem", "tiempo_desat_80_nrem", "tiempo_sueno", "t80")
    _calc_txx("tiempo_desat_70_rem", "tiempo_desat_70_nrem", "tiempo_sueno", "t70")

    cols_to_drop = [
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
    existing_drop = [column for column in cols_to_drop if column in df.columns]
    if existing_drop:
        df = df.drop(columns=existing_drop)

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
        "version_control": "basal_version_control",
    }
    df = df.rename(columns=rename_map)

    percent_cols = [
        "basal_eficiencia_sueno",
        "basal_porcentaje_sueno_rem",
        "basal_porcentaje_sueno_profundo",
        "basal_t90",
        "basal_t80",
        "basal_t70",
    ]
    for column in percent_cols:
        if column not in df.columns:
            continue
        values = _clean_float_series(df[column])
        df[column] = (values / 100).where(values > 1, values).astype("Float64")

    if "basal_eficiencia_sueno" in df.columns:
        eficiencia = _clean_float_series(df["basal_eficiencia_sueno"])
        df["cat_efic_sueno"] = pd.Series("Sin dato", index=df.index, dtype="string")
        df.loc[eficiencia < 0.41, "cat_efic_sueno"] = "Muy baja"
        df.loc[(eficiencia >= 0.41) & (eficiencia < 0.85), "cat_efic_sueno"] = "Baja"
        df.loc[eficiencia >= 0.85, "cat_efic_sueno"] = "Normal"

    if "basal_epworth" in df.columns:
        epworth = _clean_float_series(df["basal_epworth"])
        df["cat_epworth"] = pd.Series("Sin dato", index=df.index, dtype="string")
        df.loc[epworth < 10, "cat_epworth"] = "Normal"
        df.loc[(epworth >= 10) & (epworth < 14), "cat_epworth"] = "Leve"
        df.loc[(epworth >= 14) & (epworth < 18), "cat_epworth"] = "Moderada"
        df.loc[epworth >= 18, "cat_epworth"] = "Grave"

    if {"pte_anos_decimales", "basal_iah"}.issubset(df.columns):
        age_years = _clean_float_series(df["pte_anos_decimales"])
        iah = _clean_float_series(df["basal_iah"])
        df["cat_iah"] = pd.Series("Inconsistente", index=df.index, dtype="string")

        adult = age_years >= 12
        pediatric = age_years < 12

        df.loc[adult & (iah < 5), "cat_iah"] = "Normal"
        df.loc[adult & (iah >= 5) & (iah < 15), "cat_iah"] = "Leve"
        df.loc[adult & (iah >= 15) & (iah < 30), "cat_iah"] = "Moderado"
        df.loc[adult & (iah >= 30), "cat_iah"] = "Grave"

        df.loc[pediatric & (iah < 2), "cat_iah"] = "Normal"
        df.loc[pediatric & (iah >= 2) & (iah < 5), "cat_iah"] = "Leve"
        df.loc[pediatric & (iah >= 5) & (iah < 10), "cat_iah"] = "Moderado"
        df.loc[pediatric & (iah >= 10), "cat_iah"] = "Grave"

    if "pte_anos_decimales" in df.columns:
        age_years = _clean_float_series(df["pte_anos_decimales"])
        df["pte_grupo_edad"] = pd.Series(pd.NA, index=df.index, dtype="string")
        df.loc[age_years < 12, "pte_grupo_edad"] = "Menor de 12"
        df.loc[(age_years >= 12) & (age_years < 18), "pte_grupo_edad"] = "De 12 a 18"
        df.loc[age_years >= 18, "pte_grupo_edad"] = "Mayor de 18"

    if "basal_indice_microalertamientos" in df.columns:
        micro = _clean_float_series(df["basal_indice_microalertamientos"])
        df["cat_indice_microalertamientos"] = pd.Series("Sin dato", index=df.index, dtype="string")
        df.loc[micro < 10, "cat_indice_microalertamientos"] = "Normal"
        df.loc[micro >= 10, "cat_indice_microalertamientos"] = "Anormal"

    if "basal_porcentaje_sueno_profundo" in df.columns:
        profundo = _to_percent_scale(df["basal_porcentaje_sueno_profundo"])
        df["cat_porc_sueno_profundo"] = pd.Series("Sin dato", index=df.index, dtype="string")
        df.loc[profundo < 15, "cat_porc_sueno_profundo"] = "Bajo"
        df.loc[(profundo >= 15) & (profundo < 30), "cat_porc_sueno_profundo"] = "Normal"
        df.loc[profundo >= 30, "cat_porc_sueno_profundo"] = "Aumentado"

    if "basal_porcentaje_sueno_rem" in df.columns:
        rem = _to_percent_scale(df["basal_porcentaje_sueno_rem"])
        df["cat_porc_sueno_rem"] = pd.Series("Sin dato", index=df.index, dtype="string")
        df.loc[rem < 20, "cat_porc_sueno_rem"] = "Bajo"
        df.loc[(rem >= 20) & (rem < 40), "cat_porc_sueno_rem"] = "Normal"
        df.loc[rem >= 40, "cat_porc_sueno_rem"] = "Aumentado"

    for column in FINAL_COLS:
        if column not in df.columns:
            df[column] = pd.NA

    return df[FINAL_COLS].copy()


def register_psg_operations(registry) -> None:
    registry.register("psg_basal_transform", _op_psg_basal_transform)
