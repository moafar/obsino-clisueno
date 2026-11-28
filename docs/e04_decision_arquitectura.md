# E04 — Decisión de arquitectura de operación PSG

**Estado:** aprobada por el responsable del proyecto y formalizada el 2026-11-28. **Versión:** `v5.0.1`. **Alcance:** arquitectura objetivo y criterios operativos; no constituye despliegue ni habilita una ejecución automática en PRD.

## Decisión

- Ejecutar el pipeline en **WSL2**. Conservar los documentos originales y su archivo definitivo en **NTFS**. Situar CSV y demás archivos intermedios, logs y estado operativo en el sistema de archivos nativo Linux de WSL. La separación es una decisión de ubicación; su implementación y validación en cada entorno siguen las tareas del pipeline.
- Orientar el flujo a una **ejecución diaria automatizada y desatendida**. El modo diario deberá comprobar montaje y rutas reales, disponibilidad de credenciales y servicios, impedir solapamientos, aceptar lotes vacíos, registrar estados y recuentos, avisar de incidencias y reanudar sin pérdida ni duplicados. La programación productiva sigue sujeta a validación y autorización.
- Priorizar **integridad, idempotencia, trazabilidad y recuperación** ante interrupciones. Mantener `fsync`, bloqueos y archivado seguro hasta demostrar una alternativa de garantías equivalentes. No elegir una optimización por velocidad aislada.
- No desarrollar por ahora una variante para Windows nativo ni transferir los documentos originales a ext4. Conservar el formato intermedio actual mientras satisfaga el contrato y las garantías de publicación y recuperación. Las optimizaciones de E09 y PT09 solo se activarán ante incumplimiento operativo, coste recurrente relevante o riesgo demostrado, con medición y decisión explícitas.

## Fundamentos y alternativas descartadas

E01 identificó costes de escritura y parseo, sin justificar por sí solo un cambio funcional ([diagnóstico](e01_diagnostico_extractor.md)). E02 midió lotes sintéticos DOC/RTF equivalentes en WSL: `C:` NTFS/DrvFs tardó entre 6,49 y 8,82 veces el tiempo de ext4 en esas pruebas; no se midió el volumen documental `E:` ni una carga diaria real ([benchmark](e02_benchmark_entornos.md)). El resultado respalda ubicar **intermedios** en Linux, pero no demuestra que mover originales a ext4 sea necesario o seguro. E03 confirmó que el extractor vigente usa primitivas POSIX incompatibles directamente con CPython Windows y que el archivado en WSL/NTFS usa el respaldo enlace y retirada; la equivalencia de un puerto nativo y su recuperación no está demostrada ([compatibilidad](e03_compatibilidad_windows.md)).

Se descartan **por ahora**: (1) Windows nativo/Cygwin, por coste de adaptación y validación de bloqueo, conversión y archivado; (2) copiar originales a ext4 como paso de procesamiento, porque añade transferencia y estados de recuperación sin necesidad operativa demostrada; (3) optimizar `fsync` o el archivado solo para mejorar el benchmark. Estas exclusiones son decisiones de alcance vigentes, no afirmaciones de imposibilidad técnica.

## Criterio de suficiencia y datos pendientes

La operación será suficientemente rápida si completa **la ventana diaria que se acuerde**, con registros y documentos conciliados, sin pérdida, duplicación ni incidencias bloqueantes sin tratar. Un lote vacío debe concluir de forma trazable. Si no se cumple la ventana, o aparece un coste recurrente o riesgo de integridad relevante, se medirá el lote afectado y se reconsiderará únicamente la optimización necesaria. Los tiempos sintéticos de E02 no establecen un objetivo de producción.

| Dato aún no acordado | Responsable de confirmarlo | Momento de resolución |
|---|---|---|
| Hora y duración de la ventana diaria; regla para ejecuciones perdidas o tardías. | Responsable del proyecto con operación. | Antes de aprobar la programación de E32; incorporarlo al diseño y pruebas de E25–E26. |
| Volumen habitual y máximo razonable, mezcla DOC/RTF y disponibilidad del lote de entrada. | Responsable del proyecto con operación. | Antes de fijar los casos de validación diaria de E28 y de juzgar la suficiencia del rendimiento. |
| Disponibilidad del equipo WSL, montaje NTFS, credenciales y BigQuery; aviso, responsable de guardia y procedimiento ante fallos. | Responsable del proyecto con operación. | Antes de aceptar E25–E26 y habilitar E32 en producción. |

La ausencia de esos valores **no cierra** las tareas de automatización o despliegue. E25–E26 deben implementar y probar operación desatendida y recuperación; E28 debe validar lotes diarios y extremos aislados; E30 requiere autorización de despliegue; E32 habilitará la programación solo tras esas condiciones.

## Riesgos pendientes

- El código actual pide confirmación interactiva y aún no implementa el modo diario desatendido. Equipo, WSL, montaje, credenciales y BigQuery pueden no estar disponibles en la ventana prevista.
- E03 detectó una ventana entre mover el documento y registrar el traslado; debe conciliarse en E26. Las pruebas sintéticas no acreditan durabilidad ante corte eléctrico ni concurrencia entre procesos.
- El rendimiento de una carga diaria real en el NTFS objetivo y de todas las etapas integradas no está medido. Los resultados E02 no se extrapolan a `E:` ni sustituyen la validación de E28.
- Retener intermedios para recuperación puede aumentar uso de disco; E24 debe definir limpieza sin perder la última copia recuperable ni la identidad necesaria para la idempotencia.

**Resultado de PT01:** E01 caracterizó el extractor, E02 comparó los entornos viables y E03 evaluó compatibilidad y garantías. Esta decisión cierra E04 y PT01; no inicia las tareas dependientes.
