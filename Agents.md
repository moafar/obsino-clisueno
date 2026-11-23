# Guía para agentes

## Proyecto

`clisueno` es un ETL en Python para estudios clínicos de sueño. Los flujos disponibles son `psg` y `xpap`.

## Estructura

- `1_extract/`: extrae datos de documentos y genera CSV en `staging/`.
- `2_transform/`: valida y transforma los datos extraídos.
- `3_load/`: carga los datos transformados en BigQuery.
- `0_declarations/`: contiene los contratos de esquema compartidos.
- `logs/` y `procesados/`: guardan resultados operativos.

## Pautas básicas

- Consulta el `README.md` de la raíz y el de la capa que vayas a modificar.
- Mantén alineados los esquemas de `0_declarations/` con `2_transform/` y `3_load/`.
- Usa el entorno virtual `.venv` y las dependencias de la capa correspondiente.
- Valida los cambios con un flujo de prueba o con `--dry-run` cuando esté disponible.
- No incluyas credenciales ni datos clínicos en el repositorio o en los mensajes de registro.
- Evita ejecutar una carga real en `3_load/` durante una validación.
