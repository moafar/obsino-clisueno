# Extractor de Informes de laboratorio de sueño

Este proyecto permite extraer información estructurada desde archivos `.docx` de informes clínicos como AUTO CPAP, POLIGRAFÍA y ACTIGRAFÍA.

## 📁 Estructura del proyecto

```
extractor_sueno/
├── README.md
├── requirements.txt
├── main.py                        # Punto de entrada del proyecto
│
├── src/                           # Lógica principal
│   ├── __init__.py
│   ├── extractor.py               # Función para procesar archivos
│   └── processor_autocpap.py      # Extracción específica por tipo
│
├── utils/                         # Funciones auxiliares
│   ├── __init__.py
│   └── logger.py                  # Configuración de Loguru
│
├── input/                         # Archivos .docx a procesar
│
├── output/                        # Resultados exportados (CSV, Excel)
│   └── resultados.csv
│
├── logs/                          # Logs de errores de ejecución
```

## ▶️ Cómo ejecutar

1. Instala las dependencias:

```bash
pip install -r requirements.txt
```

2. Ejecuta el script pasando el directorio con archivos `.docx`:

```bash
python extractor_base.py --input ./informes
```

> Los resultados se guardan en `resultados.csv`.

## 🛠 Dependencias

- `python-docx`: Lectura de documentos `.docx`
- `pandas`: Estructura y exportación de datos
- `tqdm`: Barra de progreso
- `loguru`: Logging avanzado
- `python-dateutil`: Manejo de fechas
- `openpyxl`: Exportación opcional a Excel

## 📒 Notas

- Se crean logs automáticos por día en la carpeta `logs/`.
- Si un archivo presenta errores, se omite y se registra el incidente sin detener el proceso.
- Se puede extender fácilmente para nuevas estructuras de informes.

## 📌 Autor

Proyecto desarrollado para la CLÍNICA DE SUEÑO – Instituto Neumológico del Oriente.
