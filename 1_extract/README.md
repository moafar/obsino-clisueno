# Capa extract

## Guía rápida de ejecución

Contexto: ejecutar desde la raíz del repo o desde `1_extract/` con `.venv` activo.

```bash
source .venv/bin/activate
cd 1_extract
../.venv/bin/python main.py --flow psg --input /ruta/de/la/carpeta
```

Prueba rápida con carpeta del repo:

```bash
cd /home/rom/obsino/clisueno/1_extract
../.venv/bin/python main.py --flow psg --input ./test_files
```

Extracción estructurada desde reportes clínicos de laboratorio de sueño.

## Objetivo

- Recorrer una carpeta de entrada con archivos clínicos.
- Extraer campos relevantes por tipo de estudio.
- Generar salidas tabulares y trazabilidad de ejecución.

## Entradas y salidas

- Entrada: directorio configurado en `1_extract/config/<flow>.yaml` (`entrada.ruta`) o por CLI.
- Salida de procesamiento: archivo CSV en `staging/` (por defecto) con nombre `extract_<flow>_{timestamp}.csv` (ejemplo: `extract_psg_2026-03-29_14-19.csv`).
- Salida de trazabilidad: logs en `/home/rom/obsino/clisueno/logs`.
    - Convencion: `extract_<flow>_YYYY-MM-DD_HH-MM-SS.log`.

Flows disponibles actualmente: `psg`, `xpap`.

## Estructura principal

```text
1_extract/
    main.py
    config/
        psg.yaml
    commons/
        directorio_utils.py
        unificar_resultados.py
    src/
    ../staging/
    ../procesados/
    ../logs/  # /home/rom/obsino/clisueno/logs
```

## Configuración

Archivo principal por flujo:

- `1_extract/config/<flow>.yaml`

Secciones clave:

- `entrada.ruta`: carpeta a procesar.
- `procesamiento.tipos_validos`: extensiones permitidas.
- `procesamiento.glob_patron`: patrón de búsqueda.
- `salida.carpeta_csv`: carpeta para consolidación/unificación.
- `logging.level`: nivel de log.

## Ejecución

Chuleta operativa (desde `1_extract/`):

| Comando | Efecto |
|---|---|
| `python3 main.py --flow psg --input /ruta/de/la/carpeta` | Modo completo: procesa y luego unifica. |
| `python3 main.py --flow psg /ruta/de/la/carpeta` | Igual que el anterior usando argumento posicional (compatibilidad). |
| `python3 main.py --flow psg --input /ruta/de/la/carpeta --no-unify` | Solo procesamiento (sin unificación). |
| `python3 main.py --flow psg --no-process` | Solo unificación usando `salida.carpeta_csv` del YAML del flujo. |
| `python3 main.py --flow psg --input /ruta/de/la/carpeta --dry-run` | Simulación: valida parámetros/configuración sin ejecutar acciones. |
| `python3 main.py --flow psg --input /ruta/de/la/carpeta -v` | Modo verbose (logging en DEBUG). |

Forma recomendada (desde `1_extract/`):

```bash
python3 main.py --flow psg --input /ruta/de/la/carpeta
```

Alternativa posicional (compatibilidad):

```bash
python3 main.py --flow psg /ruta/de/la/carpeta
```

Alternativa desde la raíz del proyecto:

```bash
./.venv/bin/python 1_extract/main.py --flow psg
```

Con directorio explícito por CLI (desde raíz):

```bash
./.venv/bin/python 1_extract/main.py --flow psg --input /ruta/a/entrada
```

Con `--input` explícito (recomendado):

```bash
./.venv/bin/python 1_extract/main.py --flow psg --input /ruta/a/entrada
```

Modos de ejecución soportados:

- Completo (por defecto): procesa y luego unifica.
- Solo unificación: `--no-process`.
- Solo procesamiento: `--no-unify`.
- Simulación: `--dry-run` (valida parámetros y configuración sin ejecutar acciones).

Dry-run:

```bash
python3 main.py --flow psg --input /ruta/de/la/carpeta --dry-run
```

Solo unificación:

```bash
python3 main.py --flow psg --no-process
```

Solo procesamiento:

```bash
python3 main.py --flow psg --input /ruta/de/la/carpeta --no-unify
```

Modo verbose (más detalle de logs):

```bash
python3 main.py --flow psg --input /ruta/de/la/carpeta -v
```

## Dependencias

Instalación:

```bash
./.venv/bin/pip install -r 1_extract/requirements.txt
```

Dependencia de sistema requerida para `.doc`:

```bash
sudo apt install catdoc
```

## Notas operativas

- El proceso registra errores por archivo sin detener toda la corrida.
- Se soporta ejecución parcial (`--no-process`, `--no-unify`) según necesidad operativa.
- La opción `-v`/`--verbose` aumenta el detalle de logging (nivel DEBUG).
- Los archivos procesados se archivan en `procesados/` en la raiz del repositorio (no depende del `cwd`).

### [v4.1.1] Cambios recientes

- La salida de procesamiento (`extract_<flow>_<timestamp>.csv`) se genera siempre en `staging/` bajo la raíz del proyecto, sin importar la configuración YAML.
- Se eliminan todos los prints de depuración en pantalla; solo queda logging a archivo.
