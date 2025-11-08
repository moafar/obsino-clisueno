# v.3.1.0 -- Notas de versión — 2025-11-08

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
