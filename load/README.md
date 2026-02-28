# Capa load

Carga manual de datasets transformados a BigQuery, con controles operativos y validaciones previas.

## Objetivo

- Ejecutar cargas manuales y trazables a BigQuery.
- Despachar configuración por flujo con YAML fijo desde CLI.
- Prevenir cargas duplicadas mediante validaciones en lote y en tabla destino.

## Estructura principal

```text
load/
	main.py
	config/
		psg.yaml
	secrets/
	requirements.txt
```

## Configuración

La configuración se resuelve por flujo:

- `--flow psg` -> `load/config/psg.yaml`

Campos relevantes del YAML:

- destino BQ (`project_id`, `dataset_id`, `table_id`)
- modo de escritura (`write_disposition`)
- rutas de insumo (`source_excel_path`, `schema_yaml_path`)
- campos operativos (`uuid_field`, `date_field`, `migrated_field`)

## Autenticación

Service Account local por capa:

- `load/secrets/obsino-clisueno.json`

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

Desde la raíz del proyecto:

```bash
/home/rom/obsino/clisueno/.venv/bin/python load/main.py --flow psg
```

El script muestra configuración activa y solicita confirmación por teclado antes de cargar.

## Dependencias

```bash
/home/rom/obsino/clisueno/.venv/bin/pip install -r load/requirements.txt
```

## Control de versiones

El versionado de la capa `load` se gestiona desde la raíz del repositorio:

- `CHANGELOG.md`
- `vX.Y.Z` (archivo marcador de versión actual)