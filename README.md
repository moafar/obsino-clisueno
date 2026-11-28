# clisueno ETL

## Guía rápida de ejecución

Contexto: ejecutar desde la raíz del repo con entorno virtual activo.

```bash
source .venv/bin/activate

# PSG: rutas y destino explícitos; este comando procesa y mueve documentos.
.venv/bin/python scripts/run_psg.py --input /ruta/origen \
  --archive-dest /ruta/archivo --mount /mnt/letra --table-id TABLA_AUTORIZADA

# Reanudación explícita de la misma ejecución.
.venv/bin/python scripts/run_psg.py --resume ID_EJECUCION
```

PSG conserva CSV crudo y publica Parquet tipado (PyArrow/Snappy). Documentos y archivo
permanecen en NTFS; staging y estados, en Linux nativo de WSL2. XPAP mantiene XLSX.
La validación operativa y el despliegue requieren autorización; protocolo, limitaciones
y propuesta v6.0.0 en [PT07](docs/pt07_validacion_despliegue.md). El marcador vigente
continúa siendo v5.0.1 en `CHANGELOG.md`.

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
- Registrar rechazos individuales y advertencias; detener PSG ante errores técnicos bloqueantes.

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
- Mostrar configuración y confirmar por defecto; el orquestador PSG usa el modo no interactivo explícito.
- Validar duplicados internos; PSG omite UUID ya existentes, concilia `output_rows` y recupera cargas inciertas mediante journals.

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

PSG diario usa `scripts/run_psg.py`, que incluye la auditoría dentro de extracción, enlaza rutas explícitas y conserva un registro JSON por ejecución. La ejecución manual por capas sigue disponible:

1. Ejecutar `1_extract` para generar dataset base en `staging/` con nombre `extract_<flow>_YYYY-MM-DD_HH-MM.csv`.

2. Ejecutar `2_transform` para leer automáticamente desde `staging/` (filtrando por `extract_<flow>_...`) y generar salida con el sufijo `_transformed`.

3. Ejecutar `3_load` para tomar el archivo `..._transformed` desde `staging/` (por `--input` o autodiscovery), cargar en BigQuery y renombrar a `..._transformed_loaded` en la misma carpeta.

Comandos base:

```bash
# Desde 1_extract/
python3 main.py --flow psg --input /ruta/de/la/carpeta

# Desde raíz del proyecto
./.venv/bin/python 2_transform/main.py --flow <subproceso_ejemplo> --dry-run
./.venv/bin/python 3_load/main.py --flow psg --table-id TABLA_AUTORIZADA --input staging/extract_psg_YYYY-MM-DD_HH-MM_transformed.parquet
# Alternativa posicional para load
./.venv/bin/python 3_load/main.py --flow psg --table-id TABLA_AUTORIZADA staging/extract_psg_YYYY-MM-DD_HH-MM_transformed.parquet
```

Modos de ejecución relevantes:

- `1_extract`: PSG siempre procesa y audita; `--dry-run` no ejecuta el procesamiento. Las opciones de unificación y `--no-process` corresponden al flujo XPAP.
- `2_transform`: ejecución por archivo o autodiscovery en `staging/` filtrando por flow; `--dry-run` sin escritura.
- `3_load`: ejecución manual por `--flow` con confirmación previa; PSG admite `--yes`, preservando el bloqueo compartido y el journal de carga.

Chuleta rápida:

| Capa | Comando ejemplo | Efecto |
|---|---|---|
| `extract` | `python3 main.py --flow <subproceso_ejemplo> --input /ruta/de/la/carpeta` *(desde `1_extract/`)* | Procesa + unifica (default). |
| `transform` | `./.venv/bin/python 2_transform/main.py --flow <subproceso_ejemplo> --dry-run` | Valida y transforma sin escribir salida. |
| `load` | `./.venv/bin/python 3_load/main.py --flow psg --table-id TABLA_AUTORIZADA --input staging/extract_psg_YYYY-MM-DD_HH-MM_transformed.parquet` | Carga manual con confirmación previa. |
| `load` (posicional) | `./.venv/bin/python 3_load/main.py --flow psg --table-id TABLA_AUTORIZADA staging/extract_psg_YYYY-MM-DD_HH-MM_transformed.parquet` | Igual que el anterior, pasando el artefacto como argumento posicional. |

Ejemplos de nombre de subproceso para documentar/estandarizar comandos:

- `subproceso_respiratorio`
- `subproceso_actigrafia`

## Convenciones del repositorio

- Aislamiento por capa: `1_extract`, `2_transform` y `3_load` evolucionan de forma independiente, compartiendo `staging/` como area de handoff lineal.
- Logs centralizados: las tres capas escriben en `logs/` bajo la raíz de la instalación.
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
    - `3_load/secrets/obsino_clisueno_key.json`

### [v4.1.1] Corrección definitiva de rutas de salida y limpieza de depuración

- Los archivos de salida de `extract` (`extract_<flow>_<timestamp>.csv`) se generan siempre en la carpeta `staging/` bajo la raíz del proyecto, sin importar la configuración YAML ni el contexto de ejecución.
- Se elimina la posibilidad de rutas duplicadas o ambiguas.
- Se eliminan todos los mensajes de depuración en pantalla; el logging queda centralizado en archivos de log.
- Ver detalles en el CHANGELOG y en los README de cada capa.

## Ejecución de pruebas PSG

Las suites utilizan procesos separados porque existen módulos de prueba con el mismo nombre en distintas capas. Ejecutar una sola batería con estas cuatro invocaciones desde la raíz:

```bash
PYTHONPATH=1_extract .venv/bin/python -m unittest discover -s 1_extract/tests
PYTHONPATH=1_extract:2_transform .venv/bin/python -m unittest discover -s 2_transform/tests
PYTHONPATH=1_extract:2_transform .venv/bin/python -m unittest discover -s 3_load/tests
.venv/bin/python -m unittest discover -s scripts/tests
```

Incluyen las regresiones XPAP y la recuperación PSG, sin BigQuery real.

**Resultado histórico de referencia (24/11/2026):**
29 pruebas y 283 subpruebas superadas.

Estas pruebas utilizan datos sintéticos y clientes simulados; no realizan
cargas reales en BigQuery. Los resultados de la validación candidata se registran en PT07.
