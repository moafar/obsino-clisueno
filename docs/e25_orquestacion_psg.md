# E25 — Orquestación PSG

`scripts/run_psg.py` ejecuta las CLI de extracción (incluye auditoría), transformación y carga secuencialmente. No selecciona artefactos por fecha ni mediante autodiscovery. El identificador UTC + UUID determina el CSV, el Parquet y el directorio `staging/psg_runs/<id>/`.

```bash
.venv/bin/python scripts/run_psg.py --input /mnt/e/RESULTADOS \
  --archive-dest /mnt/e/RESULTADOS/RESULTADOS_OBSERVATORIO \
  --mount /mnt/e --table-id <tabla_canonica_autorizada>
```

Este comando mueve documentos según la política vigente y carga el destino explícito; su uso productivo requiere la validación y autorización previstas. No habilita programación ni despliegue. La entrada y el archivo deben existir, ser accesibles, pertenecer al montaje real indicado y compartir dispositivo. Origen y archivo deben ser disjuntos: se rechaza igualdad y contención en ambos sentidos; staging debe estar fuera del almacenamiento documental. Se comprueban escritura efectiva, lectura de credencial sin mostrarla y disponibilidad del directorio de logs antes de procesar. El chequeo de montaje evita trabajar sobre un directorio vacío tras perder el montaje, pero no certifica el tipo NTFS del dispositivo ni garantiza su disponibilidad durante toda la ejecución.

## Interfaces y persistencia

Se añaden opciones exclusivamente PSG: extracción `--yes`, `--output-file`, `--result-json`; transformación `--yes`; carga `--yes`, `--result-json`. La carga manual conserva su confirmación por defecto. Las interfaces procesan y validan los datos como antes; los resúmenes técnicos comunican rutas y cantidades sin incluir valores clínicos. Los subprocesos tienen stdin cerrado; cualquier interacción imprevista falla y queda registrada.

El registro `run.json` se actualiza mediante temporal en el mismo directorio, `fsync`, reemplazo atómico y sincronización del directorio. Incluye identificador, estado general, estados por etapa, rutas, cantidades, tiempos UTC y duración monotónica, destino, referencia de trabajo BigQuery y tipo de error. Cada etapa conserva su salida de consola en un log local. Estos logs pueden contener información sensible producida por las capas y permanecen en staging, fuera de Git. Los resúmenes JSON de las CLI son auxiliares; el registro consolidado se publica atómicamente tras leerlos.

El bloqueo estable `staging/.psg-run.lock`, mediante `flock` exclusivo no bloqueante, cubre todas las etapas y la persistencia final. Una segunda ejecución falla sin comenzar extracción. Se conservan los bloqueos de archivado y de carga E23. Solo quedan excluidos procesos locales que usen el mismo archivo; escritores externos o CLI independientes no quedan sujetos al bloqueo del orquestador.

## Estados y fallos

Un código de salida fallido detiene la secuencia. `ADVERTENCIA` de auditoría permite continuar y genera estado general `WARNING`. Un lote conciliado sin filas nuevas termina `EMPTY`, con transformación y carga `SKIPPED`; se mantienen los recuentos de rechazos, duplicados y archivado del extractor. El resumen general incluye `audit.state` y `audit.report`, también cuando el lote `EMPTY` tiene `ADVERTENCIA`; el resultado completo continúa en la etapa `extract_audit`. Cada etapa permanece `RUNNING` hasta superar sus controles de conciliación; una discrepancia posterior a la CLI marca esa etapa y el estado global como `ERROR`. Para un único CSV, las filas extraídas y transformadas deben ser estrictamente iguales; se rechazan tanto pérdidas como aumentos antes de cargar. La carga mantiene consulta parametrizada, deduplicación, `WRITE_APPEND`, confirmación, `output_rows` y movimiento a `_loaded` de E23–E36.

Ante fallo se conserva `ERROR`, la etapa afectada y su log. No hay borrado de CSV ni Parquet recuperables por parte del orquestador. Si la carga remota concluye y falla el movimiento o la escritura de su resumen, el registro refleja un fallo local: requiere revisión antes de reintentar. La autenticación remota se mantiene en la CLI de carga; el preflight solo verifica disponibilidad local de la credencial.

## Límites y deuda técnica

E24 queda aplazada como deuda técnica por decisión de diseño: se consultan los CSV históricos para deduplicar y recuperar archivados fallidos. Se descarta SQLite por complejidad y mantenimiento innecesarios. No se retiran artefactos.

No se implementa reanudación automática. Una terminación abrupta puede dejar `RUNNING`; perder el padre puede liberar su bloqueo mientras un hijo sigue activo. La recuperación ante interrupciones, los trabajos remotos de resultado incierto, las señales, los procesos supervivientes y la concurrencia con ejecuciones manuales corresponden a E26. No se demuestra durabilidad ante pérdida eléctrica ni atomicidad entre BigQuery y disco. La programación E32 y el despliegue quedan pendientes, igual que la validación remota autorizada E28.

## Validación

Pruebas sintéticas del orquestador con CLI simuladas: éxito, advertencias, lote vacío, fallo en cada etapa, persistencia de estados, conservación de artefactos y concurrencia. Un caso adicional ejecuta la CLI real de extracción y su auditoría sobre directorios sintéticos vacíos, omitiendo únicamente el preflight de montaje y credenciales del orquestador. Las suites de extracción, transformación y carga comprueban las regresiones de las interfaces afectadas. Comandos y resultados reales se registran en TODO.md. No se accede a PRD ni a BigQuery real.

Comandos ejecutados: `.venv/bin/python -m unittest discover -s scripts/tests -v`; `PYTHONPATH=1_extract .venv/bin/python -m unittest discover -s 1_extract/tests`; `PYTHONPATH=1_extract:2_transform .venv/bin/python -m unittest discover -s 2_transform/tests` y la misma invocación con `-s 3_load/tests`. El caso integrado adicional se ejecutó con `-s scripts/tests -k empty_with_real -v`. Resultado: 114 casos superados en total.

Correcciones finales E25: seis pruebas afectadas superadas (directorios disjuntos, lotes vacíos con/sin advertencia, discrepancias de auditoría/ruta, transformación con menos y más filas, carga no conciliada, éxito y fallos por etapa). Se conserva el caso vacío con CLI real; los demás usan CLI simuladas. No se repitieron las suites de otras capas.
