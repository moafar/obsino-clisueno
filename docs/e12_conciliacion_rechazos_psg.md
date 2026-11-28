# E12 — Conciliación de rechazos PSG

La auditoría lee exclusivamente los eventos `Rechazo PSG:` del log de la ejecución. Agrupa `codigo` según la taxonomía de E08 y compara la suma con `archivos_rechazados`. También exige evento JSON válido con código y motivo conocidos, origen único por rechazo y archivo original aún presente dentro de la raíz de entrada. El origen debe ser un archivo regular, salvo `ENLACE_SIMBOLICO`, que exige un enlace simbólico en la raíz de entrada. Un evento ausente, duplicado, malformado o con origen no localizable produce `ERROR`.

El informe incluye **solo recuentos por código** y discrepancias agregadas, nunca rutas ni datos de documentos. Las advertencias por sección se cuentan aparte y no equivalen a rechazos. La conciliación general (`válidos = archivados + reintentos + fallos de archivado + duplicados + rechazados + errores técnicos de procesamiento`) permanece independiente de la conciliación por motivo; ambas deben pasar. Los errores técnicos no generan código de rechazo individual.

**Pruebas sintéticas:** dos rechazos con códigos distintos y un enlace simbólico rechazado concilian sin revelar rutas en el informe; cambiar el contador, repetir un origen o introducir JSON malformado produce `ERROR`. Los logs históricos sin eventos E08 no pueden demostrar exhaustividad de motivos y fallarán esta comprobación si declaran rechazos.
