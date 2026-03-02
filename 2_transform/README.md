# Capa transform

## Guía rápida de ejecución

Contexto: ejecutar desde la raíz del repo o desde `2_transform/psg` con `.venv` activo.

```bash
source .venv/bin/activate

# Ejecución normal (PSG)
cd 2_transform/psg
../../.venv/bin/python main.py --input input/unificado_basal.csv
```

Prueba rápida (dry-run):

```bash
cd 2_transform/psg
../../.venv/bin/python main.py --input input/unificado_basal.csv --dry-run
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
  <subproceso_ejemplo>/
    config.yaml
    main.py
    core/
    input/
    output/
```

- `commons/`: motor genérico de pipeline (I/O, validadores, operaciones, runner).
- `<subproceso>/`: implementación de dominio por flujo clínico.

## Flujo estándar

1. Leer input (`xlsx` o `csv`).
2. Validar esquema de entrada.
3. Ejecutar transformaciones declarativas (`steps`).
4. Validar esquema de salida.
5. Escribir dataset procesado.

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

Entrypoint:

- `2_transform/<subproceso_ejemplo>/main.py`

Chuleta operativa (desde raíz del proyecto):

| Comando | Efecto |
|---|---|
| `./.venv/bin/python 2_transform/<subproceso_ejemplo>/main.py` | Auto-discovery de archivos válidos en `input/`. |
| `./.venv/bin/python 2_transform/<subproceso_ejemplo>/main.py --dry-run` | Valida y transforma sin escribir salida. |
| `./.venv/bin/python 2_transform/<subproceso_ejemplo>/main.py --input 2_transform/<subproceso_ejemplo>/input/archivo_entrada.csv` | Procesa un archivo específico. |
| `./.venv/bin/python 2_transform/<subproceso_ejemplo>/main.py --output 2_transform/<subproceso_ejemplo>/output/mi_archivo.xlsx` | Fuerza ruta/nombre de salida. |

Comandos desde raíz del proyecto:

```bash
./.venv/bin/python 2_transform/<subproceso_ejemplo>/main.py --dry-run
```

```bash
./.venv/bin/python 2_transform/<subproceso_ejemplo>/main.py \
  --config 2_transform/<subproceso_ejemplo>/config.yaml \
  --input 2_transform/<subproceso_ejemplo>/input/archivo_entrada.csv
```

Comando desde `2_transform/`:

```bash
../.venv/bin/python <subproceso_ejemplo>/main.py
```

Modos de ejecución soportados:

- Auto-discovery (por defecto): si no se pasa `--input`, procesa todos los archivos válidos en `<subproceso_ejemplo>/input/`.
- Archivo específico: usar `--input <ruta_archivo>`.
- Salida automática (por defecto): si no se pasa `--output`, genera `<input>_ready-to-load` en `<subproceso_ejemplo>/output/`.
- Salida explícita: usar `--output <ruta_salida>`.
- Simulación: `--dry-run` ejecuta validaciones/transformaciones sin escribir archivo.

Entrada por defecto:

- Si no se pasa `--input`, el runner procesa automáticamente todos los archivos válidos (`.csv`, `.xlsx`, `.xls`) que encuentre en `2_transform/<subproceso_ejemplo>/input/`.
- Si quieres procesar uno específico, usa `--input <ruta_archivo>`.

Salida por defecto:

- Si no se pasa `--output`, el runner genera automáticamente el nombre como:
  - `<nombre_input>_ready-to-load.<extensión>`
- La extensión se define con `output.format` en `config.yaml` (`xlsx` o `csv`).
- Para el input `unificado_basal.csv`, la salida será:
  - `2_transform/<subproceso_ejemplo>/output/unificado_basal_ready-to-load.xlsx`

Si necesitas forzar una ruta/nombre de salida:

```bash
./.venv/bin/python 2_transform/<subproceso_ejemplo>/main.py \
  --output 2_transform/<subproceso_ejemplo>/output/mi_archivo.xlsx
```

## Notas operativas

- El runner admite entrada `csv`, `xlsx` y `xls`.
- Si no se especifica `--output`, el nombre se genera como `<input>_ready-to-load`.
- El formato final se define con `output.format` en `config.yaml`.

## Dependencias

```bash
./.venv/bin/pip install -r 2_transform/requirements.txt
```

## Extensión a nuevos pipelines

Crear `2_transform/<nuevo_subproceso>/` con:

- `config.yaml`
- `main.py`
- `core/`
- `input/`
- `output/`

Luego ejecutar:

```bash
./.venv/bin/python 2_transform/<nuevo_subproceso>/main.py --dry-run
```
