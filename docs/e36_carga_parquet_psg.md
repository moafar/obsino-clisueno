# E36 — Carga PSG desde Parquet

## Contrato y validación

La entrada PSG es el archivo `extract_psg_..._transformed.parquet` publicado por E35. El YAML sigue definiendo los 158 campos, su orden y los tipos lógicos. Antes de consultar o insertar UUID, el cargador comprueba nombres y orden del esquema Arrow, los tipos físicos esperados del productor E35 (`string`, `int64`, `double`, `timestamp[ns]`) y los tipos pandas recuperados (`string`, `Int64`, `Float64`, `datetime64[ns]`). Rechaza incompatibilidades; no convierte ni normaliza columnas PSG al leer.

Se mantienen los controles de números finitos, porcentaje técnico de completitud, fecha sin componente horario, UUID no vacío y no repetido, esquema físico de la tabla y `WRITE_APPEND`. `meta_fecha_estudio` puede ser NULL; no se exige particionamiento por columna según E21. La conversión explícita al tipo BigQuery `DATE` corresponde al cliente BigQuery bajo el esquema declarado; la prueba local verifica la representación Arrow `date32` y NULL. El cargador preserva literalmente `pte_id` con ceros iniciales, UUID y JSON de incidencias.

El límite anterior de enteros mayores que `2**53` protegía la lectura XLSX frente a pérdida de precisión. Ya no se aplica: Parquet exige `int64` físico, pandas `Int64` y el destino BigQuery `INT64`, sin pasar por una representación de coma flotante.

La selección automática y la ruta explícita aceptan solo Parquet PSG con nombre final `..._transformed.parquet`. Se excluyen extensiones antiguas, temporales, archivos parciales y nombres `_loaded`. XPAP mantiene su lectura y carga actuales.

## Comparación de métodos de carga

| Método | Lote nuevo completo | Repetición parcial E23 | Consecuencia local |
|---|---|---|---|
| `load_table_from_dataframe()` | Envía las filas validadas | Envía directamente el subconjunto sin UUID existentes | Reutiliza el bloqueo, la conciliación y las pruebas E23; lee Parquet una vez para validar y filtrar. |
| `load_table_from_file()` con Parquet | Puede enviar el archivo completo | Exigiría escribir y gestionar otro Parquet con solo filas nuevas | Añade un artefacto temporal y reglas de recuperación; el archivo original no sirve cuando hay omisiones. |

Se conserva `load_table_from_dataframe()`. E34 midió lectura local Parquet de 0,062 s de mediana para 10.000 filas sintéticas, pero no midió transferencia, coste ni tiempo de carga remota. No hay ventaja demostrada de `load_table_from_file()` que compense el segundo camino y su temporal en repeticiones parciales. No se accedió a BigQuery real.

## Garantías y límites

Se reutiliza la consulta por bloques parametrizados y el bloqueo `flock` local de E23 durante consulta, inserción, confirmación y movimiento. Se cumple `recibidos = omitidos + enviados`; tras `job.result()` se exige `output_rows = enviados`. Si todos los UUID existen, no se inicia un trabajo de carga. Un fallo de consulta, carga o conciliación conserva el Parquet en origen. El éxito lo mueve a `_loaded.parquet`.

Las pruebas usan CSV y Parquet sintéticos y BigQuery simulado. La carga real al destino de prueba, la latencia y coste remotos, la competencia con escritores externos y la recuperación de resultados inciertos quedan pendientes de E28 y E25–E26. El bloqueo local no garantiza unicidad frente a escritores externos ni atomicidad entre BigQuery y el sistema de archivos.
