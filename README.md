# Extractor de Informes de laboratorio de sueño

Este proyecto permite extraer información estructurada desde archivos de informes clínicos de Laboratorio de Sueño

## Activar venv
source venv/bin/activate

## Instalar dependencias
pip install -r requirements.txt

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

Ojo!  Hay una dependencia adicional del sistema (no es de Python): `catdoc`
Se instala con `sudo apt install catdoc`

2. Ejecuta el script pasando el directorio correspondiente:

```bash
python main.py 'ruta/de/la/carpeta/a/procesar'
```

> Los resultados se guardan en `resultados.csv`.

## 🛠 Dependencias

- `argparse` : Lectura de argumentos
- `python-docx`: Lectura de documentos `.docx`
- `pandas`: Estructura y exportación de datos
- `tqdm`: Barra de progreso
- `logging`: Logging avanzado
- `python-dateutil`: Manejo de fechas
- `openpyxl`: Exportación opcional a Excel

## 📒 Notas

- Se crean logs para:
    - Inicio del proceso
    - Errores de directorio
    - Inicio de un nuevo subdirectorio
    - Errores de subdirectorio
    - Inicio de procesamiento de archivo
    - Compatibilidad de archivo con la extracción
    - Error en la extracción de un dato, incluyendo texto procesado
    - Procesamiento exitoso de un archivo
    - Fin del proceso
- Si un archivo presenta errores, se omite y se registra el incidente sin detener el proceso.
- Se puede extender fácilmente para nuevas estructuras de informes.

## 📌 Autor
Rafael Ortiz - ortizmartinez64gmail.com
Proyecto desarrollado para el Instituto Neumológico del Oriente.
2025
