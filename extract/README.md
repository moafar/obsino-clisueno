# Capa extract

Extracción estructurada desde reportes clínicos de laboratorio de sueño.

## Objetivo

- Recorrer una carpeta de entrada con archivos clínicos.
- Extraer campos relevantes por tipo de estudio.
- Generar salidas tabulares y trazabilidad de ejecución.

## Entradas y salidas

- Entrada: directorio configurado en `extract/commons/config.yaml` (`entrada.ruta`) o por CLI.
- Salida de procesamiento: archivos CSV en rutas de salida configuradas.
- Salida de trazabilidad: logs en `extract/logs/`.

## Estructura principal

```text
extract/
    main.py
    commons/
        config.yaml
    src/
    output/
    procesados/
    logs/
```

## Configuración

Archivo principal:

- `extract/commons/config.yaml`

Secciones clave:

- `entrada.ruta`: carpeta a procesar.
- `procesamiento.tipos_validos`: extensiones permitidas.
- `procesamiento.glob_patron`: patrón de búsqueda.
- `salida.carpeta_csv`: carpeta para consolidación/unificación.
- `logging.level`: nivel de log.

## Ejecución

Desde la raíz del proyecto:

```bash
/home/rom/obsino/clisueno/.venv/bin/python extract/main.py -c extract/commons/config.yaml
```

Con directorio explícito por CLI:

```bash
/home/rom/obsino/clisueno/.venv/bin/python extract/main.py /ruta/a/entrada -c extract/commons/config.yaml
```

Dry-run (valida parámetros sin ejecutar procesamiento):

```bash
/home/rom/obsino/clisueno/.venv/bin/python extract/main.py -c extract/commons/config.yaml --dry-run
```

## Dependencias

Instalación:

```bash
/home/rom/obsino/clisueno/.venv/bin/pip install -r extract/requirements.txt
```

Dependencia de sistema requerida para `.doc`:

```bash
sudo apt install catdoc
```

## Notas operativas

- El proceso registra errores por archivo sin detener toda la corrida.
- Se soporta ejecución parcial (`--no-process`, `--no-unify`) según necesidad operativa.
- Los archivos procesados pueden ser renombrados y archivados para trazabilidad histórica.

## Control de versiones

El control de versiones de esta capa se administra en la raíz del repositorio:

- `CHANGELOG.md`
- `vX.Y.Z` (marcador de versión actual)

No se mantiene changelog local dentro de `extract/`.
