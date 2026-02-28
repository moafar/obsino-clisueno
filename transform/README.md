# Capa transform

Transformación declarativa de datasets clínicos entre `extract` y `load`.

## Objetivo

- Estandarizar y enriquecer datasets estructurados.
- Aplicar reglas declarativas reproducibles por pipeline.
- Garantizar calidad mediante validación de esquema de entrada y salida.

## Estructura principal

```text
transform/
  commons/
  requirements.txt
  psg/
    config.yaml
    main.py
    core/
    input/
    output/
```

- `commons/`: motor genérico de pipeline (I/O, validadores, operaciones, runner).
- `<pipeline>/`: implementación de dominio (actualmente `psg`).

## Flujo estándar

1. Leer input (`xlsx` o `csv`).
2. Validar esquema de entrada.
3. Ejecutar transformaciones declarativas (`steps`).
4. Validar esquema de salida.
5. Escribir dataset procesado.

## Configuración

Cada pipeline define su contrato en:

- `transform/<pipeline>/config.yaml`

Secciones clave:

- `input`: parámetros de lectura.
- `schema.input`: columnas y tipos esperados.
- `steps`: secuencia de operaciones.
- `schema.output`: contrato de salida.
- `output`: parámetros de escritura.

## Pipeline activo: PSG

Entrypoint:

- `transform/psg/main.py`

Comandos desde raíz del proyecto:

```bash
/home/rom/obsino/clisueno/.venv/bin/python transform/psg/main.py --dry-run
```

```bash
/home/rom/obsino/clisueno/.venv/bin/python transform/psg/main.py \
  --config transform/psg/config.yaml \
  --input transform/psg/input/unificado_basal.csv \
  --output transform/psg/output/processed.xlsx
```

## Dependencias

```bash
/home/rom/obsino/clisueno/.venv/bin/pip install -r transform/requirements.txt
```

## Extensión a nuevos pipelines

Crear `transform/<nuevo_pipeline>/` con:

- `config.yaml`
- `main.py`
- `core/`
- `input/`
- `output/`

Luego ejecutar:

```bash
/home/rom/obsino/clisueno/.venv/bin/python transform/<nuevo_pipeline>/main.py --dry-run
```

## Control de versiones

El versionado de `transform` se registra en el control global del proyecto (raíz):

- `CHANGELOG.md`
- `vX.Y.Z` (marcador de versión vigente)
