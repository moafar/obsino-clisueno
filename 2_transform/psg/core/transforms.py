"""Transformación PSG: tipos canónicos y seis variables derivadas."""

from __future__ import annotations

import math
from typing import Any

import pandas as pd


DATA_TYPES: dict[str, str] = {
    "pte_nombre": "string",
    "pte_id": "string",
    "pte_edad_anos": "int",
    "pte_edad_meses": "int",
    "pte_edad_dias": "int",
    "pte_edad_decimal_anos": "float",
    "pte_grupo_edad": "string",
    "pte_peso_kg": "float",
    "pte_talla_cm": "float",
    "pte_imc_kg_m2": "float",
    "pte_cuello_cm": "float",
    "pte_perimetro_abdominal_cm": "float",
    "arq_tiempo_grabacion_min": "float",
    "arq_tiempo_cama_min": "float",
    "arq_tiempo_sueno_min": "float",
    "arq_eficiencia_pct": "float",
    "arq_latencia_sueno_min": "float",
    "arq_latencia_rem_min": "float",
    "arq_tiempo_despierto_min": "float",
    "arq_microalertamientos_total_n": "int",
    "arq_microalertamientos_respiratorios_n": "int",
    "arq_microalertamientos_plm_n": "int",
    "arq_microalertamientos_espontaneos_n": "int",
    "arq_indice_despertares_por_hora": "float",
    "fase_s1_episodios_n": "int",
    "fase_s1_duracion_min": "float",
    "fase_s1_tst_pct": "float",
    "fase_s2_episodios_n": "int",
    "fase_s2_duracion_min": "float",
    "fase_s2_tst_pct": "float",
    "fase_s3_episodios_n": "int",
    "fase_s3_duracion_min": "float",
    "fase_s3_tst_pct": "float",
    "fase_rem_episodios_n": "int",
    "fase_rem_duracion_min": "float",
    "fase_rem_tst_pct": "float",
    "fase_despierto_episodios_n": "int",
    "fase_despierto_duracion_min": "float",
    "evresp_ac_numero_n": "int",
    "evresp_ac_duracion_max_s": "float",
    "evresp_ac_duracion_media_s": "float",
    "evresp_ac_duracion_total_min": "float",
    "evresp_ac_indice_evhora": "float",
    "evresp_ao_numero_n": "int",
    "evresp_ao_duracion_max_s": "float",
    "evresp_ao_duracion_media_s": "float",
    "evresp_ao_duracion_total_min": "float",
    "evresp_ao_indice_evhora": "float",
    "evresp_am_numero_n": "int",
    "evresp_am_duracion_max_s": "float",
    "evresp_am_duracion_media_s": "float",
    "evresp_am_duracion_total_min": "float",
    "evresp_am_indice_evhora": "float",
    "evresp_ap_numero_n": "int",
    "evresp_ap_duracion_max_s": "float",
    "evresp_ap_duracion_media_s": "float",
    "evresp_ap_duracion_total_min": "float",
    "evresp_ap_indice_evhora": "float",
    "evresp_hip_numero_n": "int",
    "evresp_hip_duracion_max_s": "float",
    "evresp_hip_duracion_media_s": "float",
    "evresp_hip_duracion_total_min": "float",
    "evresp_hip_indice_evhora": "float",
    "evresp_ah_numero_n": "int",
    "evresp_ah_duracion_max_s": "float",
    "evresp_ah_duracion_media_s": "float",
    "evresp_ah_duracion_total_min": "float",
    "evresp_ah_indice_evhora": "float",
    "evresp_ac_configuracion_s": "float",
    "evresp_ao_configuracion_s": "float",
    "evresp_am_configuracion_s": "float",
    "evresp_hip_configuracion_s": "float",
    "evresp_ac_numero_nrem_n": "int",
    "evresp_ac_numero_rem_n": "int",
    "evresp_ao_numero_nrem_n": "int",
    "evresp_ao_numero_rem_n": "int",
    "evresp_am_numero_nrem_n": "int",
    "evresp_am_numero_rem_n": "int",
    "evresp_hip_numero_nrem_n": "int",
    "evresp_hip_numero_rem_n": "int",
    "evresp_ah_numero_nrem_n": "int",
    "evresp_ah_numero_rem_n": "int",
    "evresp_iah_rem_evhora": "float",
    "evresp_iah_nrem_evhora": "float",
    "evresp_iah_tst_evhora": "float",
    "oxi_spo2_promedio_despierto_pct": "float",
    "oxi_indice_desat_despierto_evhora": "float",
    "oxi_spo2_promedio_rem_pct": "float",
    "oxi_indice_desat_rem_evhora": "float",
    "oxi_spo2_promedio_nrem_pct": "float",
    "oxi_indice_desat_nrem_evhora": "float",
    "oxi_spo2_promedio_tst_pct": "float",
    "oxi_indice_desat_tst_evhora": "float",
    "oxi_t95_despierto_min": "float",
    "oxi_t95_rem_min": "float",
    "oxi_t95_nrem_min": "float",
    "oxi_t95_tst_min": "float",
    "oxi_t90_despierto_min": "float",
    "oxi_t90_rem_min": "float",
    "oxi_t90_nrem_min": "float",
    "oxi_t90_tst_min": "float",
    "oxi_t85_despierto_min": "float",
    "oxi_t85_rem_min": "float",
    "oxi_t85_nrem_min": "float",
    "oxi_t85_tst_min": "float",
    "oxi_t80_despierto_min": "float",
    "oxi_t80_rem_min": "float",
    "oxi_t80_nrem_min": "float",
    "oxi_t80_tst_min": "float",
    "oxi_t75_despierto_min": "float",
    "oxi_t75_rem_min": "float",
    "oxi_t75_nrem_min": "float",
    "oxi_t75_tst_min": "float",
    "oxi_t70_despierto_min": "float",
    "oxi_t70_rem_min": "float",
    "oxi_t70_nrem_min": "float",
    "oxi_t70_tst_min": "float",
    "oxi_t60_despierto_min": "float",
    "oxi_t60_rem_min": "float",
    "oxi_t60_nrem_min": "float",
    "oxi_t60_tst_min": "float",
    "oxi_t50_despierto_min": "float",
    "oxi_t50_rem_min": "float",
    "oxi_t50_nrem_min": "float",
    "oxi_t50_tst_min": "float",
    "oxi_t90_pct": "float",
    "oxi_spo2_eventos_promedio_pct": "float",
    "oxi_spo2_eventos_min_pct": "float",
    "oxi_spo2_sueno_min_pct": "float",
    "fc_promedio_despierto_lpm": "float",
    "fc_promedio_rem_lpm": "float",
    "fc_promedio_nrem_lpm": "float",
    "movmi_plm_total_n": "int",
    "movmi_plm_indice_evhora": "float",
    "movmi_lm_total_n": "int",
    "movmi_lm_indice_evhora": "float",
    "pos_supino_duracion_min": "float",
    "pos_supino_pct": "float",
    "pos_supino_iah_evhora": "float",
    "pos_derecho_duracion_min": "float",
    "pos_derecho_pct": "float",
    "pos_derecho_iah_evhora": "float",
    "pos_izquierdo_duracion_min": "float",
    "pos_izquierdo_pct": "float",
    "pos_izquierdo_iah_evhora": "float",
    "clin_indicacion": "string",
    "clin_epworth_puntos": "int",
    "clin_interpretacion": "string",
    "clin_conclusiones": "string",
    "clin_ronquido": "string",
    "meta_fecha_estudio": "date",
    "meta_solicita": "string",
    "meta_empresa": "string",
    "meta_fuente": "string",
    "meta_uuid": "string",
    "meta_version_control": "string",
}
FINAL_COLS = list(DATA_TYPES)
DERIVED = {
    "pte_edad_decimal_anos", "pte_grupo_edad", "pte_peso_kg",
    "pte_talla_cm", "pte_cuello_cm", "pte_perimetro_abdominal_cm",
}
UNIT_FACTORS = {
    "peso": {"kg": 1, "kgs": 1, "g": 0.001, "gr": 0.001, "grs": 0.001},
    "talla": {"cm": 1, "cms": 1, "m": 100, "mts": 100, "metros": 100, "mm": 0.1},
    "cuello": {"cm": 1, "cms": 1, "m": 100, "mts": 100, "metros": 100, "mm": 0.1},
    "perimetro_abdominal": {"cm": 1, "cms": 1, "m": 100, "mts": 100, "metros": 100, "mm": 0.1},
}


def _numeric(series: pd.Series, column: str, integer: bool = False) -> pd.Series:
    text = series.astype("string").str.strip().replace({"": pd.NA, "-": pd.NA, "--": pd.NA})
    text = text.str.replace(",", ".", regex=False)
    try:
        values = pd.to_numeric(text, errors="raise")
        if integer and ((values.dropna() % 1) != 0).any():
            raise ValueError("Valor no entero")
        return values.astype("Int64" if integer else "Float64")
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Valor numérico inválido en {column}") from exc


def _date(series: pd.Series, column: str) -> pd.Series:
    text = series.astype("string").str.strip().replace("", pd.NA)
    parsed = pd.to_datetime(text, errors="coerce", dayfirst=True, format="mixed")
    if (text.notna() & parsed.isna()).any():
        raise ValueError(f"Fecha inválida en {column}")
    return parsed


def _converted_unit(dataframe: pd.DataFrame, part: str) -> pd.Series:
    values = _numeric(dataframe[f"pte_{part}_valor"], f"pte_{part}_valor")
    units = dataframe[f"pte_{part}_unidad"].astype("string").str.strip().str.lower()
    factors = UNIT_FACTORS[part]
    if (values.notna() & ~units.isin(factors)).fillna(False).any():
        raise ValueError(f"Unidad antropométrica inválida en pte_{part}_unidad")
    result = pd.Series(pd.NA, index=dataframe.index, dtype="Float64")
    for unit, factor in factors.items():
        mask = values.notna() & units.eq(unit).fillna(False)
        result.loc[mask] = values.loc[mask] * factor
    return result


def _op_psg_basal_transform(dataframe: pd.DataFrame, **_: Any) -> pd.DataFrame:
    required = (set(FINAL_COLS) - DERIVED) | {
        f"pte_{part}_{kind}"
        for part in UNIT_FACTORS for kind in ("valor", "unidad")
    }
    if set(dataframe.columns) != required or len(dataframe.columns) != 158:
        raise ValueError("El esquema de entrada PSG debe tener exactamente 158 columnas")

    df = dataframe.copy()
    for column, dtype in DATA_TYPES.items():
        if column in DERIVED:
            continue
        if dtype == "int":
            df[column] = _numeric(df[column], column, integer=True)
        elif dtype == "float":
            df[column] = _numeric(df[column], column)
        elif dtype == "date":
            df[column] = _date(df[column], column)
        else:
            df[column] = df[column].astype("string").replace("", pd.NA)

    missing_t90 = df["oxi_t90_pct"].isna()
    t90_minutes = df["oxi_t90_tst_min"]
    sleep_minutes = df["arq_tiempo_sueno_min"]
    calculable = missing_t90 & t90_minutes.notna() & sleep_minutes.notna()
    if calculable.any():
        numerator = t90_minutes.loc[calculable]
        denominator = sleep_minutes.loc[calculable]
        if (any(not math.isfinite(value) for value in numerator) or
                any(not math.isfinite(value) for value in denominator) or
                (numerator < 0).any() or (denominator <= 0).any() or
                (numerator > denominator).any()):
            raise ValueError("No se puede derivar oxi_t90_pct con los minutos TST disponibles")
        df.loc[calculable, "oxi_t90_pct"] = (100 * numerator / denominator).astype("Float64")

    identifiers = df["pte_id"].str.strip()
    uuids = df["meta_uuid"].str.strip()
    if identifiers.isna().any() or identifiers.eq("").any():
        raise ValueError("Identificador PSG ausente")
    if uuids.isna().any() or uuids.eq("").any():
        raise ValueError("UUID PSG ausente")
    if uuids.duplicated().any():
        raise ValueError("UUID PSG duplicado en la entrada; no se eliminaron filas")

    years = df["pte_edad_anos"].astype("Float64")
    months = df["pte_edad_meses"].astype("Float64")
    days = df["pte_edad_dias"].astype("Float64")
    age_present = years.notna() | months.notna() | days.notna()
    age = (years.fillna(0) + months.fillna(0) / 12 + days.fillna(0) / 365.25).round(4)
    df["pte_edad_decimal_anos"] = age.where(age_present).astype("Float64")
    group = pd.Series(pd.NA, index=df.index, dtype="string")
    group.loc[age_present & age.lt(12)] = "Menor de 12"
    group.loc[age_present & age.ge(12) & age.lt(18)] = "De 12 a 18"
    group.loc[age_present & age.ge(18)] = "Mayor de 18"
    df["pte_grupo_edad"] = group

    for part, target in (
        ("peso", "pte_peso_kg"), ("talla", "pte_talla_cm"),
        ("cuello", "pte_cuello_cm"),
        ("perimetro_abdominal", "pte_perimetro_abdominal_cm"),
    ):
        df[target] = _converted_unit(df, part)

    return df[FINAL_COLS].copy()


def register_psg_operations(registry) -> None:
    registry.register("psg_basal_transform", _op_psg_basal_transform)
