# E01 — Diagnóstico técnico del extractor

**Fecha:** 2026-11-28. **Entorno:** DEV, rama `integration/psg-evoluciones`, revisión `dc5e278`, WSL2 Linux 6.6.87.2, Python 3.12.3, `.venv`, archivos temporales en `/tmp`. **Alcance:** análisis de los flujos PSG y XPAP, medición integral de PSG RTF y microbenchmark del CSV compartido usado por XPAP; sin cambios funcionales, sin documentos clínicos ni acceso a rutas de PRD.

## Flujo y operaciones observadas en el código

1. `main.py:320-326,248-295` carga el YAML, valida rutas y solicita confirmación; bloquea la salida con `flock`, lee UUID de CSV anteriores, procesa el directorio y audita dentro del mismo bloqueo. El tiempo que muestra el resumen (`main.py:131-143`) solo cubre `procesar_directorio`; excluye carga de CSV previos y auditoría.
2. `directorio_utils.py:38-59` recorre PSG mediante un generador `os.walk` y excluye el destino de archivo. Por tanto, la afirmación anterior de que **PSG** materializa todos los nombres con `list(glob)` no corresponde a esta rama. La ruta sin destino PSG sí usa `list(ruta.glob(...))` en la línea 56. Por archivo hay comprobación de tipo, registro y control de excepciones (`:60-101`).
3. `archivo_utils.py:469-527` filtra el nombre, lee texto, normaliza, clasifica y llama al parser basal. RTF se lee completo en UTF-8 y se convierte mediante `striprtf` (`texto_utils.py:78-85`); DOC comprueba `catdoc` y lanza un subproceso por archivo con salida y error capturados (`:88-106`). DOCX existe en la utilidad común, pero la configuración PSG solo permite DOC y RTF (`0_declarations/psg.yaml:9-10`).
4. `procesar_basal.py:188-210,532-571` separa secciones, busca filas y columnas con expresiones regulares, copia el diccionario por sección para evitar datos parciales, calcula MD5 del archivo original y completitud. `_fold` (`:109-113`) normaliza texto reiteradamente durante las búsquedas. `normalizar_texto` aplica reemplazos y regex al texto completo (`texto_utils.py:12-40`), pero el parser basal recibe el texto original (`archivo_utils.py:506-523`); la normalización global se usa para clasificar el estudio.
5. `archivo_utils.py:112-167` valida cabecera y última línea, deduplica por UUID, escribe una fila, ejecuta `flush` y `fsync` por fila y mantiene un conjunto `_PSG_SEEN`. Solo reescanea el CSV de salida si cambia su tamaño fuera de la caché. **La lectura completa en cada append de `_append_row_unified` (`:70-106`) no es el camino PSG actual**; afecta a flujos que usan esa función. `load_known_psg_uuids` (`:170-190`) sí lee todos los CSV PSG canónicos previos una vez por ejecución.
6. `archivo_utils.py:328-416,528-560` archiva tras registrar la fila: valida origen regular y mismo dispositivo, abre directorios sin seguir enlaces y usa `renameat2` sin reemplazo o enlace más retirada del origen. Conserva las rutas y el log de traslado para trazabilidad. Hay un coste por archivo de resolución de rutas, metadatos y operaciones de directorio; estas garantías no son candidatas a supresión por rendimiento.
7. `auditoria_psg.py:101-320` vuelve a recorrer el origen, lee el CSV completo en memoria y el log, comprueba esquema, tipos y completitud, compara rutas con los traslados y calcula otro MD5 sobre cada archivo archivado (`:235-247`); también puede calcular hashes de duplicados (`:298-309`). Su informe contiene controles de coherencia clínica/matemática (`:205-234,264-267`), cuya retirada está asignada a E10 y queda fuera de E01. La auditoría mantiene el bloqueo global hasta terminar (`main.py:259-291`).

**Ruta XPAP:** `main.py:327-356` configura los subflujos y llama al recorrido común sin destino PSG. Ese recorrido materializa `list(ruta.glob(glob_patron))` (`directorio_utils.py:55-56`), de modo que su memoria para nombres crece con el número de entradas. `archivo_utils.py:469-528,579-589` reutiliza conversión DOC/RTF/DOCX, normalización, clasificación y regex de los parsers XPAP; escribe con `_append_row_unified` y mueve mediante `shutil.move` (`:443-467`). `_append_row_unified` relee todas las filas existentes en cada llamada, y si cambia el esquema reescribe el CSV (`:70-106`); con cabecera estable, el trabajo acumulado es proporcional a la suma de 1 a *n* filas. XPAP no tiene aquí la auditoría ni el protocolo de archivado PSG. No se infiere equivalencia de garantías entre flujos.

## Medición reproducible

`docs/e01_perfil_extractor.py` crea informes RTF sintéticos a partir de `synthetic_report("rtf")` de la prueba existente, con identidad sintética distinta por archivo. Usa el convertidor RTF, el parser, MD5, CSV, archivado y auditoría reales, en modo PSG `test` con raíz aislada en `/tmp`; todos los archivos se eliminan al terminar. Los tiempos de fase son de reloj (`perf_counter`) medidos con envoltorios temporales; `cpu_s` usa `process_time` y RSS es el máximo del proceso (`ru_maxrss`). Las fases anidadas **no se suman**: `csv_fsync` está dentro de `csv_append`; `hash_inicial` está dentro de `parseo`; `auditoria_hash` está dentro de `auditoria`. El tamaño de entrada es 2.674 bytes por informe. Se ejecutó cada tamaño dos veces, en procesos independientes:

```bash
.venv/bin/python docs/e01_perfil_extractor.py --count 30
.venv/bin/python docs/e01_perfil_extractor.py --count 120
.venv/bin/python docs/e01_perfil_extractor.py --count 480
```

| Documentos | Pared total, s | CPU, s | RSS máximo, MiB | Append CSV, s | `fsync` CSV, s | Parseo, s | Lectura RTF, s | Archivado, s | Auditoría, s |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 30 | 0,187–0,191 | 0,138–0,139 | 37,3–37,4 | 0,059–0,063 | 0,054–0,058 | 0,042–0,043 | 0,016–0,016 | 0,009–0,009 | 0,020–0,021 |
| 120 | 0,619–0,624 | 0,414–0,418 | 38,1–38,3 | 0,237–0,241 | 0,220–0,225 | 0,165–0,169 | 0,066–0,066 | 0,035–0,040 | 0,042–0,042 |
| 480 | 2,517–2,603 | 1,635–1,665 | 41,8–41,9 | 1,042–1,102 | 0,961–1,019 | 0,688–0,701 | 0,275–0,275 | 0,175–0,182 | 0,148–0,150 |

En las seis ejecuciones, código de salida 0, filas CSV = documentos, archivos archivados = documentos y auditoría `OK`. En 480 documentos, `fsync` acumuló 0,96–1,02 s, aproximadamente el 38–39 % de la pared total; el parseo, 0,69–0,70 s (27–28 %). El hash inicial solo acumuló 0,024 s y los hashes de auditoría 0,013–0,013 s en esas ejecuciones. Son medidas de RTF pequeños en el sistema de archivos Linux de WSL; no estiman por sí solas el rendimiento de DOC, NTFS o lotes clínicos de otro tamaño.

Perfil adicional, útil para localizar CPU pero **no comparable en duración** con la tabla por la sobrecarga del profiler:

```bash
.venv/bin/python -m cProfile -s cumulative docs/e01_perfil_extractor.py --count 120
```

Registró 58.680 llamadas a `_fold`, 128.160 llamadas a `re.search` y 120 a `fsync`. La repetición de normalización y búsquedas en el parser es un candidato concreto para perfilar con documentos representativos; no demuestra que una reescritura del parser mejore el lote real.

Para aislar la lectura histórica, se ejecutó dos veces `.venv/bin/python docs/e01_perfil_extractor.py --count 30 --prior-rows 5000`. El CSV previo canónico también era sintético, con 5.000 UUID y demás campos vacíos. `load_known_psg_uuids` tardó 0,0337–0,0346 s, frente a 0,0001–0,0002 s sin histórico. La diferencia de RSS máximo frente a los 30 documentos sin histórico fue aproximadamente 0,9–1,1 MiB. Este coste crece con el histórico que se carga, y sus magnitudes no se extrapolan a CSV reales.

El microbenchmark de `_append_row_unified` escribe filas sintéticas de 20 columnas con cabecera estable, dos ejecuciones por tamaño, sin conversión, parser ni archivado. Es una medida de la operación de CSV que usa XPAP, **no** un tiempo de XPAP completo:

```bash
.venv/bin/python docs/e01_perfil_extractor.py --generic-rows 100
.venv/bin/python docs/e01_perfil_extractor.py --generic-rows 300
.venv/bin/python docs/e01_perfil_extractor.py --generic-rows 600
```

| Filas | Pared total, s | CPU, s | Filas verificadas |
|---:|---:|---:|---:|
| 100 | 0,016–0,016 | 0,017–0,017 | 100 |
| 300 | 0,137–0,142 | 0,141–0,146 | 300 |
| 600 | 0,519–0,573 | 0,534–0,589 | 600 |

Al duplicar de 300 a 600 filas, el tiempo creció aproximadamente 3,7–4,2 veces, compatible con la relectura cuadrática prevista por el código. Esta microprueba no cuantifica su impacto relativo en un lote XPAP real.

## Cuellos de botella y propuestas para revisión

| Prioridad diagnóstica | Evidencia | Propuesta acotada para fases posteriores | Riesgo o dependencia |
|---|---|---|---|
| 1 · escritura duradera | En 480 RTF, `csv_append` consumió 1,04–1,10 s; `fsync` explica 0,96–1,02 s. Código: una sincronización por fila. | En E09, evaluar escritura de un lote durable con protocolo de recuperación y comparar antes/después sobre la misma muestra. | **No retirar `fsync`, bloqueo ni durabilidad** sin equivalencia demostrada. El CSV precede al traslado: deben preservarse reintentos, deduplicación y conciliación. |
| 2 · parseo y regex | 0,69–0,70 s de parseo por 480 RTF; `_fold` y `re.search` se repiten decenas de miles de veces en 120 documentos. | Perfilar secciones y patrones con documentos sintéticos más variados y copias autorizadas antes de reutilizar texto normalizado o indexar filas. | Cambios de extracción podrían alterar campos, inclusión y completitud; exigir equivalencia de 159 columnas y pruebas DOC/RTF. |
| 3 · I/O de documentos | RTF completo: 0,275 s de lectura/conversión en 480; DOC lanza un `catdoc` por archivo según código, sin medición empírica. | Medir DOC válido y tamaños representativos en la fase de benchmarks/compatibilidad antes de cambiar el conversor. | E02–E03 tratan entornos y `catdoc`; no hay base para escoger arquitectura todavía. |
| 4 · auditoría y hashes | Auditoría 0,148–0,150 s y MD5 de archivo 0,013 s en 480 RTF. Hay segunda lectura del contenido archivado por fila. | Para E11, definir conciliación equivalente de existencia, rutas, CSV, log y cantidades sin rehash; medir con archivos mayores. | El ahorro medido aquí es pequeño; la retirada del control MD5 exige resolver cómo se detectarán incidencias de archivado. |
| 5 · CSV históricos y memoria | Carga previa O(filas históricas), 0,034 s para 5.000 filas sintéticas; auditoría mantiene todas las filas actuales en memoria. | Medir con cardinalidad y anchos representativos antes de considerar streaming o índice; conservar detección de UUID conflictivos. | No se ha observado un problema de memoria en la muestra (RSS máximo 41,9 MiB). |
| 6 · append compartido en XPAP | `_append_row_unified` relee el CSV previo en cada fila; 300 filas sintéticas tardaron 0,137–0,142 s y 600, 0,519–0,573 s. | Medir lote XPAP integral antes de proponer escritura por lotes o cabecera fija; comprobar esquema dinámico y orden. | Una reescritura debe preservar columnas y registros previos; no aplicar esta conclusión al camino PSG. |

El orden expresa **dónde medir y evaluar primero**, no autoriza cambios ni sustituye las decisiones de E02–E04. No se recomienda aplicar la propuesta antigua de optimizar `_append_row_unified` como si fuese el cuello de botella de PSG: el camino PSG usa `_append_psg_row` con caché de UUID.

## Validación y límites

- `PYTHONPATH=1_extract .venv/bin/python -m unittest discover -s 1_extract/tests -p 'test_*.py' -q`: **54 pruebas superadas** en 1,308 s. La primera invocación sin `PYTHONPATH` no cargó `test_auditoria_psg`; se corrigió el entorno y se repitió la suite completa.
- No se usaron documentos clínicos, datos personales, rutas `/mnt/e`, infraestructura externa ni archivos de producción. Las mediciones son de una única máquina y un único sistema de archivos; la comparación de entornos pertenece a E02.
- No hay medición integral DOC ni XPAP. Se intentó crear un DOC sintético con LibreOffice en `/tmp`; el proceso terminó con código 1 y mostró un error de escritura de `dconf` en el entorno restringido. El comportamiento DOC descrito arriba procede de lectura de código, no de tiempos medidos. Las garantías de archivado en Windows quedan para E03.
- Las cifras de RSS incluyen Python, dependencias y generación de la muestra; no aíslan memoria del parser. El historial de 5.000 filas tiene muchos campos vacíos, y la muestra RTF es repetitiva y pequeña. Cualquier optimización requerirá comparación con corpus aislado representativo y equivalencia de resultados.
