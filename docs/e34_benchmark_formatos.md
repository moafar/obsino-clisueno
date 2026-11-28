# E34 — Benchmark de formatos intermedios PSG

**Método.** `docs/e34_benchmark_formatos.py` genera exclusivamente datos sintéticos con los 158 campos y tipos de `schema.transform.output.columns` en `0_declarations/psg.yaml`. Cada combinación de 100, 1.000 o 10.000 filas y XLSX, CSV o Parquet se ejecutó tres veces en un proceso nuevo (27 mediciones), con el mismo generador determinista. Los archivos temporales se escribieron en `/tmp` sobre ext4 de WSL2 (Linux 6.6.87.2). Entorno: Python 3.12, pandas 2.3.3, PyArrow 23.0.1 y openpyxl 3.1.5. Parquet utilizó compresión Snappy; XLSX, openpyxl; CSV, UTF-8. La generación y el arranque del proceso quedan fuera de los tiempos de lectura/escritura.

El resultado estructurado íntegro está en `docs/e34_mediciones.json`. Las cifras siguientes son **medianas de tres ejecuciones**; CPU es tiempo de proceso para cada operación y RSS es el pico del proceso aislado, que incluye importaciones y generación de datos. Las tres lecturas de cada combinación se compararon con `assert_frame_equal(check_dtype=True, check_exact=True)` tras declarar tipos al leer CSV/XLSX; Parquet se leyó con sus tipos propios.

| Filas | Formato | Escritura s | Lectura s | CPU escritura s | CPU lectura s | Tamaño MiB | RSS pico MiB |
|---:|---|---:|---:|---:|---:|---:|---:|
| 100 | CSV | 0,014 | 0,024 | 0,015 | 0,025 | 0,10 | 105,7 |
| 100 | Parquet | 0,033 | 0,044 | 0,034 | 0,065 | 0,17 | 119,9 |
| 100 | XLSX | 0,246 | 0,107 | 0,251 | 0,111 | 0,06 | 118,4 |
| 1.000 | CSV | 0,089 | 0,069 | 0,091 | 0,071 | 0,93 | 114,6 |
| 1.000 | Parquet | 0,038 | 0,042 | 0,039 | 0,065 | 0,30 | 126,7 |
| 1.000 | XLSX | 1,884 | 0,972 | 1,959 | 1,005 | 0,49 | 166,0 |
| 10.000 | CSV | 0,745 | 0,478 | 0,771 | 0,494 | 9,31 | 158,9 |
| 10.000 | Parquet | 0,079 | 0,062 | 0,082 | 0,123 | 0,89 | 195,9 |
| 10.000 | XLSX | 20,339 | 7,260 | 21,161 | 7,508 | 5,09 | 688,2 |

**Fidelidad.** 27/27 comparaciones exactas: registros, 158 columnas y orden, tipos `Int64`/`Float64`/`string`/fecha, valores, ceros iniciales de `pte_id`, UUID únicos, NULL y JSON de `meta_incidencias_calidad`. CSV y XLSX precisaron tipos explícitos de lectura; sin ello no se demuestra esa fidelidad. A 10.000 filas, Parquet tardó aproximadamente 9,4 veces menos que CSV y 258 veces menos que XLSX en escritura; ocupó aproximadamente 10,5 y 5,7 veces menos, respectivamente. A 100 filas, CSV fue más rápido y pequeño que Parquet. La memoria pico Parquet superó la de CSV y fue muy inferior a XLSX en 10.000 filas; no representa memoria incremental aislada de E/S.

**BigQuery y E23.** BigQuery admite carga de Parquet como formato autodescriptivo desde [Cloud Storage](https://docs.cloud.google.com/bigquery/docs/loading-data-cloud-storage-parquet); el cliente Python ofrece [carga desde archivo local](https://docs.cloud.google.com/python/docs/reference/bigquery/latest/google.cloud.bigquery.client.Client#load_table_from_file) y [desde DataFrame](https://docs.cloud.google.com/python/docs/reference/bigquery/latest/google.cloud.bigquery.client.Client#load_table_from_dataframe). E36 debe comparar la carga nativa del archivo con leer Parquet y reutilizar `load_table_from_dataframe`. La carga nativa del archivo completo solo sirve cuando todos los UUID son nuevos; E23 requiere filtrar filas ya existentes, por lo que una repetición parcial necesita un subconjunto tipado antes de cargar. La consulta parametrizada, el bloqueo local, `output_rows` y la conservación del artefacto de E23 siguen siendo requisitos de E36. No se accedió a BigQuery ni se midieron tiempo/coste de carga remota.

**Conclusión y límites.** Parquet es técnicamente idóneo como formato intermedio objetivo aprobado: preservó los tipos y valores de la muestra y redujo tiempo y tamaño a 10.000 filas. Estas mediciones no prueban durabilidad, publicación atómica, recuperación tras interrupción ni compatibilidad del esquema físico en una carga real; corresponden a E35, E36 y la validación posterior autorizada. Los datos son sintéticos y muy repetitivos, de modo que compresión y tiempos no deben extrapolarse a informes clínicos reales ni a NTFS.
