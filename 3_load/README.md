# Capa load

## Guía rápida de ejecución

Contexto: ejecutar desde la raíz del repo o desde `3_load/` con `.venv` activo.

```bash
source .venv/bin/activate

# Ejecución desde 3_load/
cd 3_load
../.venv/bin/python main.py --flow <subproceso_ejemplo> --input input/archivo_ready-to-load.xlsx
```

Ejemplo completo desde raíz:

```bash
./.venv/bin/python 3_load/main.py --flow <subproceso_ejemplo> --input 3_load/input/archivo_ready-to-load.xlsx
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

## Configuración

La configuración se resuelve por flujo:

- `--flow <subproceso_ejemplo>` -> `3_load/config/<subproceso_ejemplo>.yaml`

Ejemplos de nombre de subproceso:

- `subproceso_respiratorio`
- `subproceso_actigrafia`

Campos relevantes del YAML:

- destino BQ (`project_id`, `dataset_id`, `table_id`)
- modo de escritura (`write_disposition`)
- rutas de insumo (`shared_schema_yaml_path` o `schema_yaml_path`)
- selector opcional de schema dentro del YAML (`schema_path_in_yaml`), por ejemplo `schema.output.columns`
- descripción operativa de origen (`schema_description`)
- campos operativos (`uuid_field`, `date_field`, `migrated_field`)

La ruta del Excel se recibe por CLI con `--input`.

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

## Ejecución

Chuleta operativa (desde raíz del proyecto):

| Comando | Efecto |
|---|---|
| `./.venv/bin/python 3_load/main.py --flow <subproceso_ejemplo> --input 3_load/input/archivo_ready-to-load.xlsx` | Carga manual del flujo indicado usando el Excel indicado por CLI, con confirmación previa. |
| `./.venv/bin/python 3_load/main.py --flow <subproceso_ejemplo> 3_load/input/archivo_ready-to-load.xlsx` | Igual que el anterior, usando ruta de Excel como argumento posicional. |

Desde la raíz del proyecto:

```bash
./.venv/bin/python 3_load/main.py --flow <subproceso_ejemplo> --input 3_load/input/archivo_ready-to-load.xlsx
```

Alternativa con argumento posicional:

```bash
./.venv/bin/python 3_load/main.py --flow <subproceso_ejemplo> 3_load/input/archivo_ready-to-load.xlsx
```

Modo de ejecución soportado:

- Manual por flujo: `--flow <nombre>` + (`--input <ruta_excel>` o `<ruta_excel>` posicional), con confirmación interactiva previa a la carga.

El script muestra configuración activa y solicita confirmación por teclado antes de cargar.

## Notas operativas

- El flujo seleccionado debe existir como `3_load/config/<subproceso_ejemplo>.yaml`.
- Si `write_disposition` es `WRITE_APPEND`, se validan duplicados en lote y contra BigQuery.
- Si falla cualquier validación, la carga se cancela.

## Dependencias

```bash
./.venv/bin/pip install -r 3_load/requirements.txt
```