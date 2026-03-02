from __future__ import annotations

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
    "marca_equipo": "str",
    "tipo_mascara": "str",
    "tamano_mascara": "str",
    "presion_terapeutica": "str",
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
    "pte_peso_kg",
    "pte_talla_cm",
    "pte_cuello_cm",
    "pte_perimetro_abdominal_cm",
    "xpap_solicita",
    "xpap_empresa",
    "xpap_fecha_estudio",
    "xpap_epworth",
    "xpap_tiempo_en_cama",
    "xpap_tiempo_sueno",
    "xpap_eficiencia_sueno",
    "xpap_latencia_sueno_total",
    "xpap_latencia_sueno_rem",
    "xpap_indice_microalertamientos",
    "xpap_porcentaje_sueno_rem",
    "xpap_porcentaje_sueno_profundo",
    "xpap_iac",
    "xpap_iao",
    "xpap_iam",
    "xpap_ih",
    "xpap_iah",
    "xpap_indice_desat_rem",
    "xpap_indice_desat_nrem",
    "xpap_indice_desat_total",
    "xpap_numero_eventos_ah",
    "xpap_t90",
    "xpap_t80",
    "xpap_t70",
    "xpap_marca_equipo",
    "xpap_tipo_mascara",
    "xpap_tamano_mascara",
    "xpap_presion_terapeutica",
    "xpap_fuente",
    "xpap_uuid",
    "xpap_version_control",
]


def _clean_float_series(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip().str.lower()
    text = text.replace({"": pd.NA, "na": pd.NA, "nan": pd.NA, "null": pd.NA, "none": pd.NA})
    text = text.str.replace(",", ".", regex=False)
    text = text.str.replace(r"[^0-9\.\-]", "", regex=True)
    text = text.where(~text.eq(""), pd.NA)
    return pd.to_numeric(text, errors="coerce").astype("Float64")


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


def _op_xpap_transform(dataframe: pd.DataFrame, **_: object) -> pd.DataFrame:
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
        "solicita": "xpap_solicita",
        "empresa": "xpap_empresa",
        "fecha_estudio": "xpap_fecha_estudio",
        "epworth": "xpap_epworth",
        "tiempo_en_cama": "xpap_tiempo_en_cama",
        "tiempo_sueno": "xpap_tiempo_sueno",
        "eficiencia_sueno": "xpap_eficiencia_sueno",
        "latencia_sueno_total": "xpap_latencia_sueno_total",
        "latencia_sueno_rem": "xpap_latencia_sueno_rem",
        "indice_microalertamientos": "xpap_indice_microalertamientos",
        "porcentaje_sueno_rem": "xpap_porcentaje_sueno_rem",
        "porcentaje_sueno_profundo": "xpap_porcentaje_sueno_profundo",
        "iac": "xpap_iac",
        "iao": "xpap_iao",
        "iam": "xpap_iam",
        "ih": "xpap_ih",
        "iah": "xpap_iah",
        "indice_desat_rem": "xpap_indice_desat_rem",
        "indice_desat_nrem": "xpap_indice_desat_nrem",
        "indice_desat_total": "xpap_indice_desat_total",
        "numero_eventos_ah": "xpap_numero_eventos_ah",
        "fuente": "xpap_fuente",
        "uuid": "xpap_uuid",
        "anos_decimales": "pte_anos_decimales",
        "peso_kg": "pte_peso_kg",
        "talla_cm": "pte_talla_cm",
        "cuello_cm": "pte_cuello_cm",
        "perimetro_abdominal_cm": "pte_perimetro_abdominal_cm",
        "t90": "xpap_t90",
        "t80": "xpap_t80",
        "t70": "xpap_t70",
        "version_control": "xpap_version_control",
        "marca_equipo": "xpap_marca_equipo",
        "tipo_mascara": "xpap_tipo_mascara",
        "tamano_mascara": "xpap_tamano_mascara",
        "presion_terapeutica": "xpap_presion_terapeutica",
    }
    df = df.rename(columns=rename_map)

    percent_cols = [
        "xpap_eficiencia_sueno",
        "xpap_porcentaje_sueno_rem",
        "xpap_porcentaje_sueno_profundo",
        "xpap_t90",
        "xpap_t80",
        "xpap_t70",
    ]
    for column in percent_cols:
        if column not in df.columns:
            continue
        values = _clean_float_series(df[column])
        df[column] = (values / 100).where(values > 1, values).astype("Float64")

    for column in FINAL_COLS:
        if column not in df.columns:
            df[column] = pd.NA

    return df[FINAL_COLS].copy()


def register_xpap_operations(registry) -> None:
    registry.register("xpap_transform", _op_xpap_transform)
