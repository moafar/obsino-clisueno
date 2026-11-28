"""Transformación PSG: tipos canónicos y seis variables derivadas."""

from __future__ import annotations

import math
import json
import re
import logging
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
    "meta_completitud_pct": "float",
    "meta_incidencias_calidad": "string",
}
FINAL_COLS = list(DATA_TYPES)
DERIVED = {
    "pte_edad_decimal_anos", "pte_grupo_edad", "pte_peso_kg",
    "pte_talla_cm", "pte_cuello_cm", "pte_perimetro_abdominal_cm",
    "meta_incidencias_calidad",
}
UNIT_FACTORS = {
    "peso": {"kg": 1, "kgs": 1, "g": 0.001, "gr": 0.001, "grs": 0.001},
    "talla": {"cm": 1, "cms": 1, "m": 100, "mts": 100, "metros": 100, "mm": 0.1},
    "cuello": {"cm": 1, "cms": 1, "m": 100, "mts": 100, "metros": 100, "mm": 0.1},
    "perimetro_abdominal": {"cm": 1, "cms": 1, "m": 100, "mts": 100, "metros": 100, "mm": 0.1},
}


def _numeric(series: pd.Series, column: str, integer: bool = False,
             incidents: list[list[dict[str, str]]] | None = None) -> pd.Series:
    text = series.astype("string").str.strip()
    absent = text.str.upper().isin({"", "N/A", "NA", "NAN", "NULL", "NONE"})
    absent |= text.str.fullmatch(r"[.\-]+", na=False)
    text = text.mask(absent).str.replace(",", ".", regex=False)
    values = pd.to_numeric(text, errors="coerce")
    invalid = text.notna() & (values.isna() | values.isin([math.inf, -math.inf]))
    if integer:
        invalid |= text.notna() & values.mod(1).ne(0).fillna(False)
        invalid |= values.ge(2**63).fillna(False) | values.lt(-(2**63)).fillna(False)
    if incidents is None and invalid.fillna(False).any():
        raise ValueError(f"Valor numérico inválido en {column}")
    if incidents is not None:
        error = "entero_incompatible" if integer else "decimal_incompatible"
        for position, is_invalid in enumerate(invalid.fillna(False).to_numpy(dtype=bool)):
            if is_invalid:
                incidents[position].append({
                    "campo": column, "valor_original": str(series.iloc[position]),
                    "error": error, "accion": "convertido_a_null",
                })
    return values.mask(invalid).astype("Int64" if integer else "Float64")


def _date(series: pd.Series, column: str,
          incidents: list[list[dict[str, str]]]) -> pd.Series:
    text = series.astype("string").str.strip()
    missing = text.isna() | text.str.upper().isin({"", "N/A", "NA", "NULL", "NONE"})
    text = text.mask(missing)
    parsed = pd.to_datetime(text, errors="coerce", dayfirst=True, format="mixed")
    for position, is_missing in enumerate(missing.fillna(True).to_numpy(dtype=bool)):
        if is_missing or pd.isna(parsed.iloc[position]):
            incidents[position].append({
                "campo": column,
                "valor_original": None if pd.isna(series.iloc[position]) else str(series.iloc[position]),
                "error": "fecha_ausente" if is_missing else "fecha_invalida",
                "accion": "convertido_a_null",
            })
    return parsed


def _converted_unit(dataframe: pd.DataFrame, part: str,
                    incidents: list[list[dict[str, str]]]) -> pd.Series:
    values = _numeric(dataframe[f"pte_{part}_valor"], f"pte_{part}_valor",
                      incidents=incidents)
    units = dataframe[f"pte_{part}_unidad"].astype("string").str.strip().str.lower()
    factors = UNIT_FACTORS[part]
    # Unidad ausente/no reconocida: el dato derivado queda nulo, sin inferir la unidad.
    result = pd.Series(pd.NA, index=dataframe.index, dtype="Float64")
    for unit, factor in factors.items():
        mask = values.notna() & units.eq(unit).fillna(False)
        result.loc[mask] = values.loc[mask] * factor
    return result


def validate_psg_technical_metadata(dataframe: pd.DataFrame) -> None:
    """Comprueba metadatos bloqueantes también en filas que se omitirán por UUID."""
    if dataframe.empty:
        return
    completeness = _numeric(dataframe["meta_completitud_pct"], "meta_completitud_pct")
    if completeness.isna().any() or (((completeness < 0) | (completeness > 100))
                                     .fillna(False).any()):
        raise ValueError("meta_completitud_pct ausente o fuera del rango 0-100")


def _op_psg_basal_transform(dataframe: pd.DataFrame, **_: Any) -> pd.DataFrame:
    required = (set(FINAL_COLS) - DERIVED) | {
        f"pte_{part}_{kind}"
        for part in UNIT_FACTORS for kind in ("valor", "unidad")
    }
    if set(dataframe.columns) != required or len(dataframe.columns) != len(required):
        raise ValueError("El esquema de entrada PSG no coincide con el contrato")

    source_uuids = dataframe["meta_uuid"].astype("string").str.strip()
    if not source_uuids.str.fullmatch(r"[0-9a-f]{32}", na=False).all():
        raise ValueError("UUID PSG ausente o inválido")
    repeated = source_uuids.duplicated(keep="first")
    validate_psg_technical_metadata(dataframe.loc[repeated])
    if repeated.any():
        logging.warning("UUID PSG repetidos en entrada: %s omitidos", int(repeated.sum()))
    df = dataframe.loc[~repeated].copy()
    original_ids = df["pte_id"].copy()
    incidents: list[list[dict[str, str]]] = [[] for _ in range(len(df))]
    for column, dtype in DATA_TYPES.items():
        if column in DERIVED:
            continue
        if dtype == "int":
            df[column] = _numeric(df[column], column, integer=True, incidents=incidents)
        elif dtype == "float":
            df[column] = _numeric(df[column], column,
                                  incidents=None if column.startswith("meta_") else incidents)
        elif dtype == "date":
            df[column] = _date(df[column], column, incidents)
        else:
            df[column] = df[column].astype("string").replace("", pd.NA)

    missing_id = df["pte_id"].isna() | df["pte_id"].str.strip().eq("")
    for position, is_missing in enumerate(missing_id.fillna(True).to_numpy(dtype=bool)):
        if is_missing:
            incidents[position].append({
                "campo": "pte_id",
                "valor_original": None if pd.isna(original_ids.iloc[position])
                else str(original_ids.iloc[position]),
                "error": "identificador_ausente", "accion": "conservar_null",
            })
    df["pte_id"] = df["pte_id"].mask(missing_id)

    missing_t90 = df["oxi_t90_pct"].isna()
    t90_minutes = df["oxi_t90_tst_min"]
    sleep_minutes = df["arq_tiempo_sueno_min"]
    calculable = missing_t90 & t90_minutes.notna() & sleep_minutes.notna()
    # Sin sueño registrado, 0/0 es indefinido: conservar T90% nulo.
    zero_over_zero = (t90_minutes.eq(0) & sleep_minutes.eq(0)).fillna(False)
    # La división por cero deja el derivado ausente; no valida relaciones clínicas.
    calculable = calculable & ~zero_over_zero & sleep_minutes.ne(0).fillna(False)
    if calculable.any():
        numerator = t90_minutes.loc[calculable]
        denominator = sleep_minutes.loc[calculable]
        df.loc[calculable, "oxi_t90_pct"] = (100 * numerator / denominator).astype("Float64")

    completeness = df["meta_completitud_pct"]
    if completeness.isna().any():
        raise ValueError("meta_completitud_pct ausente")
    if ((completeness < 0) | (completeness > 100)).fillna(False).any():
        raise ValueError("meta_completitud_pct fuera del rango 0-100")
    uuids = df["meta_uuid"].str.strip()
    if uuids.isna().any() or not uuids.str.fullmatch(r"[0-9a-f]{32}", na=False).all():
        raise ValueError("UUID PSG ausente o inválido")

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
        df[target] = _converted_unit(df, part, incidents)

    df["meta_incidencias_calidad"] = pd.Series(
        [json.dumps(items, ensure_ascii=False, separators=(",", ":")) if items else pd.NA
         for items in incidents], index=df.index, dtype="string")

    return df[FINAL_COLS].copy()


def register_psg_operations(registry) -> None:
    registry.register("psg_basal_transform", _op_psg_basal_transform)
