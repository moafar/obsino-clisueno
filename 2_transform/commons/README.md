# Commons (`transform`)

## Guía rápida de ejecución

Contexto: `commons` no se ejecuta directo; se usa a través de un pipeline de `transform`.

```bash
source ../../.venv/bin/activate

# Ejemplo de ejecución indirecta desde PSG:
cd ../psg
../../.venv/bin/python main.py --input input/unificado_basal.csv
```

Módulos compartidos para pipelines declarativos de `transform`.

## Estructura

- `io/`: lectura y escritura de datasets (`xlsx`, `csv`).
	- Incluye utilidades de resolución de rutas y convención de salida automática (`<input>_ready-to-load`).
- `schema/`: validación de esquemas de entrada/salida.
- `engine/`: motor declarativo para ejecutar pasos de transformación.
- `ops/`: operaciones reutilizables registrables en el motor.
- `logging/`: utilidades de logging unificado.
- `errors/`: excepciones comunes tipadas.

## Estado

Componentes en uso por los pipelines de `transform`.

- El motor y validadores se ejecutan desde los entrypoints de cada pipeline.
- Las operaciones de dominio se registran por pipeline sobre este núcleo compartido.

## Uso rápido

| Componente | Uso en pipeline |
|---|---|
| `io` | Lectura/escritura y construcción de rutas de salida. |
| `schema` | Validación de contratos de entrada y salida. |
| `engine` + `ops` | Ejecución de `steps` declarativos y registro de operaciones. |
| `logging` + `errors` | Trazabilidad y manejo unificado de errores. |
