# clisueno ETL

Proyecto ETL modular para procesamiento clínico de estudios de sueño, organizado en tres capas independientes:

- `extract`: extracción y estandarización inicial desde fuentes de documentos.
- `transform`: transformación declarativa por pipeline de dominio (actualmente `psg`).
- `load`: carga manual controlada a BigQuery con validaciones previas.

## Arquitectura general

```text
clisueno/
    extract/
    transform/
    load/
```

## 1) Capa `extract`

Responsabilidad:

- Leer fuentes de entrada (reportes/documentos por flujo).
- Extraer campos relevantes y normalizarlos a una salida tabular base.
- Registrar trazabilidad y errores de parsing sin detener todo el procesamiento.

Entrada/salida esperada:

- Entrada: carpetas de archivos clínicos por flujo.
- Salida: datasets estructurados para alimentar `transform`.

Referencia de detalle:

- `extract/README.md`

## 2) Capa `transform`

Responsabilidad:

- Aplicar reglas declarativas (schema + steps) para convertir datasets base en datasets analíticos.
- Validar esquema de entrada y salida.
- Ejecutar pipelines por subdominio clínico (ej. `psg`).

Entrada/salida esperada:

- Entrada: dataset estructurado desde `extract`.
- Salida: dataset transformado listo para `load`.

Referencia de detalle:

- `transform/README.md`

## 3) Capa `load`

Responsabilidad:

- Cargar manualmente a BigQuery con control de ejecución por consola.
- Mostrar configuración activa y solicitar confirmación humana.
- Validar duplicados en lote y contra tabla destino (modo `WRITE_APPEND`).

Entrada/salida esperada:

- Entrada: archivos tabulares finales + configuración YAML por flujo.
- Salida: inserción en tabla BigQuery objetivo.

Referencia de detalle:

- `load/README.md`

## Flujo operativo end-to-end

1. Ejecutar `extract` para generar dataset base.
2. Ejecutar `transform` para obtener dataset estandarizado por pipeline.
3. Ejecutar `load` para validar y cargar en BigQuery.

## Convenciones del repositorio

- Aislamiento por capa: `extract`, `transform` y `load` evolucionan de forma independiente.
- Configuración declarativa: YAML por pipeline/flujo cuando aplica.
- Ejecución manual controlada en `load` para minimizar riesgo operativo en cargas.

## Control de versiones del proyecto

El versionado se gestiona de forma global desde la raíz del repositorio:

- `CHANGELOG.md`: historial consolidado de cambios del proyecto ETL.
- `vX.Y.Z`: archivo marcador de la versión actual (ejemplo actual: `v4.0.0`).

Las capas `extract`, `transform` y `load` deben registrar cambios de versión en este control central,
evitando changelog/versionado aislado por subcarpeta.

## Requisitos generales

- Entorno virtual Python (`.venv`).
- Dependencias por capa (`extract/requirements.txt`, `transform/requirements.txt`, `load/requirements.txt`).
- Credenciales GCP para `load` en:
    - `load/secrets/obsino-clisueno.json`
