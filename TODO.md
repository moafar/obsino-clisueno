# TODO — Evoluciones del pipeline PSG

**Proyecto:** Obsino Clisueno · `moafar/obsino-clisueno`  
**Fecha de referencia:** 2026-11-28  
**Rama de desarrollo:** `integration/psg-evoluciones`  
**Commit base:** `d11abaf`  
**Estado:** 2/36 evoluciones cerradas (E01 validada; E02 completada; E03 pendiente).

## 1. Contexto y reglas de trabajo

- DEV: `rom@Z1081401S`, `~/obsino/clisueno` (WSL). PRD: `datosino@TERMINAL`, `~/obsino/clisueno2`, rama `main`, commit de referencia `710460c`.
- DEV y GitHub están sincronizados en la rama de integración; PRD permanece en `main` y solo recupera esa rama.
- La rama de integración incorpora la separación de paquetes `extract_commons` y `transform_commons`, y el auditor automático del PR #12. Se superaron 54 pruebas del extractor, 12 del transformador y 9 del cargador en sus respectivas etapas de integración. No se ha validado aún el pipeline integrado de extremo a extremo.
- `feature/psg-quality-check` (`8933c5d`) es una referencia técnica, no una rama que deba fusionarse íntegramente. Reutilizar selectivamente controles y pruebas pertinentes. El auditor del PR #12 ya está integrado en el código de DEV; su consolidación formal y el despliegue siguen pendientes.
- No realizar operaciones sobre documentos originales, archivos de producción, credenciales o BigQuery PRD durante el desarrollo y las pruebas. Usar copias aisladas, destinos temporales y datos de prueba. El despliegue requiere autorización expresa.
- No implementar validaciones de coherencia clínica, rangos clínicos ni consistencia matemática de indicadores clínicos en el ETL. Estos análisis corresponden a BigQuery/Looker y a los profesionales clínicos. Sí se permiten controles técnicos de estructura, tipos, identidad, fechas y trazabilidad.
- Preservar la durabilidad de las escrituras, el archivado seguro y la trazabilidad. No eliminar `fsync`, bloqueos o garantías de integridad por motivos de rendimiento sin demostrar una alternativa equivalente.
- Aplicar YAGNI. No introducir dependencias, abstracciones ni cambios de arquitectura sin necesidad demostrada.

### Protocolo obligatorio para Codex

1. Leer este archivo antes de iniciar una tarea y verificar rama, commit y estado del repositorio.
2. Trabajar sobre el primer paquete pendiente, respetando las dependencias. No iniciar tareas ajenas al alcance autorizado.
3. Mantener los identificadores E01–E36 estables. El orden de los paquetes refleja prioridad de ejecución; los identificadores conservan la numeración original.
4. Usar `[ ]` para tareas pendientes y `[x]` únicamente cuando se satisfaga su criterio de aceptación y se haya registrado evidencia. Una tarea bloqueada permanece `[ ]` y se anota en el registro con su motivo. Las decisiones pendientes de aprobación no se consideran cerradas.
5. Actualizar este TODO.md en el mismo conjunto de cambios que resuelve cada tarea: marcar la casilla, actualizar el contador inicial y añadir una entrada al registro de ejecución con evidencia concreta (pruebas, mediciones, archivos o commit cuando exista). No inventar resultados.
6. Actualizar las pruebas y documentación pertinentes durante cada implementación. Si se modifica una decisión aprobada, explicar el motivo y solicitar validación antes de aplicarla.
7. No fusionar a `main`, desplegar en PRD, modificar el esquema productivo ni ejecutar cargas reales sin autorización explícita.

## 2. Paquetes de trabajo por prioridad

### PT01 — Diagnóstico y estrategia de rendimiento (prioridad 1)

**Objetivo:** medir y entender los cuellos de botella antes de modificar el extractor. Fase inicialmente de análisis, no de implementación.

- [x] **E01 — Revisión profunda del extractor.** Analizar flujo de funciones, operaciones de disco, CPU, memoria, extracción DOC/RTF, expresiones regulares, hashes, escrituras y auditoría. **Aceptación:** informe con hallazgos sustentados, cuellos de botella y propuestas priorizadas, sin cambios funcionales.
- [x] **E02 — Benchmark de entornos de ejecución.** Comparar WSL sobre NTFS (`/mnt/e`), WSL sobre sistema de archivos Linux y Windows nativo cuando sea viable, con la misma muestra aislada y condiciones documentadas. Medir tiempo, rendimiento, CPU/memoria cuando sea posible y equivalencia de resultados. **Aceptación:** resultados reproducibles; separar entornos no medidos de los medidos.
- [ ] **E03 — Compatibilidad de catdoc y archivado en Windows.** Evaluar viabilidad de catdoc (incluida opción Cygwin si procede), equivalencia del texto y las garantías de `flock`, `renameat2` y operaciones con descriptores de directorio. **Aceptación:** matriz de compatibilidad, limitaciones y pruebas disponibles; no sustituir garantías de seguridad sin equivalencia demostrada.
- [ ] **E04 — Decisión de arquitectura de ejecución.** Elegir entorno y estrategia a partir de E01–E03, considerando rendimiento, mantenimiento e integridad. **Aceptación:** decisión documentada y aprobada por el responsable del proyecto.

### PT02 — Contrato de calidad y completitud (prioridad 2)

**Dependencia:** E01 para disponer de una caracterización del código. Puede avanzar conceptualmente mientras se resuelven benchmarks.

- [ ] **E05 — Política de auditoría técnica.** Definir controles bloqueantes, advertencias y correcciones tolerables; alinear extracción, transformación y carga. **Aceptación:** matriz de reglas aprobada, sin validaciones clínicas.
- [ ] **E06 — Verificar denominadores DOC/RTF.** Contrastar campos esperados contra el diccionario, contrato YAML, extractores y documentos representativos. **Aceptación:** listas exactas de campos aplicables por formato y sección, con justificación de exclusiones y tratamiento de la edad como indicador lógico único.
- [ ] **E07 — Implementar completitud por formato.** Sustituir el denominador uniforme por los campos esperados según DOC/RTF. Los ceros explícitos cuentan como presentes; los campos no aplicables no penalizan. **Aceptación:** pruebas por formato, ausencia, cero y edad; fórmula documentada y consistente entre extractor y auditor.
- [ ] **E10 — Eliminar controles clínicos y matemáticos del auditor.** Retirar reglas de rangos y coherencia clínica/matemática; no convertirlas en advertencias ETL. **Aceptación:** no quedan estas reglas en el auditor y los controles técnicos siguen operativos.

### PT03 — Optimización del extractor, trazabilidad y auditoría (prioridad 3)

**Dependencias:** PT01 para optimizaciones de rendimiento; PT02 para las reglas de calidad.

- [ ] **E08 — Detallar los rechazos individuales.** Registrar en el log cada rechazo con código normalizado y motivo, una sola vez por rechazo. No crear un CSV separado de rechazos. **Aceptación:** log trazable y taxonomía documentada, con casos de prueba representativos.
- [ ] **E09 — Optimizar el extractor.** Implementar solo las mejoras justificadas por E01–E04, preservando el resultado de extracción y las garantías de archivado. **Aceptación:** benchmark antes/después en muestra idéntica, equivalencia de resultados y pruebas de regresión satisfactorias.
- [ ] **E11 — Eliminar el recálculo MD5 del archivado.** Conservar el hash inicial que identifica el documento; eliminar completamente la segunda lectura para verificar el hash archivado, sin modo opcional. Conciliar existencia, rutas, CSV, log y cantidades. **Aceptación:** auditoría sin rehash y pruebas de detección de incidencias de archivado.
- [ ] **E12 — Conciliar rechazos por motivo.** Agregar los códigos de E08 al informe y comprobar que su suma coincide con el total de rechazos. **Aceptación:** reconciliación exacta y discrepancias detectables.
- [ ] **E13 — Reportar completitud por formato y sección.** Aplicar el contrato de E06–E07 al informe, incluyendo estadísticas por variable y sección, formatos y percentiles pertinentes. **Aceptación:** informe reproducible con denominadores correctos y estadísticas contrastadas.
- [ ] **E14 — Mejorar el informe Markdown.** Presentar resultados operativos, controles técnicos, advertencias, rechazos y conciliaciones de manera legible. **Aceptación:** informe único con cifras reconciliadas; sin datos clínicos individuales innecesarios.
- [ ] **E15 — Mejorar progreso y tiempos.** Registrar avance y duración de las fases, evitando sobrecarga significativa de logging. **Aceptación:** tiempos y progreso comprobables en una ejecución de prueba.

### PT04 — Transformación tolerante, identidad y metadatos (prioridad 4)

**Dependencias:** E05; coordinar el cambio de contrato con PT05 y PT06.

- [ ] **E16 — Gestionar tipos incompatibles.** Convertir a NULL los valores clínicos técnicamente incompatibles con el tipo declarado, sin bloquear el lote por ese motivo; preservar el valor original en la incidencia. Revisar conversiones y copias redundantes, evitando repetir normalizaciones cuando la equivalencia esté demostrada. **Aceptación:** pruebas de enteros, decimales y valores inválidos; distinguir ausencias legítimas de incidencias, conservar máscaras de nulos y tipos; medir cualquier optimización aplicada.
- [ ] **E17 — Incorporar `meta_incidencias_calidad`.** Única columna de metadatos, JSON serializado como STRING en BigQuery; NULL si no hay incidencias. Cada objeto tendrá `campo`, `valor_original`, `error` y `accion`. **Aceptación:** serialización reproducible, múltiples incidencias por fila y ausencia de validaciones clínicas.
- [ ] **E18 — Identificar problemas de identificación y fechas.** Marcar ID de paciente ausente y fecha ausente o inválida; comprobar que una fecha NULL es admitida por la tabla y el cargador antes de definir su tratamiento definitivo. **Aceptación:** reglas técnicas documentadas, probadas y alineadas con E05 y E17.
- [ ] **E19 — Gestionar UUID duplicados dentro del lote.** Conservar la primera aparición y descartar las posteriores, contabilizándolas; advertir si difieren. UUID ausente o inválido sigue siendo bloqueante. El auditor no comparará CSV históricos. **Aceptación:** conciliación de cantidades y pruebas de duplicados idénticos/diferentes y UUID inválidos.
- [ ] **E20 — Actualizar el contrato YAML.** Reflejar los campos, tipos y reglas aprobados; evitar cantidades de columnas codificadas de forma redundante cuando el YAML sea la fuente de verdad. **Aceptación:** comprobar explícitamente nombres, orden y tipos aplicables entre salida de extracción y entrada de transformación, y entre salida de transformación y entrada de carga; validar correspondencia con el esquema físico en E21. Pruebas que detecten incompatibilidades sin asumir igualdad de tipos entre CSV crudo y datos tipados.

### PT05 — Formato intermedio y carga eficiente (prioridad 5)

**Dependencias:** PT04 para el contrato de datos definitivo. El benchmark E34 puede adelantarse sin modificar el flujo productivo.

- [ ] **E34 — Comparar XLSX, CSV y Parquet.** Medir escritura, lectura, tamaño, consumo de recursos, fidelidad de tipos y posibilidades de carga BigQuery con una muestra idéntica. **Aceptación:** benchmark reproducible, decisión sustentada y limitaciones explícitas.
- [ ] **E35 — Sustituir XLSX por Parquet si se confirma su idoneidad.** Mantener un artefacto intermedio persistente, tipado y recuperable para reiniciar la carga. Publicar el artefacto intermedio mediante escritura temporal en el mismo sistema de archivos, validación, sincronización según garantías requeridas y renombrado atómico; no exponer archivos parciales ni sobrescribir resultados válidos inadvertidamente. **Aceptación:** decisión aprobada, equivalencia de registros/campos/UUID, pruebas de transformación, persistencia y recuperación ante escritura interrumpida. Si se descarta Parquet, documentar la alternativa y su aprobación.
- [ ] **E36 — Adaptar carga al formato intermedio.** Evaluar carga nativa BigQuery desde Parquet y alternativas, sin sacrificar validación, deduplicación ni capacidad de reintento. Revisar conversiones, copias y lecturas redundantes en el cargador; verificar fidelidad de tipos, identificadores, fechas, nulos y metadatos. **Aceptación:** implementación acorde con E35 y medición comparativa; pruebas en entorno aislado, equivalencia de tipos y valores, y exclusión de archivos parciales.
- [ ] **E21 — Alinear el esquema físico de BigQuery.** Preparar y validar el cambio de esquema correspondiente al contrato E20, incluida la columna de incidencias; proteger la tabla histórica legacy. **Aceptación:** esquema validado en entorno aislado y migración productiva autorizada y verificada cuando corresponda. No modificar PRD en esta fase sin aprobación.
- [ ] **E22 — Propagar metadatos hasta BigQuery.** Verificar que `meta_incidencias_calidad` y el resto de metadatos se conservan en todas las etapas pertinentes. **Aceptación:** conciliación de valores desde transformación hasta carga de prueba.
- [ ] **E23 — Omitir UUID existentes en BigQuery.** No sobrescribir registros existentes. Conciliar entradas, duplicados, omitidos e insertados; respetar filtros de partición cuando sean exigibles. Verificar la implementación vigente y comparar consultas por bloques, consulta parametrizada única y, si el volumen lo justifica, staging/anti-join o MERGE. Evaluar latencia, trabajos, bytes procesados, coste y riesgo de concurrencia entre comprobación e inserción; no asumir que MERGE garantiza unicidad por sí solo. **Aceptación:** alternativa justificada mediante mediciones disponibles, prueba de reejecución idempotente, conteos exactos y garantías de concurrencia documentadas y probadas según el alcance operativo.

### PT06 — Orquestación y recuperación (prioridad 6)

**Dependencias:** PT02–PT05, especialmente las reglas de identidad y el formato intermedio definitivo.

- [ ] **E24 — Definir limpieza de staging y deduplicación.** Establecer cuándo conservar, archivar o retirar artefactos. Verificar el efecto de retirar CSV sobre `load_known_psg_uuids` y la prevención de reprocesamiento/archivado repetido. Verificar que el descubrimiento automático solo selecciona entradas elegibles y excluye resultados transformados, cargados o temporales; comprobar explícitamente que no se generan transformaciones de transformaciones. **Aceptación:** política aprobada, trazabilidad y pruebas de descubrimiento y reejecución; ninguna eliminación de originales.
- [ ] **E25 — Automatizar el flujo extract → audit → transform → load.** Usar la separación de espacios de nombres ya integrada y conservar artefactos y estados de cada etapa. Incorporar un registro persistente mínimo por lote (preferentemente JSON local si es suficiente): identificador, etapas y estados, artefactos, recuentos, referencia del trabajo BigQuery y error cuando corresponda; sin datos clínicos innecesarios. **Aceptación:** ejecución integrada en entorno aislado, estados persistidos de forma segura y sin continuar ante errores bloqueantes.
- [ ] **E26 — Gestionar interrupciones y reintentos.** Definir reanudación, errores bloqueantes y recuperación segura sin duplicar cargas o perder documentos. Evaluar un `job_id` determinista asociado a la identidad del lote, destino y operación de carga; consultar el estado del trabajo anterior antes de reintentar, distinguir trabajos fallidos de resultados inciertos y reconciliar BigQuery con el estado local. No usarlo como sustituto de la deduplicación. **Aceptación:** pruebas de interrupción y reintento en las fronteras críticas, incluida carga exitosa seguida de fallo local antes de registrar el éxito, sin duplicados ni pérdida de documentos.

### PT07 — Validación, consolidación y despliegue (prioridad 7)

**Dependencias:** implementación de PT02–PT06; E27 es transversal y se trabaja desde la primera modificación.

- [ ] **E27 — Actualizar pruebas unitarias y de regresión.** Mantener cobertura de PSG y XPAP, contratos, archivado, auditoría, transformación y carga. **Aceptación:** suites pertinentes superadas y resultados registrados sobre la versión candidata final; las 75 pruebas iniciales son la línea base, no el cierre de esta tarea.
- [ ] **E28 — Validar extremo a extremo con 2024.** Usar copias aisladas de los documentos/artefactos disponibles y destino de prueba; no volver a archivar originales ni cargar sobre PRD. **Aceptación:** conteos, UUID, fechas, completitud, incidencias y resultados reconciliados; explicar cualquier diferencia frente a la referencia histórica.
- [ ] **E29 — Consolidar formalmente el PR #12.** Revisar los cambios del auditor ya incorporados en `d11abaf`, resolver su estado en GitHub y asegurar que no se integren dos veces. **Aceptación:** trazabilidad del PR original y de la versión candidata; decisión de cierre/fusión documentada y aprobada.
- [ ] **E30 — Desplegar en producción.** Promover la versión validada a `main`, aplicar migraciones aprobadas cuando proceda y actualizar PRD mediante el flujo Git establecido. **Aceptación:** autorización explícita, commit y esquema verificados, prueba operativa controlada y estrategia de reversión documentada.

### PT08 — Regularización histórica y operación (prioridad 8)

**Dependencias:** PT07 y autorización para trabajar con datos de producción.

- [ ] **E31 — Recalcular completitud histórica.** Evaluar disponibilidad del formato de origen y los campos necesarios; aplicar la definición aprobada sin inventar datos faltantes ni alterar indicadores clínicos. **Aceptación:** alcance, metodología, reconciliación antes/después y actualización autorizada.
- [ ] **E32 — Establecer ejecuciones periódicas.** Definir frecuencia, responsable, configuración y manejo de errores según necesidades operativas. **Aceptación:** procedimiento aprobado y probado, sin programar procesos productivos sin autorización.
- [ ] **E33 — Seguimiento de calidad en BigQuery/Looker.** Establecer indicadores de calidad técnica y facilitar el análisis clínico fuera del ETL. **Aceptación:** consultas o visualizaciones verificadas, con definiciones y denominadores documentados.

## 3. Decisiones y referencias que deben preservarse

- Completitud preliminar: 124 indicadores aplicables en DOC y 123 en RTF. Son denominadores candidatos, no valores definitivos hasta completar E06. La edad en años/meses/días constituye un único indicador lógico. El cero explícito se considera presente.
- La completitud mide presencia de información extraída; no certifica validez clínica. La relación entre completitud de extracción y normalización posterior de valores inválidos debe quedar definida en E05–E07.
- El contrato actual observado tiene 159 columnas de extracción y 157 de transformación; consultar el YAML vigente antes de implementar. No asumir que estos totales permanecerán constantes.
- Tabla productiva: `observatorio-ino-1.clisueno.tbl_psg_prd`. Proteger `tbl_psg_legacy_prd`.
- Referencia 2024: lote de 9.080 filas cargadas, 9.083 registros del año en BigQuery tras la carga (3 registros adicionales cuyo origen no se verificó). No usar estas cantidades como expectativa universal para una nueva extracción; documentar población y alcance de cada comparación.
- Benchmark histórico de carga XLSX: lectura aproximada 46,4 s, duración total aproximada 66,5 s para el lote de 9.080 filas. Es una observación previa, no un benchmark controlado frente a Parquet.
- El validador local respaldado puede aportar percentiles y conciliación de conjuntos UUID entre etapas; no incorporar su comparación con históricos ni mantener una segunda herramienta redundante por defecto.

- Diagnóstico E01: `docs/e01_diagnostico_extractor.md` y `docs/e01_perfil_extractor.py`. En dos ejecuciones de 480 RTF sintéticos sobre el sistema Linux de WSL, tiempo total 2,517–2,603 s, `fsync` 0,961–1,019 s, parseo 0,688–0,701 s; 480 filas y archivos archivados, auditoría OK. No extrapolar a DOC, NTFS ni documentos clínicos reales. No eliminar `fsync` sin garantías equivalentes. El tiempo del resumen del extractor no incluye lectura histórica ni auditoría: considerar en E15.
- E01 confirmó que la relectura cuadrática del CSV y la enumeración materializada del árbol afectan a XPAP, no al camino PSG actual. Conservar como referencia para una revisión futura de XPAP, sin ampliar el alcance de las 36 evoluciones PSG.
- La propuesta histórica de refactorización sobre `b7c3f2d` (v4.1.1) se revisó como antecedente. Los posibles defectos de esa versión deben comprobarse en el código vigente antes de corregirlos. Las aportaciones pertinentes se incorporan a E16, E20, E23–E26 y E35–E36. No se amplía el alcance a DOCX, cambio de algoritmo MD5, nuevas columnas de migración, unificación integral PSG/XPAP ni frameworks externos sin decisión expresa.

## 4. Registro de ejecución

Añadir una entrada por tarea terminada o bloqueada. Mantener el historial; no sustituir entradas anteriores.

| Fecha | Tarea | Estado | Evidencia / resultado | Commit o referencia |
|---|---|---|---|---|
| 2026-11-28 | Base | Consolidación previa | Rama integrada; 54 + 12 + 9 pruebas superadas en sus etapas respectivas. Sin ejecución integral de la versión consolidada. | `d11abaf` |

| 2026-11-28 | E01 | Completada y validada | Diagnóstico y script reproducible; 54 pruebas superadas según Codex. Revisión estática del script y del informe; sin cambios funcionales. DOC integral no medido por limitación del entorno; XPAP solo microbenchmark de append. | `docs/e01_diagnostico_extractor.md`, `docs/e01_perfil_extractor.py` (base de medición `dc5e278`) |
| 2026-11-28 | Hoja de ruta | Actualizada | Integración selectiva de aportaciones del diagnóstico histórico; sin nuevas tareas ni cambios de prioridad. | Propuesta histórica `b7c3f2d` |
| 2026-11-28 | E02 | Completada | 24 ejecuciones sintéticas (DOC/RTF; 30/120; tres repeticiones) en WSL ext4 y C: NTFS/DrvFs. Filas y archivados equivalentes por SHA-256; auditorías OK. NTFS/DrvFs 6,49–8,82× más lento según formato y lote. `/mnt/e` sin montar; Windows nativo sin Python y con incompatibilidades POSIX pendientes de E03. CPU/RSS, método y límites en `docs/e02_benchmark_entornos.md`; datos íntegros en `docs/e02_mediciones.json`. Sin cambios funcionales; versión v5.0.1 conservada. | `d64afa3` (base de medición) |

**Próxima tarea:** E03 — compatibilidad de catdoc y archivado en Windows (no iniciada).
