# E02 — Benchmark de entornos de ejecución del extractor PSG

**Fecha:** 2026-11-28. **Revisión de código medida:** `d64afa3`, rama DEV `integration/psg-evoluciones`, versión marcada `v5.0.1`. No se cambió código funcional ni el marcador de versión. Las mediciones proceden de [e02_mediciones.json](e02_mediciones.json); el generador y lanzador reproducible es [e02_benchmark.py](e02_benchmark.py), que reutiliza [e01_perfil_extractor.py](e01_perfil_extractor.py).

## Entornos evaluados

| Entorno | Estado | Evidencia y delimitación |
|---|---|---|
| WSL2 sobre ext4 | **Medido** | `/tmp` sobre `/dev/sdd` ext4, mismo WSL2 Linux 6.6.87.2 y Python 3.12.3 de `.venv`. |
| WSL2 sobre NTFS | **Medido** | Directorios temporales aislados bajo `/mnt/c/Users/ROM/AppData/Local/Temp`; DrvFs/9p en WSL, respaldado por `C:` NTFS según `Get-Volume`. El acceso de escritura requirió ejecutar el benchmark fuera del aislamiento del agente. |
| WSL2 sobre `/mnt/e` | **No medido** | `E:` aparece como unidad Windows, pero `findmnt -T /mnt/e` resolvió a `/` ext4: no estaba montada en WSL. No se montó ni se escribió en esa unidad. La medida de `C:` demuestra el comportamiento de **este** volumen NTFS, no el de `E:`. |
| Windows nativo | **No medido** | PowerShell 5.1 funcionó, pero `py` no existe y `python` es solo el alias de instalación de Microsoft Store. No había intérprete Python nativo listo para ejecutar el instrumento. Además, el extractor actual importa `fcntl` y usa primitivas POSIX; ejecutar la misma versión en Windows requeriría resolver compatibilidad, trabajo asignado a E03. |

## Método y equivalencia

Se generaron 120 RTF desde `synthetic_report("rtf")` de las pruebas existentes y 120 DOC desde `synthetic_report("doc")`, convirtiendo RTF sintéticos a DOC binario con LibreOffice 24.2.7.2 **antes** de medir. Cada documento contiene un identificador sintético distinto; ningún archivo clínico se leyó. Los RTF miden 2.674 bytes y los DOC 14.336 bytes cada uno. Para cada formato se tomaron subconjuntos fijos de 30 y 120 archivos. Los mismos bytes de cada subconjunto se copiaron a la raíz temporal del entorno antes del cronómetro.

En cada combinación formato/tamaño/entorno se lanzaron **tres procesos independientes**. El orden ext4/NTFS se alternó en la segunda repetición. El instrumento mide `perf_counter` durante la orquestación completa PSG en modo `test` (incluye configuración, carga de CSV previos, procesamiento, archivado y auditoría), `process_time` para CPU y `ru_maxrss` para RSS máximo. Generación de fixtures, copia de entrada y verificación final están fuera del tiempo de pared. Los temporales se eliminan al terminar. El coste de arranque de Python y de conversión DOC tampoco entra en el tiempo medido. Los tiempos de fase del instrumento son inclusivos y no deben sumarse entre sí.

En las **24 ejecuciones** hubo salida 0, 30/120 filas según lote, el mismo número de archivos archivados y auditoría `OK`. Los SHA-256 del corpus de entrada coinciden por formato/tamaño. También coincidieron entre todos los entornos y repeticiones los SHA-256 de las filas CSV ordenadas por UUID, excluyendo solo `meta_fuente` (ruta temporal) y `meta_version_control` (hora de ejecución), y los SHA-256 de nombres y contenido de archivos archivados. Esto acredita equivalencia del resultado extraído comparable y del contenido archivado para estas muestras sintéticas; no equivale a una prueba de seguridad del protocolo de movimiento ni cubre documentos clínicos reales.

Reproducción, desde la raíz del repositorio y con permiso de escritura **solo** sobre un temporal NTFS autorizado:

```bash
.venv/bin/python docs/e02_benchmark.py --probe-doc
.venv/bin/python docs/e02_benchmark.py --doc \
  --ntfs-base /mnt/c/Users/ROM/AppData/Local/Temp \
  --sizes 30 120 --repeats 3 --output docs/e02_mediciones.json
```

El segundo comando rehace el corpus y sobrescribe el JSON de resultados; los tiempos fluctuarán con la carga y caché de disco. El JSON conserva las 24 observaciones, tiempos de fases, CPU/RSS y huellas, sin rutas ni contenidos individuales. La prueba de DOC de un archivo terminó con fila, archivado y auditoría `OK` antes de ejecutar la matriz.

## Resultados medidos

La columna de tiempo muestra las **tres observaciones** y la mediana entre paréntesis. El rendimiento es tamaño del lote dividido por la mediana. CPU es la mediana; RSS, el intervalo observado. Ambos sistemas usaron el mismo proceso Linux y la misma instalación Python.

| Formato | Lote | Entorno | Pared, s (mediana) | Documentos/s | CPU, s | RSS máx., MiB |
|---|---:|---|---|---:|---:|---:|
| RTF | 30 | ext4 | 0,194 / 0,198 / 0,219 (**0,198**) | 151,1 | 0,143 | 37,8–38,0 |
| RTF | 30 | NTFS/DrvFs | 1,533 / 1,469 / 1,363 (**1,469**) | 20,4 | 0,255 | 37,4–37,5 |
| RTF | 120 | ext4 | 0,597 / 0,643 / 0,594 (**0,597**) | 201,0 | 0,415 | 39,8–40,0 |
| RTF | 120 | NTFS/DrvFs | 5,219 / 5,263 / 5,388 (**5,263**) | 22,8 | 0,858 | 39,6–39,9 |
| DOC | 30 | ext4 | 0,260 / 0,232 / 0,239 (**0,239**) | 125,7 | 0,149 | 37,7–37,9 |
| DOC | 30 | NTFS/DrvFs | 1,549 / 1,571 / 1,491 (**1,549**) | 19,4 | 0,267 | 37,5–37,6 |
| DOC | 120 | ext4 | 0,790 / 0,783 / 0,789 (**0,789**) | 152,1 | 0,469 | 39,3–39,8 |
| DOC | 120 | NTFS/DrvFs | 5,619 / 5,768 / 6,016 (**5,768**) | 20,8 | 0,929 | 39,3–39,6 |

En las medianas, NTFS/DrvFs tardó **7,40× y 8,82×** más que ext4 para 30 y 120 RTF; **6,49× y 7,31×** para DOC. La CPU del proceso creció menos que el tiempo de pared y el RSS fue similar, compatible con más espera en operaciones de archivo; no se midió por separado la actividad del host Windows.

Fases inclusivas, medianas de los lotes de **120** documentos (segundos):

| Formato/entorno | Procesamiento | Escritura CSV | `fsync` dentro de CSV | Lectura/conversión | Parser | Archivado | Auditoría | MD5 en auditoría |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| RTF/ext4 | 0,527 | 0,223 | 0,206 | 0,065 | 0,164 | 0,036 | 0,043 | 0,003 |
| RTF/NTFS | 3,768 | 0,457 | 0,161 | 0,273 | 0,397 | 1,938 | 1,391 | 0,306 |
| DOC/ext4 | 0,718 | 0,244 | 0,224 | 0,168 | 0,214 | 0,042 | 0,045 | 0,004 |
| DOC/NTFS | 4,261 | 0,500 | 0,188 | 0,461 | 0,502 | 2,023 | 1,455 | 0,320 |

En NTFS/DrvFs, el tiempo observado se concentra en archivado, auditoría y operaciones de lectura; `fsync` medido **no** explica por sí mismo la diferencia. Los tiempos de MD5 incluyen abrir y leer el archivo del entorno correspondiente. La medición no distingue si `renameat2` o su ruta de respaldo se usó en cada traslado; E03 debe verificarlo. Tampoco establece equivalencia de persistencia entre sistemas de archivos.

## Límites e insumos para E03

- **Windows nativo:** sin Python nativo disponible y con imports POSIX (`fcntl` en `main.py` y `archivo_utils.py`), no se ejecutó allí el extractor ni se intentó instalar dependencias o alterar el código. E03 debe evaluar `catdoc`, bloqueo, `renameat2` y operaciones con descriptores de directorio antes de considerar esa plataforma.
- **DOC:** los DOC fueron creados por LibreOffice desde una plantilla sintética; `catdoc` procesó los 30/120 DOC en ambos sistemas WSL y las filas comparables coincidieron. Falta contrastar texto bruto y formatos DOC representativos, propio de E03.
- **NTFS:** se midió `C:` y no `/mnt/e`. No se infiere el rendimiento de `E:` ni de otros montajes, antivirus, caché o políticas de Windows. No se modificaron datos existentes en la unidad; solo se crearon y retiraron directorios temporales de prueba.
- **Seguridad:** el éxito de las auditorías sintéticas confirma la conciliación del caso normal. No prueba comportamiento ante fallos, concurrencia, cortes de energía, enlaces o colisiones. Ninguna garantía de `fsync`, `flock` o archivado se ha suprimido ni cambiado.

E02 aporta la comparación disponible y deja la evaluación de compatibilidad y la decisión de arquitectura para E03–E04. No hay recomendación de migración de entorno basada solo en este benchmark.
