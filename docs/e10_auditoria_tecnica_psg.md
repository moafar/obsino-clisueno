# E10 — Retirada de controles clínicos del auditor

Se retiraron del auditor PSG los avisos por porcentajes clínicos fuera de 0–100, recuentos/duraciones/índices negativos y relaciones entre medidas: tiempo de sueño frente a tiempo en cama, SpO₂ mínima frente a media y jerarquía entre umbrales de desaturación. Esas reglas no se trasladaron a advertencias ETL.

Permanecen los controles **técnicos**: esquema y número de filas, tipos y finitud numérica según YAML, UUID, porcentaje declarado de completitud, fechas e ID ausentes/ilegibles, inventario, archivado y trazabilidad. Los valores clínicos fuera de rangos habituales pueden conservarse como datos si son técnicamente válidos; su interpretación corresponde a análisis posteriores fuera del ETL. La derivación T90 del transformador conserva una comprobación de dominio de su propia operación, no alterada en E10; si se decide retirar o cambiar esa derivación, requiere una evolución autorizada.
