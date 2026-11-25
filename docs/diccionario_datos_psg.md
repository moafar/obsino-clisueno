# Diccionario de datos — polisomnografía (PSG)

> **Estado:** propuesta consolidada de nomenclatura aprobada durante la revisión; **no implementada** en el repositorio. Fecha: 23 de noviembre de 2026.

## 1. Alcance y verificación

Se consolidan los nombres acordados para PSG y se contrasta su disponibilidad con **seis informes de ejemplo**: **3 RTF** y **3 DOC**. La comparación distingue presencia de un valor verificable de mera existencia de una etiqueta o una columna. Se ha revisado la matriz de extracción experimental y las tablas originales de ambas plantillas. **No equivale a validar todo el universo de informes ni el pipeline de producción**.

**Total de campos canónicos propuestos: 157**, distribuidos en 10 grupos.

### Interpretación de la disponibilidad

- `3/3`, `2/3`, etc.: valor recuperado en ese número de los tres informes del formato con el extractor experimental; **un cero explícito cuenta como valor**, nunca como ausencia.
- `0/3`: no se recuperó un valor en ninguna de las tres muestras. Puede deberse a que la plantilla no incluye el indicador o a una limitación de lectura; las excepciones conocidas se documentan.
- `Sí* (0/3 recuperado)`: dato constatado en la portada de los DOC originales, pero no recuperado en las pruebas con `antiword`. No debe clasificarse como ausente del documento.
- `Derivado`: campo calculado por la transformación y no leído literalmente del informe.
- `Generado`: campo de trazabilidad producido por el pipeline y no informado clínicamente.
- La presencia en un documento **no demuestra que el pipeline actual lo extraiga correctamente**; además, en algunos informes una celda aparece vacía o como `--`.

### Convenciones

- Prefijo de sección acordado: `pte_`, `arq_`, `fase_`, `evresp_`, `oxi_`, `fc_`, `movmi_`, `pos_`, `clin_` y `meta_`.
- Los sufijos identifican unidades (`_min`, `_s`, `_pct`, `_kg`, `_cm`, `_evhora`, `_hora`, `_lpm`, `_puntos`, `_n`); las columnas de texto, fecha y clasificación pueden carecer de sufijo de medida.
- En indicadores por estado o fase, la parte intermedia identifica REM, NREM, TST o despierto. `TST` = tiempo total de sueño.
- `n` indica recuento; `%` es un porcentaje expresado en escala 0–100; `_evhora` identifica índices de eventos por hora (incluidos movimientos por hora cuando el indicador así lo expresa) y `_hora` se conserva en `arq_indice_despertares_por_hora`.
- Se elimina el prefijo `basal_` de columnas y se utiliza **PSG** para denominar el proceso. La referencia clínica al carácter basal del estudio no debe perderse conceptualmente.
- Los asteriscos junto a algunos campos son llamadas a notas editoriales; **no forman parte del nombre canónico**.
- **Un campo canónico por medida y tabla de origen.** Se conservan `evresp_ah_indice_evhora` (índice en «Resumen de eventos respiratorios») y `evresp_iah_tst_evhora` (IAH en «Resumen del índice de eventos respiratorios»), aunque sus valores puedan coincidir. La comparación entre ambos permitirá verificar su concordancia; no se fusionan.

## 2. Diccionario de campos

Las referencias de disponibilidad se basan en la matriz de seis documentos, con las salvedades explícitas en «Observaciones».

### 2.1. Paciente (pte_) — 12 campos

| Nº | Campo canónico | Descripción | Tipo | Unidad | RTF | DOC |
|---:|---|---|---|---|:---:|:---:|
| 1 | `pte_nombre` | Nombre del paciente tal como figura en el informe. | texto | — | 3/3 | 3/3 |
| 2 | `pte_id` | Identificador del paciente informado en el documento; conservar como texto. | texto | — | 3/3 | 3/3 |
| 3 | `pte_edad_anos` | Componente en años de la edad declarada. | entero | años | 3/3 | 3/3 |
| 4 | `pte_edad_meses` | Componente adicional en meses de la edad declarada. | entero | meses | 0/3 | 0/3 |
| 5 | `pte_edad_dias` | Componente adicional en días de la edad declarada. | entero | días | 0/3 | 0/3 |
| 6 | `pte_edad_decimal_anos` | Edad total expresada como años decimales, calculada a partir de años, meses y días. | decimal | años | Derivado | Derivado |
| 7 | `pte_grupo_edad` | Grupo de edad según reglas de categorización del pipeline. | categoría | — | Derivado | Derivado |
| 8 | `pte_peso_kg` | Peso corporal del paciente convertido a kilogramos. | decimal | kg | 3/3 | 3/3 |
| 9 | `pte_talla_cm` | Talla o estatura corporal convertida a centímetros. | decimal | cm | 3/3 | 3/3 |
| 10 | `pte_imc_kg_m2` | Índice de masa corporal comunicado en el informe (kg/m²). | decimal | kg/m² | 3/3 | 3/3 |
| 11 | `pte_cuello_cm` | Perímetro cervical o del cuello convertido a centímetros. | decimal | cm | 3/3 | 3/3 |
| 12 | `pte_perimetro_abdominal_cm` | Perímetro abdominal convertido a centímetros. | decimal | cm | 3/3 | 3/3 |

### 2.2. Arquitectura del sueño (arq_) — 12 campos

| Nº | Campo canónico | Descripción | Tipo | Unidad | RTF | DOC |
|---:|---|---|---|---|:---:|:---:|
| 13 | `arq_tiempo_grabacion_min` | Duración del registro polisomnográfico informada explícitamente. | decimal | min | 3/3 | 0/3 |
| 14 | `arq_tiempo_cama_min` | Tiempo transcurrido en cama durante la evaluación. | decimal | min | 3/3 | 3/3 |
| 15 | `arq_tiempo_sueno_min` | Tiempo total de sueño efectivo (TST). | decimal | min | 3/3 | 3/3 |
| 16 | `arq_eficiencia_pct` | Porcentaje de tiempo en cama que corresponde a sueño efectivo. | decimal | % | 3/3 | 3/3 |
| 17 | `arq_latencia_sueno_min` | Intervalo hasta el inicio del sueño según el informe. | decimal | min | 3/3 | 3/3 |
| 18 | `arq_latencia_rem_min` | Latencia hasta el sueño REM según el informe. | decimal | min | 3/3 | 3/3 |
| 19 | `arq_tiempo_despierto_min` | Tiempo despierto durante el sueño. | decimal | min | 3/3 | 3/3 |
| 20 | `arq_microalertamientos_total_n` | Número total de microalertamientos del registro. | entero | n | 3/3 | 3/3 |
| 21 | `arq_microalertamientos_respiratorios_n` | Número de microalertamientos asociados a eventos respiratorios. | entero | n | 3/3 | 3/3 |
| 22 | `arq_microalertamientos_plm_n` | Número de microalertamientos asociados a movimientos periódicos de miembros inferiores. | entero | n | 3/3 | 3/3 |
| 23 | `arq_microalertamientos_espontaneos_n` | Número de microalertamientos espontáneos. | entero | n | 3/3 | 3/3 |
| 24 | `arq_indice_despertares_por_hora` | Índice que el informe denomina «Índice Despertares»; en las muestras corresponde a microalertamientos por hora de sueño. | decimal | eventos/h | 3/3 | 3/3 |

### 2.3. Fases del sueño (fase_) — 14 campos

| Nº | Campo canónico | Descripción | Tipo | Unidad | RTF | DOC |
|---:|---|---|---|---|:---:|:---:|
| 25 | `fase_s1_episodios_n` | Número de episodios de sueño S1. | entero | n | 0/3 | 3/3 |
| 26 | `fase_s1_duracion_min` | Duración acumulada de sueño S1. | decimal | min | 3/3 | 3/3 |
| 27 | `fase_s1_tst_pct` | Proporción del tiempo total de sueño (TST) correspondiente a sueño S1. | decimal | % | 3/3 | 3/3 |
| 28 | `fase_s2_episodios_n` | Número de episodios de sueño S2. | entero | n | 0/3 | 3/3 |
| 29 | `fase_s2_duracion_min` | Duración acumulada de sueño S2. | decimal | min | 3/3 | 3/3 |
| 30 | `fase_s2_tst_pct` | Proporción del tiempo total de sueño (TST) correspondiente a sueño S2. | decimal | % | 3/3 | 3/3 |
| 31 | `fase_s3_episodios_n` | Número de episodios de sueño S3 (profundo). | entero | n | 0/3 | 3/3 |
| 32 | `fase_s3_duracion_min` | Duración acumulada de sueño S3 (profundo). | decimal | min | 3/3 | 3/3 |
| 33 | `fase_s3_tst_pct` | Proporción del tiempo total de sueño (TST) correspondiente a sueño S3 (profundo). | decimal | % | 3/3 | 3/3 |
| 34 | `fase_rem_episodios_n` | Número de episodios de sueño REM. | entero | n | 0/3 | 3/3 |
| 35 | `fase_rem_duracion_min` | Duración acumulada de sueño REM. | decimal | min | 3/3 | 3/3 |
| 36 | `fase_rem_tst_pct` | Proporción del tiempo total de sueño (TST) correspondiente a sueño REM. | decimal | % | 3/3 | 3/3 |
| 37 | `fase_despierto_episodios_n` | Número de episodios clasificados como «Despierto» en la tabla de distribución de fases. | entero | n | 0/3 | 3/3 |
| 38 | `fase_despierto_duracion_min` | Duración atribuida a «Despierto» en la tabla de distribución de fases. | decimal | min | 3/3 | 3/3 |

### 2.4. Eventos respiratorios (evresp_) — 47 campos

| Nº | Campo canónico | Descripción | Tipo | Unidad | RTF | DOC |
|---:|---|---|---|---|:---:|:---:|
| 39 | `evresp_ac_numero_n` | Número total de apneas centrales contabilizados durante el sueño. | entero | n | 3/3 | 3/3 |
| 40 | `evresp_ac_duracion_max_s` | Duración máxima de un evento de apneas centrales. | decimal | s | 0/3 | 3/3 |
| 41 | `evresp_ac_duracion_media_s` | Duración media de los eventos de apneas centrales. | decimal | s | 3/3 | 3/3 |
| 42 | `evresp_ac_duracion_total_min` | Suma de las duraciones de los eventos de apneas centrales. | decimal | min | 3/3 | 3/3 |
| 43 | `evresp_ac_indice_evhora` | Índice de eventos de apneas centrales por hora de sueño (TST). | decimal | eventos/h | 3/3 | 3/3 |
| 44 | `evresp_ao_numero_n` | Número total de apneas obstructivas contabilizados durante el sueño. | entero | n | 3/3 | 3/3 |
| 45 | `evresp_ao_duracion_max_s` | Duración máxima de un evento de apneas obstructivas. | decimal | s | 0/3 | 3/3 |
| 46 | `evresp_ao_duracion_media_s` | Duración media de los eventos de apneas obstructivas. | decimal | s | 3/3 | 3/3 |
| 47 | `evresp_ao_duracion_total_min` | Suma de las duraciones de los eventos de apneas obstructivas. | decimal | min | 3/3 | 3/3 |
| 48 | `evresp_ao_indice_evhora` | Índice de eventos de apneas obstructivas por hora de sueño (TST). | decimal | eventos/h | 3/3 | 3/3 |
| 49 | `evresp_am_numero_n` | Número total de apneas mixtas contabilizados durante el sueño. | entero | n | 3/3 | 3/3 |
| 50 | `evresp_am_duracion_max_s` | Duración máxima de un evento de apneas mixtas. | decimal | s | 0/3 | 3/3 |
| 51 | `evresp_am_duracion_media_s` | Duración media de los eventos de apneas mixtas. | decimal | s | 3/3 | 3/3 |
| 52 | `evresp_am_duracion_total_min` | Suma de las duraciones de los eventos de apneas mixtas. | decimal | min | 3/3 | 3/3 |
| 53 | `evresp_am_indice_evhora` | Índice de eventos de apneas mixtas por hora de sueño (TST). | decimal | eventos/h | 3/3 | 3/3 |
| 54 | `evresp_ap_numero_n` | Número total de suma de apneas contabilizados durante el sueño. | entero | n | 0/3 | 3/3 |
| 55 | `evresp_ap_duracion_max_s` | Duración máxima de un evento de suma de apneas. | decimal | s | 0/3 | 3/3 |
| 56 | `evresp_ap_duracion_media_s` | Duración media de los eventos de suma de apneas. | decimal | s | 0/3 | 3/3 |
| 57 | `evresp_ap_duracion_total_min` | Suma de las duraciones de los eventos de suma de apneas. | decimal | min | 0/3 | 3/3 |
| 58 | `evresp_ap_indice_evhora` | Índice de eventos de suma de apneas por hora de sueño (TST). | decimal | eventos/h | 0/3 | 3/3 |
| 59 | `evresp_hip_numero_n` | Número total de hipopneas contabilizados durante el sueño. | entero | n | 3/3 | 3/3 |
| 60 | `evresp_hip_duracion_max_s` | Duración máxima de un evento de hipopneas. | decimal | s | 3/3 | 3/3 |
| 61 | `evresp_hip_duracion_media_s` | Duración media de los eventos de hipopneas. | decimal | s | 3/3 | 3/3 |
| 62 | `evresp_hip_duracion_total_min` | Suma de las duraciones de los eventos de hipopneas. | decimal | min | 3/3 | 3/3 |
| 63 | `evresp_hip_indice_evhora` | Índice de eventos de hipopneas por hora de sueño (TST). | decimal | eventos/h | 3/3 | 3/3 |
| 64 | `evresp_ah_numero_n` | Número total de apneas más hipopneas contabilizados durante el sueño. | entero | n | 3/3 | 3/3 |
| 65 | `evresp_ah_duracion_max_s` | Duración máxima de un evento de apneas más hipopneas. | decimal | s | 0/3 | 3/3 |
| 66 | `evresp_ah_duracion_media_s` | Duración media de los eventos de apneas más hipopneas. | decimal | s | 3/3 | 3/3 |
| 67 | `evresp_ah_duracion_total_min` | Suma de las duraciones de los eventos de apneas más hipopneas. | decimal | min | 3/3 | 3/3 |
| 68 | `evresp_ah_indice_evhora` | índice de la tabla Resumen de eventos respiratorios. | decimal | eventos/h | 3/3 | 3/3 |
| 69 | `evresp_ac_configuracion_s` | Umbral temporal de configuración empleado para apneas centrales en la tabla respiratoria, cuando está informado. | decimal | s | 0/3 | 3/3 |
| 70 | `evresp_ao_configuracion_s` | Umbral temporal de configuración empleado para apneas obstructivas en la tabla respiratoria, cuando está informado. | decimal | s | 0/3 | 3/3 |
| 71 | `evresp_am_configuracion_s` | Umbral temporal de configuración empleado para apneas mixtas en la tabla respiratoria, cuando está informado. | decimal | s | 0/3 | 3/3 |
| 72 | `evresp_hip_configuracion_s` | Umbral temporal de configuración empleado para hipopneas en la tabla respiratoria, cuando está informado. | decimal | s | 0/3 | 3/3 |
| 73 | `evresp_ac_numero_nrem_n`* | Número de apneas centrales durante sueño NREM. | entero | n | 3/3 | 0/3 |
| 74 | `evresp_ac_numero_rem_n`* | Número de apneas centrales durante sueño REM. | entero | n | 3/3 | 0/3 |
| 75 | `evresp_ao_numero_nrem_n`* | Número de apneas obstructivas durante sueño NREM. | entero | n | 3/3 | 0/3 |
| 76 | `evresp_ao_numero_rem_n`* | Número de apneas obstructivas durante sueño REM. | entero | n | 3/3 | 0/3 |
| 77 | `evresp_am_numero_nrem_n`* | Número de apneas mixtas durante sueño NREM. | entero | n | 3/3 | 0/3 |
| 78 | `evresp_am_numero_rem_n`* | Número de apneas mixtas durante sueño REM. | entero | n | 3/3 | 0/3 |
| 79 | `evresp_hip_numero_nrem_n`* | Número de hipopneas durante sueño NREM. | entero | n | 3/3 | 0/3 |
| 80 | `evresp_hip_numero_rem_n`* | Número de hipopneas durante sueño REM. | entero | n | 3/3 | 0/3 |
| 81 | `evresp_ah_numero_nrem_n`* | Número de apneas más hipopneas durante sueño NREM. | entero | n | 3/3 | 0/3 |
| 82 | `evresp_ah_numero_rem_n`* | Número de apneas más hipopneas durante sueño REM. | entero | n | 3/3 | 0/3 |
| 83 | `evresp_iah_rem_evhora` | Índice de apneas-hipopneas (IAH) por hora de fase REM. | decimal | eventos/h | 3/3 | 3/3 |
| 84 | `evresp_iah_nrem_evhora` | Índice de apneas-hipopneas (IAH) por hora de fase NREM. | decimal | eventos/h | 3/3 | 3/3 |
| 85 | `evresp_iah_tst_evhora` | Índice de apneas-hipopneas (IAH) por hora de tiempo total de sueño. | decimal | eventos/h | 3/3 | 3/3 |

\* Solo presentes en RTF
### 2.5. Oximetría (oxi_) — 44 campos

| Nº | Campo canónico | Descripción | Tipo | Unidad | RTF | DOC |
|---:|---|---|---|---|:---:|:---:|
| 86 | `oxi_spo2_promedio_despierto_pct` | Saturación periférica de oxígeno media registrada durante vigilia. | decimal | % | 3/3 | 3/3 |
| 87 | `oxi_indice_desat_despierto_evhora` | Número de desaturaciones por hora durante vigilia, según la definición del informe. | decimal | eventos/h | 0/3 | 3/3 |
| 88 | `oxi_spo2_promedio_rem_pct` | Saturación periférica de oxígeno media registrada durante sueño REM. | decimal | % | 3/3 | 3/3 |
| 89 | `oxi_indice_desat_rem_evhora` | Número de desaturaciones por hora durante sueño REM, según la definición del informe. | decimal | eventos/h | 3/3 | 3/3 |
| 90 | `oxi_spo2_promedio_nrem_pct` | Saturación periférica de oxígeno media registrada durante sueño NREM. | decimal | % | 3/3 | 3/3 |
| 91 | `oxi_indice_desat_nrem_evhora` | Número de desaturaciones por hora durante sueño NREM, según la definición del informe. | decimal | eventos/h | 3/3 | 3/3 |
| 92 | `oxi_spo2_promedio_tst_pct` | Saturación periférica de oxígeno media registrada durante tiempo total de sueño. | decimal | % | 3/3 | 3/3 |
| 93 | `oxi_indice_desat_tst_evhora` | Número de desaturaciones por hora durante tiempo total de sueño, según la definición del informe. | decimal | eventos/h | 3/3 | 3/3 |
| 94 | `oxi_t95_despierto_min` | Minutos con SpO₂ estrictamente inferior a 95 % durante vigilia. | decimal | min | 3/3 | 0/3 |
| 95 | `oxi_t95_rem_min` | Minutos con SpO₂ estrictamente inferior a 95 % durante fase REM. | decimal | min | 3/3 | 0/3 |
| 96 | `oxi_t95_nrem_min` | Minutos con SpO₂ estrictamente inferior a 95 % durante fase NREM. | decimal | min | 3/3 | 0/3 |
| 97 | `oxi_t95_tst_min` | Minutos con SpO₂ estrictamente inferior a 95 % durante tiempo total de sueño. | decimal | min | 3/3 | 0/3 |
| 98 | `oxi_t90_despierto_min` | Minutos con SpO₂ estrictamente inferior a 90 % durante vigilia. | decimal | min | 3/3 | 3/3 |
| 99 | `oxi_t90_rem_min` | Minutos con SpO₂ estrictamente inferior a 90 % durante fase REM. | decimal | min | 3/3 | 3/3 |
| 100 | `oxi_t90_nrem_min` | Minutos con SpO₂ estrictamente inferior a 90 % durante fase NREM. | decimal | min | 3/3 | 3/3 |
| 101 | `oxi_t90_tst_min` | Minutos con SpO₂ estrictamente inferior a 90 % durante tiempo total de sueño. | decimal | min | 3/3 | 3/3 |
| 102 | `oxi_t85_despierto_min` | Minutos con SpO₂ estrictamente inferior a 85 % durante vigilia. | decimal | min | 3/3 | 0/3 |
| 103 | `oxi_t85_rem_min` | Minutos con SpO₂ estrictamente inferior a 85 % durante fase REM. | decimal | min | 3/3 | 0/3 |
| 104 | `oxi_t85_nrem_min` | Minutos con SpO₂ estrictamente inferior a 85 % durante fase NREM. | decimal | min | 3/3 | 0/3 |
| 105 | `oxi_t85_tst_min` | Minutos con SpO₂ estrictamente inferior a 85 % durante tiempo total de sueño. | decimal | min | 3/3 | 0/3 |
| 106 | `oxi_t80_despierto_min` | Minutos con SpO₂ estrictamente inferior a 80 % durante vigilia. | decimal | min | 3/3 | 3/3 |
| 107 | `oxi_t80_rem_min` | Minutos con SpO₂ estrictamente inferior a 80 % durante fase REM. | decimal | min | 3/3 | 3/3 |
| 108 | `oxi_t80_nrem_min` | Minutos con SpO₂ estrictamente inferior a 80 % durante fase NREM. | decimal | min | 3/3 | 3/3 |
| 109 | `oxi_t80_tst_min` | Minutos con SpO₂ estrictamente inferior a 80 % durante tiempo total de sueño. | decimal | min | 3/3 | 3/3 |
| 110 | `oxi_t75_despierto_min` | Minutos con SpO₂ estrictamente inferior a 75 % durante vigilia. | decimal | min | 3/3 | 0/3 |
| 111 | `oxi_t75_rem_min` | Minutos con SpO₂ estrictamente inferior a 75 % durante fase REM. | decimal | min | 3/3 | 0/3 |
| 112 | `oxi_t75_nrem_min` | Minutos con SpO₂ estrictamente inferior a 75 % durante fase NREM. | decimal | min | 3/3 | 0/3 |
| 113 | `oxi_t75_tst_min` | Minutos con SpO₂ estrictamente inferior a 75 % durante tiempo total de sueño. | decimal | min | 3/3 | 0/3 |
| 114 | `oxi_t70_despierto_min` | Minutos con SpO₂ estrictamente inferior a 70 % durante vigilia. | decimal | min | 3/3 | 3/3 |
| 115 | `oxi_t70_rem_min` | Minutos con SpO₂ estrictamente inferior a 70 % durante fase REM. | decimal | min | 3/3 | 3/3 |
| 116 | `oxi_t70_nrem_min` | Minutos con SpO₂ estrictamente inferior a 70 % durante fase NREM. | decimal | min | 3/3 | 3/3 |
| 117 | `oxi_t70_tst_min` | Minutos con SpO₂ estrictamente inferior a 70 % durante tiempo total de sueño. | decimal | min | 3/3 | 3/3 |
| 118 | `oxi_t60_despierto_min` | Minutos con SpO₂ estrictamente inferior a 60 % durante vigilia. | decimal | min | 3/3 | 3/3 |
| 119 | `oxi_t60_rem_min` | Minutos con SpO₂ estrictamente inferior a 60 % durante fase REM. | decimal | min | 3/3 | 3/3 |
| 120 | `oxi_t60_nrem_min` | Minutos con SpO₂ estrictamente inferior a 60 % durante fase NREM. | decimal | min | 3/3 | 3/3 |
| 121 | `oxi_t60_tst_min` | Minutos con SpO₂ estrictamente inferior a 60 % durante tiempo total de sueño. | decimal | min | 3/3 | 3/3 |
| 122 | `oxi_t50_despierto_min` | Minutos con SpO₂ estrictamente inferior a 50 % durante vigilia. | decimal | min | 0/3 | 3/3 |
| 123 | `oxi_t50_rem_min` | Minutos con SpO₂ estrictamente inferior a 50 % durante fase REM. | decimal | min | 0/3 | 3/3 |
| 124 | `oxi_t50_nrem_min` | Minutos con SpO₂ estrictamente inferior a 50 % durante fase NREM. | decimal | min | 0/3 | 3/3 |
| 125 | `oxi_t50_tst_min` | Minutos con SpO₂ estrictamente inferior a 50 % durante tiempo total de sueño. | decimal | min | 0/3 | 3/3 |
| 126 | `oxi_t90_pct` | Porcentaje del TST con SpO₂ inferior al 90 %: valor T90 informado o, si falta, calculado en transformación. | decimal | % | 3/3 | 3/3 |
| 127 | `oxi_spo2_eventos_promedio_pct`* | Saturación media de oxígeno durante los eventos respiratorios. | decimal | % | 3/3 | 0/3 |
| 128 | `oxi_spo2_eventos_min_pct`* | Saturación mínima de oxígeno durante los eventos respiratorios. | decimal | % | 0/3 | 3/3 |
| 129 | `oxi_spo2_sueno_min_pct`* | Saturación mínima de oxígeno alcanzada durante el sueño. | decimal | % | 3/3 | 3/3 |

\* Definir si `128` y `129` son un mismo dato

### 2.6. Frecuencia cardíaca (fc_) — 3 campos

| Nº | Campo canónico | Descripción | Tipo | Unidad | RTF | DOC |
|---:|---|---|---|---|:---:|:---:|
| 130 | `fc_promedio_despierto_lpm` | Frecuencia cardíaca media registrada durante vigilia. | decimal | latidos/min | 3/3 | 3/3 |
| 131 | `fc_promedio_rem_lpm` | Frecuencia cardíaca media registrada durante fase REM. | decimal | latidos/min | 3/3 | 3/3 |
| 132 | `fc_promedio_nrem_lpm` | Frecuencia cardíaca media registrada durante fase NREM. | decimal | latidos/min | 3/3 | 3/3 |

### 2.7. Movimientos de miembros inferiores (movmi_) — 4 campos

| Nº | Campo canónico | Descripción | Tipo | Unidad | RTF | DOC |
|---:|---|---|---|---|:---:|:---:|
| 133 | `movmi_plm_total_n`* | Número total de movimientos periódicos de miembros inferiores (PLM). | entero | n | 3/3 | 0/3 |
| 134 | `movmi_plm_indice_evhora`* | Índice de movimientos periódicos de miembros inferiores (PLM) por hora de sueño. | decimal | movimientos/h | 3/3 | 0/3 |
| 135 | `movmi_lm_total_n`* | Número total de movimientos de miembros inferiores (LM). | entero | n | 0/3 | 3/3 |
| 136 | `movmi_lm_indice_evhora`* | Índice de movimientos de miembros inferiores (LM) por hora de sueño. | decimal | movimientos/h | 0/3 | 3/3 |

\* Definir si `lm = plm`.  De ser así, se trata de dos columnas en lugar de cuatro

### 2.8. Posición corporal (pos_) — 9 campos

| Nº | Campo canónico | Descripción | Tipo | Unidad | RTF | DOC |
|---:|---|---|---|---|:---:|:---:|
| 137 | `pos_supino_duracion_min` | Duración del sueño registrada en decúbito supino. | decimal | min | 3/3 | 3/3 |
| 138 | `pos_supino_pct` | Porcentaje de sueño atribuido a decúbito supino, según la tabla de posición. | decimal | % | 3/3 | 3/3 |
| 139 | `pos_supino_iah_evhora` | Índice de apnea-hipopnea registrado durante decúbito supino. | decimal | eventos/h | 3/3 | 3/3 |
| 140 | `pos_derecho_duracion_min` | Duración del sueño registrada en decúbito lateral derecho. | decimal | min | 3/3 | 3/3 |
| 141 | `pos_derecho_pct` | Porcentaje de sueño atribuido a decúbito lateral derecho, según la tabla de posición. | decimal | % | 3/3 | 3/3 |
| 142 | `pos_derecho_iah_evhora` | Índice de apnea-hipopnea registrado durante decúbito lateral derecho. | decimal | eventos/h | 3/3 | 3/3 |
| 143 | `pos_izquierdo_duracion_min` | Duración del sueño registrada en decúbito lateral izquierdo. | decimal | min | 3/3 | 3/3 |
| 144 | `pos_izquierdo_pct` | Porcentaje de sueño atribuido a decúbito lateral izquierdo, según la tabla de posición. | decimal | % | 3/3 | 3/3 |
| 145 | `pos_izquierdo_iah_evhora` | Índice de apnea-hipopnea registrado durante decúbito lateral izquierdo. | decimal | eventos/h | 3/3 | 3/3 |

### 2.9. Información clínica (clin_) — 5 campos

| Nº | Campo canónico | Descripción | Tipo | Unidad | RTF | DOC |
|---:|---|---|---|---|:---:|:---:|
| 146 | `clin_indicacion` | Texto de la indicación o motivo clínico del estudio. | texto | — | 3/3 | 3/3 |
| 147 | `clin_epworth_puntos` | Puntuación de la escala de somnolencia de Epworth, habitualmente de 0 a 24. | entero | puntos | 3/3 | 3/3 |
| 148 | `clin_interpretacion` | Texto íntegro de la interpretación clínica del informe. | texto | — | 3/3 | 3/3 |
| 149 | `clin_conclusiones` | Texto íntegro de las conclusiones clínicas del informe. | texto | — | 3/3 | 3/3 |
| 150 | `clin_ronquido` | Frase textual íntegra del informe relativa al ronquido y su frecuencia. | texto | — | 3/3 | 3/3 |

### 2.10. Metadatos del estudio (meta_) — 6 campos

| Nº | Campo canónico | Descripción | Tipo | Unidad | RTF | DOC |
|---:|---|---|---|---|:---:|:---:|
| 151 | `meta_fecha_estudio` | Fecha en que se efectuó la polisomnografía. | fecha | fecha | 3/3 | 3/3 |
| 152 | `meta_solicita` | Profesional o entidad solicitante consignada en la cabecera. | texto | — | 3/3 | Sí* (0/3 recuperado) |
| 153 | `meta_empresa` | Entidad, empresa o aseguradora consignada en el informe. | texto | — | 3/3 | Sí* (0/3 recuperado) |
| 154 | `meta_fuente` | Identificador o ruta del archivo origen utilizado para la extracción. | texto | — | Generado | Generado |
| 155 | `meta_uuid` | Hash identificador determinista del contenido binario del archivo de origen. | texto | — | Generado | Generado |
| 156 | `meta_version_control` | Marca de fecha y hora de la ejecución de extracción, en el formato histórico. | texto | — | Generado | Generado |
| 157 | `meta_completitud_pct` | Porcentaje de campos clínicos y técnicos del CSV de extracción con valor recuperado, sobre un denominador fijo de 152 campos no `meta_*`; 0 explícito cuenta como presente. No es una medida de exactitud clínica. | decimal | % | Generado | Generado |

## 3. Diferencias de disponibilidad entre DOC y RTF

| Familia de indicadores | RTF | DOC |
|---|---|---|
| Tiempo de grabación explícito | Sí, 3/3 | No constatado como duración explícita, 0/3; sí aparece hora de inicio |
| Episodios por fase (S1, S2, S3, REM y despierto) | No, 0/3 | Sí, 3/3 |
| Duración y porcentaje TST de S1, S2, S3 y REM | Sí, 3/3 | Sí, 3/3 |
| Fila de fase «Despierto» | Duración, 3/3 | Episodios y duración, 3/3 |
| Respiratorios «Suma AP» | No hay columna propia | Sí, 3/3 |
| Configuración temporal de eventos AC, AO, AM e HIP | No | Sí, 3/3 |
| Recuentos respiratorios por REM/NREM | Sí, 3/3 | No, 0/3 |
| Movimientos de miembros inferiores | PLMs | LMs |
| Saturación durante eventos respiratorios | Promedio | Mínima |
| Saturación mínima durante el sueño | Sí | Sí |
| Tiempo SpO₂ por debajo de 95, 85 y 75 % | Sí | No |
| Tiempo SpO₂ por debajo de 50 % | No | Sí |
| Tiempo SpO₂ por debajo de 90, 80, 70 y 60 % | Sí | Sí |
| Índice de desaturación despierto | Celda vacía en las muestras | Valor numérico |
| Cuello, perímetro abdominal, solicitante y empresa | Valores recuperados | Dato en el documento, pero no recuperado por antiword |

## 4. Incidencias de consistencia: decisiones resueltas y pendientes

**I-01. Dos duraciones distintas de vigilia en DOC (resuelta).** Se mantienen **dos campos independientes**: `arq_tiempo_despierto_min`, que captura «Tiempo despierto durante el sueño» en la tabla de arquitectura (136,2 minutos en una de las muestras), y `fase_despierto_duracion_min`, que captura «Despierto (SPT)» en la tabla de fases (147,0 minutos en esa misma muestra). No deben fusionarse ni sustituirse entre sí. Ambos están incluidos en el recuento del diccionario.

**I-02. Nombre de frecuencia cardíaca nocturna.** Los seis informes contienen una frecuencia cardíaca promedio nocturna en la interpretación narrativa, además de los promedios por vigilia, REM y NREM. La nomenclatura aprobada cubre únicamente estos tres últimos; la medida nocturna queda pendiente de decidir si se incorpora.

**I-03. Campos clínicos narrativos adicionales.** La interpretación de alteraciones del ritmo cardíaco y la clasificación textual del IAH aparecen en las muestras y en la exploración experimental, pero todavía no cuentan con nombres aprobados. También hay información sobre inicio del registro y dispositivo de adquisición. No se incorporan al diccionario aprobado sin decisión expresa.

**I-04. Valores realmente no medidos.** Los campos `pte_edad_meses` y `pte_edad_dias` no se observaron en ninguna muestra; se conservan por haber sido aprobados y por estar previstos en los formatos históricos. No deben completarse con cero salvo indicación explícita.

**I-05. Celdas de duración máxima sin medición.** En los RTF existe la fila «Máxima duración», pero varias categorías de apnea muestran `--` o celda vacía. En la columna de disponibilidad se presenta `0/3` cuando no se ha recuperado un número, sin afirmar que no exista la fila.

**I-06. Semántica de porcentajes por posición.** La suma de duraciones de posiciones de algunos DOC no coincide con TST; se debe conservar el valor publicado, no recalcular las columnas automáticamente.

**I-07. Otros indicadores no incluidos.** En las seis muestras no se observó una columna numérica RERA en el resumen respiratorio; su eventual admisión requiere una muestra real y una decisión sobre su nombre. No se han inventado valores.

## 5. Reglas para la futura implementación (sin ejecutar)

- Mantener los nombres acordados como **salida canónica única**. Los nombres históricos son referencias de migración, no campos duplicados.
- Conservar los valores clínicos originales cuando exista una diferencia real entre tablas; nunca unir medidas solo porque sus etiquetas se parezcan.
- Diferenciar **ausente**, **no legible**, **vacío** y **cero explícito**. No completar con cero un valor que no existe en el documento.
- Actualizar coordinadamente extracción, transformación, contrato YAML y esquema de carga, una vez resueltas las decisiones pendientes.
- Validar con los conversores reales del pipeline (`striprtf` para RTF y `catdoc` para DOC) y no asumir que la extracción de prueba con `unrtf`/`antiword` reproduce exactamente su comportamiento.
- Verificar que el cambio de nombres no afecte silenciosamente a consumidores analíticos, tablas históricas ni lógica de deduplicación por UUID.

## 6. Trazabilidad de la verificación

- **Muestras:** tres informes RTF y tres DOC entregados para el proyecto. Se omiten sus nombres y datos de pacientes en este diccionario.
- **Fuente de comparación:** `matriz_validacion_basal.csv` (183 indicadores experimentales) contrastada con la estructura textual de las tablas y el código original.
- **Código de referencia:** `1_extract/src/basal/procesar_basal.py`, `1_extract/commons/texto_utils.py`, `1_extract/commons/archivo_utils.py`, `2_transform/psg/core/transforms.py` y `0_declarations/psg.yaml` (GitHub `moafar/obsino-clisueno`, commit `b7c3f2d`).
- **Estado:** análisis de documentación; no se han renombrado funciones ni columnas, realizado commits ni cargado datos a BigQuery.

---

### Anexo A. Notas de captura relevantes por campo

| Campo | Nota |
|---|---|
| `pte_edad_meses` | Sin casos observados para meses/días; el patrón queda previsto. |
| `pte_edad_dias` | Sin casos observados para meses/días; el patrón queda previsto. |
| `pte_edad_decimal_anos` | Se calcula en transformación, no aparece directamente en los documentos. |
| `pte_grupo_edad` | Se calcula en transformación; las reglas de corte deben documentarse por separado. |
| `pte_peso_kg` | Se utiliza la unidad original para convertir, si procede. |
| `pte_talla_cm` | Se utiliza la unidad original para convertir, si procede. |
| `pte_cuello_cm` | En DOC se aprecia en portada, pero no se recuperó con antiword. |
| `pte_perimetro_abdominal_cm` | En DOC se aprecia en portada, pero no se recuperó con antiword. |
| `arq_tiempo_grabacion_min` | No sustituir por tiempo en cama si no está informado. |
| `arq_indice_despertares_por_hora` | Conservar la etiqueta acordada, documentando su interpretación clínica real. |
| `arq_tiempo_despierto_min` | Tiempo despierto durante el sueño informado en arquitectura; distinto del valor de la fila «Despierto» de la tabla de fases en algunos DOC. |
| `fase_despierto_duracion_min` | Duración publicada en la fila «Despierto» de la tabla de fases; no sustituir por `arq_tiempo_despierto_min`. Incidencia I-01 resuelta. |
| `evresp_ac_duracion_max_s` | En algunos RTF la fila existe pero la celda contiene «--» o está vacía. Existe la fila en RTF, pero sin valor numérico verificable en las muestras. |
| `evresp_ao_duracion_max_s` | En algunos RTF la fila existe pero la celda contiene «--» o está vacía. Existe la fila en RTF, pero sin valor numérico verificable en las muestras. |
| `evresp_am_duracion_max_s` | En algunos RTF la fila existe pero la celda contiene «--» o está vacía. Existe la fila en RTF, pero sin valor numérico verificable en las muestras. |
| `evresp_ap_duracion_max_s` | En algunos RTF la fila existe pero la celda contiene «--» o está vacía. Existe la fila en RTF, pero sin valor numérico verificable en las muestras. |
| `evresp_ah_duracion_max_s` | En algunos RTF la fila existe pero la celda contiene «--» o está vacía. Existe la fila en RTF, pero sin valor numérico verificable en las muestras. |
| `evresp_ah_indice_evhora` | Índice de la fila correspondiente a apneas más hipopneas en «Resumen de eventos respiratorios»; conservar el valor original para contrastarlo con el IAH TST. |
| `evresp_iah_tst_evhora` | IAH de la tabla «Resumen del índice de eventos respiratorios», columna TST; conservar de forma independiente para verificar concordancia con `evresp_ah_indice_evhora`. |
| `oxi_t90_pct` | Conservar el T90 % informado si existe. Si falta, calcular en `2_transform` como `100 × oxi_t90_tst_min / arq_tiempo_sueno_min` (escala 0–100), usando los minutos de la columna TST de oximetría y el TST de arquitectura. No sustituir minutos REM/NREM ausentes por cero. Conservar el cero explícito; si falta el numerador o el denominador, dejar nulo. Rechazar el cálculo si el denominador no es positivo, los minutos son negativos, superan el TST o alguno de los valores no es finito. |
| `pos_supino_duracion_min` | Se conserva el dato original: en algunos DOC la suma por posiciones no coincide con TST. |
| `pos_derecho_duracion_min` | Se conserva el dato original: en algunos DOC la suma por posiciones no coincide con TST. |
| `pos_izquierdo_duracion_min` | Se conserva el dato original: en algunos DOC la suma por posiciones no coincide con TST. |
| `clin_ronquido` | Conservar íntegra la frase sobre ronquido como texto original, incluida la frecuencia si figura; no crear categorías ni el campo separado `clin_ronquido_frecuente`. Si no aparece información, usar un valor nulo, no inferir «no». |
| `meta_solicita` | En DOC la cabecera original contiene el dato, pero antiword omitió celdas. |
| `meta_empresa` | En DOC la cabecera original contiene el dato, pero antiword omitió celdas. |
| `meta_fuente` | Se produce por el pipeline, no es indicador clínico. |
| `meta_uuid` | Permanece igual al volver a procesar el mismo fichero. |
| `meta_version_control` | El campo histórico es una marca temporal, no un identificador de versión semántica. |


### Inclusión y completitud de la extracción (desde el contrato de 157 campos)

- **Inclusión:** detección del título «INFORME DE POLISOMNOGRAFÍA BASAL» (excluidos informes DAM) en el contenido convertido; una tabla ausente o ilegible no invalida por sí sola el documento.
- **Extracción:** las secciones se evalúan independientemente. Las filas desalineadas no se asignan por conjetura; los valores no recuperables quedan nulos.
- **`meta_completitud_pct`:** `100 × número de campos no meta con valor / 152`, redondeado a dos decimales. Se calcula en `1_extract`, sin contar los metadatos ni las seis variables derivadas en `2_transform`. El cero explícito cuenta como dato presente. La misma base fija se aplica a DOC y RTF, incluso cuando una plantilla no contiene determinados indicadores: esto mide la completitud del esquema, no la integridad clínica del informe.
- **Carga:** incorporar la nueva columna `FLOAT64` a la tabla física de BigQuery antes de cargar el esquema nuevo. No mezclar CSV antiguos de 158 columnas con los nuevos de 159 en una misma ejecución de `2_transform`.
