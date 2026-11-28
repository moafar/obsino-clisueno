# E08 — Rechazos individuales PSG

En el recorrido PSG, cada documento válido por extensión que termina rechazado emite **un único evento** `Rechazo PSG:` en el log de la ejecución. El evento JSON contiene `codigo`, `origen` y `motivo`; el origen permite localizar el fichero para intervención, mientras que el informe de auditoría solo mostrará agregados. El contador `archivos_rechazados` aumenta en la misma rama que emite el evento. No se genera un CSV de rechazos ni se mueve el original rechazado.

| Código | Motivo normalizado |
|---|---|
| `EXCLUIDO_OXIGENO` | Nombre excluido por patrón OXIGENO |
| `TEXTO_ILEGIBLE` | Texto ausente o ilegible tras conversión |
| `NO_PSG_BASAL` | No se identificó un PSG basal procesable |
| `UUID_NO_GENERADO` | No se pudo generar UUID del original |
| `EXTRACCION_ILEGIBLE` | Estructura PSG no recuperable |
| `ENLACE_SIMBOLICO` | Enlace simbólico no admitido |
| `ERROR_DOCUMENTO` | Error individual restante al procesar |

La taxonomía identifica **rechazos individuales**, no fallos de acceso al directorio, montaje o recorrido incompleto: `errores_recorrido` y los controles de integridad siguen separados. Una excepción inesperada del parser BASAL o un fallo posterior al parseo, como la escritura del CSV, incrementa `errores_procesamiento` y bloquea el lote; no se registra como rechazo individual. Las advertencias de una sección o un valor ausente no generan rechazos. Los duplicados y fallos de archivado tienen contadores propios y tampoco se etiquetan como rechazados. E12 concilia estos eventos contra `archivos_rechazados`; E25–E26 definirán la respuesta automática a fallos de infraestructura.

**Evidencia:** prueba sintética con cuatro orígenes distintos (conversión ilegible, texto no PSG, hash no generado y exclusión OXIGENO): cuatro rechazos y cuatro eventos con código y motivo, sin repetición de origen. La validación integrada de E12 comprobará los contadores a partir del log real.
