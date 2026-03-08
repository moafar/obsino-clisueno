# Capa load

## Guía rápida de ejecución

Contexto: ejecutar desde la raíz del repo o desde `3_load/` con `.venv` activo.

```bash
source .venv/bin/activate

# Ejecución desde 3_load/
cd 3_load
../.venv/bin/python main.py --flow <subproceso_ejemplo> --input ../staging/extract_<subproceso_ejemplo>_YYYY-MM-DD_HH-MM_transformed.xlsx
```

Ejemplo completo desde raíz:

```bash
./.venv/bin/python 3_load/main.py --flow <subproceso_ejemplo> --input staging/extract_<subproceso_ejemplo>_YYYY-MM-DD_HH-MM_transformed.xlsx
```

Carga manual de datasets transformados a BigQuery, con controles operativos y validaciones previas.

## Objetivo

- Ejecutar cargas manuales y trazables a BigQuery.
- Despachar configuración por flujo con YAML fijo desde CLI.
- Prevenir cargas duplicadas mediante validaciones en lote y en tabla destino.

## Estructura principal

```text
3_load/
    main.py
    config/
        <subproceso_ejemplo>.yaml
    secrets/
    requirements.txt
```

Carpetas de datos operativos:

- Entrada de carga: `staging/` filtrando por `extract_<flow>_..._transformed`.
- Archivado post-carga: `staging/` con sufijo `_loaded`.

## Configuración

La configuración se resuelve por flujo:

- `--flow <subproceso_ejemplo>` -> `3_load/config/<subproceso_ejemplo>.yaml`

Estado actual de flows:

- `psg`: implementado.
- `xpap`: implementado.

Ejemplos de nombre de subproceso:

- `subproceso_respiratorio`
- `subproceso_actigrafia`

Campos relevantes del YAML:

- destino BQ (`project_id`, `dataset_id`, `table_id`)
- modo de escritura (`write_disposition`)
- rutas de insumo (`shared_schema_yaml_path` o `schema_yaml_path`)
- selector opcional de schema dentro del YAML (`schema_path_in_yaml`), por ejemplo `schema.load.input.columns`
- descripción operativa de origen (`schema_description`)
- campos operativos (`uuid_field`, `date_field`, `migrated_field`)

La ruta del Excel puede recibirse por CLI con `--input` o autodetectarse en `staging/` para el flow seleccionado.

### Contrato de schema compartido con transform

`load` puede reutilizar directamente el schema de salida de `transform` para evitar duplicación.

- YAML origen: `0_declarations/<subproceso_ejemplo>.yaml`
- ruta del schema consumida por `3_load`: `schema.load.input.columns`
- relación explícita: `schema.load.input.columns` equivale a `schema.transform.output.columns`

Con esto, el esquema de BigQuery se construye desde el mismo contrato de salida usado por `transform`.

## Autenticación

Service Account local por capa:

- `3_load/secrets/obsino-clisueno.json`

El script configura `GOOGLE_APPLICATION_CREDENTIALS` en tiempo de ejecución.

## Validaciones

- existencia de archivos requeridos (credencial, Excel, schema)
- columnas esperadas vs. schema YAML
- casting por tipos declarados
- normalización de vacíos y validación de fecha
- duplicados dentro del lote (`uuid_field`)
- duplicados contra BigQuery cuando `WRITE_APPEND`

Si falla alguna validación, la carga se cancela.

## Post-carga exitosa

Cuando la carga finaliza exitosamente en BigQuery, el archivo de entrada se mueve automáticamente dentro de `staging/`.

Y se renombra agregando el sufijo `_loaded` antes de la extensión.

Ejemplo:

- `staging/extract_psg_2026-03-08_20-01_transformed.xlsx`
- `staging/extract_psg_2026-03-08_20-01_transformed_loaded.xlsx`

Si ya existe un archivo con ese nombre, se agrega un timestamp para evitar sobrescritura.

## Ejecución

Chuleta operativa (desde raíz del proyecto):

| Comando | Efecto |
|---|---|
| `./.venv/bin/python 3_load/main.py --flow <subproceso_ejemplo> --input staging/extract_<subproceso_ejemplo>_YYYY-MM-DD_HH-MM_transformed.xlsx` | Carga manual del flujo indicado usando el Excel indicado por CLI, con confirmación previa. |
| `./.venv/bin/python 3_load/main.py --flow <subproceso_ejemplo> staging/extract_<subproceso_ejemplo>_YYYY-MM-DD_HH-MM_transformed.xlsx` | Igual que el anterior, usando ruta de Excel como argumento posicional. |
| `./.venv/bin/python 3_load/main.py --flow <subproceso_ejemplo>` | Autodiscovery: toma el archivo mas reciente para el flow desde `staging/`. |

Desde la raíz del proyecto:

```bash
./.venv/bin/python 3_load/main.py --flow <subproceso_ejemplo> --input staging/extract_<subproceso_ejemplo>_YYYY-MM-DD_HH-MM_transformed.xlsx
```

Alternativa con argumento posicional:

```bash
./.venv/bin/python 3_load/main.py --flow <subproceso_ejemplo> staging/extract_<subproceso_ejemplo>_YYYY-MM-DD_HH-MM_transformed.xlsx
```

Modos de ejecución soportados:

- Manual por flujo: `--flow <nombre>` + (`--input <ruta_excel>` o `<ruta_excel>` posicional), con confirmación interactiva previa a la carga.
- Autodiscovery por flujo: `--flow <nombre>` sin `--input`, usa el archivo mas reciente de `staging/` que cumpla `extract_<flow>_..._transformed`.
- Restricción de seguridad: si se pasa `--input`, la ruta debe pertenecer a `staging/` y cumplir la convención `extract_<flow>_..._transformed`; rutas externas o nombres no válidos son rechazados.

El script muestra configuración activa y solicita confirmación por teclado antes de cargar.

## Notas operativas

- El flujo seleccionado debe existir como `3_load/config/<subproceso_ejemplo>.yaml`.
- Si `write_disposition` es `WRITE_APPEND`, se validan duplicados en lote y contra BigQuery.
- Si falla cualquier validación, la carga se cancela.
- Logs de esta capa se escriben en `/home/rom/obsino/clisueno/logs` con nombre `load_<flow>_YYYY-MM-DD_HH-MM-SS.log`.

## Dependencias

```bash
./.venv/bin/pip install -r 3_load/requirements.txt
```