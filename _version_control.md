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
