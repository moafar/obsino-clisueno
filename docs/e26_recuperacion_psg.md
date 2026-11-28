# E26 — Recuperación explícita PSG

## Uso y alcance

Una ejecución se reanuda mediante `.venv/bin/python scripts/run_psg.py --resume <identificador>`. Se reutilizan `staging/psg_runs/<identificador>/run.json`, las rutas y el destino originales. No se aceptan rutas o tabla alternativas en esa invocación. No se inicia una ejecución nueva ni se busca el último archivo de staging. E24 sigue aplazada como deuda técnica: permanecen los CSV históricos y su consulta para deduplicación y reintento de archivados.

Cada etapa confirmada se contrasta con el artefacto correspondiente antes de omitirla. Las huellas SHA256 son de los artefactos CSV/Parquet, no de documentos originales o archivados; el MD5 documental inicial se conserva como UUID. Una alteración o ausencia no explicada detiene la recuperación. Si se detecta al revalidar una etapa confirmada, se persiste `recovery_blocked`: posteriores reanudaciones no pueden reinterpretarla como una etapa pendiente ni volver a ejecutar la CLI. Incluso restaurando el archivo, se exige revisión y resolución explícita del registro por el responsable; no existe opción CLI para saltarse la marca. Si una etapa de carga ya iniciada carece de su journal y de un resultado final confirmado, el orquestador no vuelve a invocarla: exige revisión. Si la carga ya retiró el Parquet de entrada, se exige evidencia de carga confirmada y se verifica el archivo `_loaded`. El registro local se publica con temporal, sincronización y reemplazo atómico.

## Exclusión local

Orquestador y CLI manuales PSG comparten `staging/.psg-run.lock`. Orden de adquisición: global, después archivado o tabla. El orquestador transmite el descriptor bloqueado a sus subprocesos; las CLI comprueban que corresponde al mismo archivo. No intentan adquirir una segunda descripción independiente del bloqueo. El descriptor se cierra sin desbloquearlo explícitamente: un hijo superviviente mantiene la exclusión si muere el padre. Las CLI independientes esperan al bloqueo global; un segundo orquestador falla sin iniciar procesamiento. El bloqueo cubre las CLI de extracción, auditoría independiente, transformación unificada, transformación PSG directa, carga y orquestación. XPAP mantiene su flujo.

## Extracción y documentos

El extractor conserva su mecanismo de UUID y CSV históricos. En una ejecución normal se lee una sola vez el histórico y se pasa el mismo diccionario de UUID a recuperación y procesamiento. Los journals `LOGGED` se omiten antes de comprobar rutas o evidencias: no se revalidan movimientos históricos confirmados ni bloquean un cambio legítimo de origen/archivo. Solo se recuperan pendientes `PREPARED`/`DONE` pertinentes para las rutas operativas; un pendiente incompatible bloquea con error explícito y conserva su journal. El traslado normal sincroniza el evento del log y confirma `LOGGED` antes de devolver el éxito. Antes del movimiento documental guarda un journal por UUID/origen en `staging/.psg-moves/`: rutas, UUID inicial, dispositivo, inode, tamaño, mtime y log original. Sincroniza el documento sin releerlo ni recalcular MD5. La recuperación exige la fila histórica UUID/origen y evidencia física concordante. Puede completar enlace/retirada y reconstruir, una sola vez, el evento de traslado en el log original cuando el movimiento terminó antes del registro. Para un movimiento pendiente, una colisión con otro inode o un destino desaparecido bloquean la recuperación.

Al completar el recorrido, la CLI persiste un checkpoint antes de auditar. Si falta el resumen final o informa de archivados fallidos y existe ese checkpoint, `--resume-extraction` reconcilia movimientos, ajusta únicamente los recuentos demostrados por las filas y los eventos originales, y repite la auditoría. El checkpoint original permanece como evidencia. Un resumen final válido se reutiliza. Si el proceso murió antes de confirmar el recorrido completo, no hay evidencia suficiente del inventario: se concilian los movimientos demostrables y se detiene la ejecución para revisión. No se interpreta un CSV parcial como lote completo ni se vuelve a recorrer silenciosamente el origen ya modificado. Una ejecución nueva posterior sigue teniendo disponible la recuperación histórica de archivados fallidos.

## Publicación Parquet

Una transformación no confirmada se invoca con `--recover-publication`. Reutiliza un Parquet final solo si coincide exactamente con la transformación tipada del CSV original; sincroniza archivo y directorio. Si solo queda un temporal válido, lo compara, sincroniza y publica sin reemplazar otro resultado. Un temporal incompleto no se publica ni se elimina durante la recuperación. Si no hay temporal aprovechable, el CSV conserva la posibilidad de regeneración. Una etapa ya confirmada no vuelve a transformarse. El registro de ejecución referencia explícitamente el journal de carga en `paths.load_state`.

## Carga e incertidumbre remota

Cada Parquet dispone de un journal `.load-state.json`. Guarda huella del artefacto, ruta original, destino, región, UUID seleccionados, recuentos, intento lógico, `job_id` y evidencia del archivo para el traslado final. El `job_id` determinista identifica ruta/lote, huella, tabla, intento y subconjunto enviado. El journal se persiste en `READY` y luego `SUBMITTED` **antes** de llamar a BigQuery. Se reutilizan consultas parametrizadas por bloques, filtrado E23 y `WRITE_APPEND`.

| Estado | Reanudación |
|---|---|
| `READY` | Reserva el destino. Al reanudar, reconsulta UUID existentes bajo exclusión, actualiza y persiste el plan antes de enviar; si ya existen todos, no carga. Conserva el intento lógico y ajusta el job_id al subconjunto final. |
| `SUBMITTED` / `UNKNOWN` | Consulta el mismo `job_id`, proyecto y región. Nunca reenvía mientras no se conozca el resultado. |
| `PENDING` | Consulta nuevamente en una reanudación posterior; no crea otro trabajo. |
| Trabajo `DONE` con error | Registra `FAILED` y detiene; la próxima reanudación puede crear un intento lógico nuevo. |
| Trabajo `DONE` correcto | Verifica identidad/destino/WRITE_APPEND y `output_rows`, y persiste `CONFIRMED`. |
| `CONFIRMED` | Completa únicamente enlace/retirada hacia `_loaded.parquet`, sin sobrescribir. |
| `LOADED` | Verifica identidad del archivo y reutiliza el resultado; no repite carga ni movimiento. |

Si `get_job` falla o devuelve ausencia del trabajo, el resultado se considera desconocido. Tampoco se reenvía tras expirar la retención remota: hace falta revisión. Una muerte entre guardar `SUBMITTED` y enviar puede dejar un trabajo inexistente; se prefiere detenerse a arriesgar una inserción repetida. Un error de red de `job.result()` no equivale a fallo confirmado. Los journals `READY`, `SUBMITTED`, `PENDING` y `UNKNOWN` reservan la tabla e impiden que un lote nuevo o un intento fallido se adelante. Entre varios `READY` heredados, se reconcilia primero el de ruta de journal lexicográficamente menor; los demás esperan, y cada uno reconsulta UUID antes de enviar. Cualquier estado fuera de READY/SUBMITTED/PENDING/UNKNOWN/FAILED/CONFIRMED/LOADED se rechaza expresamente. Un journal con resultado incierto bloquea los envíos READY hasta reconciliarlo; así no se elude la incertidumbre copiando el artefacto a otro nombre. Las consultas de trabajos ya existentes y el cierre de cargas confirmadas siguen permitidos para evitar bloqueos mutuos entre journals. No se incrementa el intento por timeout ni por fallo local de movimiento.

El archivado postcarga usa un nombre determinista, enlace físico sin reemplazo, sincronización del directorio, retirada del origen y sincronización. El journal y la evidencia permiten completar tanto el estado con ambos nombres como el estado con solo el destino. No se elimina el último artefacto recuperable antes de confirmar y conciliar la carga.

## Límites

No existe transacción distribuida entre BigQuery, JSON y sistema de archivos. Escritores externos que no respeten estos bloqueos pueden insertar entre consulta y carga: no se garantiza unicidad global. Las modificaciones externas de archivos provocan detención cuando contradicen las evidencias. La comprobación del montaje se repite al reanudar; no garantiza que permanezca disponible durante la etapa. No se han ensayado pérdida eléctrica real, caída del kernel, reinicio WSL ni semántica de persistencia de NTFS en todos los dispositivos. `fsync` y evidencia de inode no sustituyen esas pruebas.

Las ejecuciones anteriores a E26 no disponen necesariamente de montaje, huellas, checkpoint documental ni identidad de trabajo remoto persistida. No se migran automáticamente ni se reconstruye esa evidencia a partir de nombres o recuentos: la reanudación puede quedar detenida y exige revisión manual. La falta de huella al revalidar una etapa confirmada deja también `recovery_blocked`; no se inventa la evidencia ausente. Los journals se conservan; su limpieza continúa aplazada con E24. No se incorpora programación, despliegue ni evoluciones posteriores. La validación remota autorizada sigue pendiente de E28.

## Validación sintética

La ronda consolidada abarca orquestador y persistencia compartida, extracción/archivado, transformación y carga. Incluye fallo de escritura/espacio, SIGKILL del padre con hijo bloqueado, reanudación sin repetir etapas, montaje no disponible, huellas inconsistentes, recuperación de enlace/retirada, traslado sin log, respuesta remota perdida, estado pendiente/desconocido, fallo remoto confirmado y recuperación tras carga confirmada. Los servicios remotos se simulan. Los resultados ejecutados constan en TODO.md.


Resultados: 142 casos distintos cubiertos satisfactoriamente entre la ronda consolidada y las comprobaciones específicas posteriores: 17 de orquestación/persistencia, 74 de extracción, 21 de transformación y 30 de carga. La ronda inicial detectó una regresión del código de salida de una colisión documental; quedó corregida y se verificó el caso afectado. Una limpieza de imports causó un NameError en dos comprobaciones específicas; se restauró el import y ambas pasaron. Las ampliaciones verifican también estado READY previo al envío, error remoto confirmado aunque `result()` lance excepción, retirada del origen antes de persistir LOADED y resolución de varios journals inciertos. No se repitieron las suites completas tras esas correcciones.

Comandos base: `.venv/bin/python -m unittest discover -s scripts/tests -v`, `PYTHONPATH=1_extract .venv/bin/python -m unittest discover -s 1_extract/tests`, y `PYTHONPATH=1_extract:2_transform .venv/bin/python -m unittest discover -s 2_transform/tests` / `-s 3_load/tests`. Las repeticiones seleccionaron los casos afectados por nombre con `unittest`. Comprobación de espacios correcta en los archivos de E26; el diff global mantiene un espacio final preexistente en `docs/refactoring-proposal.md`, ajeno a esta tarea. Se conserva v5.0.1, sin commits, push ni acceso a PRD/BigQuery real.


## Correcciones finales de revisión técnica

Validadas exclusivamente 33 pruebas afectadas: 16 de carga, 9 de extracción y 8 de orquestación/bloqueo. Incluyen interrupción en READY y otro lote con UUID coincidente, omisión total y parcial al reconciliar planes antiguos, prioridad determinista entre varios READY, rechazo explícito de estados inválidos, cambio legítimo de origen, reutilización del diccionario histórico y bloqueo persistente tras una inconsistencia confirmada. Los journals históricos se conservan.

La prueba de CLI intercepta el bloqueo antes del procesamiento en las seis entradas del pipeline; se mantiene además la prueba real de descriptor heredado y SIGKILL. El auditor independiente utiliza ahora el mismo bloqueo. Se retiraron las importaciones duplicadas de `sys` introducidas en E26. No se repitieron las suites completas ni se hicieron consultas remotas. E24 sigue como deuda técnica y v5.0.1 permanece sin cambios.
