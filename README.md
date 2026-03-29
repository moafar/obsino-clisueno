# clisueno ETL

## Guía rápida de ejecución

Contexto: ejecutar desde la raíz del repo con entorno virtual activo.

```bash
source .venv/bin/activate

# 1) Extract
cd 1_extract && ../.venv/bin/python main.py --flow psg --input /ruta/de/entrada

# 2) Transform (ejemplo PSG)
cd ../2_transform && ../.venv/bin/python main.py --flow psg --input ../staging/extract_psg_YYYY-MM-DD_HH-MM.csv

# 3) Load
cd ../../3_load && ../.venv/bin/python main.py --flow <subproceso_ejemplo> --input ../staging/extract_<subproceso_ejemplo>_YYYY-MM-DD_HH-MM_transformed.xlsx
```

Proyecto ETL modular para procesamiento clínico de estudios de sueño, organizado en tres capas independientes:

- `1_extract`: extracción y estandarización inicial desde fuentes de documentos.
- `2_transform`: transformación declarativa por pipeline de dominio (ej. `subproceso_respiratorio`, `subproceso_actigrafia`).
- `3_load`: carga manual controlada a BigQuery con validaciones previas.
- `0_declarations`: contratos compartidos (schemas/metadata) reutilizables entre capas.

Flows disponibles actualmente: `psg`, `xpap`.

## Arquitectura general

```text
clisueno/
    1_extract/
    2_transform/
    3_load/
    0_declarations/
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

- `1_extract/README.md`

## 2) Capa `transform`

Responsabilidad:

- Aplicar reglas declarativas (schema + steps) para convertir datasets base en datasets analíticos.
- Validar esquema de entrada y salida.
- Ejecutar pipelines por subdominio clínico (ej. `subproceso_respiratorio`, `subproceso_actigrafia`).

Entrada/salida esperada:

- Entrada: dataset estructurado desde `extract`.
- Salida: dataset transformado listo para `load`.

Referencia de detalle:

- `2_transform/README.md`

## 3) Capa `load`

Responsabilidad:

- Cargar manualmente a BigQuery con control de ejecución por consola.
- Mostrar configuración activa y solicitar confirmación humana.
- Validar duplicados en lote y contra tabla destino (modo `WRITE_APPEND`).

Entrada/salida esperada:

- Entrada: archivos tabulares finales + configuración YAML por flujo.
- Salida: inserción en tabla BigQuery objetivo.

Referencia de detalle:

- `3_load/README.md`

## 4) Capa `declarations`

Responsabilidad:

- Centralizar contratos compartidos de schema por subproceso.
- Mantener consistencia entre `transform.output` y `load.input`.
- Evitar duplicación de definiciones YAML entre capas.

Referencia de detalle:

- `0_declarations/README.md`

## Flujo operativo end-to-end

1. Ejecutar `1_extract` para generar dataset base en `staging/` con nombre `extract_<flow>_YYYY-MM-DD_HH-MM.csv`.

2. Ejecutar `2_transform` para leer automáticamente desde `staging/` (filtrando por `extract_<flow>_...`) y generar salida con el sufijo `_transformed`.

3. Ejecutar `3_load` para tomar el archivo `..._transformed` desde `staging/` (por `--input` o autodiscovery), cargar en BigQuery y renombrar a `..._transformed_loaded` en la misma carpeta.

Comandos base:

```bash
# Desde 1_extract/
python3 main.py --flow psg --input /ruta/de/la/carpeta

# Desde raíz del proyecto
./.venv/bin/python 2_transform/main.py --flow <subproceso_ejemplo> --dry-run
./.venv/bin/python 3_load/main.py --flow <subproceso_ejemplo> --input staging/extract_<subproceso_ejemplo>_YYYY-MM-DD_HH-MM_transformed.xlsx
# Alternativa posicional para load
./.venv/bin/python 3_load/main.py --flow <subproceso_ejemplo> staging/extract_<subproceso_ejemplo>_YYYY-MM-DD_HH-MM_transformed.xlsx
```

Modos de ejecución relevantes:

- `1_extract`: completo (default), `--no-process`, `--no-unify`, `--dry-run`.
- `2_transform`: ejecución por archivo o autodiscovery en `staging/` filtrando por flow; `--dry-run` sin escritura.
- `3_load`: ejecución manual por `--flow` con confirmación interactiva previa.

Chuleta rápida:

| Capa | Comando ejemplo | Efecto |
|---|---|---|
| `extract` | `python3 main.py --flow <subproceso_ejemplo> --input /ruta/de/la/carpeta` *(desde `1_extract/`)* | Procesa + unifica (default). |
| `transform` | `./.venv/bin/python 2_transform/main.py --flow <subproceso_ejemplo> --dry-run` | Valida y transforma sin escribir salida. |
| `load` | `./.venv/bin/python 3_load/main.py --flow <subproceso_ejemplo> --input staging/extract_<subproceso_ejemplo>_YYYY-MM-DD_HH-MM_transformed.xlsx` | Carga manual con confirmación previa. |
| `load` (posicional) | `./.venv/bin/python 3_load/main.py --flow <subproceso_ejemplo> staging/extract_<subproceso_ejemplo>_YYYY-MM-DD_HH-MM_transformed.xlsx` | Igual que el anterior, pasando el Excel como argumento posicional. |

Ejemplos de nombre de subproceso para documentar/estandarizar comandos:

- `subproceso_respiratorio`
- `subproceso_actigrafia`

## Convenciones del repositorio

- Aislamiento por capa: `1_extract`, `2_transform` y `3_load` evolucionan de forma independiente, compartiendo `staging/` como area de handoff lineal.
- Logs centralizados: las tres capas escriben en `/home/rom/obsino/clisueno/logs`.
    - `1_extract`: `extract_<flow>_YYYY-MM-DD_HH-MM-SS.log`
    - `2_transform`: `transform_<flow>_YYYY-MM-DD_HH-MM-SS.log`
    - `3_load`: `load_<flow>_YYYY-MM-DD_HH-MM-SS.log`
- Contratos compartidos: `0_declarations/` define schemas reutilizables para evitar duplicación entre capas.
- Configuración declarativa: YAML por pipeline/flujo cuando aplica.
- Ejecución manual controlada en `load` para minimizar riesgo operativo en cargas.

## Requisitos generales

- Entorno virtual Python (`.venv`).
- Dependencias por capa (`1_extract/requirements.txt`, `2_transform/requirements.txt`, `3_load/requirements.txt`).
- Credenciales GCP para `load` en:
    - `3_load/secrets/obsino-clisueno.json`

### [v4.1.1] Corrección definitiva de rutas de salida y limpieza de depuración

- Los archivos de salida de `extract` (`extract_<flow>_<timestamp>.csv`) se generan siempre en la carpeta `staging/` bajo la raíz del proyecto, sin importar la configuración YAML ni el contexto de ejecución.
- Se elimina la posibilidad de rutas duplicadas o ambiguas.
- Se eliminan todos los mensajes de depuración en pantalla; el logging queda centralizado en archivos de log.
- Ver detalles en el CHANGELOG y en los README de cada capa.
