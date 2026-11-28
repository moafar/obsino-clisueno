# E35 — Parquet como salida de transformación PSG

## Decisión y alcance

La transformación PSG sigue leyendo el CSV crudo y el YAML sigue definiendo las 158 columnas de salida. Publica un solo archivo `.parquet` mediante PyArrow con compresión Snappy; no genera XLSX. Se conservan las conversiones, incidencias y reglas de duplicados de E16–E20. XPAP continúa con su salida XLSX. E36 adaptará el cargador PSG: en E35 todavía espera XLSX.

E34 verificó la equivalencia exacta de Parquet en 27 mediciones sintéticas. E35 valida también cada archivo real generado por la transformación antes de publicarlo: vuelve a leer el temporal y compara el DataFrame completo con tipos y valores exactos. Esto comprende orden y nombre de columnas, UUID, identificadores con ceros iniciales, fechas, NULL y el JSON de incidencias.

## Publicación y recuperación

1. Se escribe un temporal oculto en el mismo directorio que el destino. El nombre final queda reservado para artefactos completos.
2. Se relee y compara el temporal; después se sincroniza su descriptor de archivo.
3. Un enlace físico crea el nombre final atómicamente y falla si ya existe. Se sincroniza el directorio, se retira el nombre temporal y se vuelve a sincronizar el directorio.

Un fallo de escritura o validación no expone un archivo final parcial; el CSV de origen permanece. Una colisión no reemplaza el resultado previo. Si el proceso se interrumpe después de crear el enlace final, puede quedar también el nombre temporal; ambos apuntan al mismo archivo completo. Si falla la sincronización después del enlace, el estado debe revisarse antes de reintentar. El retiro y la reconciliación automatizados de restos e interrupciones corresponden a E24–E26.

El método requiere un sistema de archivos Linux con enlaces físicos y sincronización de directorios; el intermedio aprobado está en ext4 de WSL2. Las pruebas locales cubren fallos de software simulados y persistencia después del retorno normal. No demuestran resistencia a pérdida eléctrica, caída del sistema ni semántica idéntica en otros sistemas de archivos.

## Validación local

Los datos de prueba son sintéticos. La suite de transformación verifica el contrato de 158 campos, equivalencia exacta tras lectura, compresión, incidencias, deduplicación, conservación del CSV, colisión de destino, fallo de escritura y fallo de publicación; incluye la regresión XPAP. Resultado y comando constan en `TODO.md`.
