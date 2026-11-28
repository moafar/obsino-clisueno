# E06 — Campos aplicables para completitud DOC/RTF

**Fuentes contrastadas:** los 157 nombres y la matriz de disponibilidad de seis informes descritos en `diccionario_datos_psg.md` (3 DOC y 3 RTF; no se han reabierto los originales), las 159 columnas de `0_declarations/psg.yaml`, `PSG_COLUMNS` y los extractores de `1_extract/src/basal/procesar_basal.py`, y las dos plantillas sintéticas de `1_extract/tests/test_psg_extractor.py`. La prueba de correspondencia del esquema verifica que las 159 columnas del extractor coinciden, en orden, con las del YAML. No se infiere aplicabilidad de un mero `0/3` de valores recuperados.

## Regla de las listas exactas

Sea **B** la lista, en orden YAML, de los 152 campos no `meta_*`, retirando `pte_edad_meses` y `pte_edad_dias`: quedan **150 indicadores lógicos**. `pte_edad_anos` representa en B el indicador **edad**; su presencia se calcula con `pte_edad_anos` **o** `pte_edad_meses` **o** `pte_edad_dias`. En cada sección, las listas exactas son:

- **DOC = B menos los campos de la columna «Solo RTF»** de la tabla siguiente: **124**.
- **RTF = B menos los campos de la columna «Solo DOC»**: **129**.

Los campos de B que no figuran en ninguna columna exclusiva son comunes a ambos formatos. La tabla enumera **todos** los campos exclusivos por sección; junto con el orden completo de B en el YAML determina sin ambigüedad cada lista aplicable. La implementación de E07 expone las listas efectivas `COMPLETENESS_FIELDS` para comprobarlas directamente.

| Sección | DOC | RTF | Solo DOC, excluidos de RTF | Solo RTF, excluidos de DOC |
|---|---:|---:|---|---|
| `pte` | 12 | 12 | — | — |
| `arq` | 11 | 12 | — | `arq_tiempo_grabacion_min` |
| `fase` | 14 | 9 | `fase_s1_episodios_n`, `fase_s2_episodios_n`, `fase_s3_episodios_n`, `fase_rem_episodios_n`, `fase_despierto_episodios_n` | — |
| `evresp` | 37 | 38 | `evresp_ac_configuracion_s`, `evresp_ao_configuracion_s`, `evresp_am_configuracion_s`, `evresp_hip_configuracion_s`, `evresp_ap_numero_n`, `evresp_ap_duracion_max_s`, `evresp_ap_duracion_media_s`, `evresp_ap_duracion_total_min`, `evresp_ap_indice_evhora` | `evresp_ac_numero_nrem_n`, `evresp_ac_numero_rem_n`, `evresp_ao_numero_nrem_n`, `evresp_ao_numero_rem_n`, `evresp_am_numero_nrem_n`, `evresp_am_numero_rem_n`, `evresp_hip_numero_nrem_n`, `evresp_hip_numero_rem_n`, `evresp_ah_numero_nrem_n`, `evresp_ah_numero_rem_n` |
| `oxi` | 31 | 39 | `oxi_t50_despierto_min`, `oxi_t50_rem_min`, `oxi_t50_nrem_min`, `oxi_t50_tst_min`, `oxi_spo2_eventos_min_pct` | `oxi_t95_despierto_min`, `oxi_t95_rem_min`, `oxi_t95_nrem_min`, `oxi_t95_tst_min`, `oxi_t85_despierto_min`, `oxi_t85_rem_min`, `oxi_t85_nrem_min`, `oxi_t85_tst_min`, `oxi_t75_despierto_min`, `oxi_t75_rem_min`, `oxi_t75_nrem_min`, `oxi_t75_tst_min`, `oxi_spo2_eventos_promedio_pct` |
| `fc` | 3 | 3 | — | — |
| `movmi` | 2 | 2 | `movmi_lm_total_n`, `movmi_lm_indice_evhora` | `movmi_plm_total_n`, `movmi_plm_indice_evhora` |
| `pos` | 9 | 9 | — | — |
| `clin` | 5 | 5 | — | — |
| **Total** | **124** | **129** | **21** | **26** |

**Exclusiones comunes:** los siete `meta_*` son trazabilidad/resultado del pipeline, no indicadores de presencia; las dos columnas adicionales de edad no suman indicadores nuevos; las seis variables derivadas del diccionario (`pte_edad_decimal_anos`, `pte_grupo_edad`, `pte_peso_kg`, `pte_talla_cm`, `pte_cuello_cm`, `pte_perimetro_abdominal_cm`) pertenecen a transformación, no al CSV de extracción. Los cuatro valores y cuatro unidades antropométricas sí son campos físicos de entrada en el YAML vigente: no se renombran ni se fusionan en PT02.

## Seis campos RTF que deben constar en la justificación de 129

Los seis nombres siguientes figuran en la entrada del YAML y en la lista RTF de E07. La matriz de `diccionario_datos_psg.md` (§§2–3 e I-05) distingue valor recuperado de celda estructuralmente disponible; el extractor y la plantilla sintética RTF muestran cómo se asigna cada celda. Cada campo cuenta en el **denominador** aunque el valor esté vacío en un documento concreto.

| Campo exacto en `0_declarations/psg.yaml` | Evidencia y justificación de aplicabilidad estructural en RTF |
|---|---|
| `evresp_ac_duracion_max_s` | La tabla RTF contiene la columna AC y la fila «Máxima duración». El diccionario registra `0/3` valores porque sus celdas fueron `--` o vacías, no porque falte esa intersección. `_respiratory` asigna la celda AC cuando hay un número. |
| `evresp_ao_duracion_max_s` | La misma fila «Máxima duración» cruza la columna AO presente en RTF. El `0/3` del diccionario refleja ausencia de número en las muestras; `_respiratory` conserva el campo AO para un valor eventual. |
| `evresp_am_duracion_max_s` | La columna AM también está en el encabezado respiratorio RTF y tiene celda en «Máxima duración». El `0/3` corresponde a celda vacía o `--`; el extractor la mapea como campo aplicable. |
| `evresp_hip_duracion_max_s` | **Caso distinto de los cuatro anteriores:** el diccionario registra `3/3` valores RTF. La columna HIP y la fila «Máxima duración» están presentes; la plantilla sintética incluye un número en su intersección y `_respiratory` lo asigna a `evresp_hip_duracion_max_s`. Omitir este campo de la justificación anterior fue un error documental. |
| `evresp_ah_duracion_max_s` | La columna RTF «Apneas + Hipopneas» se mapea a `ah` y cruza «Máxima duración». El diccionario marca `0/3` por celdas sin número, pero la estructura y el mapeo existen. |
| `oxi_indice_desat_despierto_evhora` | La tabla comparativa del diccionario dice «Celda vacía en las muestras» para el índice de desaturación despierto RTF. La plantilla sintética conserva la columna «Despierto» y la fila «Índice Desat» con esa celda vacía; `_oximetry` la mapea si contiene un valor. La vaciedad no equivale a ausencia estructural. |

`evresp_ap_duracion_max_s` **no** forma parte de estos seis: «Suma AP» carece de columna propia en RTF (§3 del diccionario) y es exclusivo de DOC. La ausencia en las muestras de meses/días tampoco excluye edad: se cuenta una sola vez si cualquiera de los tres componentes está presente. Los ceros explícitos son presencia. El candidato previo **123 para RTF** no dejó una lista de exclusiones verificable; estos seis campos justifican su inclusión en el contrato de **129**, sin atribuir al cálculo preliminar una causa no documentada. El candidato **124 para DOC** queda confirmado.

**Límite de evidencia:** la matriz histórica de seis informes no representa todas las variantes posibles; esta verificación se apoya además en plantillas sintéticas de ambas rutas de extracción. Una nueva variante documental que muestre una diferencia estructural debe revisarse con muestra autorizada antes de cambiar estas listas.
