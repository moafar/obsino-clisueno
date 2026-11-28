# E13 — Estadísticas lógicas de completitud en el informe PSG

La tabla por variable usa la unión de los indicadores lógicos de E06–E07, sin metadatos ni filas separadas para meses/días. Edad se marca presente cuando cualquiera de sus tres componentes tiene valor; `0` cuenta. Para cada formato, el denominador de una variable aplicable es el número de filas de ese formato; un indicador exclusivo del otro formato muestra `—`.

La tabla por sección cuenta campos aplicables por formato: DOC **124** y RTF **129** en el total, distribuidos como en E06. Su denominador es `número de filas del formato × indicadores aplicables de la sección`. Se muestran numerador, denominador y porcentaje. La distribución por formato presenta mínimo, P50, P90 y máximo de `meta_completitud_pct` **solo para filas cuyo valor superó el recálculo técnico**; indica cuántas puntuaciones entraron. P50 y P90 usan interpolación lineal entre posiciones ordenadas `0..n-1`. Los formatos desconocidos no reciben porcentaje y siguen causando discrepancia de recálculo.

**Pruebas sintéticas:** una fila DOC y una RTF verifican edad única, ceros presentes, campos exclusivos como no aplicables, secciones con denominadores propios y puntuaciones 2,42 % y 3,10 %. Una prueba aislada verifica P90=90 para `[0, 50, 100]` y un único valor. Estas estadísticas describen presencia técnica, sin validar plausibilidad clínica.
