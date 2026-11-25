# Capa extract

## Guía rápida de ejecución

Contexto: ejecutar desde la raíz del repositorio con `.venv` activo.

```bash
source .venv/bin/activate
./.venv/bin/python 1_extract/main.py --flow psg --dry-run
```

Prueba PSG con directorios aislados y documentos sintéticos:

```bash
mkdir -p /tmp/psg-test-01/{entrada,archivo,csv}
touch /tmp/psg-test-01/.psg-test-root
./.venv/bin/python 1_extract/main.py --flow psg --mode test \
  --test-root /tmp/psg-test-01 --input /tmp/psg-test-01/entrada \
  --archive-dest /tmp/psg-test-01/archivo --output-dir /tmp/psg-test-01/csv
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
| `python3 main.py --flow psg --input /ruta/de/la/carpeta` | Modo normal: confirma, procesa y archiva en el destino configurado. |
| `python3 main.py --flow psg /ruta/de/la/carpeta` | Igual que el anterior usando argumento posicional (compatibilidad). |
| `python3 main.py --flow psg --input /ruta/de/la/carpeta --no-unify` | Solo procesamiento (sin unificación). |
| `python3 main.py --flow xpap --no-process` | Opción parcial conservada para XPAP. |
| `python3 main.py --flow psg --input /ruta/de/la/carpeta --dry-run` | Valida y muestra configuración sin extraer, escribir ni mover. |
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
- Se soporta ejecución parcial (`--no-process`, `--no-unify`) para los flujos que la admiten; PSG requiere procesamiento.
- La opción `-v`/`--verbose` aumenta el detalle de logging (nivel DEBUG).
- PSG archiva en el destino Windows configurado en `0_declarations/psg.yaml`; no usa `procesados/` como alternativa. Los demás flujos conservan su destino anterior.

### Archivado PSG

En modo normal, el YAML define el origen `/mnt/e/RESULTADOS`, el destino
`/mnt/e/RESULTADOS/RESULTADOS_OBSERVATORIO` y la salida CSV `staging/`.
`--input` permite otro origen del mismo dispositivo, incluido el reproceso histórico:

```bash
./.venv/bin/python 1_extract/main.py --flow psg --mode normal --dry-run
./.venv/bin/python 1_extract/main.py --flow psg --mode normal \
  --input /mnt/e/RESULTADOS_OBSERVATORIO_REPROCESO
```

La ejecución normal y la de prueba solicitan una confirmación antes de escribir o mover.
`--dry-run` valida y muestra la configuración sin solicitarla. El modo `test` exige
una raíz con `.psg-test-root` y rutas de entrada, archivo y CSV dentro de ella;
rechaza el solapamiento con las rutas clínicas configuradas. La salida de prueba
queda fuera del CSV ordinario.

El movimiento PSG usa `renameat2(RENAME_NOREPLACE)` cuando el volumen lo admite.
Si devuelve `EINVAL`, `ENOSYS` o `EOPNOTSUPP`, usa `os.link()` y después
`os.unlink()`, sin copiar contenido ni sobrescribir destinos. Si falla la
eliminación, ambos nombres permanecen enlazados; un reintento con UUID ya
registrado puede completar el traslado. La variante con descriptor de directorio
y la comprobación de identidad del enlace siguen pendientes de prueba en DrvFS.
Los UUID previos se leen una vez al inicio de cada ejecución. Un documento con
CSV registrado y traslado fallido solo se reintenta si conserva el mismo origen;
no se duplica su fila.
Si hubo fallos de archivado o errores al recorrer el origen, se muestra el resumen
y la ejecución termina con código no nulo; los documentos afectados permanecen en origen.

### [v4.1.1] Cambios recientes

- PSG usa la salida CSV configurada para el modo; los demás flujos respetan `salida.carpeta_csv` del YAML.
- Se eliminan todos los prints de depuración en pantalla; solo queda logging a archivo.
