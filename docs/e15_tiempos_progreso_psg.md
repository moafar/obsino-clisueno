# E15 — Progreso y tiempos PSG

La orquestación PSG registra en el log inicio y fin de tres fases: **lectura de UUID históricos**, **procesamiento** y **auditoría**. Cada fin informa duración monotónica en segundos. Una línea final registra esas tres duraciones y el **tiempo total de orquestación** desde el inicio bajo el logger hasta la liberación del bloqueo, incluidos preparación, resumen y generación del informe. Si una fase no se ejecutó, figura `NO_EVALUADO` en la línea final.

El Markdown de auditoría muestra lectura histórica, procesamiento, auditoría y orquestación **hasta preparar la escritura del informe**; el total exacto de la ejecución queda en el log final porque la escritura del propio Markdown y la liberación del bloqueo ocurren después. Esta diferencia se indica en las etiquetas, sin presentar una estimación como duración total cerrada. Los mensajes de progreso se emiten por fase, sin logging adicional por documento.

**Evidencia:** ejecución sintética del CLI PSG con un DOC; la prueba comprueba las tres marcas de progreso, la duración total en el log y las cuatro filas de tiempo del informe. La suite completa del extractor y auditoría superó 67 pruebas sintéticas en el entorno virtual del proyecto al cerrar PT03.
