# Capa transform

## Guía rápida de ejecución

Contexto: ejecutar desde la raíz del repo o desde `2_transform/psg` con `.venv` activo.

```bash
source .venv/bin/activate

# Ejecución normal (PSG)
cd 2_transform
../.venv/bin/python main.py --flow psg --input ../staging/extract_psg_YYYY-MM-DD_HH-MM.csv
```

Prueba rápida (dry-run):

```bash
cd 2_transform
../.venv/bin/python main.py --flow psg --input ../staging/extract_psg_YYYY-MM-DD_HH-MM.csv --dry-run
```

Transformación declarativa de datasets clínicos entre `extract` y `load`.

## Objetivo

- Estandarizar y enriquecer datasets estructurados.
- Aplicar reglas declarativas reproducibles por pipeline.
- Garantizar calidad mediante validación de esquema de entrada y salida.

## Estructura principal

```text
2_transform/
  commons/
  requirements.txt
  psg/
  xpap/
  <flow>/
    config.yaml
    main.py
    core/
```

- `commons/`: motor genérico de pipeline (I/O, validadores, operaciones, runner).
- `<flow>/`: implementación de dominio por flujo clínico.
- `staging/` (en raiz del repo): area compartida de entrada/salida entre capas.

## Flujo estándar

1. Leer input (`xlsx` o `csv`).
2. Validar esquema de entrada.
3. Ejecutar transformaciones declarativas (`steps`).
4. Limpiar duplicados por `UUID` (se conserva la primera fila por UUID, cuando exista esa columna).
5. Validar esquema de salida.
6. Escribir dataset procesado.

## Configuración

Cada pipeline define su contrato en:

- `2_transform/<subproceso_ejemplo>/config.yaml`

Secciones clave:

- `input`: parámetros de lectura.
- `schema.input`: columnas y tipos esperados.
- `steps`: secuencia de operaciones.
- `schema.output`: contrato de salida (inyectado desde `0_declarations/` cuando aplica).
- `output`: parámetros de escritura.

Contrato compartido por subproceso:

- `2_transform/<subproceso_ejemplo>/config.yaml` declara el puntero del contrato.
- `0_declarations/<subproceso_ejemplo>.yaml` contiene:
  - `schema.transform.input.columns`
  - `schema.transform.output.columns` (mismo contrato que `schema.load.input.columns`)

Ejemplos de nombres de subproceso:

- `subproceso_respiratorio`
- `subproceso_actigrafia`

## Pipeline por subproceso (ejemplo)

Entrypoints:

- `2_transform/main.py` (unificado por `--flow`)
- `2_transform/<flow>/main.py` (compatibilidad)

Flows disponibles actualmente:

- `psg`: implementado.
- `xpap`: implementado.

Chuleta operativa (desde raíz del proyecto):

| Comando | Efecto |
|---|---|
| `./.venv/bin/python 2_transform/main.py --flow <subproceso_ejemplo>` | Auto-discovery de archivos válidos en `staging/`, filtrados por `extract_<flow>_...`. |
| `./.venv/bin/python 2_transform/main.py --flow <subproceso_ejemplo> --dry-run` | Valida y transforma sin escribir salida. |
| `./.venv/bin/python 2_transform/main.py --flow <subproceso_ejemplo> --input staging/extract_<subproceso_ejemplo>_YYYY-MM-DD_HH-MM.csv` | Procesa un archivo específico. |
| `./.venv/bin/python 2_transform/main.py --flow <subproceso_ejemplo> staging/extract_<subproceso_ejemplo>_YYYY-MM-DD_HH-MM.csv` | Procesa un archivo específico usando argumento posicional. |
| `./.venv/bin/python 2_transform/main.py --flow <subproceso_ejemplo> --output staging/mi_archivo.xlsx` | Fuerza ruta/nombre de salida. |

Comandos desde raíz del proyecto:

```bash
./.venv/bin/python 2_transform/main.py --flow <subproceso_ejemplo> --dry-run
```

```bash
./.venv/bin/python 2_transform/main.py \
  --flow <subproceso_ejemplo> \
  --config 2_transform/<subproceso_ejemplo>/config.yaml \
  --input staging/extract_<subproceso_ejemplo>_YYYY-MM-DD_HH-MM.csv
```

Comando desde `2_transform/`:

```bash
../.venv/bin/python main.py --flow <subproceso_ejemplo>
```

Modos de ejecución soportados:

- Auto-discovery (por defecto): si no se pasa `--input`, procesa todos los archivos válidos de ese flow en `staging/`.
- Archivo específico: usar `--input <ruta_archivo>`.
- Salida automática (por defecto): si no se pasa `--output`, genera `<input>_transformed` en `staging/`.
- Salida explícita: usar `--output <ruta_salida>`.
- Simulación: `--dry-run` ejecuta validaciones/transformaciones sin escribir archivo.

Entrada por defecto:

- Si no se pasa `--input`, el runner procesa automáticamente todos los archivos válidos (`.csv`, `.xlsx`, `.xls`) que encuentre en `staging/` y correspondan al flow (`extract_<flow>_...`).
- Si quieres procesar uno específico, usa `--input <ruta_archivo>`.

Salida por defecto:

- Si no se pasa `--output`, el runner genera automáticamente el nombre como:
  - `<nombre_input>_transformed.<extensión>`
- La extensión se define con `output.format` en `config.yaml` (`xlsx` o `csv`).
- Para el input `extract_psg_YYYY-MM-DD_HH-MM.csv`, la salida será:
  - `staging/extract_psg_YYYY-MM-DD_HH-MM_transformed.xlsx`

Si necesitas forzar una ruta/nombre de salida:

```bash
./.venv/bin/python 2_transform/main.py \
  --flow <subproceso_ejemplo> \
  --output staging/mi_archivo.xlsx
```

## Notas operativas

- El runner admite entrada `csv`, `xlsx` y `xls`.
- Si no se especifica `--output`, el nombre se genera como `<input>_transformed`.
- El formato final se define con `output.format` en `config.yaml`.

## Dependencias

```bash
./.venv/bin/pip install -r 2_transform/requirements.txt
```

## Extensión a nuevos pipelines

Crear `2_transform/<nuevo_flow>/` con:

- `config.yaml`
- `main.py`
- `core/`

Luego ejecutar:

```bash
./.venv/bin/python 2_transform/main.py --flow <nuevo_flow> --dry-run
```

Logs de esta capa:

- Carpeta: `/home/rom/obsino/clisueno/logs`
- Convencion: `transform_<flow>_YYYY-MM-DD_HH-MM-SS.log`
