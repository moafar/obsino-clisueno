# Capa declarations

## Guía rápida de ejecución

Contexto: esta capa no tiene entrypoint propio; define contratos YAML consumidos por `transform` y `load`.

```bash
source .venv/bin/activate

# Validar uso con transform (ejemplo PSG)
.venv/bin/python 2_transform/main.py --flow psg --input staging/extract_psg_YYYY-MM-DD_HH-MM.csv --dry-run

# Validar uso con load (ejemplo)
.venv/bin/python 3_load/main.py --flow psg --table-id TABLA_AUTORIZADA --input staging/extract_psg_YYYY-MM-DD_HH-MM_transformed.parquet
```

Fuente única de verdad para contratos compartidos entre capas del ETL.

## ¿Por qué existe `0_declarations`?

- Evita duplicación de schemas entre `2_transform` y `3_load`.
- Reduce desalineaciones de columnas/tipos al promover un contrato único por subproceso.
- Facilita mantenimiento: el cambio de contrato se hace una vez y se propaga por referencia.
- Mejora trazabilidad: el contrato queda versionado junto al código.

## ¿Qué guarda esta carpeta?

- Archivos YAML por subproceso, por ejemplo:
  - `0_declarations/psg.yaml`
  - `0_declarations/xpap.yaml`
- Cada YAML define, como mínimo:
  - `schema.transform.input.columns`
  - `schema.transform.output.columns`
  - `schema.load.input.columns`

En el caso de `psg`, `load.input.columns` reutiliza `transform.output.columns` para garantizar equivalencia 1:1.

## ¿Cómo se usa en `transform`?

Las CLI actuales consumen directamente las secciones `transform` y `schema.transform` de este YAML. PSG lee CSV y publica Parquet; XPAP mantiene su salida XLSX. Para configuraciones declarativas externas también se admiten las referencias:

- `declarations.input_schema_yaml_path`
- `declarations.input_schema_path_in_yaml`
- `declarations.output_schema_yaml_path`
- `declarations.output_schema_path_in_yaml`

Ejemplo típico:

- YAML origen: `0_declarations/<subproceso_ejemplo>.yaml`
- path entrada: `schema.transform.input.columns`
- path salida: `schema.transform.output.columns`

## ¿Cómo se usa en `load`?

La CLI actual usa la sección `load` y `schema.load.input.columns` del mismo YAML. PSG declara `load.input_format: parquet`. En configuraciones externas siguen disponibles las referencias:

- `shared_schema_yaml_path` (o `schema_yaml_path`)
- `schema_path_in_yaml`

Ejemplo típico:

- YAML origen: `0_declarations/<subproceso_ejemplo>.yaml`
- path consumido: `schema.load.input.columns`

## Flujo recomendado de cambios

1. Actualizar contrato en `0_declarations/<subproceso>.yaml`.
2. Ajustar transformaciones en `2_transform/<subproceso>/` si cambian columnas o tipos.
3. Validar `2_transform` con `--dry-run`.
4. Validar `3_load` con el `--flow` correspondiente antes de cargar.

Flows activos en el repositorio: `psg`, `xpap`.

## Convenciones

- Mantener nombres y tipos consistentes entre `transform.output` y `load.input`.
- Preferir reutilización por anclas/alias YAML cuando aplique.
- Evitar rutas absolutas en declaraciones y configs que lo consumen.

PSG no declara ubicaciones documentales: extracción requiere `--input` y `--archive-dest`; el aislamiento test declara raíces mediante `--protected-root` repetible. Staging/logs permanecen relativos al repositorio. XPAP conserva su configuración.
