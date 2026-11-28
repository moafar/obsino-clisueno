# E14 — Informe Markdown operativo PSG

La auditoría produce un único Markdown por ejecución, junto al log. Al inicio muestra resultado global (`OK`, `ADVERTENCIA` o `ERROR`), acción operativa y número de controles por estado. Después presenta una tabla de recuentos del lote, conciliación explícita de válidos frente a sus destinos, controles técnicos del CSV y del archivado, completitud lógica de E13, motivos de rechazo de E12 y advertencias de sección separadas.

El informe conserva solo nombres de artefactos y **agregados**; los orígenes individuales de los rechazos permanecen exclusivamente en el log existente. Un `ERROR` indica detener la continuación automática; el archivado ya efectuado no se revierte. La unicidad histórica sigue fuera de este informe y la recuperación de interrupciones corresponde a E26.

**Pruebas sintéticas:** el informe de un lote correcto contiene resultado, recuentos y ecuación de conciliación; el de dos rechazos muestra tabla por código sin rutas. Las 11 pruebas del módulo de auditoría pasaron tras los cambios de E14.
