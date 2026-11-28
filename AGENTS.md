# AGENTS.md

## 1. Propósito

Estas instrucciones establecen las políticas de trabajo para los agentes que intervienen en el repositorio. Son aplicables a las tareas de análisis, desarrollo, mantenimiento, pruebas y documentación.

Priorizar la precisión, la simplicidad, la seguridad, la eficiencia y la mantenibilidad.

## 2. Gestión de tareas

- Consultar `TODO.md` antes de iniciar cualquier evolución.
- Respetar las prioridades, dependencias, decisiones y criterios de aceptación establecidos.
- Ejecutar exclusivamente la tarea o paquete de trabajo autorizado.
- No avanzar automáticamente hacia otras tareas.
- No modificar decisiones previamente acordadas sin autorización.
- Actualizar `TODO.md` al finalizar cada tarea, registrando resultados, evidencias y progreso.
- No marcar una tarea como completada si no satisface todos sus criterios de aceptación.
- Documentar los bloqueos y las decisiones pendientes.

## 3. Principio YAGNI (You Aren't Gonna Need It)

- Implementar únicamente lo necesario para satisfacer los requisitos actuales.
- Preferir la solución más sencilla que cumpla los requisitos.
- Reutilizar componentes existentes antes de crear otros nuevos.
- No introducir abstracciones, dependencias, configuraciones o funcionalidades para necesidades futuras hipotéticas.
- No crear mecanismos alternativos, capas de compatibilidad ni opciones adicionales sin una necesidad demostrada.
- No refactorizar código ajeno al alcance de la tarea.
- Evitar la duplicación de código y responsabilidades.
- No confundir simplicidad con reducción de controles necesarios.

## 4. Economía de tokens y recursos

- Minimizar el coste total de resolución: tokens, tiempo, recursos computacionales, complejidad y mantenimiento.
- Realizar búsquedas dirigidas antes de leer archivos completos.
- Consultar únicamente los archivos y fragmentos relevantes para la tarea.
- Evitar exploraciones exhaustivas del repositorio salvo que estén justificadas por el alcance.
- Reutilizar análisis, resultados y evidencias existentes cuando sigan siendo válidos.
- Evitar lecturas repetidas de archivos que no hayan cambiado.
- Limitar la salida de comandos, pruebas y logs a la información relevante.
- No reproducir archivos completos ni bloques de código que no hayan sido modificados, salvo solicitud expresa.
- Generar respuestas e informes concisos, sin introducciones innecesarias ni reiteraciones.
- No repetir pruebas innecesariamente si el código y las condiciones evaluadas no han cambiado.
- No ampliar el alcance de una tarea sin autorización.

La economía de recursos nunca debe comprometer la corrección, la seguridad, la integridad de los datos ni la calidad de las validaciones.

## 5. Calidad de ingeniería

- Respetar la arquitectura, las convenciones y los contratos de datos existentes.
- Priorizar soluciones seguras, comprobables, reproducibles, mantenibles e idempotentes cuando corresponda.
- Fundamentar las optimizaciones en mediciones y evidencias.
- Distinguir hechos observados, hipótesis, inferencias y recomendaciones.
- No inventar resultados, métricas, rutas, configuraciones ni estructuras de datos.
- Evaluar las consecuencias de los cambios sobre las demás etapas del pipeline.
- Preservar las garantías de persistencia, integridad, trazabilidad y archivado.
- Mantener separadas las responsabilidades de extracción, transformación, carga y auditoría.
- No introducir validaciones clínicas ni de coherencia clínica o matemática en el pipeline ETL. Los controles del ETL deben centrarse en la calidad técnica de los datos.

## 6. Pruebas y validación

- Ejecutar pruebas proporcionales al alcance y riesgo de los cambios.
- Reutilizar las pruebas existentes y añadir únicamente las necesarias.
- No eliminar ni debilitar pruebas para conseguir resultados satisfactorios.
- No afirmar que una prueba ha sido superada sin haberla ejecutado.
- Utilizar datos sintéticos, anonimizados o muestras expresamente autorizadas.
- Verificar las regresiones funcionales de los componentes afectados.
- Registrar los resultados de las pruebas y las limitaciones de la validación.

## 7. Seguridad y entornos

- Verificar el entorno, el directorio, la rama Git y el estado del repositorio antes de modificar archivos.
- Trabajar exclusivamente en DEV y en la rama autorizada.
- No modificar datos, archivos, configuraciones ni infraestructura de PRD.
- No acceder, copiar, exponer ni versionar credenciales o datos personales innecesariamente.
- No ejecutar operaciones destructivas o irreversibles sin autorización expresa.
- No modificar archivos ajenos a la tarea ni revertir cambios realizados por otros.
- No realizar commits, push, merge, rebase ni despliegues sin autorización expresa.
- Mantener fuera del control de versiones los datos clínicos, credenciales, logs y archivos temporales.

## 8. Documentación y comunicación

- Utilizar español para informes, documentación funcional y comunicación con el usuario.
- Respetar las convenciones existentes para identificadores, código y nombres de archivos.
- Documentar las decisiones relevantes y sus fundamentos.
- Mantener la documentación sincronizada con el comportamiento real del código.
- No duplicar información entre documentos sin necesidad.
- Presentar los resultados indicando cambios realizados, archivos afectados, pruebas, evidencias, riesgos y pendientes.
- Informar de cualquier desviación respecto a los requisitos o decisiones previamente acordados.

## 9. Responsabilidad de los documentos

- `AGENTS.md`: políticas permanentes de trabajo.
- `TODO.md`: evoluciones, prioridades, dependencias, criterios de aceptación y seguimiento.
- `README.md`: descripción, arquitectura e instrucciones de uso del proyecto.
- `docs/`: documentación técnica, informes y evidencias cuando sean necesarios.

No modificar estas políticas sin autorización del responsable del proyecto.

## 10. Versionado y publicación

- Aplicar versionado semántico (MAJOR.MINOR.PATCH).
- Incrementar MAJOR cuando se introduzcan cambios incompatibles en contratos de datos, interfaces o comportamiento público.
- Incrementar MINOR cuando se incorporen funcionalidades compatibles con la versión anterior.
- Incrementar PATCH cuando se introduzcan correcciones u optimizaciones compatibles.
- No incrementar la versión por cambios exclusivamente documentales, diagnósticos, benchmarks o pruebas.
- Distinguir entre commit, evolución completada, paquete de trabajo completado y publicación de una versión.
- No incrementar automáticamente la versión al completar una evolución.
- Evaluar el incremento de versión al completar un paquete de trabajo o alcanzar un hito funcional.
- Identificar y respetar el archivo de marcado de versión existente en el repositorio como fuente de verdad.
- No crear archivos adicionales de versionado ni duplicar el número de versión innecesariamente.
- Al proponer una nueva versión, justificar el incremento según los cambios acumulados y su compatibilidad.
- Actualizar el archivo de marcado de versión únicamente cuando el incremento haya sido autorizado.
- Mantener coherencia entre el marcador de versión, las referencias documentales existentes y las etiquetas Git.
- Registrar los cambios funcionales, incompatibilidades y requisitos de migración de cada versión.
- No crear etiquetas Git, releases ni desplegar versiones sin autorización expresa.
- No modificar retrospectivamente versiones publicadas ni sus etiquetas Git.
- Verificar las pruebas, los criterios de aceptación y el estado del repositorio antes de publicar una versión.

## Principio rector

Precisión antes que suposición. Evidencia antes que especulación. Simplicidad justificada antes que complejidad. Eficiencia sin comprometer la seguridad ni la integridad de los datos.