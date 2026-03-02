# v4.0.2 -- Ajustes de versionado, rutas y contrato compartido

**Fecha:** 2026-03-02

## Resumen ejecutivo

Esta versión corrige y consolida el gobierno de versionado posterior a `v4.0.1`, y documenta ajustes operativos que mejoran portabilidad entre entornos.

Se elimina dependencia de rutas absolutas en configuración/ejecución del flujo ETL, reforzando resolución relativa al proyecto y consumo declarativo de contrato compartido.

## Cambios incluidos

### 1) Gobierno de versión

- Se actualiza el archivo marcador de versión en raíz a `v4.0.2`.
- Se mantiene el versionado exclusivamente en `CHANGELOG.md` (sin versión explícita en `README.md`).
- Se preserva la entrada histórica de `v4.0.1` sin sobrescribirla.

### 2) Eliminación de rutas absolutas (portabilidad)

- Se estandariza el uso de rutas relativas al proyecto en comandos y configuración operativa.
- `3_load/main.py` resuelve insumos con `BASE_DIR` + rutas relativas (`config`, `secrets`, `schema`, `input`).
- `2_transform` incorpora resolución por bases de búsqueda (`cwd`, raíz proyecto, raíz de capa) para config/input/output.

### 3) Contrato compartido y resolución declarativa de schema

- `3_load/config/psg.yaml` consume contrato desde `0_declarations/psg.yaml` vía `shared_schema_yaml_path`.
- `3_load` soporta selector declarativo `schema_path_in_yaml` (actual: `schema.load.input.columns`).
- `2_transform/psg/config.yaml` resuelve input/output schema desde el mismo contrato compartido en `0_declarations`.

### 4) Ajustes operativos de ejecución

- `3_load` mantiene ejecución por `--flow` y admite Excel por `--input` o argumento posicional.
- Se refuerza la documentación por capa (`0_declarations`, `2_transform`, `3_load`) alineando ejemplos y convención de rutas.

---

# v4.0.1 -- Orden de capas, contrato compartido y ajuste de versionado

**Fecha:** 2026-03-01

## Resumen ejecutivo

Esta versión consolida mejoras de claridad operativa y gobierno de configuración sin cambiar el comportamiento funcional del pipeline ETL.

Se ordenó la estructura raíz por secuencia de ejecución, se centralizó el contrato de schemas compartidos y se alineó la documentación/versionado con esa estructura.

---

## Cambios incluidos

### 1) Estructura de carpetas ordenada por flujo

Se renombraron carpetas raíz para reflejar explícitamente el orden operativo:

- `0_declarations/`
- `1_extract/`
- `2_transform/`
- `3_load/`

Con esto, la navegación del repositorio muestra de forma inmediata la secuencia esperada del proceso.

### 2) Contrato de schema compartido fuera de las capas

Se consolidó el contrato PSG en `0_declarations/psg.yaml` con secciones explícitas por capa:

- `schema.transform.input.columns`
- `schema.transform.output.columns`
- `schema.load.input.columns`

Además, se dejó explícita la equivalencia entre capas:

- `schema.load.input.columns` reutiliza el mismo bloque que `schema.transform.output.columns`.

### 3) Ajustes de configuración y ejecución

- `2_transform/psg/config.yaml` ahora consume input/output schema desde `0_declarations/psg.yaml`.
- `3_load/config/psg.yaml` consume `schema.load.input.columns` desde el mismo contrato compartido.
- `3_load/main.py` actualizó rutas internas para resolver configuración en la nueva estructura numerada.

### 4) Documentación y gobierno

- Se actualizaron README de raíz y por capa para reflejar nuevas rutas, comandos y convención de orden.
- Se ajustó `CHANGELOG.md` para mantener coherencia con nombres de carpetas actuales.
- Se actualiza archivo marcador de versión en raíz a `v4.0.1`.

---

# v4.0.0 -- Consolidación ETL en 3 capas y gobierno central del proyecto

**Fecha:** 2026-02-28

## Resumen ejecutivo

Esta versión marca una evolución mayor del proyecto: se pasó de un foco operativo concentrado en extracción (`extract`) a una arquitectura ETL completa con tres capas explícitas y desacopladas (`extract`, `transform`, `load`).

Además, se centralizó el gobierno documental y de versionado en la raíz del repositorio para que el control de cambios aplique al sistema completo y no a una sola capa.

---

## Decisiones de arquitectura tomadas

1. **Separación explícita por capas ETL**
  - Se formalizó la responsabilidad de cada capa:
    - `extract`: extracción y normalización inicial desde documentos fuente.
    - `transform`: transformación declarativa por pipeline (pipeline activo: `psg`).
    - `load`: carga manual a BigQuery con controles operativos.
  - Se evitó acoplar lógicas entre capas para mantener evolución independiente.

2. **Diseño compartido en `3_load` (sin multiplicar código por flujo)**
  - Se descartó replicar estructura por flujo cuando la lógica era la misma.
  - Se adoptó una sola implementación (`3_load/main.py`) con configuración declarativa por flujo en YAML.

3. **Despacho de configuración por flujo con rutas fijas**
  - Se implementó selección por CLI (`--flow`).
  - Cada flujo se resuelve a un YAML predefinido (sin ruta libre por parámetro), priorizando control operativo y reducción de errores de ejecución.

4. **Carga manual y confirmada para BigQuery**
  - Se eliminó el patrón HTTP/Cloud Function heredado para esta etapa.
  - La ejecución es manual por consola con impresión de configuración y confirmación explícita del operador antes de cargar.

5. **Centralización del versionado en la raíz del repositorio**
  - El `CHANGELOG` y el archivo marcador de versión se gestionan globalmente.
  - Se eliminó el manejo aislado de versión dentro de `extract`.

---

## Cambios funcionales relevantes

### A) Capa `load`

- Migración de lógica heredada a script manual integrado:
  - validación de duplicados dentro del lote.
  - validación de duplicados contra la tabla destino en BigQuery (modo `WRITE_APPEND`).
- Incorporación de configuración declarativa por YAML de flujo.
- Reestructuración de carpeta (`3_load` aplanada; se eliminó subcarpeta `uploader`).
- Estandarización de secretos: credenciales en `3_load/secrets/`.
- Eliminación de artefactos legacy (`bq_carga_manual.py` y enfoque HTTP para esta capa).

### B) Capa `transform`

- Unificación de documentación en un único README de capa.
- Eliminación de README duplicado dentro de `2_transform/psg` para evitar divergencias documentales.

### C) Capa `extract`

- Conserva su rol de capa de origen del pipeline.
- Se armonizó documentación para integrarse al modelo ETL completo.

### D) Gobierno documental del repositorio

- Creación/actualización de README global del proyecto con descripción de las tres capas.
- Armonización de README por capa (`1_extract`, `2_transform`, `3_load`) con estructura homogénea.

---

## Nueva arquitectura (alto nivel)

```text
clisueno/
  README.md
  CHANGELOG.md
  v4.0.0
  1_extract/
  2_transform/
  3_load/
   main.py
   config/
    psg.yaml
   secrets/
```

Flujo operativo:

1. `1_extract` genera dataset base.
2. `2_transform` aplica reglas declarativas y produce dataset estandarizado.
3. `3_load` valida y carga manualmente a BigQuery.

---

## Impacto / compatibilidad

- **Cambio mayor (`major`)** por reorganización estructural y operacional del proyecto.
- Se modifica el punto de gobierno de documentación/versionado (de subcapa a raíz).
- Para `load`, cambia el modelo de ejecución esperado a consola + YAML por flujo (`--flow`).

---

## Guía de operación de versión a partir de v4

- Registrar cambios del sistema completo en `CHANGELOG.md` (raíz).
- Actualizar el archivo marcador `vX.Y.Z` en raíz en cada liberación.
- Mantener los README de capa alineados con el README global.

---

# v3.3.1 -- Tagging de versionamiento
A partir de ahora se manejan las versiones con tags de Git

# v3.3.0 -- Alineación de scripts de extracción y de upload
**Fecha:** 2025-12-21

Archivos tocados:
- archivo_utils.py
- procesar_basal.py
- procesar_xpap.py
- subir_basal_stg.py
- subir_xpap_stg.py

## Novedades
1. En procesar_xxx.py: se inserta el marcado de versión de extracción; cada registro se marca al momento de extraer con fecha/hora. Se añaden `fuente`, `uuid` y `version_control` al retorno de cada función.
2. En subir_xxx_stg.py:
   - Se definen columnas y tipos de entrada acordes a la nueva exportación (`fuente`, `uuid`, `version_control`).
   - Se ajustan las columnas de salida en el `rename_map`.
   - Las variables porcentuales se normalizan a decimales (siempre suben como 0.xx).
   - Se reordenan columnas para dejar juntos datos calculados del paciente y los extraídos.

---
# v3.2.1 -- Robustez en hashing, prefijos y archivado

**Fecha:** 2025-12-21

## Novedades
1. **Hash determinista multiplataforma:** `generar_hash_archivo()` normaliza finales de línea (LF/CRLF) antes del MD5, evitando UUID distintos por diferencias de EOL entre Windows/Linux.  
2. **Prefijos compuestos consistentes:** Se estandariza el orden y concatenación de prefijos múltiples (ej. `bs_xp_cp_`) garantizando nombres únicos y legibles cuando un mismo archivo atraviesa más de dos pipelines.  
3. **Archivado resiliente con trazabilidad:** Al faltar `fecha_estudio`, el archivo se mueve a `procesados/sin_fecha/` y se registra en log la causa, sin abortar el lote.  
4. **Resumen operativo por mes:** Al final del pipeline se agrega un reporte de conteo de archivos archivados por `YYYY-MM` y totales sin fecha, visible en consola y log.  
5. **CLI y códigos de salida afinados:** `--dry-run` valida rutas y permisos sin mover archivos; fallos de movimiento retornan códigos específicos y nunca borran la entrada original.  
6. **Cobertura de pruebas ampliada:** Nuevos tests para hashing normalizado, prefijos múltiples, archivado con/sin fecha y fallos por permisos (se captura `PermissionError`, no se borra el original y queda registrado en log).

---
# v3.2.0 -- Deterministic processing & Archiving

**Fecha:** 2025-12-08

## Novedades

1. **UUID Determinista**:  
   Se implementó `generar_hash_archivo()` usando MD5 del contenido. Esto asegura que si se reprocesa el mismo archivo, el UUID generado sea idéntico, evitando duplicados lógicos en la base de datos de destino.

2. **Renombrado Inteligente (Prefijos)**:  
   Los archivos procesados ahora reciben un prefijo según su tipo:
   - `bs_` para Basal
   - `xp_` para XPAP
   - Archivos con múltiples procesamientos (ej. Basal + CPAP) recibirán ambos prefijos (ej. `bs_xp_archivo.rtf`).

3. **Estrategia de Archivado**:  
   Se elimina el archivo de la carpeta de entrada y se mueve automáticamente a:
   `procesados/YYYY-MM/`
   La fecha (Año-Mes) se extrae del contenido del informe (`fecha_estudio`). Si no se detecta, va a `procesados/sin_fecha/`.

---
# v3.1.1 -- Notas de refactoring - módulo principal y unificación

**Fecha:** 2025-11-09 21:40:36

## 1. Objetivo general
Reorganizar la lógica principal (`main.py`) para hacer el flujo más legible, escalable y robusto.  
Separar responsabilidades, mejorar el manejo de errores y permitir la extensión futura del pipeline.

---

## 2. Cambios estructurales principales

### 2.1 Nueva organización modular
Se crearon funciones específicas para cada responsabilidad:
- `parse_args()` → Manejo de argumentos CLI.
- `load_config()` → Carga y validación del archivo YAML.
- `setup_logging_from_config()` → Configura el logging según YAML o `--verbose`.
- `resolve_input_dir()` → Determina la ruta de entrada desde CLI o YAML y valida su existencia.
- `run_processing()` → Ejecuta el procesamiento de archivos y mide el tiempo.
- `report()` → Imprime y registra resultados del procesamiento.
- `maybe_unify()` → Llama a `analizar_y_unificar()` si existe una carpeta de salida definida.
- `orchestrate()` → Punto central que coordina todas las etapas y maneja excepciones.
- `main()` → Simple envoltorio con `sys.exit(orchestrate())`.

---

## 3. Cambios funcionales

### 3.1 Flujo principal
1. Cargar configuración YAML (`load_config`).
2. Configurar logging.
3. Validar ruta de entrada (`resolve_input_dir`).
4. Procesar directorio (`run_processing`).
5. Mostrar resumen (`report`).
6. Ejecutar análisis y reporte final (`maybe_unify`).

### 3.2 Manejo de errores
Se centralizaron excepciones con códigos de salida específicos:
- `EXIT_CFG` → error de configuración.
- `EXIT_INPUT` → error en la entrada.
- `EXIT_PROCESS` → error en el procesamiento.
- `EXIT_UNIFY` → error en la unificación.

### 3.3 Flags CLI nuevos
- `--no-process`: salta la fase de procesamiento.
- `--no-unify`: salta la fase de unificación.
- `--dry-run`: valida configuración sin ejecutar efectos.

---

## 4. Comportamiento actual de la unificación

`maybe_unify()` invoca `analizar_y_unificar(carpeta_csv)`, que:
- **No genera nuevos CSV.**
- Produce **un reporte Markdown** (`reporte_analisis_<timestamp>.md`) que resume diferencias de columnas entre CSV existentes.
- Agrupa por tipo de examen (basal, xpap, dam...) usando la función `_family_from_filename`.

### Estructura de salida actual
```
output/
├── basal.csv
├── xpap.csv
├── dam.csv
└── reporte_analisis_YYYY-MM-DD_HH-MM-SS.md
```

---

## 5. Beneficios logrados

- 🔹 Código más legible y modular.
- 🔹 Manejo de errores unificado y explícito.
- 🔹 Extensible: se pueden insertar fácilmente nuevas fases (p.ej. validación o carga a BigQuery).
- 🔹 Logging coherente y controlado.
- 🔹 CLI flexible para pruebas parciales y ejecución completa.

---

**Autor:** Refactoring automático asistido por ChatGPT  
**Proyecto:** `obsino-clisueno`  
**Versión:** Refactor main + análisis CSV (2025)

---
---

# v3.1.0 -- Notas de versión — 2025-11-08

## Cambios implementados

### 1. Salidas unificadas por tipo de examen
- Se eliminó la generación del archivo genérico `unificado.csv`.
- Ahora el sistema produce **un CSV unificado independiente por tipo de examen**, por ejemplo:
  - `unificado_basal.csv`
  - `unificado_xpap.csv`
- Cada archivo acumula los resultados procesados de ese tipo, manteniendo encabezados consistentes y sin duplicados.

### 2. Integración con el flujo principal
- El módulo `analizar_y_unificar()` dejó de ejecutarse como script independiente.
- Ahora se invoca **exclusivamente desde `main.py`** al final del procesamiento, después de generar los CSVs por tipo.
- Esto asegura un flujo ordenado y registro completo en el mismo log del proceso principal.

### 3. Reporte Markdown automático
- El análisis posterior (`analizar_y_unificar`) genera **siempre un reporte en formato Markdown**, sin crear CSVs adicionales.
- El nombre del reporte se genera automáticamente con timestamp, por ejemplo:
  `reporte_analisis_2025-11-08_14-32-11.md`
- Incluye:
  - Número y tipo de archivos analizados
  - Columnas faltantes o adicionales por grupo
  - Mapa de faltantes por columna (indica en qué archivos se producen)
  - Listado completo de columnas detectadas por archivo

### 4. Limpieza y coherencia del código
- Se eliminaron banderas y parámetros innecesarios (`escribir_salida`, `escribir_resumen_columnas_csv`, etc.).
- El código quedó reducido a una función clara y determinista:

```python
analizar_y_unificar(carpeta: str) -> str
```
  que devuelve únicamente la ruta del reporte generado.
  
- Los mensajes en consola y log se simplificaron:
  solo se muestra el resumen final (“Reporte generado” y “Análisis completado”).

### 5. Ajustes en `main.py`
- Se actualizó la llamada a:

```python
archivo_reporte = analizar_y_unificar(carpeta_csv)
logging.info(f"Reporte de análisis generado: {archivo_reporte}")
```
- Ya no se hace referencia a “unificado.csv”.


# v.3.0.3
Ajuste de basal/procesar_subir.py para coincidir con la nueva estructura de la tabla (incluyendo t90, t80 y t70)

# v.3.0.2
Ajuste de basal/procesar_basal.py para extraer valores de oximetria para calculo de t70, t80 y t90 

# v.3.0.1
Ajste del script de extracción para unificar archivos de resultados a la vez que analiza desde main.py

# v.3.0.0
Refactoring para aislar las funciones de cada examen, manteniendo el commons

## v3.3.1 - 2025-12-22

- Renombrado _version_control.md a CHANGELOG.md.
- Bump de versión de 3.3.0 a 3.3.1.
