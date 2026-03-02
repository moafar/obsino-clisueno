# clisueno ETL

## Guía rápida de ejecución

Contexto: ejecutar desde la raíz del repo con entorno virtual activo.

```bash
source .venv/bin/activate

# 1) Extract
cd 1_extract && ../.venv/bin/python main.py /ruta/de/entrada

# 2) Transform (ejemplo PSG)
cd ../2_transform/psg && ../../.venv/bin/python main.py --input input/unificado_basal.csv

# 3) Load
cd ../../3_load && ../.venv/bin/python main.py --flow <subproceso_ejemplo> --input input/archivo_ready-to-load.xlsx
```

Proyecto ETL modular para procesamiento clínico de estudios de sueño, organizado en tres capas independientes:

- `1_extract`: extracción y estandarización inicial desde fuentes de documentos.
- `2_transform`: transformación declarativa por pipeline de dominio (ej. `subproceso_respiratorio`, `subproceso_actigrafia`).
- `3_load`: carga manual controlada a BigQuery con validaciones previas.
- `0_declarations`: contratos compartidos (schemas/metadata) reutilizables entre capas.

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

1. Ejecutar `1_extract` para generar dataset base. Los CSV resultantes quedan en `1_extract/output`. Los archivos procesados se mueven a `1_extract/procesados`.

2. Mover el archivo CSV a `2_transform/input`.

3. Ejecutar `2_transform` para obtener dataset estandarizado por pipeline. El resultado en XLSX queda en `2_transform/<subproceso>/output` con el sufijo `_ready-to-load.xlsx`.

4. Mover el XLSX a `3_load/input`.

5. Ejecutar `3_load` para validar y cargar en BigQuery.

Comandos base:

```bash
# Desde 1_extract/
python3 main.py /ruta/de/la/carpeta

# Desde raíz del proyecto
./.venv/bin/python 2_transform/<subproceso_ejemplo>/main.py --dry-run
./.venv/bin/python 3_load/main.py --flow <subproceso_ejemplo> --input 3_load/input/archivo_ready-to-load.xlsx
# Alternativa posicional para load
./.venv/bin/python 3_load/main.py --flow <subproceso_ejemplo> 3_load/input/archivo_ready-to-load.xlsx
```

Modos de ejecución relevantes:

- `1_extract`: completo (default), `--no-process`, `--no-unify`, `--dry-run`.
- `2_transform`: ejecución por archivo o autodiscovery en `input/`; `--dry-run` sin escritura.
- `3_load`: ejecución manual por `--flow` con confirmación interactiva previa.

Chuleta rápida:

| Capa | Comando ejemplo | Efecto |
|---|---|---|
| `extract` | `python3 main.py /ruta/de/la/carpeta` *(desde `1_extract/`)* | Procesa + unifica (default). |
| `transform` | `./.venv/bin/python 2_transform/<subproceso_ejemplo>/main.py --dry-run` | Valida y transforma sin escribir salida. |
| `load` | `./.venv/bin/python 3_load/main.py --flow <subproceso_ejemplo> --input 3_load/input/archivo_ready-to-load.xlsx` | Carga manual con confirmación previa. |
| `load` (posicional) | `./.venv/bin/python 3_load/main.py --flow <subproceso_ejemplo> 3_load/input/archivo_ready-to-load.xlsx` | Igual que el anterior, pasando el Excel como argumento posicional. |

Ejemplos de nombre de subproceso para documentar/estandarizar comandos:

- `subproceso_respiratorio`
- `subproceso_actigrafia`

## Convenciones del repositorio

- Aislamiento por capa: `1_extract`, `2_transform` y `3_load` evolucionan de forma independiente.
- Contratos compartidos: `0_declarations/` define schemas reutilizables para evitar duplicación entre capas.
- Configuración declarativa: YAML por pipeline/flujo cuando aplica.
- Ejecución manual controlada en `load` para minimizar riesgo operativo en cargas.

## Requisitos generales

- Entorno virtual Python (`.venv`).
- Dependencias por capa (`1_extract/requirements.txt`, `2_transform/requirements.txt`, `3_load/requirements.txt`).
- Credenciales GCP para `load` en:
    - `3_load/secrets/obsino-clisueno.json`
